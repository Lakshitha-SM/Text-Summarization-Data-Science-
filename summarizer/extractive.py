"""
summarizer/extractive.py
------------------------
Extractive text summarization suite supporting LSA, TextRank, and LexRank.
"""

import logging
import math
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
from sumy.summarizers.text_rank import TextRankSummarizer
from sumy.summarizers.lex_rank import LexRankSummarizer
from sumy.nlp.stemmers import Stemmer
from sumy.utils import get_stop_words

logger = logging.getLogger(__name__)

LANGUAGE = "english"

def extractive_summarize(text: str, length_ratio: float = 0.3, model_type: str = "lsa") -> str:
    """
    Summarize text extractively using LSA, TextRank, or LexRank.
    """
    text = text.strip()
    if not text:
        raise ValueError("Input text cannot be empty.")
    
    try:
        parser = PlaintextParser.from_string(text, Tokenizer(LANGUAGE))
        total_sentences = list(parser.document.sentences)
        
        if len(total_sentences) < 2:
            return text

        length_ratio = max(0.05, min(length_ratio, 0.9))
        sentences_count = max(1, math.ceil(len(total_sentences) * length_ratio))
        
        stemmer = Stemmer(LANGUAGE)
        
        # ── Model Selection (Safe Dispatch) ──
        if model_type == "text_rank":
            summarizer = TextRankSummarizer(stemmer)
        elif model_type == "lex_rank":
            summarizer = LexRankSummarizer(stemmer)
        else:
            # Default to LSA (Latent Semantic Analysis)
            summarizer = LsaSummarizer(stemmer)
            
        summarizer.stop_words = get_stop_words(LANGUAGE)

        # ── Run ──
        summary_sentences = summarizer(parser.document, sentences_count)
        summary = " ".join(str(sentence) for sentence in summary_sentences)

        return summary or str(total_sentences[0])
    except Exception as exc:
        logger.error(f"Extractive engine failure ({model_type}): {exc}")
        raise RuntimeError(f"Extractive Engine Error: {exc}")
