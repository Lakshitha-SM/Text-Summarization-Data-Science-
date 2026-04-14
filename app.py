"""
AI Text Summarization Web Application
--------------------------------------
Main Flask application entry point.
Loads the HuggingFace BART model once at startup for performance.
"""

import os
import logging
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables from .env file (if present)
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


def create_app():
    """Application factory function."""
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # ── Configuration ──────────────────────────────────────────────────────────
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
    app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(__file__), "uploads")
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "prod-secret-key-12345")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Create uploads directory if it does not exist
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # ── CORS & Database ────────────────────────────────────────────────────────
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    from utils.database import init_db
    init_db(app)

    # ── Pre-load models ────────────────────────────────────────────────────────
    # This runs once at startup so every request reuses the same pipeline object.
    logger.info("Downloading NLTK dependencies...")
    try:
        import nltk
        nltk.download('punkt', quiet=True)
        nltk.download('punkt_tab', quiet=True)
        nltk.download('stopwords', quiet=True)
        logger.info("NLTK dependencies ready.")
    except Exception as exc:
        logger.warning(f"NLTK download failed: {exc}")

    logger.info("Loading HuggingFace BART summarization model — please wait …")
    try:
        from summarizer.abstractive import load_model
        load_model()
        logger.info("BART model loaded successfully.")
    except Exception as exc:
        logger.error(f"Critical: Could not load BART model at startup: {exc}")

    # ── Blueprint registration ──────────────────────────────────────────────────
    from routes.api import api_bp
    from routes.views import views_bp

    logger.info("ROUTING DEBUG: api_bp is from %s", getattr(api_bp, '__file__', 'unknown'))

    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(views_bp)

    logger.info("Flask app created and blueprints registered.")
    return app


# ── Entry point ─────────────────────────────────────────────────────────────────
app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    logger.info("Starting development server on port %d …", port)
    # use_reloader=False prevents Flask from importing app.py twice,
    # which would double-load the BART model and crash on low-RAM machines.
    app.run(host="0.0.0.0", port=port, debug=debug, use_reloader=False)
