"""
Reports Command for CLI

Wraps gerar_relatorios.py with enhanced CLI interface and integration
with the complete canonicalization pipeline.
"""

import logging
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any
import json
from datetime import datetime


class ReportsCommand:
    """Command handler for generating canonicalization reports"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def get_description(self) -> str:
        return "Generate canonicalization reports with analysis insights"

    def add_arguments(self, parser):
        """Add command-specific arguments"""

        parser.add_argument(
            '--analysis-results',
            type=str,
            help='Path to analysis results JSON file for enhanced reports'
        )

        parser.add_argument(
            '--output-dir',
            type=str,
            default='reports',
            help='Directory to save generated reports (default: reports)'
        )

        parser.add_argument(
            '--database-config',
            type=str,
            help='Path to database configuration file'
        )

        parser.add_argument(
            '--include-analysis',
            action='store_true',
            help='Include complete dataset analysis insights in reports'
        )

        parser.add_argument(
            '--report-format',
            choices=['html', 'pdf', 'json', 'csv'],
            default='html',
            help='Report output format (default: html)'
        )

        parser.add_argument(
            '--detailed-stats',
            action='store_true',
            help='Include detailed statistics in reports'
        )

        parser.add_argument(
            '--comparison-mode',
            action='store_true',
            help='Generate comparison reports against baseline'
        )

        parser.description = '''
Generate comprehensive canonicalization reports with analysis insights.

This command uses the enhanced gerar_relatorios.py script which can include
insights from complete dataset analysis and generate various report formats.

The reports include:
- Processing statistics and performance metrics
- Canonicalization quality assessment
- Entity type distribution analysis
- Pattern discovery insights (when analysis results provided)
- Comparison against baseline (when available)

Examples:
  python -m src.cli reports --include-analysis
  python -m src.cli reports --analysis-results analysis.json --detailed-stats
  python -m src.cli reports --report-format pdf --output-dir final_reports
  python -m src.cli reports --comparison-mode --analysis-results analysis.json
        '''

    def execute(self, args) -> Dict[str, Any]:
        """Execute the reports command"""

        self.logger.info("Starting canonicalization report generation...")

        try:
            # Prepare command arguments
            cmd_args = [
                sys.executable,
                str(Path('src') / 'gerar_relatorios.py')
            ]

            # Add optional arguments
            if args.analysis_results:
                cmd_args.extend(['--analysis-results', args.analysis_results])

            if args.output_dir:
                cmd_args.extend(['--output-dir', args.output_dir])

            if args.database_config:
                cmd_args.extend(['--config', args.database_config])

            if args.report_format:
                cmd_args.extend(['--format', args.report_format])

            if args.include_analysis:
                cmd_args.append('--include-analysis')

            if args.detailed_stats:
                cmd_args.append('--detailed-stats')

            if args.comparison_mode:
                cmd_args.append('--comparison-mode')

            # Execute the reports script
            self.logger.info(f"Executing: {' '.join(cmd_args)}")

            result = subprocess.run(
                cmd_args,
                capture_output=True,
                text=True,
                cwd=Path.cwd()
            )

            # Process results
            if result.returncode == 0:
                self.logger.info("Report generation completed successfully")

                # Parse output for summary information
                summary = self._parse_reports_output(result.stdout, args.output_dir)

                return {
                    'success': True,
                    'exit_code': 0,
                    'summary': summary,
                    'stdout': result.stdout,
                    'next_steps': [
                        "Reports generated successfully! Next steps:",
                        f"1. Review reports in '{args.output_dir}' directory",
                        "2. Run 'python -m src.cli validate' to validate canonicalization quality",
                        "3. Share reports with stakeholders for review"
                    ]
                }
            else:
                self.logger.error(f"Report generation failed with exit code {result.returncode}")
                self.logger.error(f"Error output: {result.stderr}")

                return {
                    'success': False,
                    'exit_code': result.returncode,
                    'error': result.stderr,
                    'stdout': result.stdout
                }

        except FileNotFoundError:
            error_msg = "Reports script not found. Please ensure gerar_relatorios.py exists in src/"
            self.logger.error(error_msg)
            return {
                'success': False,
                'exit_code': 1,
                'error': error_msg
            }

        except Exception as e:
            error_msg = f"Unexpected error during report generation: {e}"
            self.logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'exit_code': 1,
                'error': error_msg
            }

    def _parse_reports_output(self, stdout: str, output_dir: str) -> Dict[str, Any]:
        """Parse reports output to extract summary information"""

        summary = {
            'execution_time': 'unknown',
            'reports_generated': 'unknown',
            'output_directory': output_dir,
            'report_files': []
        }

        try:
            lines = stdout.split('\n')
            for line in lines:
                if 'Relatórios gerados:' in line:
                    # Extract number from line like "Relatórios gerados: 5"
                    parts = line.split(':')
                    if len(parts) > 1:
                        summary['reports_generated'] = parts[1].strip()

                elif 'Tempo de geração:' in line:
                    parts = line.split(':')
                    if len(parts) > 1:
                        summary['execution_time'] = parts[1].strip()

                elif 'Arquivo gerado:' in line:
                    # Extract file path from line like "Arquivo gerado: reports/canonicalizacao_report.html"
                    parts = line.split(':', 1)
                    if len(parts) > 1:
                        file_path = parts[1].strip()
                        summary['report_files'].append(file_path)

        except Exception as e:
            self.logger.warning(f"Error parsing reports output: {e}")

        # If no files were found in output, try to list common report files
        if not summary['report_files']:
            output_path = Path(output_dir)
            if output_path.exists():
                common_patterns = ['*.html', '*.pdf', '*.json', '*.csv']
                for pattern in common_patterns:
                    for file_path in output_path.glob(pattern):
                        summary['report_files'].append(str(file_path))

        return summary