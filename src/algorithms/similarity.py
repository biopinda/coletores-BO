"""Similarity algorithms for name matching"""

import Levenshtein
import jellyfish


def levenshtein_score(s1: str, s2: str) -> float:
    """Calculate normalized Levenshtein similarity score (0.0-1.0)"""
    if not s1 or not s2:
        return 0.0
    
    distance = Levenshtein.distance(s1, s2)
    max_len = max(len(s1), len(s2))
    
    if max_len == 0:
        return 1.0
    
    return 1.0 - (distance / max_len)


def jaro_winkler_score(s1: str, s2: str) -> float:
    """Calculate Jaro-Winkler similarity score (0.0-1.0)"""
    if not s1 or not s2:
        return 0.0
    
    return jellyfish.jaro_winkler_similarity(s1, s2)


def similarity_score(s1: str, s2: str,
                    lev_weight: float = 0.3,
                    jw_weight: float = 0.4,
                    phonetic_weight: float = 0.3) -> float:
    """
    Calculate weighted similarity score combining Levenshtein, Jaro-Winkler, and phonetic

    Args:
        s1: First string
        s2: Second string
        lev_weight: Levenshtein weight (default 0.3)
        jw_weight: Jaro-Winkler weight (default 0.4)
        phonetic_weight: Phonetic weight (default 0.3, increased for better phonetic grouping)

    Returns:
        Weighted similarity score (0.0-1.0)
    """
    # Normalize inputs
    s1_norm = s1.upper().strip()
    s2_norm = s2.upper().strip()

    # Remove dots and spaces for better comparison (e.g., "J.C.F." vs "J. C. F" vs "J.C.F")
    s1_clean = s1_norm.replace('.', '').replace(' ', '')
    s2_clean = s2_norm.replace('.', '').replace(' ', '')

    # Calculate individual scores
    lev_score = levenshtein_score(s1_norm, s2_norm)
    jw_score = jaro_winkler_score(s1_norm, s2_norm)

    # Also check without punctuation for exact match
    if s1_clean == s2_clean:
        return 1.0

    # Phonetic matching (increased weight for better grouping)
    from .phonetic import phonetic_match
    phon_score = 1.0 if phonetic_match(s1_norm, s2_norm) else 0.0

    # Weighted average
    return (lev_score * lev_weight) + (jw_score * jw_weight) + (phon_score * phonetic_weight)
