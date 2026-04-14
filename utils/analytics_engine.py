"""
utils/analytics_engine.py
--------------------------
Engine for semantic analysis, sentiment detection, and readability metrics.
"""

import logging
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import textstat
from rake_nltk import Rake
import nltk

logger = logging.getLogger(__name__)

# Initialize VADER
analyzer = SentimentIntensityAnalyzer()

def analyze_text(text: str) -> dict:
    """
    Perform a full suite of text analysis.

    Returns:
        A dictionary containing sentiment, readability, keywords, and tone.
    """
    if not text or len(text.strip()) < 10:
        return {}

    try:
        # 1. Sentiment Analysis (Hybrid VADER + TextBlob)
        vader_scores = analyzer.polarity_scores(text)
        blob = TextBlob(text)
        
        sentiment = "Neutral"
        if vader_scores['compound'] >= 0.05:
            sentiment = "Positive"
        elif vader_scores['compound'] <= -0.05:
            sentiment = "Negative"

        # 2. Readability Metrics
        readability_score = textstat.flesch_reading_ease(text)
        readability_grade = textstat.flesch_kincaid_grade(text)
        
        # 3. Keyword Extraction (RAKE)
        r = Rake()
        r.extract_keywords_from_text(text)
        keywords = r.get_ranked_phrases()[:10]  # Top 10

        # 4. Tone Detection (Heuristic based on subjectivity and polarity)
        subjectivity = blob.sentiment.subjectivity
        tone = "Technical/Formal"
        if subjectivity > 0.5:
            tone = "Informal/Opinionated"
        elif any(word in text.lower() for word in ["how to", "step", "guide"]):
            tone = "Instructional"
        
        return {
            "sentiment": {
                "label": sentiment,
                "score": vader_scores['compound'],
                "subjectivity": round(subjectivity, 2)
            },
            "readability": {
                "flesch_score": readability_score,
                "grade_level": readability_grade,
                "interpretation": _interpret_readability(readability_score)
            },
            "keywords": keywords,
            "tone": tone,
            "word_count": len(text.split()),
            "reading_time_min": round(len(text.split()) / 200, 1) # Avg 200 wpm
        }
    except Exception as exc:
        logger.error(f"Text analysis error: {exc}")
        return {}

def _interpret_readability(score: float) -> str:
    if score >= 90: return "Very Easy"
    if score >= 80: return "Easy"
    if score >= 70: return "Fairly Easy"
    if score >= 60: return "Standard"
    if score >= 50: return "Fairly Difficult"
    if score >= 30: return "Difficult"
    return "Very Confusing"
