"""
Report Generator Service

Generates comprehensive reports for canonicalization analysis with insights
from complete dataset analysis. Provides formatted output for quality assessment,
collector statistics, and canonicalization performance metrics.
"""

import logging
import json
import csv
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from pathlib import Path
from collections import Counter, defaultdict
import pandas as pd

from .mongodb_manager import MongoDBManager
from .analysis_persistence import AnalysisPersistenceService
from ..models.canonical_collector import CanonicalCollector
from ..models.kingdom_statistics import KingdomStatistics


class ReportGenerator:
    """
    Comprehensive report generator for canonicalization analysis

    Integrates insights from complete dataset analysis to generate enriched
    reports with context and comparisons based on discovered patterns.
    """

    def __init__(self,
                 mongo_manager: Optional[MongoDBManager] = None,
                 analysis_results_path: Optional[str] = None):
        """
        Initialize report generator

        Args:
            mongo_manager: MongoDB manager instance
            analysis_results_path: Path to analysis results file
        """
        self.logger = logging.getLogger(__name__)
        self.mongo_manager = mongo_manager or MongoDBManager()

        # Load analysis results for enriched reporting
        self.analysis_service = AnalysisPersistenceService()
        self.analysis_results = None

        if analysis_results_path:
            self.analysis_results = self.analysis_service.load_analysis_results(analysis_results_path)
            if self.analysis_results:
                self.logger.info(f"Loaded analysis results from {analysis_results_path}")
            else:
                self.logger.warning(f"Failed to load analysis results from {analysis_results_path}")

    def generate_canonicalization_report(self,
                                       output_path: str,
                                       include_analysis_insights: bool = True,
                                       format_type: str = "txt") -> bool:
        """
        Generate comprehensive canonicalization report

        Args:
            output_path: Path to save report
            include_analysis_insights: Whether to include complete analysis insights
            format_type: Output format ("txt", "json", "csv", "html")

        Returns:
            True if report generated successfully
        """
        try:
            self.logger.info(f"Generating canonicalization report: {output_path}")

            # Collect report data
            report_data = self._collect_canonicalization_data()

            # Add analysis insights if available
            if include_analysis_insights and self.analysis_results:
                report_data = self._enrich_with_analysis_insights(report_data)

            # Generate report based on format
            if format_type == "txt":
                success = self._generate_text_report(report_data, output_path)
            elif format_type == "json":
                success = self._generate_json_report(report_data, output_path)
            elif format_type == "csv":
                success = self._generate_csv_report(report_data, output_path)
            elif format_type == "html":
                success = self._generate_html_report(report_data, output_path)
            else:
                self.logger.error(f"Unsupported format type: {format_type}")
                return False

            if success:
                self.logger.info(f"Canonicalization report generated successfully: {output_path}")

            return success

        except Exception as e:
            self.logger.error(f"Failed to generate canonicalization report: {e}")
            return False

    def generate_quality_validation_report(self,
                                         output_path: str,
                                         baseline_analysis: Optional[Dict] = None) -> bool:
        """
        Generate quality validation report comparing against baseline

        Args:
            output_path: Path to save report
            baseline_analysis: Baseline analysis results for comparison

        Returns:
            True if report generated successfully
        """
        try:
            self.logger.info(f"Generating quality validation report: {output_path}")

            # Use provided baseline or loaded analysis results
            baseline = baseline_analysis or self.analysis_results
            if not baseline:
                self.logger.warning("No baseline analysis available for quality validation")

            # Collect validation data
            validation_data = self._collect_quality_metrics()

            # Add baseline comparison if available
            if baseline:
                validation_data = self._add_baseline_comparison(validation_data, baseline)

            # Generate text report
            success = self._generate_quality_text_report(validation_data, output_path)

            if success:
                self.logger.info(f"Quality validation report generated successfully: {output_path}")

            return success

        except Exception as e:
            self.logger.error(f"Failed to generate quality validation report: {e}")
            return False

    def generate_collector_statistics_report(self,
                                           output_path: str,
                                           top_n: int = 100,
                                           include_kingdom_breakdown: bool = True) -> bool:
        """
        Generate detailed collector statistics report

        Args:
            output_path: Path to save report
            top_n: Number of top collectors to include
            include_kingdom_breakdown: Whether to include kingdom statistics

        Returns:
            True if report generated successfully
        """
        try:
            self.logger.info(f"Generating collector statistics report: {output_path}")

            # Collect collector statistics
            stats_data = self._collect_collector_statistics(top_n, include_kingdom_breakdown)

            # Generate text report
            success = self._generate_statistics_text_report(stats_data, output_path)

            if success:
                self.logger.info(f"Collector statistics report generated successfully: {output_path}")

            return success

        except Exception as e:
            self.logger.error(f"Failed to generate collector statistics report: {e}")
            return False

    def generate_processing_summary(self,
                                  output_path: str,
                                  include_performance_metrics: bool = True) -> bool:
        """
        Generate processing summary with performance metrics

        Args:
            output_path: Path to save summary
            include_performance_metrics: Whether to include performance data

        Returns:
            True if summary generated successfully
        """
        try:
            self.logger.info(f"Generating processing summary: {output_path}")

            # Collect processing data
            processing_data = self._collect_processing_metrics()

            if include_performance_metrics:
                processing_data = self._add_performance_metrics(processing_data)

            # Generate JSON summary
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(processing_data, f, indent=2, default=str, ensure_ascii=False)

            self.logger.info(f"Processing summary generated successfully: {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to generate processing summary: {e}")
            return False

    def _collect_canonicalization_data(self) -> Dict[str, Any]:
        """Collect canonicalization data from database"""

        data = {
            "generation_time": datetime.now(),
            "total_canonical_collectors": 0,
            "total_variations": 0,
            "total_occurrences": 0,
            "entity_type_breakdown": {},
            "kingdom_distribution": {},
            "top_collectors": [],
            "confidence_distribution": {},
            "quality_metrics": {}
        }

        try:
            # Get canonical collectors
            canonical_pipeline = [
                {"$group": {
                    "_id": None,
                    "total_canonicals": {"$sum": 1},
                    "total_occurrences": {"$sum": "$total_ocorrencias"},
                    "entity_types": {"$push": "$tipo_entidade"}
                }}
            ]

            canonical_stats = list(self.mongo_manager.coletores.aggregate(canonical_pipeline))

            if canonical_stats:
                stats = canonical_stats[0]
                data["total_canonical_collectors"] = stats.get("total_canonicals", 0)
                data["total_occurrences"] = stats.get("total_occurrences", 0)

                # Entity type breakdown
                entity_types = stats.get("entity_types", [])
                data["entity_type_breakdown"] = Counter(entity_types)

            # Get variations count
            variation_count = 0
            for collector in self.mongo_manager.coletores.find({}, {"variacoes": 1}):
                variation_count += len(collector.get("variacoes", []))

            data["total_variations"] = variation_count

            # Get top collectors
            top_collectors = list(self.mongo_manager.coletores.find(
                {},
                {
                    "forma_canonica": 1,
                    "tipo_entidade": 1,
                    "total_ocorrencias": 1,
                    "estatisticas_reino": 1
                }
            ).sort("total_ocorrencias", -1).limit(20))

            data["top_collectors"] = [
                {
                    "canonical_form": collector["forma_canonica"],
                    "entity_type": collector["tipo_entidade"],
                    "total_occurrences": collector["total_ocorrencias"],
                    "kingdom_stats": collector.get("estatisticas_reino", {})
                }
                for collector in top_collectors
            ]

            # Kingdom distribution
            kingdom_pipeline = [
                {"$unwind": "$estatisticas_reino"},
                {"$group": {
                    "_id": "$estatisticas_reino.reino",
                    "collectors": {"$sum": 1},
                    "occurrences": {"$sum": "$estatisticas_reino.contagem_coletas"}
                }}
            ]

            kingdom_stats = list(self.mongo_manager.coletores.aggregate(kingdom_pipeline))
            for kingdom in kingdom_stats:
                data["kingdom_distribution"][kingdom["_id"]] = {
                    "collectors": kingdom["collectors"],
                    "occurrences": kingdom["occurrences"]
                }

            return data

        except Exception as e:
            self.logger.error(f"Failed to collect canonicalization data: {e}")
            return data

    def _collect_quality_metrics(self) -> Dict[str, Any]:
        """Collect quality metrics for validation"""

        metrics = {
            "generation_time": datetime.now(),
            "classification_accuracy": {},
            "similarity_distribution": {},
            "confidence_metrics": {},
            "anomaly_detection": {},
            "coverage_analysis": {}
        }

        try:
            # Classification results analysis
            if hasattr(self.mongo_manager, 'classifications'):
                classification_pipeline = [
                    {"$group": {
                        "_id": "$entity_type",
                        "count": {"$sum": 1},
                        "avg_confidence": {"$avg": "$confidence_score"},
                        "min_confidence": {"$min": "$confidence_score"},
                        "max_confidence": {"$max": "$confidence_score"}
                    }}
                ]

                classification_stats = list(self.mongo_manager.classifications.aggregate(classification_pipeline))
                for stat in classification_stats:
                    metrics["classification_accuracy"][stat["_id"]] = {
                        "count": stat["count"],
                        "avg_confidence": stat["avg_confidence"],
                        "min_confidence": stat["min_confidence"],
                        "max_confidence": stat["max_confidence"]
                    }

            # Similarity score distribution
            similarity_ranges = {"0.85-1.0": 0, "0.7-0.85": 0, "0.5-0.7": 0, "0.0-0.5": 0}

            # Confidence score distribution
            confidence_ranges = {"High (>0.8)": 0, "Medium (0.5-0.8)": 0, "Low (<0.5)": 0}

            # These would be populated from actual similarity and confidence data
            metrics["similarity_distribution"] = similarity_ranges
            metrics["confidence_metrics"] = confidence_ranges

            return metrics

        except Exception as e:
            self.logger.error(f"Failed to collect quality metrics: {e}")
            return metrics

    def _collect_collector_statistics(self, top_n: int, include_kingdom: bool) -> Dict[str, Any]:
        """Collect detailed collector statistics"""

        stats = {
            "generation_time": datetime.now(),
            "top_collectors": [],
            "kingdom_specialization": {},
            "temporal_analysis": {},
            "geographic_distribution": {}
        }

        try:
            # Get top collectors with detailed stats
            collectors = list(self.mongo_manager.coletores.find(
                {},
                {
                    "forma_canonica": 1,
                    "tipo_entidade": 1,
                    "total_ocorrencias": 1,
                    "primeira_ocorrencia": 1,
                    "ultima_ocorrencia": 1,
                    "estatisticas_reino": 1,
                    "variacoes": 1
                }
            ).sort("total_ocorrencias", -1).limit(top_n))

            for collector in collectors:
                collector_stat = {
                    "canonical_form": collector["forma_canonica"],
                    "entity_type": collector["tipo_entidade"],
                    "total_occurrences": collector["total_ocorrencias"],
                    "variation_count": len(collector.get("variacoes", [])),
                    "first_occurrence": collector.get("primeira_ocorrencia"),
                    "last_occurrence": collector.get("ultima_ocorrencia"),
                    "active_period_years": self._calculate_active_years(
                        collector.get("primeira_ocorrencia"),
                        collector.get("ultima_ocorrencia")
                    )
                }

                if include_kingdom:
                    kingdom_stats = collector.get("estatisticas_reino", {})
                    collector_stat["kingdom_stats"] = kingdom_stats

                    # Calculate specialization
                    total_collections = sum(
                        kingdom.get("contagem_coletas", 0)
                        for kingdom in kingdom_stats.values()
                    )
                    if total_collections > 0:
                        specialization = {}
                        for kingdom, data in kingdom_stats.items():
                            specialization[kingdom] = data.get("contagem_coletas", 0) / total_collections
                        collector_stat["kingdom_specialization"] = specialization

                stats["top_collectors"].append(collector_stat)

            return stats

        except Exception as e:
            self.logger.error(f"Failed to collect collector statistics: {e}")
            return stats

    def _collect_processing_metrics(self) -> Dict[str, Any]:
        """Collect processing performance metrics"""

        metrics = {
            "generation_time": datetime.now(),
            "database_statistics": {},
            "processing_performance": {},
            "memory_usage": {},
            "checkpoint_statistics": {}
        }

        try:
            # Database collection statistics
            for collection_name in ["coletores", "ocorrencias", "checkpoints"]:
                if hasattr(self.mongo_manager, collection_name):
                    collection = getattr(self.mongo_manager, collection_name)
                    metrics["database_statistics"][collection_name] = {
                        "document_count": collection.count_documents({}),
                        "estimated_size": collection.estimated_document_count()
                    }

            # Checkpoint statistics
            if hasattr(self.mongo_manager, "checkpoints"):
                checkpoint_stats = list(self.mongo_manager.checkpoints.aggregate([
                    {"$group": {
                        "_id": "$checkpoint_type",
                        "count": {"$sum": 1},
                        "latest": {"$max": "$created_at"}
                    }}
                ]))

                for stat in checkpoint_stats:
                    metrics["checkpoint_statistics"][stat["_id"]] = {
                        "count": stat["count"],
                        "latest": stat["latest"]
                    }

            return metrics

        except Exception as e:
            self.logger.error(f"Failed to collect processing metrics: {e}")
            return metrics

    def _enrich_with_analysis_insights(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich report data with complete analysis insights"""

        if not self.analysis_results:
            return report_data

        try:
            analysis = self.analysis_results

            # Add analysis baseline comparison
            report_data["analysis_insights"] = {
                "total_records_analyzed": analysis.get("total_records", 0),
                "analysis_date": analysis.get("analysis_date"),
                "pattern_discovery": analysis.get("pattern_statistics", {}),
                "threshold_recommendations": analysis.get("threshold_analysis", {}),
                "quality_baseline": analysis.get("quality_metrics", {})
            }

            # Compare current results with analysis baseline
            if "total_records_analyzed" in analysis:
                coverage_percent = (report_data.get("total_occurrences", 0) /
                                  analysis["total_records_analyzed"] * 100)
                report_data["analysis_insights"]["processing_coverage"] = coverage_percent

            return report_data

        except Exception as e:
            self.logger.error(f"Failed to enrich with analysis insights: {e}")
            return report_data

    def _add_baseline_comparison(self, validation_data: Dict, baseline: Dict) -> Dict[str, Any]:
        """Add baseline comparison to validation data"""

        try:
            validation_data["baseline_comparison"] = {
                "baseline_date": baseline.get("analysis_date"),
                "baseline_records": baseline.get("total_records", 0),
                "expected_patterns": baseline.get("pattern_statistics", {}),
                "expected_quality": baseline.get("quality_metrics", {}),
                "threshold_compliance": {}
            }

            return validation_data

        except Exception as e:
            self.logger.error(f"Failed to add baseline comparison: {e}")
            return validation_data

    def _add_performance_metrics(self, processing_data: Dict) -> Dict[str, Any]:
        """Add performance metrics to processing data"""

        # This would integrate with actual performance monitoring
        processing_data["performance_metrics"] = {
            "records_per_second": 0,
            "memory_efficiency": {},
            "processing_time": {},
            "checkpoint_overhead": {}
        }

        return processing_data

    def _calculate_active_years(self, first_date: datetime, last_date: datetime) -> int:
        """Calculate number of active years for a collector"""

        if not first_date or not last_date:
            return 0

        delta = last_date - first_date
        return max(1, int(delta.days / 365.25))

    def _generate_text_report(self, data: Dict[str, Any], output_path: str) -> bool:
        """Generate text format report"""

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("CANONICALIZATION REPORT\n")
                f.write("=" * 80 + "\n")
                f.write(f"Generated: {data['generation_time']}\n\n")

                # Summary statistics
                f.write("SUMMARY STATISTICS\n")
                f.write("-" * 40 + "\n")
                f.write(f"Total Canonical Collectors: {data['total_canonical_collectors']:,}\n")
                f.write(f"Total Variations: {data['total_variations']:,}\n")
                f.write(f"Total Occurrences: {data['total_occurrences']:,}\n\n")

                # Entity type breakdown
                if data['entity_type_breakdown']:
                    f.write("ENTITY TYPE BREAKDOWN\n")
                    f.write("-" * 40 + "\n")
                    for entity_type, count in data['entity_type_breakdown'].most_common():
                        percentage = (count / data['total_canonical_collectors']) * 100
                        f.write(f"{entity_type:25}: {count:6,} ({percentage:5.1f}%)\n")
                    f.write("\n")

                # Kingdom distribution
                if data['kingdom_distribution']:
                    f.write("KINGDOM DISTRIBUTION\n")
                    f.write("-" * 40 + "\n")
                    for kingdom, stats in data['kingdom_distribution'].items():
                        f.write(f"{kingdom:15}: {stats['collectors']:5,} collectors, {stats['occurrences']:8,} occurrences\n")
                    f.write("\n")

                # Top collectors
                if data['top_collectors']:
                    f.write("TOP 20 COLLECTORS\n")
                    f.write("-" * 80 + "\n")
                    f.write(f"{'Canonical Form':40} {'Type':20} {'Occurrences':12}\n")
                    f.write("-" * 80 + "\n")

                    for collector in data['top_collectors']:
                        f.write(f"{collector['canonical_form'][:40]:40} "
                               f"{collector['entity_type'][:20]:20} "
                               f"{collector['total_occurrences']:12,}\n")

                # Analysis insights if available
                if 'analysis_insights' in data:
                    f.write("\n" + "=" * 80 + "\n")
                    f.write("ANALYSIS INSIGHTS\n")
                    f.write("=" * 80 + "\n")

                    insights = data['analysis_insights']
                    f.write(f"Analysis Date: {insights.get('analysis_date', 'N/A')}\n")
                    f.write(f"Records Analyzed: {insights.get('total_records_analyzed', 0):,}\n")

                    if 'processing_coverage' in insights:
                        f.write(f"Processing Coverage: {insights['processing_coverage']:.1f}%\n")

            return True

        except Exception as e:
            self.logger.error(f"Failed to generate text report: {e}")
            return False

    def _generate_json_report(self, data: Dict[str, Any], output_path: str) -> bool:
        """Generate JSON format report"""

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str, ensure_ascii=False)
            return True

        except Exception as e:
            self.logger.error(f"Failed to generate JSON report: {e}")
            return False

    def _generate_csv_report(self, data: Dict[str, Any], output_path: str) -> bool:
        """Generate CSV format report"""

        try:
            # Convert top collectors to CSV
            if data['top_collectors']:
                df = pd.DataFrame(data['top_collectors'])
                df.to_csv(output_path, index=False, encoding='utf-8')
                return True

        except Exception as e:
            self.logger.error(f"Failed to generate CSV report: {e}")
            return False

    def _generate_html_report(self, data: Dict[str, Any], output_path: str) -> bool:
        """Generate HTML format report"""

        try:
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Canonicalization Report</title>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; }}
                    h1, h2 {{ color: #333; }}
                    table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                </style>
            </head>
            <body>
                <h1>Canonicalization Report</h1>
                <p><strong>Generated:</strong> {data['generation_time']}</p>

                <h2>Summary Statistics</h2>
                <ul>
                    <li>Total Canonical Collectors: {data['total_canonical_collectors']:,}</li>
                    <li>Total Variations: {data['total_variations']:,}</li>
                    <li>Total Occurrences: {data['total_occurrences']:,}</li>
                </ul>
            </body>
            </html>
            """

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            return True

        except Exception as e:
            self.logger.error(f"Failed to generate HTML report: {e}")
            return False

    def _generate_quality_text_report(self, data: Dict[str, Any], output_path: str) -> bool:
        """Generate quality validation text report"""

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("QUALITY VALIDATION REPORT\n")
                f.write("=" * 80 + "\n")
                f.write(f"Generated: {data['generation_time']}\n\n")

                # Classification accuracy
                if data['classification_accuracy']:
                    f.write("CLASSIFICATION ACCURACY\n")
                    f.write("-" * 40 + "\n")
                    for entity_type, metrics in data['classification_accuracy'].items():
                        f.write(f"{entity_type:25}: {metrics['count']:6,} records, "
                               f"avg confidence: {metrics['avg_confidence']:.3f}\n")
                    f.write("\n")

                # Baseline comparison if available
                if 'baseline_comparison' in data:
                    f.write("BASELINE COMPARISON\n")
                    f.write("-" * 40 + "\n")
                    baseline = data['baseline_comparison']
                    f.write(f"Baseline Date: {baseline.get('baseline_date', 'N/A')}\n")
                    f.write(f"Baseline Records: {baseline.get('baseline_records', 0):,}\n\n")

            return True

        except Exception as e:
            self.logger.error(f"Failed to generate quality text report: {e}")
            return False

    def _generate_statistics_text_report(self, data: Dict[str, Any], output_path: str) -> bool:
        """Generate collector statistics text report"""

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("COLLECTOR STATISTICS REPORT\n")
                f.write("=" * 80 + "\n")
                f.write(f"Generated: {data['generation_time']}\n\n")

                # Top collectors with detailed statistics
                if data['top_collectors']:
                    f.write("TOP COLLECTORS (DETAILED STATISTICS)\n")
                    f.write("=" * 80 + "\n")

                    for i, collector in enumerate(data['top_collectors'], 1):
                        f.write(f"{i:3d}. {collector['canonical_form']}\n")
                        f.write(f"     Type: {collector['entity_type']}\n")
                        f.write(f"     Occurrences: {collector['total_occurrences']:,}\n")
                        f.write(f"     Variations: {collector['variation_count']:,}\n")
                        f.write(f"     Active Years: {collector.get('active_period_years', 'N/A')}\n")

                        if 'kingdom_specialization' in collector:
                            f.write("     Kingdom Specialization:\n")
                            for kingdom, percentage in collector['kingdom_specialization'].items():
                                f.write(f"       {kingdom}: {percentage:.1%}\n")

                        f.write("\n")

            return True

        except Exception as e:
            self.logger.error(f"Failed to generate statistics text report: {e}")
            return False