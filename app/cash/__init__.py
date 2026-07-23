from flask import Blueprint

cash_bp = Blueprint("cash", __name__, url_prefix="/cash")
from app.cash import routes  # noqa: E402, F401