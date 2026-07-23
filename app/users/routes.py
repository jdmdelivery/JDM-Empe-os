"""Rutas de usuarios."""

from flask import abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.forms.user_forms import ProfilePasswordForm, UserForm
from app.models import Branch, Role, User
from app.repositories.user_repository import UserRepository
from app.services.audit_service import log_action
from app.users import users_bp
from app.utils.decorators import permission_required


def _role_choices() -> list[tuple[int, str]]:
    roles = Role.query.order_by(Role.name.asc()).all()
    if not current_user.has_role("superadmin"):
        roles = [r for r in roles if r.code != "superadmin"]
    return [(r.id, r.name) for r in roles]


def _branch_choices() -> list[tuple[int, str]]:
    branches = Branch.query.filter_by(is_deleted=False, is_active=True).order_by(Branch.name).all()
    choices = [(0, "— Sin sucursal —")]
    choices.extend((b.id, b.name) for b in branches)
    return choices


@users_bp.route("/")
@login_required
@permission_required("users.view", "users.manage")
def index():
    if current_user.has_role("superadmin", "auditor"):
        users = UserRepository.list_active()
    else:
        users = UserRepository.list_active(branch_id=current_user.branch_id)
    return render_template("users/index.html", title="Usuarios", users=users)


@users_bp.route("/create", methods=["GET", "POST"])
@login_required
@permission_required("users.manage")
def create():
    form = UserForm()
    form._require_password = True
    form.role_id.choices = _role_choices()
    form.branch_id.choices = _branch_choices()

    if form.validate_on_submit():
        if UserRepository.username_exists(form.username.data or ""):
            flash("El nombre de usuario ya existe.", "danger")
        elif UserRepository.email_exists(form.email.data or ""):
            flash("El correo ya está registrado.", "danger")
        else:
            role = db.session.get(Role, form.role_id.data)
            if role is None:
                flash("Rol no válido.", "danger")
            elif role.code == "superadmin" and not current_user.has_role("superadmin"):
                abort(403)
            else:
                branch_id = form.branch_id.data or None
                if branch_id == 0:
                    branch_id = None
                if not current_user.has_role("superadmin"):
                    branch_id = current_user.branch_id

                user = User(
                    username=(form.username.data or "").strip().lower(),
                    email=(form.email.data or "").strip().lower(),
                    first_name=(form.first_name.data or "").strip(),
                    last_name=(form.last_name.data or "").strip(),
                    phone=form.phone.data,
                    role_id=role.id,
                    branch_id=branch_id,
                    account_active=bool(form.account_active.data),
                    must_change_password=bool(form.must_change_password.data),
                    notes=form.notes.data,
                )
                user.set_password(form.password.data or "")
                db.session.add(user)
                log_action(
                    action="create",
                    module="users",
                    record_type="user",
                    new_value={"username": user.username, "role": role.code},
                )
                db.session.commit()
                flash("Usuario creado correctamente.", "success")
                return redirect(url_for("users.index"))
    elif form.is_submitted():
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{field}: {error}", "danger")

    return render_template("users/form.html", title="Nuevo usuario", form=form)


@users_bp.route("/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("users.manage")
def edit(user_id: int):
    user = UserRepository.get_by_id(user_id)
    if user is None or user.is_deleted:
        abort(404)
    if not current_user.has_role("superadmin", "auditor") and user.branch_id != current_user.branch_id:
        abort(403)

    form = UserForm(obj=user)
    form._require_password = False
    form.role_id.choices = _role_choices()
    form.branch_id.choices = _branch_choices()
    form.account_active.data = user.account_active
    if not form.is_submitted():
        form.branch_id.data = user.branch_id or 0
        form.password.data = ""
        form.password2.data = ""

    if form.validate_on_submit():
        if UserRepository.username_exists(form.username.data or "", exclude_id=user.id):
            flash("El nombre de usuario ya existe.", "danger")
        elif UserRepository.email_exists(form.email.data or "", exclude_id=user.id):
            flash("El correo ya está registrado.", "danger")
        else:
            role = db.session.get(Role, form.role_id.data)
            if role is None:
                flash("Rol no válido.", "danger")
            elif role.code == "superadmin" and not current_user.has_role("superadmin"):
                abort(403)
            else:
                old = {
                    "username": user.username,
                    "role_id": user.role_id,
                    "account_active": user.account_active,
                }
                branch_id = form.branch_id.data or None
                if branch_id == 0:
                    branch_id = None
                if not current_user.has_role("superadmin"):
                    branch_id = current_user.branch_id

                user.username = (form.username.data or "").strip().lower()
                user.email = (form.email.data or "").strip().lower()
                user.first_name = (form.first_name.data or "").strip()
                user.last_name = (form.last_name.data or "").strip()
                user.phone = form.phone.data
                user.role_id = role.id
                user.branch_id = branch_id
                user.account_active = bool(form.account_active.data)
                user.must_change_password = bool(form.must_change_password.data)
                user.notes = form.notes.data
                if form.password.data:
                    user.set_password(form.password.data)
                log_action(
                    action="update",
                    module="users",
                    record_type="user",
                    record_id=user.id,
                    old_value=old,
                    new_value={
                        "username": user.username,
                        "role_id": user.role_id,
                        "account_active": user.account_active,
                    },
                )
                db.session.commit()
                flash("Usuario actualizado correctamente.", "success")
                return redirect(url_for("users.index"))

    return render_template("users/form.html", title="Editar usuario", form=form, user=user)


@users_bp.route("/profile/password", methods=["GET", "POST"])
@login_required
def change_password():
    form = ProfilePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data or ""):
            flash("La contraseña actual no es correcta.", "danger")
        else:
            current_user.set_password(form.password.data or "")
            current_user.must_change_password = False
            log_action(
                action="password_change",
                module="users",
                record_type="user",
                record_id=current_user.id,
            )
            db.session.commit()
            flash("Contraseña actualizada.", "success")
            return redirect(url_for("dashboard.index"))
    return render_template("users/change_password.html", title="Cambiar contraseña", form=form)