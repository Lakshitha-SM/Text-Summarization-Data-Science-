"""
utils/input_parser.py
-----------------------
Utility to detect input type (Article, Resume, Research Paper, etc.)
"""

import re

def detect_input_type(text: str) -> str:
    """
    Heuristically detect the type of input text.
    """
    text_lower = text.lower()
    
    # Check for Resume
    resume_keywords = ["education", "experience", "skills", "projects", "certifications", "summary"]
    if sum(1 for word in resume_keywords if word in text_lower) >= 3:
        return "Resume / CV"
    
    # Check for Research Paper
    research_keywords = ["abstract", "introduction", "methodology", "results", "conclusion", "references", "cite", "et al."]
    if sum(1 for word in research_keywords if word in text_lower) >= 3:
        return "Research Paper"
    
    # Check for Email
    if "subject:" in text_lower or (re.search(r"dear\s+[a-z]+", text_lower) and re.search(r"sincerely|best regards|thanks", text_lower)):
        return "Email / Letter"
    
    # Check for Article
    if len(text.split()) > 300:
        return "Article / Long-form Text"
        
    return "General Text"
