"""
Pipeline Command for CLI

Orchestrates the complete canonicalization pipeline in the correct execution order:
análise → processamento → relatórios → validação
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List
from pathlib import Path

from .analysis import AnalysisCommand
from .process import ProcessCommand
from .reports import ReportsCommand
from .validate import ValidateCommand


class PipelineCommand:
    """Command handler for complete canonicalization pipeline execution"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Initialize command handlers
        self.analysis_cmd = AnalysisCommand()
        self.process_cmd = ProcessCommand()
        self.reports_cmd = ReportsCommand()
        self.validate_cmd = ValidateCommand()

    def get_description(self) -> str:
        return "Run complete pipeline in correct order (analyze → process → reports → validate)"

    def add_arguments(self, parser):
        """Add command-specific arguments"""

        parser.add_argument(
            '--full-process',
            action='store_true',
            help='Run complete pipeline from analysis to validation'
        )

        parser.add_argument(
            '--skip-analysis',
            action='store_true',
            help='Skip analysis phase (use existing results)'
        )

        parser.add_argument(
            '--analysis-results',
            type=str,
            help='Path to existing analysis results (if skipping analysis)'
        )

        parser.add_argument(
            '--output-dir',
            type=str,
            default='pipeline_results',
            help='Directory for all pipeline outputs (default: pipeline_results)'
        )

        parser.add_argument(
            '--database-config',
            type=str,
            help='Path to database configuration file'
        )

        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Batch size for processing (default: 1000)'
        )

        parser.add_argument(
            '--quality-threshold',
            type=float,
            default=0.85,
            help='Minimum quality threshold for validation (default: 0.85)'
        )

        parser.add_argument(
            '--stop-on-failure',
            action='store_true',
            help='Stop pipeline execution on first command failure'
        )

        parser.add_argument(
            '--generate-final-report',
            action='store_true',
            help='Generate comprehensive final report'
        )

        parser.description = '''
Execute the complete canonicalization pipeline in the correct execution order.

EXECUTION ORDER (MANDATORY):
1. análise (analyze) - Discover patterns from complete dataset (11M+ records)
2. processamento (process) - Apply discovered patterns for canonicalization
3. relatórios (reports) - Generate comprehensive reports with insights
4. validação (validate) - Validate quality against baseline

This command ensures proper dependency management and provides comprehensive
logging and monitoring throughout the entire pipeline execution.

Examples:
  python -m src.cli pipeline --full-process
  python -m src.cli pipeline --skip-analysis --analysis-results analysis.json
  python -m src.cli pipeline --quality-threshold 0.90 --generate-final-report
  python -m src.cli pipeline --batch-size 2000 --stop-on-failure
        '''

    def execute(self, args) -> Dict[str, Any]:
        """Execute the complete pipeline"""

        self.logger.info("=" * 80)
        self.logger.info("STARTING COMPLETE CANONICALIZATION PIPELINE")
        self.logger.info("=" * 80)

        pipeline_start = datetime.now()
        pipeline_results = {
            'pipeline_start': pipeline_start,
            'execution_order': [],
            'stage_results': {},
            'overall_success': False,
            'total_duration': None,
            'final_summary': {}
        }

        # Create output directory
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Stage 1: Analysis (if not skipped)
            if not args.skip_analysis:
                self.logger.info("\n" + "=" * 60)
                self.logger.info("STAGE 1: COMPLETE DATASET ANALYSIS")
                self.logger.info("=" * 60)

                analysis_result = self._execute_analysis_stage(args, output_dir)
                pipeline_results['stage_results']['analysis'] = analysis_result
                pipeline_results['execution_order'].append('analysis')

                if not analysis_result['success'] and args.stop_on_failure:
                    self.logger.error("Analysis stage failed. Stopping pipeline.")
                    return self._finalize_pipeline_results(pipeline_results, False)

                # Set analysis results path for subsequent stages
                analysis_results_path = output_dir / "analysis_results.json"

            else:
                self.logger.info("Skipping analysis stage (using existing results)")
                if not args.analysis_results:
                    error_msg = "Analysis results path required when skipping analysis"
                    self.logger.error(error_msg)
                    return self._finalize_pipeline_results(pipeline_results, False, error_msg)

                analysis_results_path = Path(args.analysis_results)
                if not analysis_results_path.exists():
                    error_msg = f"Analysis results file not found: {args.analysis_results}"
                    self.logger.error(error_msg)
                    return self._finalize_pipeline_results(pipeline_results, False, error_msg)

            # Stage 2: Processing
            self.logger.info("\n" + "=" * 60)
            self.logger.info("STAGE 2: COLLECTOR CANONICALIZATION PROCESSING")
            self.logger.info("=" * 60)

            process_result = self._execute_processing_stage(args, output_dir, analysis_results_path)
            pipeline_results['stage_results']['processing'] = process_result
            pipeline_results['execution_order'].append('processing')

            if not process_result['success'] and args.stop_on_failure:
                self.logger.error("Processing stage failed. Stopping pipeline.")
                return self._finalize_pipeline_results(pipeline_results, False)

            # Stage 3: Reports
            self.logger.info("\n" + "=" * 60)
            self.logger.info("STAGE 3: REPORT GENERATION")
            self.logger.info("=" * 60)

            reports_result = self._execute_reports_stage(args, output_dir, analysis_results_path)
            pipeline_results['stage_results']['reports'] = reports_result
            pipeline_results['execution_order'].append('reports')

            if not reports_result['success'] and args.stop_on_failure:
                self.logger.error("Reports stage failed. Stopping pipeline.")
                return self._finalize_pipeline_results(pipeline_results, False)

            # Stage 4: Validation
            self.logger.info("\n" + "=" * 60)
            self.logger.info("STAGE 4: QUALITY VALIDATION")
            self.logger.info("=" * 60)

            validate_result = self._execute_validation_stage(args, output_dir, analysis_results_path)
            pipeline_results['stage_results']['validation'] = validate_result
            pipeline_results['execution_order'].append('validation')

            # Determine overall success
            overall_success = all(
                result['success'] for result in pipeline_results['stage_results'].values()
            )

            # Generate final report if requested
            if args.generate_final_report:
                self.logger.info("\n" + "=" * 60)
                self.logger.info("GENERATING FINAL COMPREHENSIVE REPORT")
                self.logger.info("=" * 60)
                self._generate_final_pipeline_report(pipeline_results, output_dir)

            return self._finalize_pipeline_results(pipeline_results, overall_success)

        except Exception as e:
            self.logger.error(f"Unexpected error in pipeline execution: {e}", exc_info=True)
            return self._finalize_pipeline_results(pipeline_results, False, str(e))

    def _execute_analysis_stage(self, args, output_dir: Path) -> Dict[str, Any]:
        """Execute analysis stage"""

        # Prepare analysis arguments
        analysis_args = type('Args', (), {
            'output_path': str(output_dir / "analysis_results.json"),
            'database_config': args.database_config,
            'save_patterns': True,
            'force_fresh_analysis': False
        })()

        stage_start = time.time()
        result = self.analysis_cmd.execute(analysis_args)
        result['stage_duration'] = time.time() - stage_start

        self.logger.info(f"Analysis stage completed in {result['stage_duration']:.1f} seconds")
        return result

    def _execute_processing_stage(self, args, output_dir: Path, analysis_results_path: Path) -> Dict[str, Any]:
        """Execute processing stage"""

        # Prepare processing arguments
        process_args = type('Args', (), {
            'analysis_results': str(analysis_results_path),
            'output_path': str(output_dir / "processing_results.json"),
            'database_config': args.database_config,
            'batch_size': args.batch_size,
            'force_refresh': False,
            'enable_checkpoints': False
        })()

        stage_start = time.time()
        result = self.process_cmd.execute(process_args)
        result['stage_duration'] = time.time() - stage_start

        self.logger.info(f"Processing stage completed in {result['stage_duration']:.1f} seconds")
        return result

    def _execute_reports_stage(self, args, output_dir: Path, analysis_results_path: Path) -> Dict[str, Any]:
        """Execute reports stage"""

        # Prepare reports arguments
        reports_args = type('Args', (), {
            'analysis_results': str(analysis_results_path),
            'output_dir': str(output_dir / "reports"),
            'database_config': args.database_config,
            'include_analysis': True,
            'report_format': 'html',
            'detailed_stats': True,
            'comparison_mode': True
        })()

        stage_start = time.time()
        result = self.reports_cmd.execute(reports_args)
        result['stage_duration'] = time.time() - stage_start

        self.logger.info(f"Reports stage completed in {result['stage_duration']:.1f} seconds")
        return result

    def _execute_validation_stage(self, args, output_dir: Path, analysis_results_path: Path) -> Dict[str, Any]:
        """Execute validation stage"""

        # Prepare validation arguments
        validate_args = type('Args', (), {
            'baseline_analysis': str(analysis_results_path),
            'output_path': str(output_dir / "validation_results.json"),
            'database_config': args.database_config,
            'validation_level': 'comprehensive',
            'quality_threshold': args.quality_threshold,
            'sample_size': None,
            'generate_report': True,
            'strict_validation': False
        })()

        stage_start = time.time()
        result = self.validate_cmd.execute(validate_args)
        result['stage_duration'] = time.time() - stage_start

        self.logger.info(f"Validation stage completed in {result['stage_duration']:.1f} seconds")
        return result

    def _generate_final_pipeline_report(self, pipeline_results: Dict[str, Any], output_dir: Path):
        """Generate comprehensive final pipeline report"""

        report_lines = [
            "# Complete Canonicalization Pipeline Report",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Pipeline Execution Summary",
            f"- Execution Order: {' → '.join(pipeline_results['execution_order'])}",
            f"- Total Duration: {pipeline_results.get('total_duration', 'unknown')}",
            f"- Overall Success: {'✅' if pipeline_results['overall_success'] else '❌'}",
            ""
        ]

        # Add stage summaries
        for stage_name, result in pipeline_results['stage_results'].items():
            status_icon = "✅" if result['success'] else "❌"
            duration = result.get('stage_duration', 'unknown')

            report_lines.extend([
                f"## {stage_name.title()} Stage {status_icon}",
                f"- Duration: {duration:.1f}s" if isinstance(duration, (int, float)) else f"- Duration: {duration}",
                f"- Exit Code: {result.get('exit_code', 'unknown')}",
                ""
            ])

            # Add stage-specific summary
            if 'summary' in result:
                summary = result['summary']
                for key, value in summary.items():
                    report_lines.append(f"- {key.replace('_', ' ').title()}: {value}")
                report_lines.append("")

        # Write final report
        final_report_path = output_dir / "pipeline_final_report.md"
        try:
            with open(final_report_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(report_lines))
            self.logger.info(f"Final pipeline report saved to: {final_report_path}")
        except Exception as e:
            self.logger.error(f"Failed to generate final report: {e}")

    def _finalize_pipeline_results(self, pipeline_results: Dict[str, Any], success: bool, error: str = None) -> Dict[str, Any]:
        """Finalize pipeline results"""

        pipeline_end = datetime.now()
        total_duration = pipeline_end - pipeline_results['pipeline_start']

        pipeline_results.update({
            'pipeline_end': pipeline_end,
            'total_duration': total_duration.total_seconds(),
            'overall_success': success,
            'success': success,
            'exit_code': 0 if success else 1
        })

        if error:
            pipeline_results['error'] = error

        # Generate final summary
        pipeline_results['final_summary'] = {
            'execution_order': ' → '.join(pipeline_results['execution_order']),
            'stages_executed': len(pipeline_results['execution_order']),
            'total_duration_formatted': str(total_duration).split('.')[0],  # Remove microseconds
            'overall_status': 'SUCCESS' if success else 'FAILED'
        }

        self.logger.info("\n" + "=" * 80)
        self.logger.info("PIPELINE EXECUTION COMPLETED")
        self.logger.info("=" * 80)
        self.logger.info(f"Status: {pipeline_results['final_summary']['overall_status']}")
        self.logger.info(f"Duration: {pipeline_results['final_summary']['total_duration_formatted']}")
        self.logger.info(f"Stages: {pipeline_results['final_summary']['execution_order']}")
        self.logger.info("=" * 80)

        return pipeline_results