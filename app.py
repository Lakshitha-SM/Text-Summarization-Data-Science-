"""
AI Text Summarization Web Application
--------------------------------------
Main Flask application entry point.

Startup sequence:
  1. Load env vars
  2. Download NLTK data (each independently, failures are non-fatal)
  3. Load HuggingFace model (failure sets degraded flag, app still runs)
  4. Register blueprints
"""

import os
import logging
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables from .env file (if present)
load_dotenv()

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


def _download_nltk_data():
    """Download required NLTK corpora. Each is attempted independently."""
    import nltk
    for resource in ("punkt", "punkt_tab", "stopwords"):
        try:
            nltk.download(resource, quiet=True)
            logger.info("NLTK '%s' ready.", resource)
        except Exception as exc:
            logger.warning("NLTK '%s' download skipped: %s", resource, exc)


def _preload_model():
    """
    Load the HuggingFace model at startup.
    On failure the app continues in degraded (extractive-only) mode.
    """
    from summarizer.abstractive import load_model, _model_failed
    logger.info("Pre-loading summarization model — please wait …")
    try:
        load_model()
        logger.info("✅ Summarization model ready.")
    except Exception as exc:
        logger.error(
            "⚠️  Model load failed — app will run in extractive-only mode. Error: %s", exc
        )


def create_app() -> Flask:
    """Application factory."""
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # ── Configuration ──────────────────────────────────────────────────────────
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
    app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(__file__), "uploads")
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "prod-secret-key-change-me")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL", "sqlite:///app.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # ── CORS & Database ────────────────────────────────────────────────────────
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    from utils.database import init_db
    init_db(app)

    # ── NLTK & Model (startup tasks) ───────────────────────────────────────────
    _download_nltk_data()
    _preload_model()

    # ── Blueprints ─────────────────────────────────────────────────────────────
    from routes.api import api_bp
    from routes.views import views_bp

    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(views_bp)

    logger.info("🚀 Flask app ready. All blueprints registered.")
    return app


# ── Entry point ─────────────────────────────────────────────────────────────────
app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    # Debug off by default — enable via FLASK_DEBUG=true for local dev
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    logger.info("Starting development server on port %d (debug=%s) …", port, debug)
    # use_reloader=False prevents double-loading BART on low-RAM machines
    app.run(host="0.0.0.0", port=port, debug=debug, use_reloader=False)
