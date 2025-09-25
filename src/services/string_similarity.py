"""
String Similarity Calculator Service

This service provides various string similarity algorithms optimized for collector
name comparison, including exact matching, fuzzy matching, and Portuguese-specific
text processing. It complements the phonetic similarity calculator with orthographic
similarity measures.
"""

import logging
import re
import unicodedata
from typing import Dict, List, Optional, Tuple, Set, Any
from dataclasses import dataclass
from collections import defaultdict
import difflib

# Optional imports for advanced algorithms
try:
    from fuzzywuzzy import fuzz, process
    FUZZYWUZZY_AVAILABLE = True
except ImportError:
    FUZZYWUZZY_AVAILABLE = False
    logging.warning("FuzzyWuzzy library not available. Install with: pip install fuzzywuzzy python-levenshtein")


@dataclass
class SimilarityConfig:
    """Configuration for string similarity calculations"""

    # Algorithm weights (should sum to 1.0)
    exact_weight: float = 0.25
    levenshtein_weight: float = 0.25
    jaro_winkler_weight: float = 0.25
    fuzzy_weight: float = 0.25

    # Thresholds
    high_similarity_threshold: float = 0.90
    medium_similarity_threshold: float = 0.70
    low_similarity_threshold: float = 0.50

    # Preprocessing options
    normalize_case: bool = True
    normalize_accents: bool = True
    normalize_whitespace: bool = True
    remove_punctuation: bool = True

    # Portuguese-specific processing
    handle_portuguese_contractions: bool = True
    normalize_prepositions: bool = True
    handle_abbreviations: bool = True

    # Performance settings
    cache_enabled: bool = True
    cache_size: int = 10000


@dataclass
class SimilarityResult:
    """Result of string similarity calculation"""

    string1: str
    string2: str
    overall_similarity: float

    # Individual algorithm scores
    exact_match: bool = False
    levenshtein_similarity: float = 0.0
    jaro_winkler_similarity: float = 0.0
    fuzzy_similarity: float = 0.0

    # Processed strings used in comparison
    processed_string1: str = ""
    processed_string2: str = ""

    # Similarity classification
    similarity_level: str = "low"  # low, medium, high, exact

    # Additional metrics
    length_difference: int = 0
    common_tokens: Set[str] = None
    unique_tokens: Set[str] = None


class PortugueseStringProcessor:
    """
    Portuguese-specific string preprocessing for collector names

    Handles Portuguese-specific text normalization including contractions,
    prepositions, abbreviations, and naming conventions common in Brazil.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Portuguese contractions and prepositions
        self.contractions = {
            r'\bda\s+': 'da ',
            r'\bde\s+': 'de ',
            r'\bdo\s+': 'do ',
            r'\bdos\s+': 'dos ',
            r'\bdas\s+': 'das ',
            r'\bna\s+': 'na ',
            r'\bno\s+': 'no ',
            r'\bnos\s+': 'nos ',
            r'\bnas\s+': 'nas ',
            r'\bpela\s+': 'pela ',
            r'\bpelo\s+': 'pelo ',
            r'\bpelos\s+': 'pelos ',
            r'\bpelas\s+': 'pelas ',
        }

        # Common Portuguese abbreviations in names
        self.abbreviations = {
            r'\bdr\.?\s*': 'doutor ',
            r'\bdra\.?\s*': 'doutora ',
            r'\bprof\.?\s*': 'professor ',
            r'\bprofa\.?\s*': 'professora ',
            r'\bsr\.?\s*': 'senhor ',
            r'\bsra\.?\s*': 'senhora ',
            r'\bjr\.?\s*': 'junior ',
            r'\bfilho\s*': 'filho ',
            r'\bneto\s*': 'neto ',
        }

        # Portuguese name particles (often ignored in similarity)
        self.name_particles = {
            'de', 'da', 'do', 'dos', 'das', 'e', 'del', 'della', 'di', 'du', 'van', 'von'
        }

        # Common Portuguese surnames that might be abbreviated
        self.common_surnames = {
            'silva', 'santos', 'oliveira', 'souza', 'rodrigues', 'ferreira', 'alves',
            'pereira', 'lima', 'gomes', 'ribeiro', 'carvalho', 'almeida', 'lopes',
            'soares', 'fernandes', 'vieira', 'barbosa', 'rocha', 'dias', 'nunes',
            'mendes', 'castro', 'pinto', 'azevedo', 'monteiro', 'cardoso', 'melo'
        }

    def process(self, text: str, config: SimilarityConfig) -> str:
        """
        Process Portuguese text for similarity comparison

        Args:
            text: Input text to process
            config: Processing configuration

        Returns:
            Processed text
        """
        if not text:
            return ""

        processed = text.strip()

        # Basic normalization
        if config.normalize_case:
            processed = processed.lower()

        if config.normalize_accents:
            processed = self._remove_accents(processed)

        if config.remove_punctuation:
            processed = re.sub(r'[^\w\s]', ' ', processed)

        if config.normalize_whitespace:
            processed = ' '.join(processed.split())

        # Portuguese-specific processing
        if config.handle_abbreviations:
            processed = self._expand_abbreviations(processed)

        if config.handle_portuguese_contractions:
            processed = self._normalize_contractions(processed)

        if config.normalize_prepositions:
            processed = self._normalize_prepositions(processed)

        # Final cleanup
        processed = ' '.join(processed.split())

        return processed

    def _remove_accents(self, text: str) -> str:
        """Remove accents and diacritical marks"""

        # Normalize to NFD (decomposed form)
        normalized = unicodedata.normalize('NFD', text)

        # Filter out combining characters (diacritics)
        without_accents = ''.join(
            char for char in normalized
            if unicodedata.category(char) != 'Mn'
        )

        return without_accents

    def _expand_abbreviations(self, text: str) -> str:
        """Expand common Portuguese abbreviations"""

        for abbrev_pattern, expansion in self.abbreviations.items():
            text = re.sub(abbrev_pattern, expansion, text, flags=re.IGNORECASE)

        return text

    def _normalize_contractions(self, text: str) -> str:
        """Normalize Portuguese contractions"""

        for contraction_pattern, normalized in self.contractions.items():
            text = re.sub(contraction_pattern, normalized, text, flags=re.IGNORECASE)

        return text

    def _normalize_prepositions(self, text: str) -> str:
        """Normalize Portuguese prepositions and articles"""

        # Split into tokens
        tokens = text.split()
        normalized_tokens = []

        for token in tokens:
            if token.lower() in self.name_particles:
                # Keep name particles but normalize case
                normalized_tokens.append(token.lower())
            else:
                normalized_tokens.append(token)

        return ' '.join(normalized_tokens)

    def extract_meaningful_parts(self, text: str) -> List[str]:
        """Extract meaningful parts of a name, excluding common particles"""

        tokens = text.lower().split()
        meaningful = []

        for token in tokens:
            if len(token) > 1 and token not in self.name_particles:
                meaningful.append(token)

        return meaningful


class StringSimilarityCalculator:
    """
    Multi-algorithm string similarity calculator for collector names

    Combines various string similarity algorithms with Portuguese-specific
    preprocessing to provide robust similarity scoring for collector names.
    """

    def __init__(self, config: Optional[SimilarityConfig] = None):
        """
        Initialize string similarity calculator

        Args:
            config: Optional configuration for similarity algorithms
        """
        self.config = config or SimilarityConfig()
        self.logger = logging.getLogger(__name__)

        # Initialize processors
        self.portuguese_processor = PortugueseStringProcessor()

        # Result cache for performance
        self._similarity_cache: Dict[str, float] = {}

        # Validate configuration
        self._validate_config()

        self.logger.info(f"StringSimilarityCalculator initialized")

    def _validate_config(self):
        """Validate similarity configuration"""

        total_weight = (self.config.exact_weight +
                       self.config.levenshtein_weight +
                       self.config.jaro_winkler_weight +
                       self.config.fuzzy_weight)

        if abs(total_weight - 1.0) > 0.01:
            self.logger.warning(f"Algorithm weights do not sum to 1.0 (sum: {total_weight})")

        if not FUZZYWUZZY_AVAILABLE and self.config.fuzzy_weight > 0:
            self.logger.warning("FuzzyWuzzy not available but weight > 0. Consider installing fuzzywuzzy.")

    def calculate_similarity(self, string1: str, string2: str) -> SimilarityResult:
        """
        Calculate string similarity between two strings

        Args:
            string1: First string for comparison
            string2: Second string for comparison

        Returns:
            SimilarityResult with similarity scores and details
        """
        # Create cache key
        cache_key = f"{string1}|{string2}"
        if self.config.cache_enabled and cache_key in self._similarity_cache:
            similarity = self._similarity_cache[cache_key]
            return SimilarityResult(
                string1=string1,
                string2=string2,
                overall_similarity=similarity,
                similarity_level=self._classify_similarity(similarity)
            )

        # Preprocess strings
        processed1 = self.portuguese_processor.process(string1, self.config)
        processed2 = self.portuguese_processor.process(string2, self.config)

        # Check for exact match first
        exact_match = processed1 == processed2

        # Calculate individual similarities
        levenshtein_sim = self._calculate_levenshtein_similarity(processed1, processed2)
        jaro_winkler_sim = self._calculate_jaro_winkler_similarity(processed1, processed2)
        fuzzy_sim = self._calculate_fuzzy_similarity(processed1, processed2)

        # Calculate overall weighted similarity
        overall_sim = (
            (1.0 if exact_match else 0.0) * self.config.exact_weight +
            levenshtein_sim * self.config.levenshtein_weight +
            jaro_winkler_sim * self.config.jaro_winkler_weight +
            fuzzy_sim * self.config.fuzzy_weight
        )

        # Extract additional metrics
        common_tokens = self._find_common_tokens(processed1, processed2)
        unique_tokens = self._find_unique_tokens(processed1, processed2)
        length_diff = abs(len(processed1) - len(processed2))

        # Cache result
        if self.config.cache_enabled and len(self._similarity_cache) < self.config.cache_size:
            self._similarity_cache[cache_key] = overall_sim

        # Create result
        result = SimilarityResult(
            string1=string1,
            string2=string2,
            overall_similarity=overall_sim,
            exact_match=exact_match,
            levenshtein_similarity=levenshtein_sim,
            jaro_winkler_similarity=jaro_winkler_sim,
            fuzzy_similarity=fuzzy_sim,
            processed_string1=processed1,
            processed_string2=processed2,
            similarity_level=self._classify_similarity(overall_sim),
            length_difference=length_diff,
            common_tokens=common_tokens,
            unique_tokens=unique_tokens
        )

        return result

    def _calculate_levenshtein_similarity(self, str1: str, str2: str) -> float:
        """Calculate Levenshtein distance-based similarity"""

        if not str1 and not str2:
            return 1.0

        if not str1 or not str2:
            return 0.0

        # Calculate Levenshtein distance
        distance = self._levenshtein_distance(str1, str2)
        max_length = max(len(str1), len(str2))

        # Convert distance to similarity (0-1)
        similarity = 1.0 - (distance / max_length) if max_length > 0 else 0.0

        return max(0.0, similarity)

    def _levenshtein_distance(self, str1: str, str2: str) -> int:
        """Calculate Levenshtein distance between two strings"""

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
                cost = 0 if str1[i-1] == str2[j-1] else 1

                matrix[i][j] = min(
                    matrix[i-1][j] + 1,      # deletion
                    matrix[i][j-1] + 1,      # insertion
                    matrix[i-1][j-1] + cost  # substitution
                )

        return matrix[len1][len2]

    def _calculate_jaro_winkler_similarity(self, str1: str, str2: str) -> float:
        """Calculate Jaro-Winkler similarity"""

        if not str1 and not str2:
            return 1.0

        if not str1 or not str2:
            return 0.0

        if str1 == str2:
            return 1.0

        # Jaro similarity calculation
        jaro_sim = self._jaro_similarity(str1, str2)

        # Winkler modification (boost for common prefix)
        if jaro_sim < 0.7:
            return jaro_sim

        # Find common prefix (up to 4 characters)
        prefix = 0
        for i in range(min(len(str1), len(str2), 4)):
            if str1[i] == str2[i]:
                prefix += 1
            else:
                break

        # Apply Winkler boost
        return jaro_sim + (0.1 * prefix * (1 - jaro_sim))

    def _jaro_similarity(self, str1: str, str2: str) -> float:
        """Calculate Jaro similarity"""

        len1, len2 = len(str1), len(str2)
        match_window = max(len1, len2) // 2 - 1
        match_window = max(0, match_window)

        str1_matches = [False] * len1
        str2_matches = [False] * len2

        matches = 0
        transpositions = 0

        # Find matches
        for i in range(len1):
            start = max(0, i - match_window)
            end = min(i + match_window + 1, len2)

            for j in range(start, end):
                if str2_matches[j] or str1[i] != str2[j]:
                    continue

                str1_matches[i] = str2_matches[j] = True
                matches += 1
                break

        if matches == 0:
            return 0.0

        # Find transpositions
        k = 0
        for i in range(len1):
            if not str1_matches[i]:
                continue

            while not str2_matches[k]:
                k += 1

            if str1[i] != str2[k]:
                transpositions += 1

            k += 1

        return (matches / len1 + matches / len2 +
                (matches - transpositions / 2) / matches) / 3

    def _calculate_fuzzy_similarity(self, str1: str, str2: str) -> float:
        """Calculate fuzzy similarity using FuzzyWuzzy if available"""

        if not FUZZYWUZZY_AVAILABLE or not str1 or not str2:
            # Fallback to simple ratio
            return difflib.SequenceMatcher(None, str1, str2).ratio()

        try:
            # Use FuzzyWuzzy token sort ratio for better handling of word order
            return fuzz.token_sort_ratio(str1, str2) / 100.0

        except Exception as e:
            self.logger.warning(f"FuzzyWuzzy calculation error: {e}")
            return difflib.SequenceMatcher(None, str1, str2).ratio()

    def _find_common_tokens(self, str1: str, str2: str) -> Set[str]:
        """Find common tokens between two strings"""

        tokens1 = set(str1.split())
        tokens2 = set(str2.split())

        return tokens1.intersection(tokens2)

    def _find_unique_tokens(self, str1: str, str2: str) -> Set[str]:
        """Find tokens unique to either string"""

        tokens1 = set(str1.split())
        tokens2 = set(str2.split())

        return tokens1.symmetric_difference(tokens2)

    def _classify_similarity(self, similarity: float) -> str:
        """Classify similarity score into level"""

        if similarity >= 1.0:
            return "exact"
        elif similarity >= self.config.high_similarity_threshold:
            return "high"
        elif similarity >= self.config.medium_similarity_threshold:
            return "medium"
        elif similarity >= self.config.low_similarity_threshold:
            return "low"
        else:
            return "very_low"

    def batch_calculate_similarities(
        self,
        string_pairs: List[Tuple[str, str]]
    ) -> List[SimilarityResult]:
        """
        Calculate similarities for multiple string pairs efficiently

        Args:
            string_pairs: List of (string1, string2) tuples

        Returns:
            List of SimilarityResult objects
        """
        results = []

        for str1, str2 in string_pairs:
            try:
                result = self.calculate_similarity(str1, str2)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Error calculating similarity for '{str1}' vs '{str2}': {e}")
                # Add error result
                results.append(SimilarityResult(
                    string1=str1,
                    string2=str2,
                    overall_similarity=0.0,
                    similarity_level="error"
                ))

        return results

    def find_best_matches(
        self,
        query: str,
        candidates: List[str],
        limit: int = 10,
        min_similarity: float = 0.5
    ) -> List[Tuple[str, float]]:
        """
        Find best matching strings from candidates

        Args:
            query: Query string to match against
            candidates: List of candidate strings
            limit: Maximum number of matches to return
            min_similarity: Minimum similarity threshold

        Returns:
            List of (candidate, similarity) tuples sorted by similarity
        """
        matches = []

        for candidate in candidates:
            try:
                result = self.calculate_similarity(query, candidate)
                if result.overall_similarity >= min_similarity:
                    matches.append((candidate, result.overall_similarity))
            except Exception as e:
                self.logger.warning(f"Error matching '{query}' vs '{candidate}': {e}")

        # Sort by similarity (descending) and limit results
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches[:limit]

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""

        return {
            'cache_size': len(self._similarity_cache),
            'max_cache_size': self.config.cache_size if self.config.cache_enabled else 0,
            'cache_enabled': self.config.cache_enabled,
            'fuzzy_available': FUZZYWUZZY_AVAILABLE,
            'algorithms': {
                'exact_weight': self.config.exact_weight,
                'levenshtein_weight': self.config.levenshtein_weight,
                'jaro_winkler_weight': self.config.jaro_winkler_weight,
                'fuzzy_weight': self.config.fuzzy_weight
            }
        }

    def clear_cache(self):
        """Clear similarity cache"""

        self._similarity_cache.clear()
        self.logger.info("String similarity cache cleared")

    def analyze_string_patterns(self, strings: List[str]) -> Dict[str, Any]:
        """
        Analyze patterns in a collection of strings

        Args:
            strings: List of strings to analyze

        Returns:
            Dictionary with pattern analysis
        """
        if not strings:
            return {}

        analysis = {
            'total_strings': len(strings),
            'unique_strings': len(set(strings)),
            'average_length': sum(len(s) for s in strings) / len(strings),
            'length_distribution': defaultdict(int),
            'common_tokens': defaultdict(int),
            'common_prefixes': defaultdict(int),
            'common_suffixes': defaultdict(int)
        }

        # Analyze lengths
        for string in strings:
            length_bucket = (len(string) // 5) * 5  # Group by 5-character buckets
            analysis['length_distribution'][length_bucket] += 1

        # Analyze tokens
        for string in strings:
            processed = self.portuguese_processor.process(string, self.config)
            tokens = processed.split()

            for token in tokens:
                if len(token) > 2:  # Only consider meaningful tokens
                    analysis['common_tokens'][token] += 1

        # Analyze prefixes and suffixes (first/last 3 characters)
        for string in strings:
            processed = self.portuguese_processor.process(string, self.config)

            if len(processed) >= 3:
                prefix = processed[:3]
                suffix = processed[-3:]

                analysis['common_prefixes'][prefix] += 1
                analysis['common_suffixes'][suffix] += 1

        # Convert defaultdicts to regular dicts and get top items
        analysis['length_distribution'] = dict(analysis['length_distribution'])
        analysis['common_tokens'] = dict(sorted(
            analysis['common_tokens'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:20])
        analysis['common_prefixes'] = dict(sorted(
            analysis['common_prefixes'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:10])
        analysis['common_suffixes'] = dict(sorted(
            analysis['common_suffixes'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:10])

        return analysis