# routes/settings.py
from flask import Blueprint, jsonify
from flask_login import login_required

settings_bp = Blueprint("settings", __name__)


@settings_bp.route("/templates", methods=["GET", "POST"])
@login_required
def handle_templates():
    return jsonify({"status": "pending implementation"})


@settings_bp.route("/stats", methods=["GET"])
@login_required
def get_stats():
    # BUG FIX: added @login_required — was missing, endpoint was publicly accessible
    return jsonify({"status": "pending implementation"})