"""Rutas de sucursales."""

from flask import abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.branches import branches_bp
from app.extensions import db
from app.forms.branch_forms import BranchForm
from app.models import Branch
from app.repositories.branch_repository import BranchRepository
from app.services.audit_service import log_action
from app.utils.decorators import permission_required


@branches_bp.route("/")
@login_required
@permission_required("branches.view", "branches.manage")
def index():
    if current_user.has_role("superadmin", "auditor"):
        branches = BranchRepository.list_all(include_inactive=True)
    else:
        branches = []
        if current_user.branch_id:
            branch = BranchRepository.get_by_id(current_user.branch_id)
            if branch and not branch.is_deleted:
                branches = [branch]
    return render_template("branches/index.html", title="Sucursales", branches=branches)


@branches_bp.route("/create", methods=["GET", "POST"])
@login_required
@permission_required("branches.manage")
def create():
    form = BranchForm()
    if form.validate_on_submit():
        if BranchRepository.code_exists(form.code.data or ""):
            flash("Ya existe una sucursal con ese código.", "danger")
        else:
            if form.is_main.data:
                Branch.query.filter_by(is_main=True).update({"is_main": False})
            branch = Branch(
                code=(form.code.data or "").strip().upper(),
                name=(form.name.data or "").strip(),
                phone=form.phone.data,
                whatsapp=form.whatsapp.data,
                email=form.email.data,
                address=form.address.data,
                sector=form.sector.data,
                city=form.city.data,
                province=form.province.data,
                country=form.country.data or "República Dominicana",
                rnc=form.rnc.data,
                is_active=bool(form.is_active.data),
                is_main=bool(form.is_main.data),
                notes=form.notes.data,
            )
            db.session.add(branch)
            log_action(
                action="create",
                module="branches",
                record_type="branch",
                new_value={"code": branch.code, "name": branch.name},
            )
            db.session.commit()
            flash("Sucursal creada correctamente.", "success")
            return redirect(url_for("branches.index"))
    return render_template("branches/form.html", title="Nueva sucursal", form=form)


@branches_bp.route("/<int:branch_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("branches.manage")
def edit(branch_id: int):
    branch = BranchRepository.get_by_id(branch_id)
    if branch is None or branch.is_deleted:
        abort(404)
    form = BranchForm(obj=branch)
    if form.validate_on_submit():
        if BranchRepository.code_exists(form.code.data or "", exclude_id=branch.id):
            flash("Ya existe una sucursal con ese código.", "danger")
        else:
            old = {"code": branch.code, "name": branch.name, "is_active": branch.is_active}
            if form.is_main.data:
                Branch.query.filter(Branch.id != branch.id, Branch.is_main.is_(True)).update(
                    {"is_main": False}
                )
            branch.code = (form.code.data or "").strip().upper()
            branch.name = (form.name.data or "").strip()
            branch.phone = form.phone.data
            branch.whatsapp = form.whatsapp.data
            branch.email = form.email.data
            branch.address = form.address.data
            branch.sector = form.sector.data
            branch.city = form.city.data
            branch.province = form.province.data
            branch.country = form.country.data or "República Dominicana"
            branch.rnc = form.rnc.data
            branch.is_active = bool(form.is_active.data)
            branch.is_main = bool(form.is_main.data)
            branch.notes = form.notes.data
            log_action(
                action="update",
                module="branches",
                record_type="branch",
                record_id=branch.id,
                old_value=old,
                new_value={"code": branch.code, "name": branch.name, "is_active": branch.is_active},
            )
            db.session.commit()
            flash("Sucursal actualizada correctamente.", "success")
            return redirect(url_for("branches.index"))
    return render_template(
        "branches/form.html", title="Editar sucursal", form=form, branch=branch
    )


@branches_bp.route("/<int:branch_id>/deactivate", methods=["POST"])
@login_required
@permission_required("branches.manage")
def deactivate(branch_id: int):
    branch = BranchRepository.get_by_id(branch_id)
    if branch is None or branch.is_deleted:
        abort(404)
    if branch.is_main:
        flash("No se puede desactivar la sucursal principal.", "danger")
        return redirect(url_for("branches.index"))
    branch.is_active = False
    log_action(
        action="deactivate",
        module="branches",
        record_type="branch",
        record_id=branch.id,
        reason="Desactivación desde panel",
    )
    db.session.commit()
    flash("Sucursal desactivada.", "warning")
    return redirect(url_for("branches.index"))


@branches_bp.route("/<int:branch_id>/activate", methods=["POST"])
@login_required
@permission_required("branches.manage")
def activate(branch_id: int):
    branch = BranchRepository.get_by_id(branch_id)
    if branch is None or branch.is_deleted:
        abort(404)
    branch.is_active = True
    log_action(
        action="activate",
        module="branches",
        record_type="branch",
        record_id=branch.id,
    )
    db.session.commit()
    flash("Sucursal activada.", "success")
    return redirect(url_for("branches.index"))