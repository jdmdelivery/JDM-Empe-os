from flask import Blueprint

renewals_bp = Blueprint("renewals", __name__, url_prefix="/renewals")
from app.renewals import routes  # noqa: E402, F401