"""Rutas de empeños y vencidos."""

from __future__ import annotations

from flask import Response, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_

from app.extensions import db
from app.forms.pawn_forms import AuthorizeExpiredForm, PawnContractForm
from app.models import Customer, Deliverer, Item, ItemCategory, ItemImage, PawnContract, Setting
from app.pawn import pawn_bp
from app.services.audit_service import log_action
from app.services.category_seed import seed_item_categories
from app.services.document_service import (
    build_pawn_contract_pdf,
    build_ticket_58mm_pdf,
    generate_qr_png,
)
from app.services.file_storage import save_upload
from app.services.finance_service import build_breakdown
from app.services.numbering import next_item_code
from app.services.pawn_service import (
    create_pawn_contract,
    refresh_late_fee,
    resolve_default_percent,
    update_expiration_statuses,
)
from app.utils.decorators import permission_required
from app.utils.datetime_utils import utc_now
from app.utils.money import to_decimal


def _last_item_code() -> str | None:
    row = Item.query.order_by(Item.id.desc()).first()
    return row.code if row else None


def _choices(*, user_id: int | None = None):
    from app.services.deliverer_service import ensure_deliverers_for_customers

    seed_item_categories()

    customers = (
        Customer.query.filter_by(is_deleted=False)
        .order_by(Customer.first_name)
        .limit(300)
        .all()
    )
    # Si no hay “quien entrega”, se crea automáticamente = mismo cliente.
    ensure_deliverers_for_customers(customers, user_id=user_id)

    deliverers = Deliverer.query.filter_by(is_deleted=False).order_by(Deliverer.id.desc()).limit(300)
    categories = (
        ItemCategory.query.filter_by(is_deleted=False, is_active=True)
        .order_by(ItemCategory.sort_order, ItemCategory.name)
        .all()
    )
    active_statuses = ("activo", "renovado", "proximo_vencer", "vencido", "en_periodo_gracia")
    busy_item_ids = {
        row[0]
        for row in db.session.query(PawnContract.item_id)
        .filter(
            PawnContract.is_deleted.is_(False),
            PawnContract.status.in_(active_statuses),
            PawnContract.item_id.isnot(None),
        )
        .all()
    }
    items_q = Item.query.filter(
        Item.is_deleted.is_(False),
        Item.status.notin_(["vendido", "perdido", "retirado", "empenado"]),
    )
    if busy_item_ids:
        items_q = items_q.filter(~Item.id.in_(busy_item_ids))
    items = items_q.order_by(Item.id.desc()).limit(100)

    deliverer_choices = [(0, "— Seleccione —")]
    for d in deliverers:
        label = f"{d.code} · {d.full_name}"
        if d.is_same_as_customer:
            label += " (mismo cliente)"
        deliverer_choices.append((d.id, label))

    category_choices = [(0, "— Seleccione tipo —")] + [
        (c.id, c.name) for c in categories
    ]
    item_choices = [(0, "— Crear artículo nuevo —")] + [
        (i.id, f"{i.code} · {i.brand or ''} {i.model or ''}") for i in items
    ]

    return (
        [(0, "— Seleccione —")] + [(c.id, f"{c.code} · {c.full_name}") for c in customers],
        deliverer_choices,
        category_choices,
        item_choices,
    )


def _create_item_from_form(form, *, customer_id: int, deliverer_id: int, branch_id: int) -> Item:
    category = db.session.get(ItemCategory, form.category_id.data)
    if category is None:
        raise ValueError("Seleccione un tipo de artículo.")

    brand = (form.item_brand.data or "").strip()
    model = (form.item_model.data or "").strip() or None
    serial = (form.item_serial.data or "").strip() or None
    weight = form.item_weight.data
    desc_parts = [brand]
    if model:
        desc_parts.append(model)
    if weight:
        desc_parts.append(f"{weight} g")
    description = " · ".join(str(p) for p in desc_parts if p)

    item = Item(
        code=next_item_code(_last_item_code()),
        category_id=category.id,
        brand=brand,
        model=model,
        serial_number=serial,
        imei=serial if category.requires_imei else None,
        description=description,
        status="en_evaluacion",
        branch_id=branch_id,
        customer_id=customer_id,
        deliverer_id=deliverer_id,
        loan_amount=to_decimal(form.capital.data),
    )
    db.session.add(item)
    db.session.flush()

    photo = form.item_photo.data
    if photo and getattr(photo, "filename", None):
        stored = save_upload(photo, folder="items")
        db.session.add(
            ItemImage(
                item_id=item.id,
                image_type="general",
                file_path=stored.relative_path,
                file_url=stored.url_path,
                safe_name=stored.safe_name,
                mime_type=stored.mime_type,
                file_size=stored.file_size,
                sha256_hash=stored.sha256_hash,
                captured_by_id=current_user.id,
                branch_id=branch_id,
                customer_id=customer_id,
                deliverer_id=deliverer_id,
            )
        )
    return item


def _deliverer_customer_map() -> dict[str, int]:
    """Mapa customer_id -> deliverer_id (mismo cliente) para el JS del formulario."""
    rows = Deliverer.query.filter_by(is_deleted=False, is_same_as_customer=True).all()
    mapping: dict[str, int] = {}
    for d in rows:
        mapping[str(d.customer_id)] = d.id
    return mapping


@pawn_bp.route("/")
@login_required
@permission_required("pawn.view", "pawn.manage")
def index():
    update_expiration_statuses()
    q = (request.args.get("q") or "").strip()
    query = PawnContract.query.filter_by(is_deleted=False)
    if not current_user.has_role("superadmin", "auditor"):
        query = query.filter_by(branch_id=current_user.branch_id)
    if q:
        like = f"%{q}%"
        query = (
            query.outerjoin(Customer, PawnContract.customer_id == Customer.id)
            .outerjoin(Item, PawnContract.item_id == Item.id)
            .filter(
                or_(
                    PawnContract.contract_number.ilike(like),
                    PawnContract.status.ilike(like),
                    Customer.first_name.ilike(like),
                    Customer.last_name.ilike(like),
                    Customer.phone_primary.ilike(like),
                    Customer.national_id.ilike(like),
                    Item.code.ilike(like),
                    Item.brand.ilike(like),
                    Item.model.ilike(like),
                )
            )
        )
    contracts = query.order_by(PawnContract.created_at.desc()).limit(200).all()
    return render_template("pawn/index.html", title="Empeños", contracts=contracts, q=q)


@pawn_bp.route("/create", methods=["GET", "POST"])
@login_required
@permission_required("pawn.manage")
def create():
    form = PawnContractForm()
    c_choices, d_choices, cat_choices, i_choices = _choices(user_id=current_user.id)
    form.customer_id.choices = c_choices
    form.deliverer_id.choices = d_choices
    form.category_id.choices = cat_choices
    form.item_id.choices = i_choices
    if not form.is_submitted():
        form.percent.data = resolve_default_percent()
        form.same_as_customer.data = True
        # Preseleccionar quien entrega del primer cliente si aplica.
        if form.customer_id.choices and len(form.customer_id.choices) > 1:
            from app.services.deliverer_service import ensure_customer_deliverer

            first_customer = db.session.get(Customer, form.customer_id.choices[1][0])
            if first_customer:
                d = ensure_customer_deliverer(first_customer, user_id=current_user.id)
                form.customer_id.data = first_customer.id
                form.deliverer_id.data = d.id
        # Prefiere categoría "Otros" o la primera real.
        if len(cat_choices) > 1:
            otros = next((c for c in cat_choices if "Otros" in c[1]), None)
            form.category_id.data = otros[0] if otros else cat_choices[1][0]

    if form.validate_on_submit():
        if form.customer_id.data in (None, 0):
            flash("Seleccione un cliente.", "danger")
        elif form.item_id.data in (None, 0) and form.category_id.data in (None, 0):
            flash("Seleccione el tipo de artículo.", "danger")
        elif form.item_id.data in (None, 0) and not (form.item_brand.data or "").strip():
            flash("Escriba la marca o nombre del artículo.", "danger")
        elif not form.declaration_accepted.data:
            flash("Debe aceptar la declaración/términos.", "danger")
        elif form.interest_type.data == "compuesto":
            flash("El interés compuesto está desactivado por defecto.", "danger")
        else:
            from app.services.deliverer_service import ensure_customer_deliverer

            deliverer_id = form.deliverer_id.data
            if form.same_as_customer.data or deliverer_id in (None, 0):
                customer = db.session.get(Customer, form.customer_id.data)
                if customer is None:
                    flash("Cliente no válido.", "danger")
                    return render_template(
                        "pawn/form.html",
                        title="Nuevo empeño",
                        form=form,
                        deliverer_map=_deliverer_customer_map(),
                    )
                deliverer_id = ensure_customer_deliverer(
                    customer, user_id=current_user.id
                ).id

            try:
                branch_id = current_user.branch_id
                if not branch_id:
                    from app.models import Branch
                    main = Branch.query.filter_by(is_main=True).first()
                    branch_id = main.id

                item_id = form.item_id.data
                if item_id in (None, 0):
                    item = _create_item_from_form(
                        form,
                        customer_id=form.customer_id.data,
                        deliverer_id=deliverer_id,
                        branch_id=branch_id,
                    )
                    item_id = item.id

                contract = create_pawn_contract(
                    customer_id=form.customer_id.data,
                    deliverer_id=deliverer_id,
                    item_id=item_id,
                    branch_id=branch_id,
                    capital=to_decimal(form.capital.data),
                    percent=to_decimal(form.percent.data),
                    interest_type=form.interest_type.data,
                    duration_days=form.duration_days.data,
                    grace_days=form.grace_days.data,
                    fees_amount=to_decimal(form.fees_amount.data or 0),
                    late_percent=to_decimal(form.late_percent.data or 0),
                    late_fixed=to_decimal(form.late_fixed.data or 0),
                    late_mode=form.late_mode.data,
                    conditions=form.conditions.data,
                    observations=form.observations.data,
                    percent_manual=False,
                    declaration_accepted=True,
                    user_id=current_user.id,
                )
                flash(f"Contrato {contract.contract_number} creado.", "success")
                return redirect(url_for("pawn.detail", contract_id=contract.id))
            except ValueError as exc:
                flash(str(exc), "danger")
    return render_template(
        "pawn/form.html",
        title="Nuevo empeño",
        form=form,
        deliverer_map=_deliverer_customer_map(),
    )


@pawn_bp.route("/<int:contract_id>")
@login_required
@permission_required("pawn.view", "pawn.manage")
def detail(contract_id: int):
    contract = db.session.get(PawnContract, contract_id)
    if contract is None or contract.is_deleted:
        abort(404)
    refresh_late_fee(contract)
    db.session.commit()
    preview = build_breakdown(
        capital=contract.capital_balance,
        percent=contract.percent,
        interest_type=contract.interest_type,
        fixed_fee=contract.fee_balance,
        late_fee=contract.late_fee_balance,
        grace_days=contract.grace_days,
        start_date=contract.start_date,
        duration_days=contract.duration_days,
    )
    return render_template(
        "pawn/detail.html",
        title=contract.contract_number,
        contract=contract,
        preview=preview,
    )


@pawn_bp.route("/<int:contract_id>/pdf")
@login_required
@permission_required("pawn.view", "pawn.manage")
def pdf(contract_id: int):
    contract = db.session.get(PawnContract, contract_id)
    if contract is None:
        abort(404)
    name = Setting.query.filter_by(key="business_name").first()
    business = name.value if name and name.value else "JDM Empeños"
    generate_qr_png(f"EMP:{contract.contract_number}", f"{contract.contract_number}.png")
    data = build_pawn_contract_pdf(contract, business_name=business)
    return Response(
        data,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"inline; filename={contract.contract_number}.pdf"},
    )


@pawn_bp.route("/<int:contract_id>/photo", methods=["POST"])
@login_required
@permission_required("pawn.manage")
def upload_photo(contract_id: int):
    contract = db.session.get(PawnContract, contract_id)
    if contract is None or contract.is_deleted or contract.item is None:
        abort(404)
    photo = request.files.get("item_photo")
    if not photo or not photo.filename:
        flash("Seleccione una foto del artículo.", "danger")
        return redirect(url_for("pawn.detail", contract_id=contract.id))
    try:
        stored = save_upload(photo, folder="items")
        db.session.add(
            ItemImage(
                item_id=contract.item.id,
                image_type="general",
                file_path=stored.relative_path,
                file_url=stored.url_path,
                safe_name=stored.safe_name,
                mime_type=stored.mime_type,
                file_size=stored.file_size,
                sha256_hash=stored.sha256_hash,
                captured_by_id=current_user.id,
                branch_id=contract.branch_id,
                customer_id=contract.customer_id,
                deliverer_id=contract.deliverer_id,
            )
        )
        db.session.commit()
        flash("Foto del artículo guardada.", "success")
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("pawn.detail", contract_id=contract.id))


@pawn_bp.route("/<int:contract_id>/ticket")
@login_required
@permission_required("pawn.view", "pawn.manage")
def ticket(contract_id: int):
    """Recibo térmico 58 mm (HTML para imprimir)."""
    contract = db.session.get(PawnContract, contract_id)
    if contract is None or contract.is_deleted:
        abort(404)
    name = Setting.query.filter_by(key="business_name").first()
    business = name.value if name and name.value else "JDM Empeños"
    return render_template(
        "pawn/ticket_58.html",
        title=f"Recibo {contract.contract_number}",
        contract=contract,
        business_name=business,
    )


@pawn_bp.route("/<int:contract_id>/ticket.pdf")
@login_required
@permission_required("pawn.view", "pawn.manage")
def ticket_pdf(contract_id: int):
    contract = db.session.get(PawnContract, contract_id)
    if contract is None or contract.is_deleted:
        abort(404)
    name = Setting.query.filter_by(key="business_name").first()
    business = name.value if name and name.value else "JDM Empeños"
    data = build_ticket_58mm_pdf(contract, business_name=business)
    return Response(
        data,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename=recibo_{contract.contract_number}_58mm.pdf"
        },
    )


@pawn_bp.route("/expired")
@login_required
@permission_required("pawn.view", "pawn.manage")
def expired():
    update_expiration_statuses()
    query = PawnContract.query.filter(
        PawnContract.is_deleted.is_(False),
        PawnContract.status.in_(
            ["vencido", "en_periodo_gracia", "pendiente_autorizacion", "proximo_vencer"]
        ),
    )
    if not current_user.has_role("superadmin", "auditor"):
        query = query.filter_by(branch_id=current_user.branch_id)
    contracts = query.order_by(PawnContract.due_date.asc()).all()
    return render_template("pawn/expired.html", title="Vencimientos", contracts=contracts)


@pawn_bp.route("/expired/<int:contract_id>/authorize", methods=["GET", "POST"])
@login_required
@permission_required("exceptions.authorize")
def authorize_expired(contract_id: int):
    contract = db.session.get(PawnContract, contract_id)
    if contract is None:
        abort(404)
    form = AuthorizeExpiredForm()
    if form.validate_on_submit():
        contract.status = "autorizado_inventario"
        contract.authorized_for_inventory = True
        contract.authorized_inventory_at = utc_now()
        contract.authorized_inventory_by_id = current_user.id
        if contract.item:
            contract.item.status = "autorizado_inventario"
        log_action(
            action="authorize_inventory",
            module="pawn",
            record_type="pawn_contract",
            record_id=contract.id,
            reason=form.reason.data,
        )
        db.session.commit()
        flash("Artículo autorizado para inventario/venta.", "success")
        return redirect(url_for("pawn.expired"))
    return render_template(
        "pawn/authorize.html", title="Autorizar vencido", form=form, contract=contract
    )