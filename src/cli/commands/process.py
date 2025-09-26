"""
Processing Command for CLI

Wraps processar_coletores.py with enhanced CLI interface and integration
with the complete canonicalization pipeline.
"""

import logging
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any
import json
from datetime import datetime


class ProcessCommand:
    """Command handler for collector canonicalization processing"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def get_description(self) -> str:
        return "Process collectors with canonicalization using discovered patterns"

    def add_arguments(self, parser):
        """Add command-specific arguments"""

        parser.add_argument(
            '--analysis-results',
            type=str,
            help='Path to analysis results JSON file (required for pattern-driven processing)'
        )

        parser.add_argument(
            '--output-path',
            type=str,
            help='Path to save processing results'
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
            '--force-refresh',
            action='store_true',
            help='Force fresh processing even if results exist'
        )

        parser.add_argument(
            '--enable-checkpoints',
            action='store_true',
            help='Enable checkpoint management for recovery'
        )

        parser.description = '''
Process collector canonicalization using patterns discovered from complete dataset analysis.

This command uses the enhanced processar_coletores.py script which automatically
loads optimized thresholds and patterns from the analysis phase.

IMPORTANT: This command requires analysis results from the "analyze" command.
The analysis results provide dynamic thresholds and patterns that optimize
processing accuracy and performance.

Examples:
  python -m src.cli process --analysis-results analysis.json
  python -m src.cli process --analysis-results analysis.json --batch-size 2000
  python -m src.cli process --analysis-results analysis.json --enable-checkpoints
        '''

    def execute(self, args) -> Dict[str, Any]:
        """Execute the processing command"""

        self.logger.info("Starting collector canonicalization processing...")

        # Validate analysis results requirement
        if not args.analysis_results:
            error_msg = """
Analysis results are required for processing. Please run analysis first:
  python -m src.cli analyze --save-patterns
  python -m src.cli process --analysis-results analysis.json
            """.strip()
            self.logger.error(error_msg)
            return {
                'success': False,
                'exit_code': 1,
                'error': error_msg
            }

        # Validate analysis results file exists
        analysis_path = Path(args.analysis_results)
        if not analysis_path.exists():
            error_msg = f"Analysis results file not found: {args.analysis_results}"
            self.logger.error(error_msg)
            return {
                'success': False,
                'exit_code': 1,
                'error': error_msg
            }

        try:
            # Prepare command arguments
            cmd_args = [
                sys.executable,
                str(Path('src') / 'processar_coletores.py'),
                '--analysis-results', args.analysis_results
            ]

            # Add optional arguments that the script supports
            if hasattr(args, 'sample') and args.sample:
                cmd_args.extend(['--sample', str(args.sample)])

            if hasattr(args, 'restart') and args.restart:
                cmd_args.append('--restart')

            if hasattr(args, 'revisao') and args.revisao:
                cmd_args.append('--revisao')

            if hasattr(args, 'no_analysis_integration') and args.no_analysis_integration:
                cmd_args.append('--no-analysis-integration')

            # Execute the processing script
            self.logger.info(f"Executing: {' '.join(cmd_args)}")

            result = subprocess.run(
                cmd_args,
                capture_output=True,
                text=True,
                cwd=Path.cwd()
            )

            # Process results
            if result.returncode == 0:
                self.logger.info("Processing completed successfully")

                # Parse output for summary information
                summary = self._parse_processing_output(result.stdout)

                return {
                    'success': True,
                    'exit_code': 0,
                    'summary': summary,
                    'stdout': result.stdout,
                    'next_steps': [
                        "Processing complete! Now you can:",
                        "1. Run 'python -m src.cli reports' to generate reports",
                        "2. Run 'python -m src.cli validate' to validate results",
                        "3. Review processing logs for detailed information"
                    ]
                }
            else:
                self.logger.error(f"Processing failed with exit code {result.returncode}")
                self.logger.error(f"Error output: {result.stderr}")

                return {
                    'success': False,
                    'exit_code': result.returncode,
                    'error': result.stderr,
                    'stdout': result.stdout
                }

        except FileNotFoundError:
            error_msg = "Processing script not found. Please ensure processar_coletores.py exists in src/"
            self.logger.error(error_msg)
            return {
                'success': False,
                'exit_code': 1,
                'error': error_msg
            }

        except Exception as e:
            error_msg = f"Unexpected error during processing: {e}"
            self.logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'exit_code': 1,
                'error': error_msg
            }

    def _parse_processing_output(self, stdout: str) -> Dict[str, Any]:
        """Parse processing output to extract summary information"""

        summary = {
            'execution_time': 'unknown',
            'total_processed': 'unknown',
            'canonical_groups': 'unknown',
            'processing_rate': 'unknown'
        }

        try:
            lines = stdout.split('\n')
            for line in lines:
                if 'Total de coletores processados:' in line:
                    # Extract number from line like "Total de coletores processados: 45,678"
                    parts = line.split(':')
                    if len(parts) > 1:
                        summary['total_processed'] = parts[1].strip()

                elif 'Grupos canônicos criados:' in line:
                    parts = line.split(':')
                    if len(parts) > 1:
                        summary['canonical_groups'] = parts[1].strip()

                elif 'Tempo total de processamento:' in line:
                    parts = line.split(':')
                    if len(parts) > 1:
                        summary['execution_time'] = parts[1].strip()

                elif 'Taxa de processamento:' in line:
                    parts = line.split(':')
                    if len(parts) > 1:
                        summary['processing_rate'] = parts[1].strip()

        except Exception as e:
            self.logger.warning(f"Error parsing processing output: {e}")

        return summary