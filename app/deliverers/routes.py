"""Rutas de persona que entrega."""

from __future__ import annotations

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.deliverers import deliverers_bp
from app.extensions import db
from app.forms.deliverer_forms import LEGITIMACY_DECLARATION, DelivererForm
from app.models import (
    Customer,
    Deliverer,
    DelivererDocument,
    DelivererSignature,
    EvidenceFile,
    OperationException,
)
from app.services.audit_service import log_action
from app.services.file_storage import save_base64_image, save_upload
from app.services.numbering import next_deliverer_code
from app.utils.datetime_utils import utc_now
from app.utils.decorators import permission_required


REQUIRED_PHOTOS = (
    ("photo", "Foto de la persona"),
    ("document_front", "Foto frontal del documento"),
    ("document_back", "Foto trasera del documento"),
    ("holding_item_photo", "Foto sosteniendo el artículo"),
)


def _customer_choices() -> list[tuple[int, str]]:
    query = Customer.query.filter_by(is_deleted=False, status="activo")
    if not current_user.has_role("superadmin", "auditor"):
        query = query.filter_by(branch_id=current_user.branch_id)
    return [(0, "— Seleccione —")] + [
        (c.id, f"{c.code} · {c.full_name} · {c.national_id}")
        for c in query.order_by(Customer.first_name).limit(500).all()
    ]


def _last_deliverer_code() -> str | None:
    row = Deliverer.query.order_by(Deliverer.id.desc()).first()
    return row.code if row else None


@deliverers_bp.route("/")
@login_required
@permission_required("deliverers.view", "deliverers.manage")
def index():
    query = Deliverer.query.filter_by(is_deleted=False)
    if not current_user.has_role("superadmin", "auditor"):
        query = query.filter_by(branch_id=current_user.branch_id)
    q = (request.args.get("q") or "").strip()
    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(
                Deliverer.code.ilike(like),
                Deliverer.first_name.ilike(like),
                Deliverer.last_name.ilike(like),
                Deliverer.national_id.ilike(like),
            )
        )
    deliverers = query.order_by(Deliverer.created_at.desc()).limit(200).all()
    return render_template(
        "deliverers/index.html",
        title="Persona que entrega",
        deliverers=deliverers,
        q=q,
    )


@deliverers_bp.route("/create", methods=["GET", "POST"])
@login_required
@permission_required("deliverers.manage")
def create():
    form = DelivererForm()
    form.customer_id.choices = _customer_choices()

    if form.validate_on_submit():
        customer = db.session.get(Customer, form.customer_id.data)
        if customer is None or customer.is_deleted or form.customer_id.data == 0:
            flash("Debe seleccionar un cliente válido.", "danger")
        elif not current_user.can_access_branch(customer.branch_id):
            abort(403)
        else:
            missing = []
            stored_files = {}
            for field_name, label in REQUIRED_PHOTOS:
                field = getattr(form, field_name)
                if field.data and getattr(field.data, "filename", None):
                    try:
                        stored_files[field_name] = save_upload(field.data, folder="deliverers")
                    except ValueError as exc:
                        flash(str(exc), "danger")
                        return render_template(
                            "deliverers/form.html",
                            title="Nueva persona que entrega",
                            form=form,
                            declaration=LEGITIMACY_DECLARATION,
                        )
                else:
                    missing.append(label)

            if missing and not form.authorize_missing_photos.data:
                flash(
                    "Faltan fotografías obligatorias: "
                    + ", ".join(missing)
                    + ". Un administrador puede autorizar la excepción.",
                    "danger",
                )
            elif missing and form.authorize_missing_photos.data:
                if not current_user.has_any_permission("exceptions.authorize") and not current_user.has_role(
                    "admin", "superadmin"
                ):
                    flash("No tiene permiso para autorizar excepciones de fotografías.", "danger")
                    return render_template(
                        "deliverers/form.html",
                        title="Nueva persona que entrega",
                        form=form,
                        declaration=LEGITIMACY_DECLARATION,
                    )
                if not (form.missing_photos_reason.data or "").strip():
                    flash("Debe indicar el motivo de la excepción fotográfica.", "danger")
                    return render_template(
                        "deliverers/form.html",
                        title="Nueva persona que entrega",
                        form=form,
                        declaration=LEGITIMACY_DECLARATION,
                    )
                deliverer = _create_deliverer(form, customer, stored_files)
                for label in missing:
                    db.session.add(
                        OperationException(
                            exception_type="missing_photo",
                            related_type="deliverer",
                            related_id=deliverer.id,
                            missing_item=label,
                            reason=form.missing_photos_reason.data.strip(),
                            authorized_by_id=current_user.id,
                            branch_id=deliverer.branch_id,
                        )
                    )
                log_action(
                    action="create_with_photo_exception",
                    module="deliverers",
                    record_type="deliverer",
                    record_id=deliverer.id,
                    reason=form.missing_photos_reason.data,
                )
                db.session.commit()
                flash("Persona que entrega registrada con excepción fotográfica.", "warning")
                return redirect(url_for("deliverers.detail", deliverer_id=deliverer.id))
            else:
                if not form.signature_data.data:
                    flash("La firma digital es obligatoria.", "danger")
                elif not form.legitimate_origin_accepted.data:
                    flash("Debe aceptar la declaración de procedencia legítima.", "danger")
                else:
                    try:
                        deliverer = _create_deliverer(form, customer, stored_files)
                    except ValueError as exc:
                        flash(str(exc), "danger")
                        return render_template(
                            "deliverers/form.html",
                            title="Nueva persona que entrega",
                            form=form,
                            declaration=LEGITIMACY_DECLARATION,
                        )
                    log_action(
                        action="create",
                        module="deliverers",
                        record_type="deliverer",
                        record_id=deliverer.id,
                        new_value={"code": deliverer.code, "customer_id": customer.id},
                    )
                    db.session.commit()
                    flash("Persona que entrega registrada correctamente.", "success")
                    return redirect(url_for("deliverers.detail", deliverer_id=deliverer.id))

    return render_template(
        "deliverers/form.html",
        title="Nueva persona que entrega",
        form=form,
        declaration=LEGITIMACY_DECLARATION,
    )


@deliverers_bp.route("/<int:deliverer_id>")
@login_required
@permission_required("deliverers.view", "deliverers.manage")
def detail(deliverer_id: int):
    deliverer = db.session.get(Deliverer, deliverer_id)
    if deliverer is None or deliverer.is_deleted:
        abort(404)
    if not current_user.can_access_branch(deliverer.branch_id):
        abort(403)
    evidence = EvidenceFile.query.filter_by(
        related_type="deliverer", related_id=deliverer.id, is_deleted=False
    ).all()
    return render_template(
        "deliverers/detail.html",
        title=f"Entrega {deliverer.code}",
        deliverer=deliverer,
        evidence=evidence,
        declaration=LEGITIMACY_DECLARATION,
    )


def _create_deliverer(form: DelivererForm, customer: Customer, stored_files: dict) -> Deliverer:
    if form.is_same_as_customer.data:
        first_name = customer.first_name
        last_name = customer.last_name
        national_id = customer.national_id
        phone = customer.phone_primary
        address = customer.address
        relationship = "Mismo cliente"
    else:
        first_name = (form.first_name.data or "").strip()
        last_name = (form.last_name.data or "").strip()
        national_id = (form.national_id.data or "").strip()
        phone = form.phone.data
        address = form.address.data
        relationship = form.relationship_to_customer.data
        if not first_name or not last_name or not national_id:
            raise ValueError("Complete los datos de la persona que entrega.")

    branch_id = customer.branch_id
    deliverer = Deliverer(
        code=next_deliverer_code(_last_deliverer_code()),
        is_same_as_customer=bool(form.is_same_as_customer.data),
        first_name=first_name,
        last_name=last_name,
        national_id=national_id,
        passport=form.passport.data,
        phone=phone,
        address=address,
        relationship_to_customer=relationship,
        delivery_reason=form.delivery_reason.data,
        legitimate_origin_accepted=bool(form.legitimate_origin_accepted.data),
        declaration_accepted_at=utc_now(),
        declaration_ip=request.headers.get("X-Forwarded-For", request.remote_addr),
        observations=form.observations.data,
        customer_id=customer.id,
        branch_id=branch_id,
        received_by_id=current_user.id,
    )
    db.session.add(deliverer)
    db.session.flush()

    path_map = {
        "photo": "photo_path",
        "document_front": "document_front_path",
        "document_back": "document_back_path",
        "holding_item_photo": "holding_item_photo_path",
    }
    for field_name, attr in path_map.items():
        stored = stored_files.get(field_name)
        if not stored:
            continue
        setattr(deliverer, attr, stored.relative_path)
        db.session.add(
            DelivererDocument(
                deliverer_id=deliverer.id,
                document_type=field_name,
                file_path=stored.relative_path,
                file_url=stored.url_path,
                safe_name=stored.safe_name,
                mime_type=stored.mime_type,
                file_size=stored.file_size,
                sha256_hash=stored.sha256_hash,
                uploaded_by_id=current_user.id,
            )
        )
        db.session.add(
            EvidenceFile(
                uuid=stored.uuid,
                evidence_type=f"deliverer_{field_name}",
                related_type="deliverer",
                related_id=deliverer.id,
                customer_id=customer.id,
                deliverer_id=deliverer.id,
                file_path=stored.relative_path,
                file_url=stored.url_path,
                safe_name=stored.safe_name,
                mime_type=stored.mime_type,
                file_size=stored.file_size,
                sha256_hash=stored.sha256_hash,
                captured_by_id=current_user.id,
                branch_id=branch_id,
            )
        )

    if form.signature_data.data and form.signature_data.data.startswith("data:image"):
        stored = save_base64_image(form.signature_data.data, folder="signatures")
        deliverer.signature_path = stored.relative_path
        db.session.add(
            DelivererSignature(
                deliverer_id=deliverer.id,
                signature_type="deliverer",
                file_path=stored.relative_path,
                sha256_hash=stored.sha256_hash,
                accepted_declaration=True,
                ip_address=request.headers.get("X-Forwarded-For", request.remote_addr),
                captured_by_id=current_user.id,
            )
        )
        db.session.add(
            EvidenceFile(
                uuid=stored.uuid,
                evidence_type="deliverer_signature",
                related_type="deliverer",
                related_id=deliverer.id,
                customer_id=customer.id,
                deliverer_id=deliverer.id,
                file_path=stored.relative_path,
                file_url=stored.url_path,
                safe_name=stored.safe_name,
                mime_type=stored.mime_type,
                file_size=stored.file_size,
                sha256_hash=stored.sha256_hash,
                captured_by_id=current_user.id,
                branch_id=branch_id,
            )
        )

    return deliverer