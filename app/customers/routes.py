"""Rutas de clientes."""

from __future__ import annotations

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.customers import customers_bp
from app.extensions import db
from app.forms.customer_forms import CustomerForm, CustomerSearchForm
from app.models import Customer, EvidenceFile, OperationException, OperationSignature
from app.repositories.customer_repository import CustomerRepository
from app.services.audit_service import log_action
from app.services.file_storage import save_base64_image, save_upload
from app.services.numbering import next_customer_code
from app.utils.decorators import permission_required
from app.utils.money import to_decimal


def _branch_scope() -> int | None:
    if current_user.has_role("superadmin", "auditor"):
        return None
    return current_user.branch_id


def _save_optional_upload(field, folder: str):
    if field.data and getattr(field.data, "filename", None):
        return save_upload(field.data, folder=folder)
    return None


@customers_bp.route("/")
@login_required
@permission_required("customers.view", "customers.manage")
def index():
    form = CustomerSearchForm(request.args, meta={"csrf": False})
    customers = CustomerRepository.search(
        term=form.q.data or "",
        status=form.status.data or "",
        branch_id=_branch_scope(),
    )
    return render_template(
        "customers/index.html",
        title="Clientes",
        customers=customers,
        form=form,
    )


@customers_bp.route("/create", methods=["GET", "POST"])
@login_required
@permission_required("customers.manage")
def create():
    if not current_user.branch_id and not current_user.has_role("superadmin"):
        flash("Debe tener una sucursal asignada para registrar clientes.", "danger")
        return redirect(url_for("customers.index"))

    form = CustomerForm()
    if form.validate_on_submit():
        national_id = (form.national_id.data or "").strip()
        duplicates = CustomerRepository.find_by_national_id(national_id)
        if duplicates and not form.authorize_duplicate.data:
            flash(
                "Ya existe un cliente con esa cédula. Un administrador debe autorizar el duplicado.",
                "danger",
            )
        elif duplicates and form.authorize_duplicate.data:
            if not current_user.has_any_permission("exceptions.authorize") and not current_user.has_role(
                "superadmin", "admin"
            ):
                flash("No tiene permiso para autorizar cédulas duplicadas.", "danger")
                return render_template("customers/form.html", title="Nuevo cliente", form=form)
            if not (form.duplicate_reason.data or "").strip():
                flash("Debe indicar el motivo de autorización del duplicado.", "danger")
                return render_template("customers/form.html", title="Nuevo cliente", form=form)
            customer = _build_customer(form, duplicates=True)
            db.session.add(customer)
            db.session.flush()
            db.session.add(
                OperationException(
                    exception_type="customer_duplicate_id",
                    related_type="customer",
                    related_id=customer.id,
                    missing_item="cedula_unica",
                    reason=form.duplicate_reason.data.strip(),
                    authorized_by_id=current_user.id,
                    branch_id=customer.branch_id,
                )
            )
            _attach_files(customer, form)
            log_action(
                action="create_duplicate_authorized",
                module="customers",
                record_type="customer",
                record_id=customer.id,
                reason=form.duplicate_reason.data,
                new_value={"code": customer.code, "national_id": customer.national_id},
            )
            db.session.commit()
            flash("Cliente creado con autorización de cédula duplicada.", "warning")
            return redirect(url_for("customers.detail", customer_id=customer.id))
        else:
            customer = _build_customer(form, duplicates=False)
            db.session.add(customer)
            db.session.flush()
            _attach_files(customer, form)
            log_action(
                action="create",
                module="customers",
                record_type="customer",
                record_id=customer.id,
                new_value={"code": customer.code, "name": customer.full_name},
            )
            db.session.commit()
            flash("Cliente registrado correctamente.", "success")
            return redirect(url_for("customers.detail", customer_id=customer.id))
    elif form.is_submitted():
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{field}: {error}", "danger")

    return render_template("customers/form.html", title="Nuevo cliente", form=form)


@customers_bp.route("/<int:customer_id>")
@login_required
@permission_required("customers.view", "customers.manage")
def detail(customer_id: int):
    from app.models import PawnContract, PawnPayment
    from app.utils.money import ZERO, money_add, to_decimal

    customer = CustomerRepository.get_by_id(customer_id)
    if customer is None or customer.is_deleted:
        abort(404)
    if not current_user.can_access_branch(customer.branch_id):
        abort(403)

    evidence = EvidenceFile.query.filter_by(
        related_type="customer", related_id=customer.id, is_deleted=False
    ).all()

    contracts = (
        PawnContract.query.filter_by(customer_id=customer.id, is_deleted=False)
        .order_by(PawnContract.id.desc())
        .all()
    )
    open_statuses = {
        "activo",
        "renovado",
        "proximo_vencer",
        "vencido",
        "en_periodo_gracia",
        "pendiente_autorizacion",
    }
    open_contracts = [c for c in contracts if c.status in open_statuses]
    paid_contracts = sum(1 for c in contracts if c.status in {"pagado", "cerrado", "retirado"})

    payments = (
        PawnPayment.query.filter_by(
            customer_id=customer.id, is_voided=False, is_deleted=False
        )
        .order_by(PawnPayment.paid_at.desc())
        .limit(100)
        .all()
    )

    payment_rows = []
    interest_paid = ZERO
    for payment in payments:
        capital = ZERO
        interest = ZERO
        for alloc in payment.allocations:
            if alloc.concept == "capital":
                capital = money_add(capital, alloc.amount)
            elif alloc.concept == "interes":
                interest = money_add(interest, alloc.amount)
        interest_paid = money_add(interest_paid, interest)
        payment_rows.append({"payment": payment, "capital": capital, "interest": interest})

    capital_pending = sum((to_decimal(c.capital_balance) for c in open_contracts), ZERO)
    total_pending = sum((to_decimal(c.pending_total) for c in open_contracts), ZERO)

    # Score simple operativo (0-100)
    score = 70
    if paid_contracts:
        score += min(20, paid_contracts * 5)
    if interest_paid > ZERO:
        score += 5
    late = sum(1 for c in open_contracts if c.status in {"vencido", "en_periodo_gracia"})
    score -= late * 15
    if customer.status in {"bloqueado", "restringido"}:
        score -= 25
    score = max(0, min(100, score))
    if score >= 75:
        score_label, score_tone = "Bueno", "good"
    elif score >= 45:
        score_label, score_tone = "Medio", "mid"
    else:
        score_label, score_tone = "Riesgo", "bad"

    stats = {
        "interest_paid": interest_paid,
        "paid_contracts": paid_contracts,
        "active_contracts": len(open_contracts),
        "capital_pending": capital_pending,
        "total_pending": total_pending,
        "score": score,
        "score_label": score_label,
        "score_tone": score_tone,
    }

    return render_template(
        "customers/detail.html",
        title=f"Cliente {customer.code}",
        customer=customer,
        evidence=evidence,
        open_contracts=open_contracts,
        payment_rows=payment_rows,
        stats=stats,
    )


@customers_bp.route("/<int:customer_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("customers.manage")
def edit(customer_id: int):
    customer = CustomerRepository.get_by_id(customer_id)
    if customer is None or customer.is_deleted:
        abort(404)
    if not current_user.can_access_branch(customer.branch_id):
        abort(403)

    form = CustomerForm(obj=customer)
    if form.validate_on_submit():
        national_id = (form.national_id.data or "").strip()
        duplicates = CustomerRepository.find_by_national_id(national_id, exclude_id=customer.id)
        if duplicates and not form.authorize_duplicate.data:
            flash("Ya existe otro cliente con esa cédula.", "danger")
        else:
            old = {"status": customer.status, "national_id": customer.national_id}
            _apply_form(customer, form)
            if duplicates and form.authorize_duplicate.data:
                if not (form.duplicate_reason.data or "").strip():
                    flash("Indique el motivo de autorización.", "danger")
                    return render_template(
                        "customers/form.html", title="Editar cliente", form=form, customer=customer
                    )
                customer.duplicate_authorized = True
                customer.duplicate_authorized_by_id = current_user.id
                customer.duplicate_authorization_reason = form.duplicate_reason.data
            _attach_files(customer, form)
            log_action(
                action="update",
                module="customers",
                record_type="customer",
                record_id=customer.id,
                old_value=old,
                new_value={"status": customer.status, "national_id": customer.national_id},
            )
            db.session.commit()
            flash("Cliente actualizado.", "success")
            return redirect(url_for("customers.detail", customer_id=customer.id))
    return render_template(
        "customers/form.html", title="Editar cliente", form=form, customer=customer
    )


def _build_customer(form: CustomerForm, *, duplicates: bool) -> Customer:
    branch_id = current_user.branch_id
    if branch_id is None and current_user.has_role("superadmin"):
        from app.models import Branch

        main = Branch.query.filter_by(is_main=True, is_deleted=False).first()
        branch_id = main.id if main else None
    if branch_id is None:
        raise RuntimeError("No hay sucursal disponible.")

    customer = Customer(
        code=next_customer_code(CustomerRepository.last_code()),
        branch_id=branch_id,
        created_by_id=current_user.id,
        duplicate_authorized=duplicates,
        duplicate_authorized_by_id=current_user.id if duplicates else None,
        duplicate_authorization_reason=(form.duplicate_reason.data or None) if duplicates else None,
    )
    _apply_form(customer, form)
    return customer


def _apply_form(customer: Customer, form: CustomerForm) -> None:
    customer.first_name = (form.first_name.data or "").strip()
    customer.last_name = (form.last_name.data or "").strip()
    customer.national_id = (form.national_id.data or "").strip()
    customer.passport = form.passport.data
    customer.other_document = form.other_document.data
    customer.birth_date = form.birth_date.data
    customer.phone_primary = (form.phone_primary.data or "").strip()
    customer.phone_secondary = form.phone_secondary.data
    customer.whatsapp = form.whatsapp.data
    customer.email = form.email.data
    customer.address = form.address.data
    customer.sector = form.sector.data
    customer.city = form.city.data
    customer.province = form.province.data
    customer.country = form.country.data or "República Dominicana"
    customer.occupation = form.occupation.data
    customer.workplace = form.workplace.data
    customer.approximate_income = to_decimal(form.approximate_income.data) if form.approximate_income.data is not None else None
    customer.reference_name = form.reference_name.data
    customer.reference_phone = form.reference_phone.data
    customer.status = form.status.data or "activo"
    customer.internal_notes = form.internal_notes.data


def _attach_files(customer: Customer, form: CustomerForm) -> None:
    mapping = [
        ("photo", "customer_photo", "photo_path"),
        ("document_front", "customer_doc_front", "document_front_path"),
        ("document_back", "customer_doc_back", "document_back_path"),
    ]
    for field_name, evidence_type, attr in mapping:
        stored = _save_optional_upload(getattr(form, field_name), folder="customers")
        if stored:
            setattr(customer, attr, stored.relative_path)
            db.session.add(
                EvidenceFile(
                    uuid=stored.uuid,
                    evidence_type=evidence_type,
                    related_type="customer",
                    related_id=customer.id,
                    customer_id=customer.id,
                    file_path=stored.relative_path,
                    file_url=stored.url_path,
                    safe_name=stored.safe_name,
                    mime_type=stored.mime_type,
                    file_size=stored.file_size,
                    sha256_hash=stored.sha256_hash,
                    captured_by_id=current_user.id,
                    branch_id=customer.branch_id,
                )
            )

    if form.signature_data.data and form.signature_data.data.startswith("data:image"):
        stored = save_base64_image(form.signature_data.data, folder="signatures")
        customer.signature_path = stored.relative_path
        db.session.add(
            OperationSignature(
                signer_role="customer",
                related_type="customer",
                related_id=customer.id,
                customer_id=customer.id,
                file_path=stored.relative_path,
                sha256_hash=stored.sha256_hash,
                captured_by_id=current_user.id,
                branch_id=customer.branch_id,
            )
        )
        db.session.add(
            EvidenceFile(
                uuid=stored.uuid,
                evidence_type="customer_signature",
                related_type="customer",
                related_id=customer.id,
                customer_id=customer.id,
                file_path=stored.relative_path,
                file_url=stored.url_path,
                safe_name=stored.safe_name,
                mime_type=stored.mime_type,
                file_size=stored.file_size,
                sha256_hash=stored.sha256_hash,
                captured_by_id=current_user.id,
                branch_id=customer.branch_id,
            )
        )