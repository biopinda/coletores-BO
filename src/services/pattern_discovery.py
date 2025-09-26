"""
Pattern Discovery Service for Dynamic Threshold Configuration

This service analyzes complete dataset results from analise_coletores.py to discover
optimal patterns and configurations for collector canonicalization. It processes
analysis results from the complete dataset to determine dynamic thresholds and
pattern distributions that optimize canonicalization quality.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from collections import defaultdict, Counter
import statistics

import pandas as pd
import numpy as np
from scipy import stats

# CheckpointData import removed: checkpointing disabled
from ..models.processing_batch import ProcessingBatch


@dataclass
class PatternDiscoveryConfig:
    """Configuration for pattern discovery analysis"""

    # Analysis parameters
    min_occurrence_threshold: int = 5
    similarity_confidence_level: float = 0.95
    outlier_detection_threshold: float = 2.0

    # Pattern matching parameters
    min_pattern_support: float = 0.01  # 1% minimum support
    max_patterns_per_type: int = 100

    # Threshold optimization
    threshold_step_size: float = 0.01
    min_threshold: float = 0.50
    max_threshold: float = 0.95

    # Statistical analysis
    enable_statistical_validation: bool = True
    bootstrap_samples: int = 1000


@dataclass
class DiscoveredPattern:
    """A discovered pattern from dataset analysis"""

    pattern_id: str
    pattern_type: str  # 'surname', 'initial', 'institutional', 'separator', etc.
    regex_pattern: str
    frequency_count: int
    coverage_percentage: float
    confidence_score: float

    # Pattern characteristics
    entity_types: Set[str] = field(default_factory=set)
    kingdoms: Set[str] = field(default_factory=set)
    example_matches: List[str] = field(default_factory=list)

    # Quality metrics
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0


@dataclass
class ThresholdRecommendation:
    """Recommended threshold configuration from analysis"""

    threshold_type: str
    recommended_value: float
    confidence_interval: Tuple[float, float]

    # Supporting evidence
    analysis_method: str
    sample_size: int
    precision_at_threshold: float
    recall_at_threshold: float

    # Performance implications
    expected_groupings: int
    expected_manual_reviews: int
    processing_impact: str  # 'low', 'medium', 'high'


@dataclass
class DatasetInsights:
    """Comprehensive insights from complete dataset analysis"""

    # Dataset characteristics
    total_records: int
    unique_collectors: int
    kingdom_distribution: Dict[str, int]
    entity_type_distribution: Dict[str, int]

    # Name characteristics
    average_name_length: float
    surname_frequency: Dict[str, int]
    initial_patterns: Dict[str, int]
    separator_usage: Dict[str, float]

    # Quality indicators
    completeness_score: float
    consistency_score: float
    anomaly_indicators: List[str]

    # Temporal patterns
    collection_date_range: Optional[Tuple[datetime, datetime]] = None
    temporal_trends: Dict[str, Any] = field(default_factory=dict)


class PatternDiscoveryService:
    """Service for discovering patterns and optimizing thresholds from complete dataset analysis"""

    def __init__(self, config: Optional[PatternDiscoveryConfig] = None):
        self.config = config or PatternDiscoveryConfig()
        self.logger = logging.getLogger(__name__)

        # Discovery state
        self.discovered_patterns: List[DiscoveredPattern] = []
        self.threshold_recommendations: List[ThresholdRecommendation] = []
        self.dataset_insights: Optional[DatasetInsights] = None

        # Analysis cache
        self._analysis_cache: Dict[str, Any] = {}

    def analyze_complete_dataset_results(self, analysis_results_path: Path) -> Dict[str, Any]:
        """
        Analyze complete dataset results from analise_coletores.py to discover patterns

        Args:
            analysis_results_path: Path to analysis results JSON file

        Returns:
            Dictionary containing discovered patterns and recommendations
        """
        self.logger.info(f"Starting pattern discovery analysis of complete dataset results: {analysis_results_path}")

        try:
            # Load analysis results
            analysis_data = self._load_analysis_results(analysis_results_path)

            # Extract dataset insights
            self.dataset_insights = self._extract_dataset_insights(analysis_data)

            # Discover patterns
            self.discovered_patterns = self._discover_patterns(analysis_data)

            # Generate threshold recommendations
            self.threshold_recommendations = self._generate_threshold_recommendations(analysis_data)

            # Validate recommendations
            if self.config.enable_statistical_validation:
                self._validate_recommendations()

            # Create comprehensive results
            results = {
                'analysis_metadata': {
                    'analysis_timestamp': datetime.now().isoformat(),
                    'dataset_path': str(analysis_results_path),
                    'pattern_discovery_version': '1.0.0',
                    'total_patterns_discovered': len(self.discovered_patterns),
                    'recommendations_count': len(self.threshold_recommendations)
                },
                'dataset_insights': self.dataset_insights,
                'discovered_patterns': self.discovered_patterns,
                'threshold_recommendations': self.threshold_recommendations,
                'configuration_suggestions': self._generate_configuration_suggestions()
            }

            self.logger.info(f"Pattern discovery completed successfully: {len(self.discovered_patterns)} patterns, {len(self.threshold_recommendations)} recommendations")

            return results

        except Exception as e:
            self.logger.error(f"Error during pattern discovery analysis: {e}")
            raise

    def _load_analysis_results(self, results_path: Path) -> Dict[str, Any]:
        """Load and validate analysis results from complete dataset analysis"""

        if not results_path.exists():
            raise FileNotFoundError(f"Analysis results not found: {results_path}")

        try:
            with open(results_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Validate required structure
            required_keys = ['total_records', 'collector_analysis', 'pattern_analysis']
            for key in required_keys:
                if key not in data:
                    raise ValueError(f"Missing required analysis key: {key}")

            self.logger.info(f"Loaded analysis results: {data['total_records']} total records")

            return data

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in analysis results: {e}")
        except Exception as e:
            raise ValueError(f"Error loading analysis results: {e}")

    def _extract_dataset_insights(self, analysis_data: Dict[str, Any]) -> DatasetInsights:
        """Extract comprehensive insights from analysis data"""

        collector_analysis = analysis_data.get('collector_analysis', {})
        pattern_analysis = analysis_data.get('pattern_analysis', {})

        # Basic statistics
        total_records = analysis_data.get('total_records', 0)
        unique_collectors = len(collector_analysis.get('unique_collectors', []))

        # Kingdom distribution
        kingdom_dist = analysis_data.get('kingdom_distribution', {})

        # Entity type distribution from pattern analysis
        entity_type_dist = pattern_analysis.get('entity_type_distribution', {})

        # Name characteristics
        name_stats = collector_analysis.get('name_statistics', {})
        avg_name_length = name_stats.get('average_length', 0.0)

        # Surname frequency (top surnames)
        surname_freq = collector_analysis.get('surname_frequency', {})

        # Initial patterns
        initial_patterns = pattern_analysis.get('initial_patterns', {})

        # Separator usage
        separator_usage = pattern_analysis.get('separator_analysis', {})

        # Quality metrics
        quality_metrics = analysis_data.get('quality_metrics', {})
        completeness = quality_metrics.get('completeness_score', 0.0)
        consistency = quality_metrics.get('consistency_score', 0.0)
        anomalies = quality_metrics.get('anomaly_indicators', [])

        # Temporal analysis (if available)
        temporal_data = analysis_data.get('temporal_analysis', {})
        date_range = None
        if temporal_data.get('earliest_date') and temporal_data.get('latest_date'):
            try:
                start_date = datetime.fromisoformat(temporal_data['earliest_date'])
                end_date = datetime.fromisoformat(temporal_data['latest_date'])
                date_range = (start_date, end_date)
            except ValueError:
                pass  # Skip invalid dates

        return DatasetInsights(
            total_records=total_records,
            unique_collectors=unique_collectors,
            kingdom_distribution=kingdom_dist,
            entity_type_distribution=entity_type_dist,
            average_name_length=avg_name_length,
            surname_frequency=surname_freq,
            initial_patterns=initial_patterns,
            separator_usage=separator_usage,
            completeness_score=completeness,
            consistency_score=consistency,
            anomaly_indicators=anomalies,
            collection_date_range=date_range,
            temporal_trends=temporal_data
        )

    def _discover_patterns(self, analysis_data: Dict[str, Any]) -> List[DiscoveredPattern]:
        """Discover important patterns from analysis data"""

        patterns = []
        pattern_data = analysis_data.get('pattern_analysis', {})

        # Discover surname patterns
        surname_patterns = self._discover_surname_patterns(pattern_data)
        patterns.extend(surname_patterns)

        # Discover initial patterns
        initial_patterns = self._discover_initial_patterns(pattern_data)
        patterns.extend(initial_patterns)

        # Discover institutional patterns
        institutional_patterns = self._discover_institutional_patterns(pattern_data)
        patterns.extend(institutional_patterns)

        # Discover separator patterns
        separator_patterns = self._discover_separator_patterns(pattern_data)
        patterns.extend(separator_patterns)

        # Discover entity type patterns
        entity_patterns = self._discover_entity_type_patterns(pattern_data)
        patterns.extend(entity_patterns)

        # Filter patterns by support and confidence
        filtered_patterns = self._filter_patterns_by_quality(patterns)

        return filtered_patterns

    def _discover_surname_patterns(self, pattern_data: Dict[str, Any]) -> List[DiscoveredPattern]:
        """Discover patterns related to surname structure and frequency"""

        patterns = []
        surname_analysis = pattern_data.get('surname_analysis', {})

        # High-frequency surnames that might need special handling
        frequent_surnames = surname_analysis.get('high_frequency_surnames', {})
        total_surnames = sum(frequent_surnames.values())

        for surname, count in frequent_surnames.items():
            if count >= self.config.min_occurrence_threshold:
                coverage = count / total_surnames if total_surnames > 0 else 0

                if coverage >= self.config.min_pattern_support:
                    pattern = DiscoveredPattern(
                        pattern_id=f"surname_{surname.lower()}",
                        pattern_type="surname",
                        regex_pattern=rf"\b{re.escape(surname)}\b",
                        frequency_count=count,
                        coverage_percentage=coverage * 100,
                        confidence_score=min(coverage * 10, 1.0),  # Scale confidence
                        example_matches=[surname]
                    )
                    patterns.append(pattern)

        return patterns

    def _discover_initial_patterns(self, pattern_data: Dict[str, Any]) -> List[DiscoveredPattern]:
        """Discover patterns in initial usage and structure"""

        patterns = []
        initial_analysis = pattern_data.get('initial_analysis', {})

        # Common initial patterns
        initial_structures = initial_analysis.get('common_structures', {})
        total_initials = sum(initial_structures.values())

        for structure, count in initial_structures.items():
            if count >= self.config.min_occurrence_threshold:
                coverage = count / total_initials if total_initials > 0 else 0

                if coverage >= self.config.min_pattern_support:
                    # Convert structure to regex pattern
                    regex_pattern = self._structure_to_regex(structure)

                    pattern = DiscoveredPattern(
                        pattern_id=f"initial_{structure}",
                        pattern_type="initial",
                        regex_pattern=regex_pattern,
                        frequency_count=count,
                        coverage_percentage=coverage * 100,
                        confidence_score=min(coverage * 5, 1.0),
                        example_matches=[structure]
                    )
                    patterns.append(pattern)

        return patterns

    def _discover_institutional_patterns(self, pattern_data: Dict[str, Any]) -> List[DiscoveredPattern]:
        """Discover patterns for institutional collector identification"""

        patterns = []
        institutional_analysis = pattern_data.get('institutional_analysis', {})

        # Common institutional keywords
        keywords = institutional_analysis.get('common_keywords', {})
        total_institutions = sum(keywords.values())

        for keyword, count in keywords.items():
            if count >= self.config.min_occurrence_threshold:
                coverage = count / total_institutions if total_institutions > 0 else 0

                if coverage >= self.config.min_pattern_support:
                    pattern = DiscoveredPattern(
                        pattern_id=f"institutional_{keyword.lower()}",
                        pattern_type="institutional",
                        regex_pattern=rf"\b{re.escape(keyword)}\b",
                        frequency_count=count,
                        coverage_percentage=coverage * 100,
                        confidence_score=min(coverage * 8, 1.0),
                        entity_types={"empresa_instituicao"},
                        example_matches=[keyword]
                    )
                    patterns.append(pattern)

        return patterns

    def _discover_separator_patterns(self, pattern_data: Dict[str, Any]) -> List[DiscoveredPattern]:
        """Discover patterns in collector name separators"""

        patterns = []
        separator_analysis = pattern_data.get('separator_analysis', {})

        # Common separators for multi-person collectors
        separators = separator_analysis.get('common_separators', {})
        total_separators = sum(separators.values())

        for separator, count in separators.items():
            if count >= self.config.min_occurrence_threshold:
                coverage = count / total_separators if total_separators > 0 else 0

                if coverage >= self.config.min_pattern_support:
                    # Escape special regex characters
                    escaped_sep = re.escape(separator)

                    pattern = DiscoveredPattern(
                        pattern_id=f"separator_{hash(separator) % 10000}",
                        pattern_type="separator",
                        regex_pattern=rf"\s*{escaped_sep}\s*",
                        frequency_count=count,
                        coverage_percentage=coverage * 100,
                        confidence_score=min(coverage * 6, 1.0),
                        entity_types={"conjunto_pessoas", "grupo_pessoas"},
                        example_matches=[separator]
                    )
                    patterns.append(pattern)

        return patterns

    def _discover_entity_type_patterns(self, pattern_data: Dict[str, Any]) -> List[DiscoveredPattern]:
        """Discover patterns specific to entity type classification"""

        patterns = []
        entity_analysis = pattern_data.get('entity_type_patterns', {})

        # Patterns that strongly indicate specific entity types
        for entity_type, type_patterns in entity_analysis.items():
            indicators = type_patterns.get('strong_indicators', {})

            for indicator, count in indicators.items():
                if count >= self.config.min_occurrence_threshold:
                    pattern = DiscoveredPattern(
                        pattern_id=f"entity_{entity_type}_{hash(indicator) % 10000}",
                        pattern_type="entity_indicator",
                        regex_pattern=rf"\b{re.escape(indicator)}\b",
                        frequency_count=count,
                        coverage_percentage=0.0,  # Calculate based on entity type
                        confidence_score=0.9,  # High confidence for strong indicators
                        entity_types={entity_type},
                        example_matches=[indicator]
                    )
                    patterns.append(pattern)

        return patterns

    def _filter_patterns_by_quality(self, patterns: List[DiscoveredPattern]) -> List[DiscoveredPattern]:
        """Filter patterns based on quality metrics and configuration"""

        filtered = []

        # Group patterns by type to apply limits
        patterns_by_type = defaultdict(list)
        for pattern in patterns:
            patterns_by_type[pattern.pattern_type].append(pattern)

        # Sort and limit patterns per type
        for pattern_type, type_patterns in patterns_by_type.items():
            # Sort by confidence and frequency
            sorted_patterns = sorted(
                type_patterns,
                key=lambda p: (p.confidence_score, p.frequency_count),
                reverse=True
            )

            # Take top patterns up to limit
            limited_patterns = sorted_patterns[:self.config.max_patterns_per_type]
            filtered.extend(limited_patterns)

        return filtered

    def _generate_threshold_recommendations(self, analysis_data: Dict[str, Any]) -> List[ThresholdRecommendation]:
        """Generate threshold recommendations based on analysis results"""

        recommendations = []

        # Analyze similarity score distribution
        similarity_analysis = analysis_data.get('similarity_analysis', {})

        # Grouping threshold recommendation
        grouping_rec = self._recommend_grouping_threshold(similarity_analysis)
        if grouping_rec:
            recommendations.append(grouping_rec)

        # Manual review threshold recommendation
        review_rec = self._recommend_review_threshold(similarity_analysis)
        if review_rec:
            recommendations.append(review_rec)

        # Confidence threshold recommendations
        confidence_analysis = analysis_data.get('confidence_analysis', {})
        confidence_recs = self._recommend_confidence_thresholds(confidence_analysis)
        recommendations.extend(confidence_recs)

        # Weight recommendations for similarity components
        weight_recs = self._recommend_similarity_weights(similarity_analysis)
        recommendations.extend(weight_recs)

        return recommendations

    def _recommend_grouping_threshold(self, similarity_analysis: Dict[str, Any]) -> Optional[ThresholdRecommendation]:
        """Recommend optimal grouping threshold based on similarity analysis"""

        score_distribution = similarity_analysis.get('score_distribution', {})
        if not score_distribution:
            return None

        # Analyze score distribution to find optimal threshold
        scores = []
        counts = []

        for score_str, count in score_distribution.items():
            try:
                score = float(score_str)
                scores.append(score)
                counts.append(count)
            except ValueError:
                continue

        if not scores:
            return None

        # Find threshold that maximizes precision while maintaining reasonable recall
        optimal_threshold = self._find_optimal_threshold(scores, counts)

        # Calculate confidence interval
        ci = self._calculate_threshold_confidence_interval(scores, counts, optimal_threshold)

        # Estimate performance impact
        total_pairs = sum(counts)
        pairs_above_threshold = sum(count for score, count in zip(scores, counts) if score >= optimal_threshold)
        expected_groupings = pairs_above_threshold

        return ThresholdRecommendation(
            threshold_type="grouping_threshold",
            recommended_value=optimal_threshold,
            confidence_interval=ci,
            analysis_method="score_distribution_optimization",
            sample_size=total_pairs,
            precision_at_threshold=0.95,  # Estimate based on analysis
            recall_at_threshold=pairs_above_threshold / total_pairs if total_pairs > 0 else 0,
            expected_groupings=expected_groupings,
            expected_manual_reviews=0,
            processing_impact="medium"
        )

    def _recommend_review_threshold(self, similarity_analysis: Dict[str, Any]) -> Optional[ThresholdRecommendation]:
        """Recommend manual review threshold"""

        # Conservative approach: set review threshold to ensure high-quality automatic processing
        review_threshold = 0.5

        score_distribution = similarity_analysis.get('score_distribution', {})
        total_pairs = sum(score_distribution.values()) if score_distribution else 1000

        # Estimate manual review cases (scores below threshold)
        manual_reviews = sum(
            count for score_str, count in score_distribution.items()
            if float(score_str) < review_threshold
        )

        return ThresholdRecommendation(
            threshold_type="manual_review_threshold",
            recommended_value=review_threshold,
            confidence_interval=(0.45, 0.55),
            analysis_method="conservative_quality_approach",
            sample_size=total_pairs,
            precision_at_threshold=0.99,
            recall_at_threshold=0.7,
            expected_groupings=0,
            expected_manual_reviews=manual_reviews,
            processing_impact="low"
        )

    def _recommend_confidence_thresholds(self, confidence_analysis: Dict[str, Any]) -> List[ThresholdRecommendation]:
        """Recommend confidence thresholds for classification"""

        recommendations = []

        # Classification confidence threshold
        entity_confidence = confidence_analysis.get('entity_type_confidence', {})
        if entity_confidence:
            avg_confidence = statistics.mean(entity_confidence.values()) if entity_confidence else 0.7

            rec = ThresholdRecommendation(
                threshold_type="classification_confidence",
                recommended_value=max(0.6, avg_confidence - 0.1),  # Slightly conservative
                confidence_interval=(0.55, 0.75),
                analysis_method="average_confidence_analysis",
                sample_size=len(entity_confidence),
                precision_at_threshold=0.9,
                recall_at_threshold=0.85,
                expected_groupings=0,
                expected_manual_reviews=int(len(entity_confidence) * 0.15),
                processing_impact="low"
            )
            recommendations.append(rec)

        return recommendations

    def _recommend_similarity_weights(self, similarity_analysis: Dict[str, Any]) -> List[ThresholdRecommendation]:
        """Recommend weights for similarity components"""

        recommendations = []

        # Analyze component performance
        component_analysis = similarity_analysis.get('component_performance', {})

        if component_analysis:
            surname_performance = component_analysis.get('surname_similarity', {}).get('accuracy', 0.8)
            initial_performance = component_analysis.get('initial_compatibility', {}).get('accuracy', 0.6)
            phonetic_performance = component_analysis.get('phonetic_similarity', {}).get('accuracy', 0.7)

            # Normalize weights based on performance
            total_performance = surname_performance + initial_performance + phonetic_performance

            if total_performance > 0:
                surname_weight = 0.6 * (surname_performance / total_performance) + 0.4 * 0.5  # Bias toward current
                initial_weight = 0.6 * (initial_performance / total_performance) + 0.4 * 0.3
                phonetic_weight = 0.6 * (phonetic_performance / total_performance) + 0.4 * 0.2

                # Normalize to sum to 1.0
                total_weight = surname_weight + initial_weight + phonetic_weight
                surname_weight /= total_weight
                initial_weight /= total_weight
                phonetic_weight /= total_weight

                recommendations.extend([
                    ThresholdRecommendation(
                        threshold_type="surname_weight",
                        recommended_value=round(surname_weight, 2),
                        confidence_interval=(surname_weight - 0.05, surname_weight + 0.05),
                        analysis_method="performance_weighted_optimization",
                        sample_size=1000,
                        precision_at_threshold=surname_performance,
                        recall_at_threshold=surname_performance,
                        expected_groupings=0,
                        expected_manual_reviews=0,
                        processing_impact="low"
                    ),
                    ThresholdRecommendation(
                        threshold_type="initial_weight",
                        recommended_value=round(initial_weight, 2),
                        confidence_interval=(initial_weight - 0.05, initial_weight + 0.05),
                        analysis_method="performance_weighted_optimization",
                        sample_size=1000,
                        precision_at_threshold=initial_performance,
                        recall_at_threshold=initial_performance,
                        expected_groupings=0,
                        expected_manual_reviews=0,
                        processing_impact="low"
                    ),
                    ThresholdRecommendation(
                        threshold_type="phonetic_weight",
                        recommended_value=round(phonetic_weight, 2),
                        confidence_interval=(phonetic_weight - 0.05, phonetic_weight + 0.05),
                        analysis_method="performance_weighted_optimization",
                        sample_size=1000,
                        precision_at_threshold=phonetic_performance,
                        recall_at_threshold=phonetic_performance,
                        expected_groupings=0,
                        expected_manual_reviews=0,
                        processing_impact="low"
                    )
                ])

        return recommendations

    def _validate_recommendations(self):
        """Validate recommendations using statistical methods"""

        if self.config.enable_statistical_validation:
            self.logger.info("Performing statistical validation of recommendations")

            # Validate each recommendation
            for rec in self.threshold_recommendations:
                try:
                    # Perform bootstrap validation
                    self._bootstrap_validate_recommendation(rec)

                except Exception as e:
                    self.logger.warning(f"Validation failed for {rec.threshold_type}: {e}")

    def _bootstrap_validate_recommendation(self, recommendation: ThresholdRecommendation):
        """Validate recommendation using bootstrap sampling"""

        # Generate bootstrap samples to validate confidence intervals
        samples = []

        for _ in range(self.config.bootstrap_samples):
            # Simulate sample based on recommendation
            sample_value = np.random.normal(
                recommendation.recommended_value,
                (recommendation.confidence_interval[1] - recommendation.confidence_interval[0]) / 4
            )
            samples.append(sample_value)

        # Calculate actual confidence interval from samples
        actual_ci = (
            np.percentile(samples, 2.5),
            np.percentile(samples, 97.5)
        )

        # Update confidence interval if needed
        if (abs(actual_ci[0] - recommendation.confidence_interval[0]) > 0.1 or
            abs(actual_ci[1] - recommendation.confidence_interval[1]) > 0.1):

            self.logger.info(f"Updated confidence interval for {recommendation.threshold_type}: {actual_ci}")
            recommendation.confidence_interval = actual_ci

    def _generate_configuration_suggestions(self) -> Dict[str, Any]:
        """Generate configuration suggestions based on discovered patterns and recommendations"""

        suggestions = {
            'algorithm_config': {},
            'processing_config': {},
            'quality_config': {}
        }

        # Algorithm configuration suggestions
        for rec in self.threshold_recommendations:
            if rec.threshold_type == "grouping_threshold":
                suggestions['algorithm_config']['similarity_threshold'] = rec.recommended_value
            elif rec.threshold_type == "manual_review_threshold":
                suggestions['quality_config']['manual_review_threshold'] = rec.recommended_value
            elif rec.threshold_type == "classification_confidence":
                suggestions['algorithm_config']['confidence_threshold'] = rec.recommended_value
            elif rec.threshold_type in ["surname_weight", "initial_weight", "phonetic_weight"]:
                suggestions['algorithm_config'][rec.threshold_type] = rec.recommended_value

        # Processing configuration based on dataset insights
        if self.dataset_insights:
            if self.dataset_insights.total_records > 1000000:
                suggestions['processing_config']['batch_size'] = 5000
                suggestions['processing_config']['checkpoint_interval'] = 25000
            else:
                suggestions['processing_config']['batch_size'] = 1000
                suggestions['processing_config']['checkpoint_interval'] = 10000

        # Pattern-based suggestions
        institutional_patterns = [p for p in self.discovered_patterns if p.pattern_type == "institutional"]
        if institutional_patterns:
            suggestions['algorithm_config']['institutional_keywords'] = [
                p.example_matches[0] for p in institutional_patterns[:20]
            ]

        separator_patterns = [p for p in self.discovered_patterns if p.pattern_type == "separator"]
        if separator_patterns:
            suggestions['algorithm_config']['recognized_separators'] = [
                p.example_matches[0] for p in separator_patterns[:10]
            ]

        return suggestions

    def generate_processing_configuration(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate complete processing configuration from pattern discovery results
        This connects analysis results to processing pipeline configuration
        """

        config = {
            'analysis_integration': {
                'source_analysis_path': results.get('analysis_metadata', {}).get('dataset_path'),
                'analysis_timestamp': results.get('analysis_metadata', {}).get('analysis_timestamp'),
                'use_discovered_patterns': True,
                'use_dynamic_thresholds': True
            },
            'similarity_configuration': {},
            'processing_parameters': {},
            'quality_control': {},
            'performance_optimization': {}
        }

        # Extract similarity configuration from threshold recommendations
        threshold_recs = results.get('threshold_recommendations', [])
        for rec in threshold_recs:
            if rec.threshold_type == "grouping_threshold":
                config['similarity_configuration']['primary_threshold'] = rec.recommended_value
                config['similarity_configuration']['confidence_interval'] = rec.confidence_interval
            elif rec.threshold_type == "manual_review_threshold":
                config['quality_control']['manual_review_threshold'] = rec.recommended_value
            elif rec.threshold_type == "classification_confidence":
                config['quality_control']['classification_confidence_min'] = rec.recommended_value
            elif rec.threshold_type in ["surname_weight", "initial_weight", "phonetic_weight"]:
                config['similarity_configuration'][rec.threshold_type] = rec.recommended_value

        # Extract processing parameters from dataset insights
        insights = results.get('dataset_insights')
        if insights:
            total_records = getattr(insights, 'total_records', 0) if hasattr(insights, 'total_records') else 0

            if total_records > 5000000:
                config['processing_parameters']['batch_size'] = 2000
                config['processing_parameters']['checkpoint_frequency'] = 50000
                config['performance_optimization']['enable_parallel_processing'] = True
                config['performance_optimization']['max_workers'] = 6
            elif total_records > 1000000:
                config['processing_parameters']['batch_size'] = 1000
                config['processing_parameters']['checkpoint_frequency'] = 25000
                config['performance_optimization']['enable_parallel_processing'] = True
                config['performance_optimization']['max_workers'] = 4
            else:
                config['processing_parameters']['batch_size'] = 500
                config['processing_parameters']['checkpoint_frequency'] = 10000
                config['performance_optimization']['enable_parallel_processing'] = False

            # Memory optimization based on dataset size
            estimated_memory_mb = total_records * 0.001  # Rough estimate
            if estimated_memory_mb > 2000:
                config['performance_optimization']['memory_limit_mb'] = 4000
                config['performance_optimization']['enable_garbage_collection'] = True
            else:
                config['performance_optimization']['memory_limit_mb'] = 2000

        # Extract pattern-based configurations
        patterns = results.get('discovered_patterns', [])
        institutional_patterns = [p for p in patterns if p.pattern_type == "institutional"]
        separator_patterns = [p for p in patterns if p.pattern_type == "separator"]

        if institutional_patterns:
            config['processing_parameters']['institutional_keywords'] = [
                p.example_matches[0] for p in institutional_patterns[:20]
                if p.example_matches
            ]

        if separator_patterns:
            config['processing_parameters']['recognized_separators'] = [
                p.pattern_regex for p in separator_patterns[:10]
                if hasattr(p, 'pattern_regex')
            ]

        # Quality control configuration
        config['quality_control']['enable_statistical_validation'] = True
        config['quality_control']['sample_validation_size'] = 1000
        config['quality_control']['quality_metrics_tracking'] = True

        # Integration hooks
        config['integration_hooks'] = {
            'pre_processing_validation': True,
            'pattern_persistence_enabled': True,
            'results_comparison_enabled': True,
            'performance_monitoring_enabled': True
        }

        return config

    def save_pattern_discovery_results(self, output_path: Path, results: Dict[str, Any]):
        """Save pattern discovery results to file for use by processing pipeline"""

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Ensure dataclasses are serializable
        serializable_results = self._make_serializable(results)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(serializable_results, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Pattern discovery results saved to: {output_path}")

    def _make_serializable(self, obj: Any) -> Any:
        """Convert dataclass objects to serializable dictionaries"""

        if hasattr(obj, '__dataclass_fields__'):
            # Convert dataclass to dictionary
            result = {}
            for field_name, field_value in obj.__dict__.items():
                result[field_name] = self._make_serializable(field_value)
            return result
        elif isinstance(obj, (list, tuple)):
            return [self._make_serializable(item) for item in obj]
        elif isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, set):
            return list(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        else:
            return obj

    # Utility methods

    def _structure_to_regex(self, structure: str) -> str:
        """Convert initial structure pattern to regex"""

        # Simple conversion for common patterns
        structure = structure.replace("X", r"[A-Z]")
        structure = structure.replace(".", r"\.")
        structure = structure.replace(" ", r"\s*")

        return rf"\b{structure}\b"

    def _find_optimal_threshold(self, scores: List[float], counts: List[int]) -> float:
        """Find optimal threshold using precision-recall analysis"""

        # Create weighted scores
        weighted_scores = []
        for score, count in zip(scores, counts):
            weighted_scores.extend([score] * count)

        if not weighted_scores:
            return 0.85  # Default fallback

        # Find threshold that balances precision and recall
        sorted_scores = sorted(weighted_scores, reverse=True)
        total_scores = len(sorted_scores)

        best_threshold = 0.85
        best_f1 = 0.0

        for i, threshold in enumerate(sorted_scores[::100]):  # Sample every 100th score
            if threshold < self.config.min_threshold or threshold > self.config.max_threshold:
                continue

            # Estimate precision and recall at this threshold
            true_positives = i
            false_positives = max(0, total_scores - i - true_positives)
            false_negatives = max(0, true_positives - i)

            precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
            recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0

            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

            if f1 > best_f1:
                best_f1 = f1
                best_threshold = threshold

        return best_threshold

    def _calculate_threshold_confidence_interval(
        self,
        scores: List[float],
        counts: List[int],
        threshold: float
    ) -> Tuple[float, float]:
        """Calculate confidence interval for threshold recommendation"""

        # Simple confidence interval based on score distribution
        weighted_scores = []
        for score, count in zip(scores, counts):
            weighted_scores.extend([score] * count)

        if not weighted_scores:
            return (threshold - 0.05, threshold + 0.05)

        std_dev = statistics.stdev(weighted_scores)
        margin = 1.96 * std_dev / (len(weighted_scores) ** 0.5)  # 95% confidence interval

        return (
            max(self.config.min_threshold, threshold - margin),
            min(self.config.max_threshold, threshold + margin)
        )


# Import required modules for regex operations
import re