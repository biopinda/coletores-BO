"""Phonetic matching using Metaphone algorithm"""

import jellyfish


def phonetic_match(s1: str, s2: str) -> bool:
    """
    Check if two strings are phonetically similar using Metaphone.

    Args:
        s1: First string
        s2: Second string

    Returns:
        True if phonetic codes match, False otherwise
    """
    if not s1 or not s2:
        return False

    # Get metaphone codes for both strings
    code1 = jellyfish.metaphone(s1)
    code2 = jellyfish.metaphone(s2)

    return code1 == code2


def phonetic_code(s: str) -> str:
    """
    Get the phonetic code for a string.

    Args:
        s: Input string

    Returns:
        Metaphone phonetic code
    """
    if not s:
        return ""

    return jellyfish.metaphone(s)
