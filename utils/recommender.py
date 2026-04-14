"""
utils/recommender.py
---------------------
Logic to recommend the best summarization model based on input characteristics.
"""

def recommend_model(text: str) -> dict:
    """
    Recommend the best model based on text length and complexity.
    """
    word_count = len(text.split())
    
    if word_count < 100:
        return {
            "recommended": "abstractive",
            "reason": "Short text benefits from abstractive rephrasing for better flow.",
            "mode": "short"
        }
    elif word_count > 2000:
        return {
            "recommended": "lex_rank",
            "reason": "Very long text is best handled by extractive methods for speed and coherence.",
            "mode": "standard"
        }
    elif "abstract" in text.lower() or "methodology" in text.lower():
        return {
            "recommended": "lsa",
            "reason": "Academic/Research text works well with LSA semantic extraction.",
            "mode": "standard"
        }
    else:
        return {
            "recommended": "abstractive",
            "reason": "Standard articles are best handled by Transformer models for high-quality summaries.",
            "mode": "standard"
        }
