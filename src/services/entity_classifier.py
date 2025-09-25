"""
Entity Type Classifier Service

This service classifies collector entities into predefined categories based on
patterns, rules, and machine learning approaches. It identifies whether a collector
represents a person, group, institution, or other entity type.
"""

import logging
import re
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import unicodedata


class EntityType(Enum):
    """Collector entity types"""
    PESSOA = "pessoa"
    CONJUNTO_PESSOAS = "conjunto_pessoas"
    GRUPO_PESSOAS = "grupo_pessoas"
    EMPRESA_INSTITUICAO = "empresa_instituicao"
    COLETOR_INDETERMINADO = "coletor_indeterminado"
    REPRESENTACAO_INSUFICIENTE = "representacao_insuficiente"


@dataclass
class ClassificationRule:
    """Rule for entity classification"""
    rule_id: str
    entity_type: EntityType
    patterns: List[str]
    weight: float
    confidence_threshold: float = 0.8


@dataclass
class ClassificationResult:
    """Result of entity classification"""
    text: str
    predicted_type: EntityType
    confidence: float
    rule_matches: List[str] = field(default_factory=list)
    scores: Dict[EntityType, float] = field(default_factory=dict)
    features: Dict[str, Any] = field(default_factory=dict)


class EntityTypeClassifier:
    """
    Rule-based entity type classifier for collector names

    Uses pattern matching and heuristics to classify collector entities
    into appropriate categories based on textual patterns and features.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._initialize_rules()
        self._initialize_patterns()

    def _initialize_rules(self):
        """Initialize classification rules"""

        self.classification_rules = [
            # Individual person patterns
            ClassificationRule(
                rule_id="single_person_initials",
                entity_type=EntityType.PESSOA,
                patterns=[
                    r"^[A-Z]\.\s*[A-Z]\.\s*[A-Za-z]+$",  # J. A. Silva
                    r"^[A-Za-z]+,\s*[A-Z]\.\s*[A-Z]\.$", # Silva, J. A.
                ],
                weight=0.9
            ),

            # Multi-person separators
            ClassificationRule(
                rule_id="multi_person_separators",
                entity_type=EntityType.CONJUNTO_PESSOAS,
                patterns=[
                    r".+\s+&\s+.+",     # Silva & Costa
                    r".+\s+et\s+.+",    # Silva et Costa
                    r".+,\s+.+,\s+.+",  # Silva, Costa, Santos
                    r".+\s+e\s+.+",     # Silva e Costa
                ],
                weight=0.95
            ),

            # Group indicators
            ClassificationRule(
                rule_id="group_indicators",
                entity_type=EntityType.GRUPO_PESSOAS,
                patterns=[
                    r".*et\s+al\.?.*",
                    r".*equipe.*",
                    r".*grupo.*",
                    r".*time.*",
                    r".*pesquisadores.*",
                ],
                weight=0.9
            ),

            # Institutional keywords
            ClassificationRule(
                rule_id="institutional_keywords",
                entity_type=EntityType.EMPRESA_INSTITUICAO,
                patterns=[
                    r".*herbario.*",
                    r".*museu.*",
                    r".*instituto.*",
                    r".*universidade.*",
                    r".*faculdade.*",
                    r".*laboratorio.*",
                    r".*departamento.*",
                    r".*fundacao.*",
                    r".*ong.*",
                    r".*empresa.*",
                ],
                weight=0.85
            ),

            # Indeterminate collectors
            ClassificationRule(
                rule_id="indeterminate_collectors",
                entity_type=EntityType.COLETOR_INDETERMINADO,
                patterns=[
                    r"^\?\s*$",
                    r"^sem\s+coletor.*",
                    r"^indeterminado.*",
                    r"^desconhecido.*",
                    r"^n[aã]o\s+informado.*",
                    r"^s[/.]?n[/.]?$",  # s/n, s.n.
                ],
                weight=1.0
            ),

            # Insufficient representation
            ClassificationRule(
                rule_id="insufficient_representation",
                entity_type=EntityType.REPRESENTACAO_INSUFICIENTE,
                patterns=[
                    r"^[A-Z]\.$",          # Single initial
                    r"^[A-Za-z]{1,2}$",    # Very short names
                    r"^\d+$",              # Just numbers
                ],
                weight=0.9
            ),
        ]

    def _initialize_patterns(self):
        """Initialize helper patterns and dictionaries"""

        # Common Portuguese first names (simplified list)
        self.common_first_names = {
            'antonio', 'jose', 'francisco', 'carlos', 'paulo', 'pedro', 'lucas', 'luis',
            'marcos', 'rafael', 'daniel', 'marcelo', 'fabio', 'bruno', 'rodrigo',
            'maria', 'ana', 'francisca', 'antonia', 'adriana', 'juliana', 'patricia',
            'marcia', 'fernanda', 'aline', 'cristina', 'sandra', 'monica'
        }

        # Common Portuguese surnames
        self.common_surnames = {
            'silva', 'santos', 'oliveira', 'souza', 'rodrigues', 'ferreira', 'alves',
            'pereira', 'lima', 'gomes', 'ribeiro', 'carvalho', 'almeida', 'lopes',
            'soares', 'fernandes', 'vieira', 'barbosa', 'rocha', 'dias', 'nunes'
        }

        # Institutional terms
        self.institutional_terms = {
            'herbario', 'museu', 'instituto', 'universidade', 'faculdade', 'escola',
            'centro', 'laboratorio', 'departamento', 'setor', 'divisao', 'fundacao',
            'associacao', 'sociedade', 'ong', 'empresa', 'consultoria'
        }

        # Title indicators
        self.title_patterns = {
            r'\b(dr|dra|prof|profa|sr|sra|mr|mrs|ms)\.?\s+': 'title'
        }

    def classify(self, text: str) -> ClassificationResult:
        """
        Classify collector entity type

        Args:
            text: Collector text to classify

        Returns:
            ClassificationResult with predicted type and confidence
        """
        if not text or not text.strip():
            return ClassificationResult(
                text=text,
                predicted_type=EntityType.COLETOR_INDETERMINADO,
                confidence=1.0,
                rule_matches=["empty_input"]
            )

        # Normalize text
        normalized_text = self._normalize_text(text)

        # Extract features
        features = self._extract_features(normalized_text)

        # Apply rules
        scores = {entity_type: 0.0 for entity_type in EntityType}
        matched_rules = []

        for rule in self.classification_rules:
            rule_score = self._apply_rule(rule, normalized_text, features)
            if rule_score > 0:
                scores[rule.entity_type] += rule_score * rule.weight
                if rule_score >= rule.confidence_threshold:
                    matched_rules.append(rule.rule_id)

        # Determine best classification
        best_type = max(scores.keys(), key=lambda k: scores[k])
        best_confidence = scores[best_type]

        # Apply additional heuristics if confidence is low
        if best_confidence < 0.5:
            best_type, best_confidence = self._apply_heuristics(
                normalized_text, features, scores
            )

        return ClassificationResult(
            text=text,
            predicted_type=best_type,
            confidence=min(best_confidence, 1.0),
            rule_matches=matched_rules,
            scores=scores,
            features=features
        )

    def _normalize_text(self, text: str) -> str:
        """Normalize text for classification"""

        # Convert to lowercase
        normalized = text.lower().strip()

        # Remove accents
        normalized = unicodedata.normalize('NFD', normalized)
        normalized = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')

        # Normalize whitespace
        normalized = ' '.join(normalized.split())

        return normalized

    def _extract_features(self, text: str) -> Dict[str, Any]:
        """Extract features for classification"""

        features = {
            'length': len(text),
            'word_count': len(text.split()),
            'has_comma': ',' in text,
            'has_ampersand': '&' in text,
            'has_et': ' et ' in text,
            'has_numbers': bool(re.search(r'\d', text)),
            'has_periods': '.' in text,
            'starts_with_number': text.split()[0].isdigit() if text.split() else False,
            'all_caps': text.isupper() if text else False,
            'has_parentheses': '(' in text or ')' in text,
        }

        # Count initials (single letters followed by period)
        features['initial_count'] = len(re.findall(r'\b[A-Za-z]\.', text))

        # Check for common name patterns
        words = text.split()
        features['first_name_detected'] = any(
            word in self.common_first_names for word in words
        )
        features['surname_detected'] = any(
            word in self.common_surnames for word in words
        )
        features['institutional_term_detected'] = any(
            word in self.institutional_terms for word in words
        )

        # Pattern-based features
        features['likely_person_format'] = bool(
            re.match(r'^[A-Za-z]+,\s+[A-Za-z\.\s]+$', text) or  # "Silva, João"
            re.match(r'^[A-Za-z\.\s]+\s+[A-Za-z]+$', text)      # "João Silva"
        )

        return features

    def _apply_rule(self, rule: ClassificationRule, text: str, features: Dict[str, Any]) -> float:
        """Apply classification rule to text"""

        max_score = 0.0

        for pattern in rule.patterns:
            if re.search(pattern, text, re.IGNORECASE):
                # Base score for pattern match
                score = 0.8

                # Boost score based on features
                if rule.entity_type == EntityType.PESSOA:
                    if features['first_name_detected'] or features['surname_detected']:
                        score += 0.1
                    if features['likely_person_format']:
                        score += 0.1

                elif rule.entity_type == EntityType.EMPRESA_INSTITUICAO:
                    if features['institutional_term_detected']:
                        score += 0.2

                max_score = max(max_score, score)

        return max_score

    def _apply_heuristics(
        self,
        text: str,
        features: Dict[str, Any],
        scores: Dict[EntityType, float]
    ) -> Tuple[EntityType, float]:
        """Apply additional heuristic rules"""

        # Very short text likely insufficient
        if features['length'] < 3:
            return EntityType.REPRESENTACAO_INSUFICIENTE, 0.9

        # Just initials
        if features['word_count'] <= 2 and features['initial_count'] >= features['word_count']:
            return EntityType.REPRESENTACAO_INSUFICIENTE, 0.8

        # Single word that's not a common name
        if features['word_count'] == 1:
            word = text.strip()
            if (word not in self.common_surnames and
                word not in self.common_first_names and
                word not in self.institutional_terms):
                return EntityType.REPRESENTACAO_INSUFICIENTE, 0.7

        # Multiple separators suggest group
        separator_count = text.count('&') + text.count(',') + text.count(' e ')
        if separator_count >= 2:
            return EntityType.CONJUNTO_PESSOAS, 0.8

        # Default to person if features suggest it
        if (features['first_name_detected'] or features['surname_detected'] or
            features['likely_person_format']):
            return EntityType.PESSOA, 0.6

        # Otherwise, insufficient representation
        return EntityType.REPRESENTACAO_INSUFICIENTE, 0.5

    def batch_classify(self, texts: List[str]) -> List[ClassificationResult]:
        """Classify multiple texts"""

        results = []
        for text in texts:
            try:
                result = self.classify(text)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Error classifying '{text}': {e}")
                results.append(ClassificationResult(
                    text=text,
                    predicted_type=EntityType.REPRESENTACAO_INSUFICIENTE,
                    confidence=0.0,
                    rule_matches=["error"]
                ))

        return results

    def get_classification_stats(self, results: List[ClassificationResult]) -> Dict[str, Any]:
        """Get statistics from classification results"""

        if not results:
            return {}

        stats = {
            'total_classified': len(results),
            'type_distribution': {},
            'confidence_distribution': {'high': 0, 'medium': 0, 'low': 0},
            'average_confidence': 0.0
        }

        # Count by type
        for entity_type in EntityType:
            count = sum(1 for r in results if r.predicted_type == entity_type)
            stats['type_distribution'][entity_type.value] = {
                'count': count,
                'percentage': count / len(results) * 100
            }

        # Confidence distribution
        total_confidence = 0.0
        for result in results:
            total_confidence += result.confidence

            if result.confidence >= 0.8:
                stats['confidence_distribution']['high'] += 1
            elif result.confidence >= 0.6:
                stats['confidence_distribution']['medium'] += 1
            else:
                stats['confidence_distribution']['low'] += 1

        stats['average_confidence'] = total_confidence / len(results)

        return stats