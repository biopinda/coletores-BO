"""
Validation Command for CLI

Wraps validar_canonicalizacao.py with enhanced CLI interface and integration
with the complete canonicalization pipeline.
"""

import logging
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any
import json
from datetime import datetime


class ValidateCommand:
    """Command handler for canonicalization quality validation"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def get_description(self) -> str:
        return "Validate canonicalization quality against baseline analysis"

    def add_arguments(self, parser):
        """Add command-specific arguments"""

        parser.add_argument(
            '--baseline-analysis',
            type=str,
            help='Path to baseline analysis results JSON file for validation'
        )

        parser.add_argument(
            '--output-path',
            type=str,
            help='Path to save validation results'
        )

        parser.add_argument(
            '--database-config',
            type=str,
            help='Path to database configuration file'
        )

        parser.add_argument(
            '--validation-level',
            choices=['basic', 'comprehensive', 'full'],
            default='comprehensive',
            help='Level of validation to perform (default: comprehensive)'
        )

        parser.add_argument(
            '--quality-threshold',
            type=float,
            default=0.85,
            help='Minimum quality threshold for validation (default: 0.85)'
        )

        parser.add_argument(
            '--sample-size',
            type=int,
            help='Sample size for validation (default: use all data)'
        )

        parser.add_argument(
            '--generate-report',
            action='store_true',
            help='Generate detailed validation report'
        )

        parser.add_argument(
            '--strict-validation',
            action='store_true',
            help='Use strict validation criteria'
        )

        parser.description = '''
Validate canonicalization quality against baseline analysis and expected patterns.

This command uses the enhanced validar_canonicalizacao.py script which compares
current canonicalization results against the baseline established by complete
dataset analysis.

Validation includes:
- Quality metrics against baseline patterns
- Entity type distribution validation
- Similarity score distribution checks
- Performance validation against expected thresholds
- Data integrity and consistency checks

Examples:
  python -m src.cli validate --baseline-analysis analysis.json
  python -m src.cli validate --validation-level full --generate-report
  python -m src.cli validate --quality-threshold 0.90 --strict-validation
  python -m src.cli validate --sample-size 10000 --output-path validation.json
        '''

    def execute(self, args) -> Dict[str, Any]:
        """Execute the validation command"""

        self.logger.info("Starting canonicalization quality validation...")

        try:
            # Prepare command arguments
            cmd_args = [
                sys.executable,
                str(Path('src') / 'validar_canonicalizacao.py')
            ]

            # Add optional arguments
            if args.baseline_analysis:
                cmd_args.extend(['--baseline-analysis', args.baseline_analysis])

            if args.output_path:
                cmd_args.extend(['--output', args.output_path])

            if args.database_config:
                cmd_args.extend(['--config', args.database_config])

            if args.validation_level:
                cmd_args.extend(['--level', args.validation_level])

            if args.quality_threshold:
                cmd_args.extend(['--threshold', str(args.quality_threshold)])

            if args.sample_size:
                cmd_args.extend(['--sample-size', str(args.sample_size)])

            if args.generate_report:
                cmd_args.append('--generate-report')

            if args.strict_validation:
                cmd_args.append('--strict-validation')

            # Execute the validation script
            self.logger.info(f"Executing: {' '.join(cmd_args)}")

            result = subprocess.run(
                cmd_args,
                capture_output=True,
                text=True,
                cwd=Path.cwd()
            )

            # Process results
            if result.returncode == 0:
                self.logger.info("Validation completed successfully")

                # Parse output for summary information
                summary = self._parse_validation_output(result.stdout)

                return {
                    'success': True,
                    'exit_code': 0,
                    'summary': summary,
                    'stdout': result.stdout,
                    'next_steps': [
                        "Validation complete! Results:",
                        f"1. Quality score: {summary.get('quality_score', 'unknown')}",
                        f"2. Validation status: {summary.get('validation_status', 'unknown')}",
                        "3. Review detailed results for any issues",
                        "4. Consider re-running analysis if quality is below threshold"
                    ]
                }
            else:
                self.logger.error(f"Validation failed with exit code {result.returncode}")
                self.logger.error(f"Error output: {result.stderr}")

                # Check if it's a validation failure (quality below threshold) vs system error
                validation_failure = "Quality threshold not met" in result.stderr or "Validation failed" in result.stderr

                return {
                    'success': False,
                    'exit_code': result.returncode,
                    'error': result.stderr,
                    'stdout': result.stdout,
                    'validation_failure': validation_failure
                }

        except FileNotFoundError:
            error_msg = "Validation script not found. Please ensure validar_canonicalizacao.py exists in src/"
            self.logger.error(error_msg)
            return {
                'success': False,
                'exit_code': 1,
                'error': error_msg
            }

        except Exception as e:
            error_msg = f"Unexpected error during validation: {e}"
            self.logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'exit_code': 1,
                'error': error_msg
            }

    def _parse_validation_output(self, stdout: str) -> Dict[str, Any]:
        """Parse validation output to extract summary information"""

        summary = {
            'execution_time': 'unknown',
            'validation_status': 'unknown',
            'quality_score': 'unknown',
            'tests_passed': 'unknown',
            'tests_failed': 'unknown',
            'warnings': 'unknown'
        }

        try:
            lines = stdout.split('\n')
            for line in lines:
                if 'Pontuação de qualidade:' in line:
                    # Extract score from line like "Pontuação de qualidade: 0.87"
                    parts = line.split(':')
                    if len(parts) > 1:
                        summary['quality_score'] = parts[1].strip()

                elif 'Status da validação:' in line:
                    parts = line.split(':')
                    if len(parts) > 1:
                        summary['validation_status'] = parts[1].strip()

                elif 'Testes aprovados:' in line:
                    parts = line.split(':')
                    if len(parts) > 1:
                        summary['tests_passed'] = parts[1].strip()

                elif 'Testes falharam:' in line:
                    parts = line.split(':')
                    if len(parts) > 1:
                        summary['tests_failed'] = parts[1].strip()

                elif 'Tempo de validação:' in line:
                    parts = line.split(':')
                    if len(parts) > 1:
                        summary['execution_time'] = parts[1].strip()

                elif 'Avisos encontrados:' in line:
                    parts = line.split(':')
                    if len(parts) > 1:
                        summary['warnings'] = parts[1].strip()

        except Exception as e:
            self.logger.warning(f"Error parsing validation output: {e}")

        return summary