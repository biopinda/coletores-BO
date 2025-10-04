"""Phonetic algorithms for name matching"""

import jellyfish


def phonetic_match(s1: str, s2: str) -> bool:
    """
    Check if two strings match phonetically using Metaphone
    
    Args:
        s1: First string
        s2: Second string
    
    Returns:
        True if phonetically similar, False otherwise
    """
    if not s1 or not s2:
        return False
    
    # Use Metaphone for Portuguese/Brazilian names
    code1 = jellyfish.metaphone(s1)
    code2 = jellyfish.metaphone(s2)
    
    return code1 == code2
