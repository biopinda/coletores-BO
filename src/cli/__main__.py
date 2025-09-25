"""
Main CLI Entry Point for Collector Canonicalization System

This is the primary command-line interface that orchestrates the complete
canonicalization pipeline with proper execution order and dependency management.

Usage:
    python -m src.cli [command] [options]

Commands:
    analyze     - Run complete dataset analysis (analise_coletores.py)
    process     - Process collectors with canonicalization (processar_coletores.py)
    reports     - Generate canonicalization reports (gerar_relatorios.py)
    validate    - Validate canonicalization quality (validar_canonicalizacao.py)
    pipeline    - Run complete pipeline in correct order
    status      - Show system status and health
"""

import sys
import os
import argparse
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.cli.commands.analysis import AnalysisCommand
from src.cli.commands.process import ProcessCommand
from src.cli.commands.reports import ReportsCommand
from src.cli.commands.validate import ValidateCommand
from src.cli.commands.pipeline import PipelineCommand
from src.cli.commands.status import StatusCommand
from src.services.performance_monitor import PerformanceMonitor


class ColetoresCLI:
    """
    Main CLI orchestrator for the collector canonicalization system

    Provides unified interface to all processing stages with proper
    dependency management and execution order enforcement.
    """

    def __init__(self):
        self.logger = self._setup_logging()
        self.performance_monitor = PerformanceMonitor()

        # Initialize command handlers
        self.commands = {
            'analyze': AnalysisCommand(),
            'process': ProcessCommand(),
            'reports': ReportsCommand(),
            'validate': ValidateCommand(),
            'pipeline': PipelineCommand(),
            'status': StatusCommand()
        }

    def _setup_logging(self) -> logging.Logger:
        """Setup CLI logging configuration"""

        # Create logs directory
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / 'cli.log', encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )

        # Set specific log levels
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('pymongo').setLevel(logging.WARNING)

        return logging.getLogger(__name__)

    def create_parser(self) -> argparse.ArgumentParser:
        """Create the main argument parser"""

        parser = argparse.ArgumentParser(
            prog='coletores-cli',
            description='Collector Canonicalization System - Complete Pipeline',
            epilog='''
Examples:
  # Run complete analysis of all records
  python -m src.cli analyze --full-dataset

  # Process collectors with discovered patterns
  python -m src.cli process --analysis-results analysis.json

  # Generate comprehensive reports
  python -m src.cli reports --include-analysis

  # Validate against baseline
  python -m src.cli validate --baseline-analysis analysis.json

  # Run complete pipeline
  python -m src.cli pipeline --full-process

  # Check system status
  python -m src.cli status --detailed
            ''',
            formatter_class=argparse.RawDescriptionHelpFormatter
        )

        # Global options
        parser.add_argument(
            '--verbose', '-v',
            action='store_true',
            help='Enable verbose logging'
        )

        parser.add_argument(
            '--quiet', '-q',
            action='store_true',
            help='Suppress non-error output'
        )

        parser.add_argument(
            '--config',
            type=str,
            help='Path to configuration file'
        )

        parser.add_argument(
            '--performance-monitoring',
            action='store_true',
            help='Enable performance monitoring during execution'
        )

        # Subcommands
        subparsers = parser.add_subparsers(
            dest='command',
            help='Available commands',
            metavar='COMMAND'
        )

        # Add command parsers
        for command_name, command_handler in self.commands.items():
            command_parser = subparsers.add_parser(
                command_name,
                help=command_handler.get_description(),
                formatter_class=argparse.RawDescriptionHelpFormatter
            )
            command_handler.add_arguments(command_parser)

        return parser

    def run(self, argv: Optional[List[str]] = None) -> int:
        """
        Main CLI execution entry point

        Args:
            argv: Command line arguments (defaults to sys.argv)

        Returns:
            Exit code (0 for success, non-zero for error)
        """
        parser = self.create_parser()

        if argv is None:
            argv = sys.argv[1:]

        # Show help if no command provided
        if not argv:
            parser.print_help()
            return 0

        try:
            args = parser.parse_args(argv)

            # Configure logging based on verbosity
            if args.verbose:
                logging.getLogger().setLevel(logging.DEBUG)
            elif args.quiet:
                logging.getLogger().setLevel(logging.ERROR)

            # Start performance monitoring if requested
            if args.performance_monitoring:
                self.performance_monitor.start_monitoring()
                self.performance_monitor.start_processing_timer()

            self.logger.info("=" * 80)
            self.logger.info("COLLECTOR CANONICALIZATION SYSTEM CLI")
            self.logger.info("=" * 80)
            self.logger.info(f"Command: {args.command}")
            self.logger.info(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            # Execute command
            if args.command in self.commands:
                result = self.commands[args.command].execute(args)
                exit_code = result.get('exit_code', 0)

                # Log execution summary
                if result.get('success', True):
                    self.logger.info(f"Command '{args.command}' completed successfully")
                    if 'summary' in result:
                        self._log_execution_summary(result['summary'])
                else:
                    self.logger.error(f"Command '{args.command}' failed: {result.get('error', 'Unknown error')}")

            else:
                self.logger.error(f"Unknown command: {args.command}")
                parser.print_help()
                exit_code = 1

            # Stop performance monitoring and show results
            if args.performance_monitoring:
                self.performance_monitor.end_processing_timer()
                self.performance_monitor.stop_monitoring()

                print("\n" + "=" * 60)
                print("PERFORMANCE SUMMARY")
                print("=" * 60)
                print(self.performance_monitor.generate_performance_report())

            self.logger.info("=" * 80)
            self.logger.info(f"CLI execution completed with exit code: {exit_code}")
            self.logger.info("=" * 80)

            return exit_code

        except KeyboardInterrupt:
            self.logger.warning("Execution interrupted by user")
            return 130

        except Exception as e:
            self.logger.error(f"Unexpected error: {e}", exc_info=True)
            return 1

        finally:
            # Ensure performance monitoring is stopped
            if hasattr(self, 'performance_monitor'):
                try:
                    self.performance_monitor.stop_monitoring()
                except:
                    pass

    def _log_execution_summary(self, summary: Dict[str, Any]):
        """Log execution summary in structured format"""

        self.logger.info("EXECUTION SUMMARY:")
        self.logger.info("-" * 40)

        for key, value in summary.items():
            if isinstance(value, dict):
                self.logger.info(f"{key.replace('_', ' ').title()}:")
                for subkey, subvalue in value.items():
                    self.logger.info(f"  {subkey.replace('_', ' ').title()}: {subvalue}")
            else:
                self.logger.info(f"{key.replace('_', ' ').title()}: {value}")

    def get_system_info(self) -> Dict[str, Any]:
        """Get comprehensive system information"""

        info = {
            'cli_version': '1.0.0',
            'python_version': sys.version,
            'platform': sys.platform,
            'working_directory': os.getcwd(),
            'available_commands': list(self.commands.keys())
        }

        # Add performance info if monitoring is available
        if hasattr(self, 'performance_monitor'):
            try:
                current_metrics = self.performance_monitor.get_current_metrics()
                if current_metrics:
                    info['system_metrics'] = {
                        'cpu_percent': current_metrics.cpu_percent,
                        'memory_percent': current_metrics.memory_percent,
                        'memory_used_mb': current_metrics.memory_used_mb
                    }
            except:
                pass

        return info

    def validate_dependencies(self) -> Dict[str, bool]:
        """Validate system dependencies"""

        dependencies = {
            'python_version_ok': sys.version_info >= (3, 8),
            'logs_directory': Path('logs').exists(),
            'src_directory': Path('src').exists(),
            'config_directory': Path('config').exists()
        }

        # Check for required Python packages
        try:
            import pymongo
            dependencies['pymongo_available'] = True
        except ImportError:
            dependencies['pymongo_available'] = False

        try:
            import pandas
            dependencies['pandas_available'] = True
        except ImportError:
            dependencies['pandas_available'] = False

        try:
            import tqdm
            dependencies['tqdm_available'] = True
        except ImportError:
            dependencies['tqdm_available'] = False

        return dependencies


def main():
    """Main entry point for CLI execution"""

    cli = ColetoresCLI()
    exit_code = cli.run()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()