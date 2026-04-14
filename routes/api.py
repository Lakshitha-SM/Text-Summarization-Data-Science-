"""
routes/api.py
--------------
REST API Blueprint for the Text Summarization application.

Fallback policy:
  - If abstractive (BART) model fails or is unavailable, _run_summarization
    automatically falls back to LSA extractive summarization.
  - /api/health reports model_status so the frontend can show a badge.
"""

import os
import logging
import time
from io import BytesIO
from flask import Blueprint, request, jsonify, current_app, send_file
from werkzeug.utils import secure_filename
from fpdf import FPDF

from summarizer.extractive import extractive_summarize
from summarizer.abstractive import abstractive_summarize, is_model_available
from utils.file_handler import allowed_file, extract_text_from_file, cleanup_file
from utils.analytics import record_summary, get_stats
from utils.analytics_engine import analyze_text
from utils.input_parser import detect_input_type
from utils.recommender import recommend_model
from utils.database import db, SummaryHistory

logger = logging.getLogger(__name__)
api_bp = Blueprint("api", __name__)

# ── Constants ────────────────────────────────────────────────────────────────────
# Keep below BART's comfortable processing range on free-tier CPU
MAX_TEXT_CHARS = 3000


# ── Helpers ──────────────────────────────────────────────────────────────────────

def _build_stats(original: str, summary: str, method: str, elapsed: float) -> dict:
    """Compute compression and timing statistics."""
    orig_words = len(original.split())
    summ_words = len(summary.split())
    compression = round((1 - summ_words / max(orig_words, 1)) * 100, 1)
    return {
        "original_words": orig_words,
        "summary_words": summ_words,
        "compression_ratio": compression,
        "processing_time_ms": round(elapsed * 1000),
        "method": method,
    }


def _run_summarization(
    text: str, method: str, length_ratio: float, mode: str = "standard"
) -> tuple[str, dict, str]:
    """
    Dispatch to the correct summarizer.

    Returns:
        (summary, stats_dict, effective_method)
        effective_method may differ from `method` when fallback kicks in.
    """
    start = time.perf_counter()
    effective_method = method

    if method == "abstractive":
        if not is_model_available():
            # Model unavailable — use extractive fallback
            logger.warning("BART unavailable; falling back to LSA extractive.")
            summary = extractive_summarize(text, length_ratio, model_type="lsa")
            effective_method = "lsa (fallback)"
        else:
            try:
                summary = abstractive_summarize(text, length_ratio, mode=mode)
            except Exception as exc:
                logger.error("BART failed (%s); falling back to LSA.", exc)
                summary = extractive_summarize(text, length_ratio, model_type="lsa")
                effective_method = "lsa (fallback)"
    else:
        # Pass method directly to extractive suite (lsa, text_rank, lex_rank)
        summary = extractive_summarize(text, length_ratio, model_type=method)

    elapsed = time.perf_counter() - start
    stats = _build_stats(text, summary, effective_method, elapsed)
    return summary, stats, effective_method


# ── Routes ────────────────────────────────────────────────────────────────────────

@api_bp.route("/health", methods=["GET"])
def health():
    """
    Health-check endpoint.
    Returns model_status so the frontend can display a live badge.
    """
    model_ok = is_model_available()
    return jsonify({
        "status": "ok",
        "model_status": "ready" if model_ok else "fallback",
        "model_name": "sshleifer/distilbart-cnn-6-6" if model_ok else "extractive-only (lsa)",
    }), 200


@api_bp.route("/summarize", methods=["POST"])
def summarize():
    """Summarize plain text with full analysis suite."""
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"success": False, "error": "Request body must be JSON."}), 400

        text = data.get("text", "").strip()
        if not text or len(text) < 50:
            return jsonify({
                "success": False,
                "error": "Text too short. Please provide at least 50 characters."
            }), 400

        # Truncate to safe processing limit
        if len(text) > MAX_TEXT_CHARS:
            text = text[:MAX_TEXT_CHARS]
            logger.info("Input truncated to %d chars.", MAX_TEXT_CHARS)

        raw_method = data.get("method", "abstractive").lower()
        method_map = {
            "lsa": "lsa",
            "text_rank": "text_rank",
            "lex_rank": "lex_rank",
            "abstractive": "abstractive",
            "extractive": "lsa",
        }
        method = method_map.get(raw_method, "abstractive")
        mode = data.get("mode", "standard").lower()
        length_ratio = float(data.get("length_ratio", 0.3))

        logger.info("Summarize: method=%s, mode=%s, chars=%d", method, mode, len(text))

        # Analysis (non-fatal)
        input_type = detect_input_type(text)
        recommendation = recommend_model(text)
        analysis = {}
        try:
            analysis = analyze_text(text)
        except Exception as ae:
            logger.warning("Analysis engine failed (non-fatal): %s", ae)

        # Summarize with automatic fallback
        summary, stats, effective_method = _run_summarization(text, method, length_ratio, mode=mode)

        # Persist to DB (non-fatal)
        try:
            entry = SummaryHistory(
                original_text=text,
                summary_text=summary,
                method=effective_method,
                input_type=input_type,
                sentiment=analysis.get("sentiment", {}).get("label", "Neutral"),
            )
            db.session.add(entry)
            db.session.commit()
        except Exception as db_err:
            logger.error("DB write failed (non-fatal): %s", db_err)

        try:
            record_summary(effective_method, from_file=False)
        except Exception:
            pass

        return jsonify({
            "success": True,
            "summary": summary,
            "stats": stats,
            "analysis": analysis,
            "input_type": input_type,
            "recommendation": recommendation,
            "fallback_used": effective_method != method,
        }), 200

    except Exception as exc:
        logger.error("Summarize API error: %s", exc, exc_info=True)
        return jsonify({"success": False, "error": f"Summarization Error: {str(exc)}"}), 500


@api_bp.route("/history", methods=["GET"])
def history():
    """Retrieve recent summary history."""
    try:
        items = SummaryHistory.query.order_by(
            SummaryHistory.created_at.desc()
        ).limit(20).all()

        history_list = []
        for item in items:
            summary_text = item.summary_text or ""
            preview = (summary_text[:200] + "…") if len(summary_text) > 200 else summary_text
            history_list.append({
                "id": item.id,
                "summary": preview,
                "full_summary": summary_text,
                "method": item.method or "unknown",
                "sentiment": item.sentiment or "Neutral",
                "timestamp": item.created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            })

        return jsonify({"success": True, "history": history_list}), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@api_bp.route("/download", methods=["POST"])
def download():
    """Generate and download a PDF version of the summary."""
    try:
        data = request.get_json(silent=True)
        if not data or "summary" not in data:
            return jsonify({"success": False, "error": "Summary text required."}), 400

        summary = data["summary"]

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(190, 10, "AI Text Analysis Report", ln=True, align="C")
        pdf.ln(10)
        pdf.set_font("Helvetica", size=12)
        pdf.multi_cell(0, 10, summary)

        pdf_bytes = pdf.output(dest="S")
        buffer = BytesIO(pdf_bytes)
        buffer.seek(0)

        return send_file(
            buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name="Summary_Report.pdf",
        )
    except Exception as exc:
        logger.error("PDF generation error: %s", exc)
        return jsonify({"success": False, "error": f"Failed to generate PDF: {str(exc)}"}), 500


@api_bp.route("/upload", methods=["POST"])
def upload():
    """File upload, text extraction, and summarization."""
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file provided."}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "error": "No file selected."}), 400

    method = request.form.get("method", "abstractive").lower()
    filename = secure_filename(file.filename)
    filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)

    try:
        file.save(filepath)
        text = extract_text_from_file(filepath)

        if len(text) < 50:
            return jsonify({"success": False, "error": "Extracted text too short."}), 400

        if len(text) > MAX_TEXT_CHARS:
            text = text[:MAX_TEXT_CHARS]

        summary, stats, effective_method = _run_summarization(text, method, 0.3)

        input_type = detect_input_type(text)
        recommendation = recommend_model(text)
        analysis = {}
        try:
            analysis = analyze_text(text)
        except Exception:
            pass

        return jsonify({
            "success": True,
            "summary": summary,
            "stats": stats,
            "analysis": analysis,
            "input_type": input_type,
            "recommendation": recommendation,
            "extracted_text": text[:500],
            "fallback_used": effective_method != method,
        }), 200

    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500
    finally:
        cleanup_file(filepath)


@api_bp.route("/analytics", methods=["GET"])
def analytics():
    """Return session stats plus per-method breakdown from DB history."""
    try:
        session_stats = get_stats()
        from sqlalchemy import func

        method_counts = db.session.query(
            SummaryHistory.method, func.count(SummaryHistory.id)
        ).group_by(SummaryHistory.method).all()

        sentiment_counts = db.session.query(
            SummaryHistory.sentiment, func.count(SummaryHistory.id)
        ).group_by(SummaryHistory.sentiment).all()

        total_db = SummaryHistory.query.count()

        return jsonify({
            "success": True,
            "stats": session_stats,
            "db_total": total_db,
            "method_counts": {m: c for m, c in method_counts},
            "sentiment_counts": {s: c for s, c in sentiment_counts},
        }), 200

    except Exception as exc:
        logger.error("Analytics error: %s", exc)
        return jsonify({
            "success": True,
            "stats": get_stats(),
            "db_total": 0,
            "method_counts": {},
            "sentiment_counts": {},
        }), 200


@api_bp.route("/compare", methods=["POST"])
def compare():
    """
    Run two summarization models on the same text and return both results.
    Body: { text, model_a, model_b, mode }
    """
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"success": False, "error": "Request body must be JSON."}), 400

        text = data.get("text", "").strip()
        if not text or len(text) < 50:
            return jsonify({"success": False, "error": "Please provide at least 50 characters."}), 400

        if len(text) > MAX_TEXT_CHARS:
            text = text[:MAX_TEXT_CHARS]

        method_map = {
            "lsa": "lsa", "text_rank": "text_rank", "lex_rank": "lex_rank",
            "abstractive": "abstractive", "extractive": "lsa",
        }
        model_a = method_map.get(data.get("model_a", "lsa"), "lsa")
        model_b = method_map.get(data.get("model_b", "text_rank"), "text_rank")
        mode = data.get("mode", "standard").lower()
        length_ratio = float(data.get("length_ratio", 0.3))

        logger.info("Compare: model_a=%s, model_b=%s", model_a, model_b)

        summary_a, stats_a, eff_a = _run_summarization(text, model_a, length_ratio, mode=mode)
        summary_b, stats_b, eff_b = _run_summarization(text, model_b, length_ratio, mode=mode)

        analysis = {}
        try:
            analysis = analyze_text(text)
        except Exception:
            pass

        return jsonify({
            "success": True,
            "text_length": len(text.split()),
            "model_a": {"name": eff_a, "summary": summary_a, "stats": stats_a},
            "model_b": {"name": eff_b, "summary": summary_b, "stats": stats_b},
            "analysis": analysis,
        }), 200

    except Exception as exc:
        logger.error("Compare error: %s", exc, exc_info=True)
        return jsonify({"success": False, "error": str(exc)}), 500
