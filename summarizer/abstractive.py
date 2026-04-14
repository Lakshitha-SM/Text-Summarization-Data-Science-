"""
summarizer/abstractive.py
--------------------------
Abstractive text summarization using HuggingFace Transformers.
Model: facebook/bart-large-cnn (fine-tuned on CNN/DailyMail news)

The model is loaded ONCE via load_model() and reused across all requests
to avoid repeated cold-start overhead.
"""

import logging
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

logger = logging.getLogger(__name__)

# ── Global model/tokenizer objects (loaded once at startup) ─────────────────
_tokenizer = None
_model = None
MODEL_NAME = "sshleifer/distilbart-cnn-6-6"

# BART's hard token limits
BART_MAX_INPUT_TOKENS = 1024


def load_model():
    """
    Load the BART model and tokenizer into global variables.
    Call this once at app startup.
    """
    global _tokenizer, _model
    if _model is None:
        logger.info("Initializing model: %s", MODEL_NAME)
        try:
            _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
            _model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)
            
            # Move to CPU explicitly and set to eval mode
            _model.to("cpu")
            _model.eval()
            
            logger.info("Model and tokenizer ready.")
        except Exception as exc:
            logger.error("Failed to load model: %s", exc)
            raise exc
    return _model, _tokenizer


def get_model_and_tokenizer():
    """Return the cached model/tokenizer, loading them on demand if necessary."""
    global _model, _tokenizer
    if _model is None:
        logger.warning("Model not pre-loaded; loading now (may be slow).")
        load_model()
    return _model, _tokenizer


def _chunk_text(text: str, max_words: int = 800) -> list[str]:
    """
    Split text into chunks of at most `max_words` words so BART doesn't
    exceed its 1024-token input limit.
    """
    words = text.split()
    chunks = []
    for i in range(0, len(words), max_words):
        chunks.append(" ".join(words[i : i + max_words]))
    return chunks


def abstractive_summarize(text: str, length_ratio: float = 0.3, mode: str = "standard") -> str:
    """
    Summarize text abstractively with smart modes.

    Args:
        text         : The input text to summarize.
        length_ratio : Base verbosity control.
        mode         : "standard" | "short" | "detailed" | "bullets" | "eli5"

    Returns:
        Generated summary string.
    """
    text = text.strip()
    if not text:
        raise ValueError("Input text cannot be empty.")

    model, tokenizer = get_model_and_tokenizer()

    # ── Adjust parameters based on mode ──────────────────────────────────────────
    num_beams = 4
    length_penalty = 1.0
    
    if mode == "short":
        length_ratio = 0.1
        max_words_per_chunk = 400
    elif mode == "detailed":
        length_ratio = 0.5
        max_words_per_chunk = 800
    elif mode == "eli5":
        # Simulate ELI5 by encouraging simpler vocabulary and shorter sentences
        # In a production app, we might use a specific model or prompt
        length_penalty = 2.0
        max_words_per_chunk = 600
    else:
        max_words_per_chunk = 800

    chunks = _chunk_text(text, max_words=max_words_per_chunk)[:10]
    partial_summaries = []

    try:
        with torch.no_grad():
            for i, chunk in enumerate(chunks):
                inputs = tokenizer(
                    chunk, 
                    max_length=BART_MAX_INPUT_TOKENS, 
                    return_tensors="pt", 
                    truncation=True
                )
                
                input_len = inputs["input_ids"].shape[1]
                
                # Dynamic length calculation
                if mode == "short":
                    max_len = 60
                    min_len = 15
                elif mode == "detailed":
                    max_len = 300
                    min_len = 120
                elif mode == "bullets":
                    max_len = 220
                    min_len = 60
                else:
                    # Standard: at least 80 tokens, at most 200
                    max_len = max(80, min(int(input_len * length_ratio), 200))
                    min_len = max(20, int(max_len * 0.3))

                summary_ids = model.generate(
                    inputs["input_ids"],
                    num_beams=num_beams,
                    max_length=max_len,
                    min_length=min_len,
                    length_penalty=length_penalty,
                    no_repeat_ngram_size=3,  # prevents looping/repetition
                    early_stopping=True,
                    # NOTE: max_time removed — it causes mid-sentence truncation on slow CPUs
                )
                
                summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
                
                if mode == "bullets":
                    # Simple conversion to bullets by splitting on sentence boundaries
                    sentences = summary.split(". ")
                    summary = "\n".join([f"• {s.strip()}" for s in sentences if s.strip()])
                
                partial_summaries.append(summary)
                
    except Exception as exc:
        logger.error("BART generation error: %s", exc)
        raise RuntimeError(f"Abstractive summarization failed: {exc}") from exc

    return "".join(partial_summaries) if mode == "bullets" else " ".join(partial_summaries)
