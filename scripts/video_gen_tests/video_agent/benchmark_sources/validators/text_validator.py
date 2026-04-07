"""Text extraction accuracy validator."""

from difflib import SequenceMatcher

def validate_text_extraction(extracted_text: str, expected_keywords: list) -> float:
    """
    Validate text extraction accuracy.

    Returns accuracy score 0.0-1.0 based on:
    - Presence of expected keywords
    - Text length is reasonable
    - Text is not error message
    """
    if not extracted_text:
        return 0.0

    extracted_lower = extracted_text.lower()

    # Check for error messages
    error_indicators = ["error", "404", "not found", "access denied", "forbidden"]
    if any(err in extracted_lower for err in error_indicators):
        return 0.1

    # Check expected keywords
    if not expected_keywords:
        return 0.5  # No expectations, assume partial success

    matches = sum(1 for keyword in expected_keywords if keyword.lower() in extracted_lower)
    keyword_score = matches / len(expected_keywords)

    # Check text length (too short = incomplete)
    length_score = 0.0
    if len(extracted_text) > 100:
        length_score = 0.3
    elif len(extracted_text) > 50:
        length_score = 0.2
    elif len(extracted_text) > 10:
        length_score = 0.1

    total_score = (keyword_score * 0.7) + (length_score * 0.3)
    return min(1.0, total_score)
