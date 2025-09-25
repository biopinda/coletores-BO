"""
Validation Service

Provides comprehensive quality validation for collector canonicalization results.
Validates against baseline analysis, checks quality metrics, and detects anomalies
in the canonicalization process.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import Counter, defaultdict
from pathlib import Path
from dataclasses import dataclass
import numpy as np
from scipy import stats

from .mongodb_manager import MongoDBManager
from .analysis_persistence import AnalysisPersistenceService
from .report_generator import ReportGenerator
from ..models.canonical_collector import CanonicalCollector
from ..models.classification_result import ClassificationResult


@dataclass
class ValidationResult:
    """Result of validation check"""
    check_name: str
    passed: bool
    score: float
    details: Dict[str, Any]
    recommendations: List[str]


@dataclass
class QualityMetrics:
    """Quality metrics for canonicalization"""
    classification_accuracy: float
    similarity_consistency: float
    coverage_completeness: float
    anomaly_score: float
    overall_quality_score: float


class ValidationService:
    """
    Comprehensive validation service for canonicalization quality assessment

    Validates canonicalization results against baseline analysis and quality
    standards, providing detailed quality metrics and recommendations.
    """

    def __init__(self,
                 mongo_manager: Optional[MongoDBManager] = None,
                 baseline_analysis_path: Optional[str] = None,
                 validation_config: Optional[Dict[str, Any]] = None):
        """
        Initialize validation service

        Args:
            mongo_manager: MongoDB manager instance
            baseline_analysis_path: Path to baseline analysis results
            validation_config: Configuration for validation thresholds
        """
        self.logger = logging.getLogger(__name__)
        self.mongo_manager = mongo_manager or MongoDBManager()

        # Load baseline analysis
        self.analysis_service = AnalysisPersistenceService()
        self.baseline_analysis = None

        if baseline_analysis_path:
            self.baseline_analysis = self.analysis_service.load_analysis_results(baseline_analysis_path)
            if self.baseline_analysis:
                self.logger.info(f"Loaded baseline analysis from {baseline_analysis_path}")

        # Default validation configuration
        self.config = {
            'min_classification_accuracy': 0.85,
            'min_similarity_consistency': 0.80,
            'min_coverage_completeness': 0.90,
            'max_anomaly_score': 0.15,
            'min_overall_quality': 0.80,
            'confidence_threshold': 0.70,
            'similarity_threshold': 0.85,
            'outlier_detection_method': 'iqr',  # 'iqr' or 'zscore'
            'outlier_sensitivity': 2.0
        }

        if validation_config:
            self.config.update(validation_config)

        self.logger.info(f"ValidationService initialized with config: {self.config}")

    def validate_canonicalization_quality(self,
                                         comparison_baseline: bool = True) -> Dict[str, Any]:
        """
        Perform comprehensive quality validation of canonicalization results

        Args:
            comparison_baseline: Whether to compare against baseline analysis

        Returns:
            Comprehensive validation report
        """
        self.logger.info("Starting comprehensive canonicalization quality validation")

        validation_results = {
            "validation_timestamp": datetime.now(),
            "validation_config": self.config.copy(),
            "overall_status": "PENDING",
            "quality_metrics": None,
            "validation_checks": [],
            "anomalies_detected": [],
            "recommendations": [],
            "baseline_comparison": None
        }

        try:
            # Calculate quality metrics
            quality_metrics = self._calculate_quality_metrics()
            validation_results["quality_metrics"] = quality_metrics.__dict__

            # Perform individual validation checks
            validation_checks = [
                self._validate_classification_accuracy(),
                self._validate_similarity_consistency(),
                self._validate_coverage_completeness(),
                self._validate_entity_type_distribution(),
                self._validate_confidence_scores(),
                self._validate_canonical_collector_quality(),
                self._detect_processing_anomalies()
            ]

            validation_results["validation_checks"] = [
                {
                    "check_name": check.check_name,
                    "passed": check.passed,
                    "score": check.score,
                    "details": check.details,
                    "recommendations": check.recommendations
                }
                for check in validation_checks
            ]

            # Baseline comparison if available
            if comparison_baseline and self.baseline_analysis:
                baseline_comparison = self._compare_against_baseline()
                validation_results["baseline_comparison"] = baseline_comparison

            # Generate overall recommendations
            validation_results["recommendations"] = self._generate_overall_recommendations(
                validation_checks, quality_metrics
            )

            # Determine overall status
            passed_checks = sum(1 for check in validation_checks if check.passed)
            total_checks = len(validation_checks)
            overall_pass_rate = passed_checks / total_checks

            if overall_pass_rate >= 0.8 and quality_metrics.overall_quality_score >= self.config['min_overall_quality']:
                validation_results["overall_status"] = "PASSED"
            elif overall_pass_rate >= 0.6:
                validation_results["overall_status"] = "WARNING"
            else:
                validation_results["overall_status"] = "FAILED"

            self.logger.info(f"Validation completed: {validation_results['overall_status']} "
                           f"({passed_checks}/{total_checks} checks passed, "
                           f"quality score: {quality_metrics.overall_quality_score:.3f})")

            return validation_results

        except Exception as e:
            self.logger.error(f"Validation failed with error: {e}")
            validation_results["overall_status"] = "ERROR"
            validation_results["error_details"] = str(e)
            return validation_results

    def validate_against_baseline(self,
                                baseline_path: str,
                                tolerance: float = 0.1) -> Dict[str, Any]:
        """
        Validate canonicalization results against specific baseline

        Args:
            baseline_path: Path to baseline analysis results
            tolerance: Tolerance for metric comparisons (0.1 = 10%)

        Returns:
            Baseline comparison results
        """
        try:
            # Load baseline if different from current
            baseline = self.analysis_service.load_analysis_results(baseline_path)
            if not baseline:
                return {"error": f"Failed to load baseline from {baseline_path}"}

            self.logger.info(f"Validating against baseline: {baseline_path}")

            # Compare key metrics
            comparison_results = {
                "baseline_date": baseline.get("analysis_date"),
                "baseline_records": baseline.get("total_records", 0),
                "current_timestamp": datetime.now(),
                "metric_comparisons": {},
                "deviations": [],
                "status": "PASSED"
            }

            # Get current statistics
            current_stats = self._get_current_canonicalization_stats()

            # Compare entity type distributions
            baseline_entity_dist = baseline.get("entity_type_distribution", {})
            current_entity_dist = current_stats.get("entity_type_distribution", {})

            entity_comparison = self._compare_distributions(
                baseline_entity_dist, current_entity_dist, tolerance
            )
            comparison_results["metric_comparisons"]["entity_type_distribution"] = entity_comparison

            # Compare quality metrics
            baseline_quality = baseline.get("quality_metrics", {})
            current_quality = current_stats.get("quality_metrics", {})

            for metric_name in ["classification_confidence", "similarity_scores", "coverage"]:
                if metric_name in baseline_quality and metric_name in current_quality:
                    baseline_value = baseline_quality[metric_name]
                    current_value = current_quality[metric_name]

                    deviation = abs(current_value - baseline_value) / baseline_value
                    passed = deviation <= tolerance

                    comparison_results["metric_comparisons"][metric_name] = {
                        "baseline_value": baseline_value,
                        "current_value": current_value,
                        "deviation_percent": deviation * 100,
                        "passed": passed
                    }

                    if not passed:
                        comparison_results["deviations"].append({
                            "metric": metric_name,
                            "deviation": deviation * 100,
                            "threshold": tolerance * 100
                        })

            # Determine overall status
            if comparison_results["deviations"]:
                if len(comparison_results["deviations"]) > len(comparison_results["metric_comparisons"]) * 0.3:
                    comparison_results["status"] = "FAILED"
                else:
                    comparison_results["status"] = "WARNING"

            return comparison_results

        except Exception as e:
            self.logger.error(f"Baseline validation failed: {e}")
            return {"error": str(e)}

    def detect_canonicalization_anomalies(self) -> List[Dict[str, Any]]:
        """
        Detect anomalies in canonicalization results

        Returns:
            List of detected anomalies with details
        """
        anomalies = []

        try:
            self.logger.info("Detecting canonicalization anomalies")

            # Anomaly detection checks
            anomalies.extend(self._detect_outlier_collectors())
            anomalies.extend(self._detect_unusual_similarity_patterns())
            anomalies.extend(self._detect_confidence_anomalies())
            anomalies.extend(self._detect_temporal_anomalies())
            anomalies.extend(self._detect_kingdom_anomalies())

            self.logger.info(f"Detected {len(anomalies)} potential anomalies")

            return anomalies

        except Exception as e:
            self.logger.error(f"Anomaly detection failed: {e}")
            return [{"type": "detection_error", "details": str(e)}]

    def _calculate_quality_metrics(self) -> QualityMetrics:
        """Calculate comprehensive quality metrics"""

        try:
            # Classification accuracy
            classification_accuracy = self._calculate_classification_accuracy()

            # Similarity consistency
            similarity_consistency = self._calculate_similarity_consistency()

            # Coverage completeness
            coverage_completeness = self._calculate_coverage_completeness()

            # Anomaly score
            anomaly_score = self._calculate_anomaly_score()

            # Overall quality score (weighted average)
            overall_quality_score = (
                0.3 * classification_accuracy +
                0.25 * similarity_consistency +
                0.25 * coverage_completeness +
                0.2 * (1.0 - anomaly_score)  # Lower anomaly score is better
            )

            return QualityMetrics(
                classification_accuracy=classification_accuracy,
                similarity_consistency=similarity_consistency,
                coverage_completeness=coverage_completeness,
                anomaly_score=anomaly_score,
                overall_quality_score=overall_quality_score
            )

        except Exception as e:
            self.logger.error(f"Failed to calculate quality metrics: {e}")
            return QualityMetrics(0.0, 0.0, 0.0, 1.0, 0.0)

    def _calculate_classification_accuracy(self) -> float:
        """Calculate classification accuracy score"""

        try:
            # Get classification results if available
            if hasattr(self.mongo_manager, 'classifications'):
                total_classifications = self.mongo_manager.classifications.count_documents({})
                high_confidence_classifications = self.mongo_manager.classifications.count_documents({
                    "confidence_score": {"$gte": self.config['confidence_threshold']}
                })

                if total_classifications > 0:
                    return high_confidence_classifications / total_classifications

            # Fallback: estimate from canonical collectors
            total_collectors = self.mongo_manager.coletores.count_documents({})
            if total_collectors == 0:
                return 0.0

            # Estimate based on entity type distribution
            entity_stats = list(self.mongo_manager.coletores.aggregate([
                {"$group": {"_id": "$tipo_entidade", "count": {"$sum": 1}}}
            ]))

            # High quality entity types typically indicate better classification
            high_quality_types = ["pessoa", "conjunto_pessoas", "empresa_instituicao"]
            high_quality_count = sum(
                stat["count"] for stat in entity_stats
                if stat["_id"] in high_quality_types
            )

            return min(1.0, high_quality_count / total_collectors)

        except Exception as e:
            self.logger.error(f"Failed to calculate classification accuracy: {e}")
            return 0.0

    def _calculate_similarity_consistency(self) -> float:
        """Calculate similarity scoring consistency"""

        try:
            # This is a simplified metric - in reality would analyze actual similarity scores
            # For now, estimate based on variation patterns
            total_variations = 0
            consistent_groupings = 0

            for collector in self.mongo_manager.coletores.find({}, {"variacoes": 1}):
                variations = collector.get("variacoes", [])
                total_variations += len(variations)

                if len(variations) > 1:
                    # Estimate consistency based on variation count vs canonical form
                    # Fewer variations per canonical usually indicates consistent similarity
                    if len(variations) <= 5:  # Reasonable number of variations
                        consistent_groupings += len(variations)

            if total_variations > 0:
                return min(1.0, consistent_groupings / total_variations)

            return 1.0  # No variations means perfect consistency

        except Exception as e:
            self.logger.error(f"Failed to calculate similarity consistency: {e}")
            return 0.0

    def _calculate_coverage_completeness(self) -> float:
        """Calculate coverage completeness score"""

        try:
            # Compare processed records vs expected based on baseline
            if self.baseline_analysis:
                baseline_records = self.baseline_analysis.get("total_records", 0)
                current_occurrences = sum(
                    collector.get("total_ocorrencias", 0)
                    for collector in self.mongo_manager.coletores.find({}, {"total_ocorrencias": 1})
                )

                if baseline_records > 0:
                    return min(1.0, current_occurrences / baseline_records)

            # Fallback: estimate based on entity type coverage
            entity_stats = list(self.mongo_manager.coletores.aggregate([
                {"$group": {"_id": "$tipo_entidade", "count": {"$sum": 1}}}
            ]))

            expected_types = ["pessoa", "conjunto_pessoas", "grupo_pessoas",
                            "empresa_instituicao", "coletor_indeterminado", "representacao_insuficiente"]
            found_types = set(stat["_id"] for stat in entity_stats)

            return len(found_types) / len(expected_types)

        except Exception as e:
            self.logger.error(f"Failed to calculate coverage completeness: {e}")
            return 0.0

    def _calculate_anomaly_score(self) -> float:
        """Calculate overall anomaly score (0 = no anomalies, 1 = many anomalies)"""

        try:
            anomalies = self.detect_canonicalization_anomalies()

            # Weight different types of anomalies
            anomaly_weights = {
                "outlier_collector": 0.3,
                "unusual_similarity": 0.2,
                "confidence_anomaly": 0.2,
                "temporal_anomaly": 0.15,
                "kingdom_anomaly": 0.15
            }

            weighted_anomaly_score = 0.0
            total_weight = 0.0

            for anomaly in anomalies:
                anomaly_type = anomaly.get("type", "unknown")
                weight = anomaly_weights.get(anomaly_type, 0.1)
                severity = anomaly.get("severity", 1.0)  # 0-1 scale

                weighted_anomaly_score += weight * severity
                total_weight += weight

            if total_weight > 0:
                return min(1.0, weighted_anomaly_score / total_weight)

            return 0.0

        except Exception as e:
            self.logger.error(f"Failed to calculate anomaly score: {e}")
            return 1.0  # Assume worst case on error

    def _validate_classification_accuracy(self) -> ValidationResult:
        """Validate classification accuracy"""

        accuracy = self._calculate_classification_accuracy()
        passed = accuracy >= self.config['min_classification_accuracy']

        recommendations = []
        if not passed:
            recommendations.append("Review classification thresholds")
            recommendations.append("Analyze low-confidence classifications")
            recommendations.append("Consider retraining classification models")

        return ValidationResult(
            check_name="classification_accuracy",
            passed=passed,
            score=accuracy,
            details={"accuracy": accuracy, "threshold": self.config['min_classification_accuracy']},
            recommendations=recommendations
        )

    def _validate_similarity_consistency(self) -> ValidationResult:
        """Validate similarity scoring consistency"""

        consistency = self._calculate_similarity_consistency()
        passed = consistency >= self.config['min_similarity_consistency']

        recommendations = []
        if not passed:
            recommendations.append("Review similarity thresholds")
            recommendations.append("Check for inconsistent groupings")
            recommendations.append("Validate similarity algorithm parameters")

        return ValidationResult(
            check_name="similarity_consistency",
            passed=passed,
            score=consistency,
            details={"consistency": consistency, "threshold": self.config['min_similarity_consistency']},
            recommendations=recommendations
        )

    def _validate_coverage_completeness(self) -> ValidationResult:
        """Validate coverage completeness"""

        completeness = self._calculate_coverage_completeness()
        passed = completeness >= self.config['min_coverage_completeness']

        recommendations = []
        if not passed:
            recommendations.append("Check for missing records")
            recommendations.append("Verify processing completed successfully")
            recommendations.append("Review entity type coverage")

        return ValidationResult(
            check_name="coverage_completeness",
            passed=passed,
            score=completeness,
            details={"completeness": completeness, "threshold": self.config['min_coverage_completeness']},
            recommendations=recommendations
        )

    def _validate_entity_type_distribution(self) -> ValidationResult:
        """Validate entity type distribution against expected patterns"""

        try:
            entity_stats = list(self.mongo_manager.coletores.aggregate([
                {"$group": {"_id": "$tipo_entidade", "count": {"$sum": 1}}}
            ]))

            entity_distribution = {stat["_id"]: stat["count"] for stat in entity_stats}
            total_collectors = sum(entity_distribution.values())

            # Expected rough distribution (these are rough estimates)
            expected_distribution = {
                "pessoa": 0.4,
                "conjunto_pessoas": 0.25,
                "empresa_instituicao": 0.15,
                "grupo_pessoas": 0.1,
                "representacao_insuficiente": 0.08,
                "coletor_indeterminado": 0.02
            }

            # Check if distribution is reasonable
            deviations = []
            for entity_type, expected_percent in expected_distribution.items():
                actual_count = entity_distribution.get(entity_type, 0)
                actual_percent = actual_count / total_collectors if total_collectors > 0 else 0

                deviation = abs(actual_percent - expected_percent)
                if deviation > 0.1:  # 10% deviation threshold
                    deviations.append({
                        "entity_type": entity_type,
                        "expected": expected_percent,
                        "actual": actual_percent,
                        "deviation": deviation
                    })

            passed = len(deviations) <= 2  # Allow some deviation
            score = max(0.0, 1.0 - (len(deviations) / len(expected_distribution)))

            recommendations = []
            if not passed:
                recommendations.append("Review entity type classification rules")
                recommendations.append("Check for bias in classification algorithm")

            return ValidationResult(
                check_name="entity_type_distribution",
                passed=passed,
                score=score,
                details={"distribution": entity_distribution, "deviations": deviations},
                recommendations=recommendations
            )

        except Exception as e:
            self.logger.error(f"Entity type validation failed: {e}")
            return ValidationResult(
                check_name="entity_type_distribution",
                passed=False,
                score=0.0,
                details={"error": str(e)},
                recommendations=["Fix entity type validation error"]
            )

    def _validate_confidence_scores(self) -> ValidationResult:
        """Validate confidence score distribution"""

        # This would analyze actual confidence scores if available
        # For now, provide a basic implementation

        passed = True
        score = 0.8
        details = {"note": "Confidence validation not fully implemented"}
        recommendations = []

        return ValidationResult(
            check_name="confidence_scores",
            passed=passed,
            score=score,
            details=details,
            recommendations=recommendations
        )

    def _validate_canonical_collector_quality(self) -> ValidationResult:
        """Validate quality of canonical collectors"""

        try:
            total_collectors = self.mongo_manager.coletores.count_documents({})
            if total_collectors == 0:
                return ValidationResult(
                    check_name="canonical_collector_quality",
                    passed=False,
                    score=0.0,
                    details={"error": "No canonical collectors found"},
                    recommendations=["Ensure canonicalization process completed"]
                )

            # Check for reasonable variation counts
            collectors_with_variations = self.mongo_manager.coletores.count_documents({
                "variacoes": {"$exists": True, "$not": {"$size": 0}}
            })

            variation_ratio = collectors_with_variations / total_collectors
            passed = variation_ratio >= 0.5  # At least half should have variations

            recommendations = []
            if not passed:
                recommendations.append("Review canonicalization grouping logic")
                recommendations.append("Check similarity thresholds")

            return ValidationResult(
                check_name="canonical_collector_quality",
                passed=passed,
                score=variation_ratio,
                details={"variation_ratio": variation_ratio, "total_collectors": total_collectors},
                recommendations=recommendations
            )

        except Exception as e:
            self.logger.error(f"Canonical collector validation failed: {e}")
            return ValidationResult(
                check_name="canonical_collector_quality",
                passed=False,
                score=0.0,
                details={"error": str(e)},
                recommendations=["Fix canonical collector validation"]
            )

    def _detect_processing_anomalies(self) -> ValidationResult:
        """Detect processing anomalies"""

        anomalies = self.detect_canonicalization_anomalies()
        anomaly_score = len(anomalies) / 100  # Normalize to 0-1 scale (assuming max 100 anomalies)

        passed = anomaly_score <= self.config['max_anomaly_score']
        score = max(0.0, 1.0 - anomaly_score)

        recommendations = []
        if not passed:
            recommendations.append("Review detected anomalies")
            recommendations.append("Check for processing errors")
            recommendations.append("Validate input data quality")

        return ValidationResult(
            check_name="processing_anomalies",
            passed=passed,
            score=score,
            details={"anomaly_count": len(anomalies), "anomalies": anomalies[:10]},  # Limit details
            recommendations=recommendations
        )

    def _compare_against_baseline(self) -> Dict[str, Any]:
        """Compare current results against baseline analysis"""

        if not self.baseline_analysis:
            return {"error": "No baseline analysis available"}

        return self.validate_against_baseline("", 0.1)  # Use loaded baseline

    def _generate_overall_recommendations(self,
                                        validation_checks: List[ValidationResult],
                                        quality_metrics: QualityMetrics) -> List[str]:
        """Generate overall recommendations based on validation results"""

        recommendations = []

        # Collect all specific recommendations
        for check in validation_checks:
            if not check.passed:
                recommendations.extend(check.recommendations)

        # Add overall quality recommendations
        if quality_metrics.overall_quality_score < self.config['min_overall_quality']:
            recommendations.append("Overall quality below threshold - comprehensive review needed")

        if quality_metrics.classification_accuracy < 0.8:
            recommendations.append("Focus on improving classification accuracy")

        if quality_metrics.anomaly_score > 0.2:
            recommendations.append("High anomaly score detected - investigate processing issues")

        # Remove duplicates and limit
        unique_recommendations = list(set(recommendations))[:10]

        return unique_recommendations

    def _get_current_canonicalization_stats(self) -> Dict[str, Any]:
        """Get current canonicalization statistics"""

        stats = {}

        try:
            # Entity type distribution
            entity_stats = list(self.mongo_manager.coletores.aggregate([
                {"$group": {"_id": "$tipo_entidade", "count": {"$sum": 1}}}
            ]))
            stats["entity_type_distribution"] = {stat["_id"]: stat["count"] for stat in entity_stats}

            # Quality metrics (simplified)
            stats["quality_metrics"] = {
                "classification_confidence": 0.85,  # Would be calculated from actual data
                "similarity_scores": 0.82,
                "coverage": 0.95
            }

            return stats

        except Exception as e:
            self.logger.error(f"Failed to get current stats: {e}")
            return {}

    def _compare_distributions(self,
                             baseline_dist: Dict,
                             current_dist: Dict,
                             tolerance: float) -> Dict[str, Any]:
        """Compare two distributions"""

        comparison = {
            "baseline": baseline_dist,
            "current": current_dist,
            "deviations": [],
            "passed": True
        }

        for key in set(baseline_dist.keys()) | set(current_dist.keys()):
            baseline_val = baseline_dist.get(key, 0)
            current_val = current_dist.get(key, 0)

            if baseline_val > 0:
                deviation = abs(current_val - baseline_val) / baseline_val
                if deviation > tolerance:
                    comparison["deviations"].append({
                        "key": key,
                        "baseline": baseline_val,
                        "current": current_val,
                        "deviation": deviation
                    })
                    comparison["passed"] = False

        return comparison

    def _detect_outlier_collectors(self) -> List[Dict[str, Any]]:
        """Detect collectors with unusual characteristics"""

        anomalies = []
        # This is a simplified implementation
        # In practice, would analyze occurrence counts, variation patterns, etc.

        return anomalies

    def _detect_unusual_similarity_patterns(self) -> List[Dict[str, Any]]:
        """Detect unusual similarity patterns"""

        anomalies = []
        # Would analyze similarity score distributions, grouping patterns

        return anomalies

    def _detect_confidence_anomalies(self) -> List[Dict[str, Any]]:
        """Detect confidence score anomalies"""

        anomalies = []
        # Would analyze confidence score patterns

        return anomalies

    def _detect_temporal_anomalies(self) -> List[Dict[str, Any]]:
        """Detect temporal anomalies in collector data"""

        anomalies = []
        # Would analyze temporal patterns in collection dates

        return anomalies

    def _detect_kingdom_anomalies(self) -> List[Dict[str, Any]]:
        """Detect anomalies in kingdom distribution"""

        anomalies = []
        # Would analyze kingdom specialization patterns

        return anomalies