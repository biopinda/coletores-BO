"""
Phonetic Similarity Calculator Service

This service provides phonetic similarity calculation using multiple algorithms
optimized for Portuguese names and collector identification. It supports various
phonetic algorithms and provides configurable similarity metrics for the
canonicalization system.
"""

import logging
import re
from typing import Dict, List, Optional, Tuple, Set, Any
from dataclasses import dataclass
from collections import defaultdict
import unicodedata

# Import phonetic libraries
try:
    from metaphone import doublemetaphone
    METAPHONE_AVAILABLE = True
except ImportError:
    METAPHONE_AVAILABLE = False
    logging.warning("Metaphone library not available. Install with: pip install metaphone")

try:
    import soundex as soundex_lib
    SOUNDEX_AVAILABLE = True
except ImportError:
    SOUNDEX_AVAILABLE = False


@dataclass
class PhoneticConfig:
    """Configuration for phonetic similarity calculations"""

    # Algorithm weights (sum should be 1.0)
    metaphone_weight: float = 0.4
    soundex_weight: float = 0.3
    portuguese_phonetic_weight: float = 0.3

    # Portuguese-specific settings
    normalize_portuguese: bool = True
    handle_double_letters: bool = True
    consonant_groups_similarity: bool = True

    # Similarity thresholds
    high_similarity_threshold: float = 0.85
    medium_similarity_threshold: float = 0.65

    # Performance settings
    cache_size: int = 10000
    enable_preprocessing: bool = True


@dataclass
class PhoneticResult:
    """Result of phonetic similarity calculation"""

    name1: str
    name2: str
    overall_similarity: float

    # Individual algorithm scores
    metaphone_similarity: float = 0.0
    soundex_similarity: float = 0.0
    portuguese_similarity: float = 0.0

    # Phonetic codes
    metaphone_codes: Dict[str, Tuple[str, str]] = None
    soundex_codes: Dict[str, str] = None
    portuguese_codes: Dict[str, str] = None

    # Classification
    similarity_level: str = "low"  # low, medium, high


class PortuguesePhonetic:
    """
    Portuguese-specific phonetic algorithm optimized for Brazilian names

    This algorithm handles Portuguese-specific phonetic patterns common in
    collector names, including Brazilian and Portuguese naming conventions.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Portuguese phonetic rules
        self.consonant_rules = {
            # Portuguese-specific consonant transformations
            'ç': 's',
            'ch': 'x',
            'lh': 'y',
            'nh': 'n',
            'ph': 'f',
            'th': 't',
            'rr': 'r',
            'll': 'l',
            'ss': 's',
            'sc': 's',
            'sç': 's'
        }

        self.vowel_rules = {
            # Vowel normalizations
            'á': 'a', 'à': 'a', 'â': 'a', 'ã': 'a',
            'é': 'e', 'ê': 'e',
            'í': 'i',
            'ó': 'o', 'ô': 'o', 'õ': 'o',
            'ú': 'u', 'ü': 'u'
        }

        # Common Portuguese surname patterns
        self.surname_patterns = {
            r'\bde\s+': '',      # "de Silva" -> "Silva"
            r'\bda\s+': '',      # "da Costa" -> "Costa"
            r'\bdo\s+': '',      # "do Santos" -> "Santos"
            r'\bdos\s+': '',     # "dos Santos" -> "Santos"
            r'\bdas\s+': '',     # "das Neves" -> "Neves"
            r'\be\s+': '',       # "Silva e Costa" -> "Silva Costa"
        }

    def encode(self, name: str) -> str:
        """
        Generate Portuguese phonetic code for a name

        Args:
            name: Input name to encode

        Returns:
            Phonetic code string
        """
        if not name:
            return ""

        # Normalize and clean
        code = self._normalize_name(name)

        # Apply Portuguese phonetic rules
        code = self._apply_portuguese_rules(code)

        # Generate final phonetic code
        code = self._generate_phonetic_code(code)

        return code

    def _normalize_name(self, name: str) -> str:
        """Normalize name for phonetic processing"""

        # Convert to lowercase
        normalized = name.lower().strip()

        # Remove accents and diacritics
        normalized = unicodedata.normalize('NFD', normalized)
        normalized = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')

        # Apply vowel rules
        for accented, base in self.vowel_rules.items():
            normalized = normalized.replace(accented, base)

        # Remove common Portuguese prepositions and articles
        for pattern, replacement in self.surname_patterns.items():
            normalized = re.sub(pattern, replacement, normalized)

        # Remove non-alphabetic characters except spaces
        normalized = re.sub(r'[^a-z\s]', '', normalized)

        # Normalize whitespace
        normalized = ' '.join(normalized.split())

        return normalized

    def _apply_portuguese_rules(self, name: str) -> str:
        """Apply Portuguese-specific phonetic transformation rules"""

        # Apply consonant rules
        for pattern, replacement in self.consonant_rules.items():
            name = name.replace(pattern, replacement)

        # Handle Portuguese-specific patterns
        transformations = [
            # Silent letters in Portuguese context
            (r'\bh', ''),           # Silent h at beginning
            (r'([aeiou])h', r'\1'), # Silent h after vowels

            # Portuguese consonant clusters
            (r'([aeiou])x([aeiou])', r'\1s\2'),  # "exame" -> "esame"
            (r'x$', 's'),                        # "Felix" -> "Felis"
            (r'^x', 's'),                        # "Xavier" -> "Savier"

            # Double consonants
            (r'([bcdfgjklmnpqrstvwxyz])\1+', r'\1'),  # Remove double consonants

            # Portuguese sound patterns
            (r'qu', 'k'),           # "que" -> "ke"
            (r'gu([ei])', r'g\1'),  # "guerra" -> "gerra"

            # Final consonant patterns
            (r'([aeiou])r$', r'\1'), # Silent final r in some cases
            (r'([aeiou])l$', r'\1'), # Silent final l in some cases
        ]

        for pattern, replacement in transformations:
            name = re.sub(pattern, replacement, name)

        return name

    def _generate_phonetic_code(self, name: str) -> str:
        """Generate final phonetic code from processed name"""

        words = name.split()
        codes = []

        for word in words:
            if len(word) < 2:
                continue

            # Keep first letter and process remainder
            code = word[0]

            # Process consonants and vowels
            prev_char = word[0]
            for char in word[1:]:
                if char != prev_char:  # Avoid duplicates
                    if char in 'aeiou':
                        # Keep vowels but encode them
                        if len(code) == 1 or code[-1] not in 'aeiou':
                            code += char
                    else:
                        # Keep consonants
                        code += char
                    prev_char = char

            # Limit code length
            if len(code) > 6:
                code = code[:6]

            codes.append(code)

        return '_'.join(codes)


class PhoneticSimilarityCalculator:
    """
    Multi-algorithm phonetic similarity calculator for collector names

    Combines multiple phonetic algorithms with configurable weights to provide
    robust similarity scoring for Portuguese and international names.
    """

    def __init__(self, config: Optional[PhoneticConfig] = None):
        """
        Initialize phonetic calculator

        Args:
            config: Optional configuration for phonetic algorithms
        """
        self.config = config or PhoneticConfig()
        self.logger = logging.getLogger(__name__)

        # Initialize phonetic engines
        self.portuguese_phonetic = PortuguesePhonetic()

        # Result cache for performance
        self._similarity_cache: Dict[str, float] = {}
        self._phonetic_cache: Dict[str, Dict[str, str]] = {}

        # Validate configuration
        self._validate_config()

        self.logger.info(f"PhoneticSimilarityCalculator initialized with config: {self.config}")

    def _validate_config(self):
        """Validate phonetic configuration"""

        total_weight = (self.config.metaphone_weight +
                       self.config.soundex_weight +
                       self.config.portuguese_phonetic_weight)

        if abs(total_weight - 1.0) > 0.01:
            self.logger.warning(f"Algorithm weights do not sum to 1.0 (sum: {total_weight})")

        if not METAPHONE_AVAILABLE and self.config.metaphone_weight > 0:
            self.logger.warning("Metaphone not available but weight > 0. Consider installing metaphone library.")

        if not SOUNDEX_AVAILABLE and self.config.soundex_weight > 0:
            self.logger.warning("Soundex not available but weight > 0. Consider installing soundex library.")

    def calculate_similarity(self, name1: str, name2: str) -> PhoneticResult:
        """
        Calculate phonetic similarity between two names

        Args:
            name1: First name for comparison
            name2: Second name for comparison

        Returns:
            PhoneticResult with similarity scores and codes
        """
        # Create cache key
        cache_key = f"{name1.lower()}|{name2.lower()}"
        if cache_key in self._similarity_cache and len(self._similarity_cache) < self.config.cache_size:
            # Return cached result (simplified)
            similarity = self._similarity_cache[cache_key]
            return PhoneticResult(
                name1=name1,
                name2=name2,
                overall_similarity=similarity,
                similarity_level=self._classify_similarity(similarity)
            )

        # Preprocess names
        if self.config.enable_preprocessing:
            processed_name1 = self._preprocess_name(name1)
            processed_name2 = self._preprocess_name(name2)
        else:
            processed_name1 = name1
            processed_name2 = name2

        # Calculate individual algorithm similarities
        metaphone_sim = self._calculate_metaphone_similarity(processed_name1, processed_name2)
        soundex_sim = self._calculate_soundex_similarity(processed_name1, processed_name2)
        portuguese_sim = self._calculate_portuguese_similarity(processed_name1, processed_name2)

        # Calculate weighted overall similarity
        overall_sim = (
            metaphone_sim * self.config.metaphone_weight +
            soundex_sim * self.config.soundex_weight +
            portuguese_sim * self.config.portuguese_phonetic_weight
        )

        # Get phonetic codes for reference
        metaphone_codes = self._get_metaphone_codes(processed_name1, processed_name2)
        soundex_codes = self._get_soundex_codes(processed_name1, processed_name2)
        portuguese_codes = self._get_portuguese_codes(processed_name1, processed_name2)

        # Cache result
        self._similarity_cache[cache_key] = overall_sim

        # Create result
        result = PhoneticResult(
            name1=name1,
            name2=name2,
            overall_similarity=overall_sim,
            metaphone_similarity=metaphone_sim,
            soundex_similarity=soundex_sim,
            portuguese_similarity=portuguese_sim,
            metaphone_codes=metaphone_codes,
            soundex_codes=soundex_codes,
            portuguese_codes=portuguese_codes,
            similarity_level=self._classify_similarity(overall_sim)
        )

        return result

    def _preprocess_name(self, name: str) -> str:
        """Preprocess name for phonetic comparison"""

        if not name:
            return ""

        # Basic cleaning
        processed = name.strip().lower()

        # Remove common titles and prefixes
        prefixes_to_remove = [
            r'\bdr\.?\s+',       # Dr., Dr
            r'\bprof\.?\s+',     # Prof., Prof
            r'\bmr\.?\s+',       # Mr., Mr
            r'\bmrs\.?\s+',      # Mrs., Mrs
            r'\bms\.?\s+',       # Ms., Ms
            r'\bsra?\.?\s+',     # Sr., Sra., Sr, Sra
        ]

        for prefix in prefixes_to_remove:
            processed = re.sub(prefix, '', processed, flags=re.IGNORECASE)

        # Normalize whitespace
        processed = ' '.join(processed.split())

        return processed

    def _calculate_metaphone_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity using Double Metaphone algorithm"""

        if not METAPHONE_AVAILABLE or not name1 or not name2:
            return 0.0

        try:
            # Get metaphone codes for both names
            codes1 = doublemetaphone(name1)
            codes2 = doublemetaphone(name2)

            # Compare primary and secondary codes
            max_similarity = 0.0

            for code1 in codes1:
                for code2 in codes2:
                    if code1 and code2:
                        if code1 == code2:
                            max_similarity = max(max_similarity, 1.0)
                        else:
                            # Calculate partial similarity
                            similarity = self._string_similarity(code1, code2)
                            max_similarity = max(max_similarity, similarity)

            return max_similarity

        except Exception as e:
            self.logger.warning(f"Metaphone calculation error for '{name1}' vs '{name2}': {e}")
            return 0.0

    def _calculate_soundex_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity using Soundex algorithm"""

        if not SOUNDEX_AVAILABLE or not name1 or not name2:
            return 0.0

        try:
            # Generate soundex codes
            soundex1 = soundex_lib.soundex(name1)
            soundex2 = soundex_lib.soundex(name2)

            if soundex1 == soundex2:
                return 1.0
            else:
                # Calculate partial similarity
                return self._string_similarity(soundex1, soundex2)

        except Exception as e:
            self.logger.warning(f"Soundex calculation error for '{name1}' vs '{name2}': {e}")
            return 0.0

    def _calculate_portuguese_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity using Portuguese-specific phonetic algorithm"""

        if not name1 or not name2:
            return 0.0

        try:
            # Generate Portuguese phonetic codes
            code1 = self.portuguese_phonetic.encode(name1)
            code2 = self.portuguese_phonetic.encode(name2)

            if code1 == code2:
                return 1.0
            else:
                # Calculate similarity between codes
                return self._string_similarity(code1, code2)

        except Exception as e:
            self.logger.warning(f"Portuguese phonetic calculation error for '{name1}' vs '{name2}': {e}")
            return 0.0

    def _string_similarity(self, str1: str, str2: str) -> float:
        """Calculate string similarity using Levenshtein distance"""

        if str1 == str2:
            return 1.0

        if not str1 or not str2:
            return 0.0

        # Calculate Levenshtein distance
        len1, len2 = len(str1), len(str2)

        # Create matrix
        matrix = [[0] * (len2 + 1) for _ in range(len1 + 1)]

        # Initialize first row and column
        for i in range(len1 + 1):
            matrix[i][0] = i
        for j in range(len2 + 1):
            matrix[0][j] = j

        # Fill matrix
        for i in range(1, len1 + 1):
            for j in range(1, len2 + 1):
                if str1[i-1] == str2[j-1]:
                    cost = 0
                else:
                    cost = 1

                matrix[i][j] = min(
                    matrix[i-1][j] + 1,      # deletion
                    matrix[i][j-1] + 1,      # insertion
                    matrix[i-1][j-1] + cost  # substitution
                )

        # Calculate similarity as 1 - (distance / max_length)
        distance = matrix[len1][len2]
        max_length = max(len1, len2)

        similarity = 1.0 - (distance / max_length) if max_length > 0 else 0.0

        return max(0.0, similarity)

    def _get_metaphone_codes(self, name1: str, name2: str) -> Dict[str, Tuple[str, str]]:
        """Get Metaphone codes for both names"""

        if not METAPHONE_AVAILABLE:
            return {}

        try:
            return {
                name1: doublemetaphone(name1),
                name2: doublemetaphone(name2)
            }
        except Exception:
            return {}

    def _get_soundex_codes(self, name1: str, name2: str) -> Dict[str, str]:
        """Get Soundex codes for both names"""

        if not SOUNDEX_AVAILABLE:
            return {}

        try:
            return {
                name1: soundex_lib.soundex(name1),
                name2: soundex_lib.soundex(name2)
            }
        except Exception:
            return {}

    def _get_portuguese_codes(self, name1: str, name2: str) -> Dict[str, str]:
        """Get Portuguese phonetic codes for both names"""

        try:
            return {
                name1: self.portuguese_phonetic.encode(name1),
                name2: self.portuguese_phonetic.encode(name2)
            }
        except Exception:
            return {}

    def _classify_similarity(self, similarity: float) -> str:
        """Classify similarity score into level"""

        if similarity >= self.config.high_similarity_threshold:
            return "high"
        elif similarity >= self.config.medium_similarity_threshold:
            return "medium"
        else:
            return "low"

    def batch_calculate_similarities(
        self,
        name_pairs: List[Tuple[str, str]]
    ) -> List[PhoneticResult]:
        """
        Calculate similarities for multiple name pairs efficiently

        Args:
            name_pairs: List of (name1, name2) tuples

        Returns:
            List of PhoneticResult objects
        """
        results = []

        for name1, name2 in name_pairs:
            try:
                result = self.calculate_similarity(name1, name2)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Error calculating similarity for '{name1}' vs '{name2}': {e}")
                # Add error result
                results.append(PhoneticResult(
                    name1=name1,
                    name2=name2,
                    overall_similarity=0.0,
                    similarity_level="error"
                ))

        return results

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""

        return {
            'cache_size': len(self._similarity_cache),
            'max_cache_size': self.config.cache_size,
            'cache_hit_rate': 'Not tracked',  # Could be implemented
            'algorithms_available': {
                'metaphone': METAPHONE_AVAILABLE,
                'soundex': SOUNDEX_AVAILABLE,
                'portuguese': True
            }
        }

    def clear_cache(self):
        """Clear similarity cache"""

        self._similarity_cache.clear()
        self._phonetic_cache.clear()
        self.logger.info("Phonetic similarity cache cleared")