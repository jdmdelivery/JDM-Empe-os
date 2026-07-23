"""Rutas de artículos y categorías."""

from __future__ import annotations

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_

from app.extensions import db
from app.forms.item_forms import ItemForm
from app.items import items_bp
from app.models import (
    Customer,
    Deliverer,
    EvidenceFile,
    Item,
    ItemCategory,
    ItemImage,
    OperationException,
)
from app.services.audit_service import log_action
from app.services.category_seed import seed_item_categories
from app.services.file_storage import save_upload
from app.services.numbering import next_item_code
from app.utils.decorators import permission_required
from app.utils.money import to_decimal


def _category_choices() -> list[tuple[int, str]]:
    seed_item_categories()
    cats = (
        ItemCategory.query.filter_by(is_deleted=False, is_active=True)
        .order_by(ItemCategory.sort_order, ItemCategory.name)
        .all()
    )
    return [(0, "— Seleccione —")] + [(c.id, c.name) for c in cats]


def _customer_choices() -> list[tuple[int, str]]:
    query = Customer.query.filter_by(is_deleted=False)
    if not current_user.has_role("superadmin", "auditor"):
        query = query.filter_by(branch_id=current_user.branch_id)
    return [(0, "— Opcional —")] + [
        (c.id, f"{c.code} · {c.full_name}") for c in query.order_by(Customer.first_name).limit(300)
    ]


def _deliverer_choices(customer_id: int | None = None) -> list[tuple[int, str]]:
    query = Deliverer.query.filter_by(is_deleted=False)
    if not current_user.has_role("superadmin", "auditor"):
        query = query.filter_by(branch_id=current_user.branch_id)
    if customer_id:
        query = query.filter_by(customer_id=customer_id)
    return [(0, "— Opcional —")] + [
        (d.id, f"{d.code} · {d.full_name}") for d in query.order_by(Deliverer.created_at.desc()).limit(300)
    ]


def _last_item_code() -> str | None:
    row = Item.query.order_by(Item.id.desc()).first()
    return row.code if row else None


def _find_duplicates(form: ItemForm, exclude_id: int | None = None) -> list[str]:
    alerts: list[str] = []
    checks = [
        ("serial_number", form.serial_number.data, "número de serie"),
        ("imei", form.imei.data, "IMEI"),
        ("chassis_number", form.chassis_number.data, "chasis"),
        ("plate_number", form.plate_number.data, "matrícula/placa"),
    ]
    for attr, value, label in checks:
        value = (value or "").strip()
        if not value:
            continue
        query = Item.query.filter(
            Item.is_deleted.is_(False),
            getattr(Item, attr) == value,
            Item.status.notin_(["vendido", "retirado", "eliminado_logicamente"]),
        )
        if exclude_id:
            query = query.filter(Item.id != exclude_id)
        if query.first():
            alerts.append(label)
    return alerts


@items_bp.route("/")
@login_required
@permission_required("items.view", "items.manage")
def index():
    seed_item_categories()
    q = (request.args.get("q") or "").strip()
    status = (request.args.get("status") or "").strip()
    query = Item.query.filter_by(is_deleted=False)
    if not current_user.has_role("superadmin", "auditor"):
        query = query.filter_by(branch_id=current_user.branch_id)
    if status:
        query = query.filter_by(status=status)
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Item.code.ilike(like),
                Item.serial_number.ilike(like),
                Item.imei.ilike(like),
                Item.brand.ilike(like),
                Item.model.ilike(like),
                Item.barcode.ilike(like),
            )
        )
    items = query.order_by(Item.created_at.desc()).limit(200).all()
    return render_template("items/index.html", title="Artículos", items=items, q=q, status=status)


@items_bp.route("/categories")
@login_required
@permission_required("items.view", "items.manage")
def categories():
    seed_item_categories()
    cats = ItemCategory.query.filter_by(is_deleted=False).order_by(ItemCategory.sort_order).all()
    return render_template("items/categories.html", title="Categorías", categories=cats)


@items_bp.route("/create", methods=["GET", "POST"])
@login_required
@permission_required("items.manage")
def create():
    form = ItemForm()
    form.category_id.choices = _category_choices()
    form.customer_id.choices = _customer_choices()
    form.deliverer_id.choices = _deliverer_choices()

    if form.validate_on_submit():
        if form.category_id.data == 0:
            flash("Seleccione una categoría.", "danger")
        else:
            duplicates = _find_duplicates(form)
            if duplicates and not form.authorize_duplicate.data:
                flash(
                    "Existen artículos activos con el mismo "
                    + ", ".join(duplicates)
                    + ". Se requiere autorización para continuar.",
                    "danger",
                )
            elif duplicates and form.authorize_duplicate.data:
                if not current_user.has_any_permission("exceptions.authorize") and not current_user.has_role(
                    "admin", "superadmin"
                ):
                    flash("No tiene permiso para autorizar duplicados.", "danger")
                elif not (form.duplicate_reason.data or "").strip():
                    flash("Indique el motivo de autorización del duplicado.", "danger")
                else:
                    item = _save_item(form, duplicates=True)
                    flash("Artículo creado con autorización de duplicado.", "warning")
                    return redirect(url_for("items.detail", item_id=item.id))
            else:
                item = _save_item(form, duplicates=False)
                flash("Artículo registrado correctamente.", "success")
                return redirect(url_for("items.detail", item_id=item.id))
    elif form.is_submitted():
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{field}: {error}", "danger")

    return render_template("items/form.html", title="Nuevo artículo", form=form)


@items_bp.route("/<int:item_id>")
@login_required
@permission_required("items.view", "items.manage")
def detail(item_id: int):
    item = db.session.get(Item, item_id)
    if item is None or item.is_deleted:
        abort(404)
    if not current_user.can_access_branch(item.branch_id):
        abort(403)
    evidence = EvidenceFile.query.filter_by(
        related_type="item", related_id=item.id, is_deleted=False
    ).all()
    return render_template(
        "items/detail.html",
        title=f"Artículo {item.code}",
        item=item,
        evidence=evidence,
    )


@items_bp.route("/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("items.manage")
def edit(item_id: int):
    item = db.session.get(Item, item_id)
    if item is None or item.is_deleted:
        abort(404)
    if not current_user.can_access_branch(item.branch_id):
        abort(403)

    form = ItemForm(obj=item)
    form.category_id.choices = _category_choices()
    form.customer_id.choices = _customer_choices()
    form.deliverer_id.choices = _deliverer_choices(item.customer_id)
    if not form.is_submitted():
        form.customer_id.data = item.customer_id or 0
        form.deliverer_id.data = item.deliverer_id or 0
        form.category_id.data = item.category_id or 0

    if form.validate_on_submit():
        duplicates = _find_duplicates(form, exclude_id=item.id)
        if duplicates and not form.authorize_duplicate.data:
            flash("Hay duplicados activos. Se requiere autorización.", "danger")
        else:
            _apply_item_fields(item, form)
            if duplicates and form.authorize_duplicate.data:
                item.duplicate_authorized = True
                item.duplicate_authorized_by_id = current_user.id
                item.duplicate_authorization_reason = form.duplicate_reason.data
            _attach_item_photos(item, form)
            log_action(
                action="update",
                module="items",
                record_type="item",
                record_id=item.id,
                new_value={"code": item.code, "status": item.status},
            )
            db.session.commit()
            flash("Artículo actualizado.", "success")
            return redirect(url_for("items.detail", item_id=item.id))

    return render_template("items/form.html", title="Editar artículo", form=form, item=item)


def _save_item(form: ItemForm, *, duplicates: bool) -> Item:
    branch_id = current_user.branch_id
    if branch_id is None and current_user.has_role("superadmin"):
        from app.models import Branch

        main = Branch.query.filter_by(is_main=True, is_deleted=False).first()
        branch_id = main.id if main else None
    if branch_id is None:
        raise RuntimeError("No hay sucursal asignada.")

    code = next_item_code(_last_item_code())
    item = Item(
        code=code,
        barcode=f"BC-{code}",
        qr_code=f"QR-{code}",
        branch_id=branch_id,
        received_by_id=current_user.id,
        duplicate_authorized=duplicates,
        duplicate_authorized_by_id=current_user.id if duplicates else None,
        duplicate_authorization_reason=form.duplicate_reason.data if duplicates else None,
    )
    _apply_item_fields(item, form)
    db.session.add(item)
    db.session.flush()
    _attach_item_photos(item, form)
    if duplicates:
        db.session.add(
            OperationException(
                exception_type="item_duplicate_identifier",
                related_type="item",
                related_id=item.id,
                missing_item="identificador_unico",
                reason=form.duplicate_reason.data or "Duplicado autorizado",
                authorized_by_id=current_user.id,
                branch_id=branch_id,
            )
        )
    log_action(
        action="create_duplicate_authorized" if duplicates else "create",
        module="items",
        record_type="item",
        record_id=item.id,
        new_value={"code": item.code, "status": item.status},
        reason=form.duplicate_reason.data if duplicates else None,
    )
    db.session.commit()
    return item


def _apply_item_fields(item: Item, form: ItemForm) -> None:
    item.category_id = form.category_id.data or None
    item.customer_id = form.customer_id.data or None
    if item.customer_id == 0:
        item.customer_id = None
    item.deliverer_id = form.deliverer_id.data or None
    if item.deliverer_id == 0:
        item.deliverer_id = None
    item.brand = form.brand.data
    item.model = form.model.data
    item.serial_number = (form.serial_number.data or "").strip() or None
    item.imei = (form.imei.data or "").strip() or None
    item.chassis_number = (form.chassis_number.data or "").strip() or None
    item.plate_number = (form.plate_number.data or "").strip() or None
    item.color = form.color.data
    item.year = form.year.data
    item.description = form.description.data
    item.physical_condition = form.physical_condition.data
    item.functional_condition = form.functional_condition.data
    item.damages = form.damages.data
    item.scratches = form.scratches.data
    item.missing_parts = form.missing_parts.data
    item.accessories = form.accessories.data
    item.estimated_value = to_decimal(form.estimated_value.data) if form.estimated_value.data is not None else None
    item.purchase_price = to_decimal(form.purchase_price.data) if form.purchase_price.data is not None else None
    item.loan_amount = to_decimal(form.loan_amount.data) if form.loan_amount.data is not None else None
    item.min_sale_price = to_decimal(form.min_sale_price.data) if form.min_sale_price.data is not None else None
    item.sale_price = to_decimal(form.sale_price.data) if form.sale_price.data is not None else None
    item.location = form.location.data
    item.shelf = form.shelf.data
    item.warehouse = form.warehouse.data
    item.status = form.status.data or "en_evaluacion"
    item.observations = form.observations.data


def _attach_item_photos(item: Item, form: ItemForm) -> None:
    singles = [
        ("photo_general", "general"),
        ("photo_front", "frontal"),
        ("photo_back", "trasera"),
        ("photo_serial", "numero_serie"),
        ("photo_imei", "imei"),
    ]
    for field_name, image_type in singles:
        field = getattr(form, field_name)
        if field.data and getattr(field.data, "filename", None):
            stored = save_upload(field.data, folder="items")
            db.session.add(
                ItemImage(
                    item_id=item.id,
                    image_type=image_type,
                    file_path=stored.relative_path,
                    file_url=stored.url_path,
                    safe_name=stored.safe_name,
                    mime_type=stored.mime_type,
                    file_size=stored.file_size,
                    sha256_hash=stored.sha256_hash,
                    captured_by_id=current_user.id,
                    branch_id=item.branch_id,
                    customer_id=item.customer_id,
                    deliverer_id=item.deliverer_id,
                )
            )
            db.session.add(
                EvidenceFile(
                    uuid=stored.uuid,
                    evidence_type=f"item_{image_type}",
                    related_type="item",
                    related_id=item.id,
                    customer_id=item.customer_id,
                    deliverer_id=item.deliverer_id,
                    item_id=item.id,
                    file_path=stored.relative_path,
                    file_url=stored.url_path,
                    safe_name=stored.safe_name,
                    mime_type=stored.mime_type,
                    file_size=stored.file_size,
                    sha256_hash=stored.sha256_hash,
                    captured_by_id=current_user.id,
                    branch_id=item.branch_id,
                )
            )