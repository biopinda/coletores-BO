"""Similarity algorithms for name matching (Levenshtein + Jaro-Winkler)"""

import Levenshtein
import jellyfish


def levenshtein_score(s1: str, s2: str) -> float:
    """
    Calculate normalized Levenshtein similarity score.

    Args:
        s1: First string
        s2: Second string

    Returns:
        Similarity score between 0.0 and 1.0
    """
    if not s1 or not s2:
        return 0.0

    distance = Levenshtein.distance(s1, s2)
    max_len = max(len(s1), len(s2))

    if max_len == 0:
        return 1.0

    return 1.0 - (distance / max_len)


def jaro_winkler_score(s1: str, s2: str) -> float:
    """
    Calculate Jaro-Winkler similarity score.

    Args:
        s1: First string
        s2: Second string

    Returns:
        Similarity score between 0.0 and 1.0
    """
    if not s1 or not s2:
        return 0.0

    return jellyfish.jaro_winkler_similarity(s1, s2)


def similarity_score(
    s1: str, s2: str, lev_weight: float = 0.4, jw_weight: float = 0.4, phonetic_weight: float = 0.2
) -> float:
    """
    Calculate combined similarity score using weighted average.

    Args:
        s1: First string
        s2: Second string
        lev_weight: Weight for Levenshtein score (default: 0.4)
        jw_weight: Weight for Jaro-Winkler score (default: 0.4)
        phonetic_weight: Weight for phonetic score (default: 0.2)

    Returns:
        Combined similarity score between 0.0 and 1.0
    """
    from src.algorithms.phonetic import phonetic_match

    lev = levenshtein_score(s1, s2)
    jw = jaro_winkler_score(s1, s2)
    phonetic = 1.0 if phonetic_match(s1, s2) else 0.0

    return (lev * lev_weight) + (jw * jw_weight) + (phonetic * phonetic_weight)
