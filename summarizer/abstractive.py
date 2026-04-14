"""
summarizer/abstractive.py
--------------------------
Abstractive text summarization using HuggingFace Transformers.
Model: sshleifer/tiny-distilbart-cnn-6-6 (~70 MB, CPU-optimized)

Design:
  - Model is loaded ONCE at startup and cached globally.
  - Results are cached via functools.lru_cache to avoid re-running
    the model on identical inputs.
  - If load fails, _model_failed is set True so callers can fallback
    to extractive summarization immediately.
"""

import logging
import hashlib
import torch
from functools import lru_cache
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

logger = logging.getLogger(__name__)

# ── Global state ────────────────────────────────────────────────────────────────
_tokenizer = None
_model = None
_model_failed = False          # Set True on load failure; signals routes to fallback

# distilbart-cnn-6-6: ~460 MB, 6 encoder + 6 decoder layers
# Lightest publicly available DistilBART variant on HuggingFace
# (tiny-distilbart no longer exists as a public model)
MODEL_NAME = "sshleifer/distilbart-cnn-6-6"

# BART's hard token limit
BART_MAX_INPUT_TOKENS = 1024


def is_model_available() -> bool:
    """Return True if the model is loaded and ready."""
    return _model is not None and not _model_failed


def load_model():
    """
    Load the BART tokenizer and model into global variables.
    Call this ONCE at app startup.
    Sets _model_failed=True if loading is impossible.
    """
    global _tokenizer, _model, _model_failed

    if _model is not None:
        return _model, _tokenizer          # Already loaded

    logger.info("Loading model: %s …", MODEL_NAME)
    try:
        _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        _model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)
        _model.to("cpu")
        _model.eval()
        logger.info("✅ Model loaded successfully: %s", MODEL_NAME)
        _model_failed = False
    except Exception as exc:
        _model_failed = True
        logger.error("❌ Failed to load model '%s': %s", MODEL_NAME, exc)
        raise RuntimeError(f"Model load failed: {exc}") from exc

    return _model, _tokenizer


def get_model_and_tokenizer():
    """Return cached model/tokenizer, loading on demand if not yet loaded."""
    global _model, _tokenizer
    if _model is None and not _model_failed:
        logger.warning("Model not pre-loaded; loading on first request (may be slow).")
        load_model()
    if _model_failed or _model is None:
        raise RuntimeError("Abstractive model is unavailable. Using extractive fallback.")
    return _model, _tokenizer


# ── Simple in-memory result cache ───────────────────────────────────────────────
_result_cache: dict = {}
MAX_CACHE_SIZE = 50


def _cache_key(text: str, mode: str, length_ratio: float) -> str:
    """Generate a stable cache key from the first 300 chars + mode + ratio."""
    raw = f"{text[:300]}|{mode}|{length_ratio:.2f}"
    return hashlib.md5(raw.encode()).hexdigest()


def _chunk_text(text: str, max_words: int = 400) -> list[str]:
    """
    Split text into chunks of at most `max_words` words so BART doesn't
    exceed its 1024-token input limit. Reduced default to 400 for low-RAM
    environments.
    """
    words = text.split()
    return [" ".join(words[i: i + max_words]) for i in range(0, len(words), max_words)]


def abstractive_summarize(text: str, length_ratio: float = 0.3, mode: str = "standard") -> str:
    """
    Summarize text abstractively.

    Args:
        text         : Input text to summarize.
        length_ratio : Verbosity control (0.1 – 0.9).
        mode         : "standard" | "short" | "detailed" | "bullets" | "eli5"

    Returns:
        Generated summary string.

    Raises:
        RuntimeError if the model is not available.
    """
    text = text.strip()
    if not text:
        raise ValueError("Input text cannot be empty.")

    # ── Cache lookup ──────────────────────────────────────────────────────────
    key = _cache_key(text, mode, length_ratio)
    if key in _result_cache:
        logger.info("Cache hit for abstractive summarization.")
        return _result_cache[key]

    model, tokenizer = get_model_and_tokenizer()

    # ── Mode parameters ───────────────────────────────────────────────────────
    num_beams = 2          # Reduced from 4 → saves ~50% CPU time on free tier
    length_penalty = 1.0
    max_words_per_chunk = 400

    if mode == "short":
        length_ratio = 0.1
        max_words_per_chunk = 300
    elif mode == "detailed":
        length_ratio = 0.5
        max_words_per_chunk = 400
    elif mode == "eli5":
        length_penalty = 2.0
        max_words_per_chunk = 350

    # Limit to 5 chunks max (≈2000 words) — prevents RAM exhaustion
    chunks = _chunk_text(text, max_words=max_words_per_chunk)[:5]
    partial_summaries = []

    try:
        with torch.no_grad():
            for chunk in chunks:
                inputs = tokenizer(
                    chunk,
                    max_length=BART_MAX_INPUT_TOKENS,
                    return_tensors="pt",
                    truncation=True
                )

                input_len = inputs["input_ids"].shape[1]

                if mode == "short":
                    max_len, min_len = 60, 15
                elif mode == "detailed":
                    max_len, min_len = 250, 80
                elif mode == "bullets":
                    max_len, min_len = 180, 50
                else:
                    max_len = max(60, min(int(input_len * length_ratio), 180))
                    min_len = max(15, int(max_len * 0.3))

                summary_ids = model.generate(
                    inputs["input_ids"],
                    num_beams=num_beams,
                    max_length=max_len,
                    min_length=min_len,
                    length_penalty=length_penalty,
                    no_repeat_ngram_size=3,
                    early_stopping=True,
                )

                summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)

                if mode == "bullets":
                    sentences = summary.split(". ")
                    summary = "\n".join(f"• {s.strip()}" for s in sentences if s.strip())

                partial_summaries.append(summary)

    except Exception as exc:
        logger.error("BART generation error: %s", exc)
        raise RuntimeError(f"Abstractive summarization failed: {exc}") from exc

    result = "\n\n".join(partial_summaries) if mode == "bullets" else " ".join(partial_summaries)

    # ── Cache store (evict oldest if full) ────────────────────────────────────
    if len(_result_cache) >= MAX_CACHE_SIZE:
        oldest_key = next(iter(_result_cache))
        del _result_cache[oldest_key]
    _result_cache[key] = result

    return result
