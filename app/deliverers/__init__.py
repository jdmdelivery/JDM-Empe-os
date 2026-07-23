"""Blueprint de persona que entrega."""

from flask import Blueprint

deliverers_bp = Blueprint("deliverers", __name__, url_prefix="/deliverers")

from app.deliverers import routes  # noqa: E402, F401