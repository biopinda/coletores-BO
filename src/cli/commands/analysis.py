"""
Analysis Command for CLI

Wraps analise_coletores.py with enhanced CLI interface and integration
with the complete canonicalization pipeline.
"""

import logging
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any
import json
from datetime import datetime


class AnalysisCommand:
    """Command handler for complete dataset analysis"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def get_description(self) -> str:
        return "Run complete dataset analysis (processes ALL records)"

    def add_arguments(self, parser):
        """Add command-specific arguments"""

        parser.add_argument(
            '--output-path',
            type=str,
            help='Path to save analysis results JSON file'
        )

        parser.add_argument(
            '--database-config',
            type=str,
            help='Path to database configuration file'
        )

        parser.add_argument(
            '--save-patterns',
            action='store_true',
            help='Save discovered patterns for downstream processing'
        )

        parser.add_argument(
            '--force-fresh-analysis',
            action='store_true',
            help='Force fresh analysis even if recent results exist'
        )

        parser.description = '''
Run complete dataset analysis of all records in the "ocorrencias" collection.

This command processes ALL records (11M+) to discover patterns, calculate
statistics, and generate baseline data for the canonicalization pipeline.

IMPORTANT: This is the first step that should be run before any processing.
The analysis results are used by all subsequent steps to optimize processing.

Examples:
  python -m src.cli analyze --save-patterns
  python -m src.cli analyze --output-path analysis_results.json
        '''

    def execute(self, args) -> Dict[str, Any]:
        """Execute the analysis command"""

        self.logger.info("Starting complete dataset analysis...")

        try:
            # Prepare command arguments
            cmd_args = [
                sys.executable,
                str(Path('src') / 'analise_coletores.py')
            ]

            # Add optional arguments
            if args.output_path:
                cmd_args.extend(['--output', args.output_path])

            if args.database_config:
                cmd_args.extend(['--config', args.database_config])

            if args.force_fresh_analysis:
                cmd_args.append('--force-refresh')

            # Execute the analysis script
            self.logger.info(f"Executing: {' '.join(cmd_args)}")

            # Run with real-time output for progress monitoring
            print(f"\n[INICIANDO] Análise completa do dataset de 10.5M+ registros")
            print(f"[INFO] Comando: {' '.join(cmd_args)}")
            print(f"[AVISO] Esta operação pode demorar 1-3 horas")
            print(f"{'='*80}")

            result = subprocess.run(
                cmd_args,
                text=True,
                cwd=Path.cwd()
            )

            # Process results
            if result.returncode == 0:
                self.logger.info("Analysis completed successfully")

                print(f"\n{'='*80}")
                print(f"[SUCESSO] Análise completa concluída!")
                print(f"{'='*80}")
                print(f"Próximos passos disponíveis:")
                print(f"  1. python -m src.cli process  # Canonicalizar coletores")
                print(f"  2. python -m src.cli reports  # Gerar relatórios")
                print(f"  3. python -m src.cli validate # Validar resultados")
                print(f"{'='*80}")

                return {
                    'success': True,
                    'exit_code': 0,
                    'summary': {'message': 'Analysis completed successfully'},
                    'next_steps': [
                        "Analysis complete! Now you can:",
                        "1. Run 'python -m src.cli process' to canonicalize collectors",
                        "2. Run 'python -m src.cli reports' to generate reports",
                        "3. Run 'python -m src.cli validate' to validate results"
                    ]
                }
            else:
                self.logger.error(f"Analysis failed with exit code {result.returncode}")

                print(f"\n{'='*80}")
                print(f"[ERRO] Análise falhou com código de saída {result.returncode}")
                print(f"[DICA] Verifique os logs em logs/analise_completa.log")
                print(f"{'='*80}")

                return {
                    'success': False,
                    'exit_code': result.returncode,
                    'error': f'Analysis failed with exit code {result.returncode}'
                }

        except FileNotFoundError:
            error_msg = "Analysis script not found. Please ensure analise_coletores.py exists in src/"
            self.logger.error(error_msg)
            return {
                'success': False,
                'exit_code': 1,
                'error': error_msg
            }

        except Exception as e:
            error_msg = f"Unexpected error during analysis: {e}"
            self.logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'exit_code': 1,
                'error': error_msg
            }

    def _parse_analysis_output(self, stdout: str) -> Dict[str, Any]:
        """Parse analysis output to extract summary information"""

        summary = {
            'execution_time': 'unknown',
            'total_records': 'unknown',
            'unique_collectors': 'unknown',
            'patterns_discovered': 'unknown'
        }

        try:
            lines = stdout.split('\n')
            for line in lines:
                if 'Total de registros processados:' in line:
                    # Extract number from line like "Total de registros processados: 11,234,567"
                    parts = line.split(':')
                    if len(parts) > 1:
                        summary['total_records'] = parts[1].strip()

                elif 'Coletores únicos estimados:' in line:
                    parts = line.split(':')
                    if len(parts) > 1:
                        summary['unique_collectors'] = parts[1].strip()

                elif 'Tempo total de análise:' in line:
                    parts = line.split(':')
                    if len(parts) > 1:
                        summary['execution_time'] = parts[1].strip()

                elif 'Padrões descobertos:' in line:
                    parts = line.split(':')
                    if len(parts) > 1:
                        summary['patterns_discovered'] = parts[1].strip()

        except Exception as e:
            self.logger.warning(f"Error parsing analysis output: {e}")

        return summary