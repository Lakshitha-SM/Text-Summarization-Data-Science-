"""
routes/views.py
----------------
Serves the single-page frontend of the application.
"""

from flask import Blueprint, render_template

views_bp = Blueprint("views", __name__)


@views_bp.route("/")
def index():
    """Render the main application page."""
    return render_template("index.html")
