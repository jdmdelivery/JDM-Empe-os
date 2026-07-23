from flask import Blueprint

pawn_bp = Blueprint("pawn", __name__, url_prefix="/pawn")
from app.pawn import routes  # noqa: E402, F401