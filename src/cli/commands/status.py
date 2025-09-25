"""
Status Command for CLI

Provides system status, health checks, and dependency validation
for the collector canonicalization system.
"""

import logging
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import json


class StatusCommand:
    """Command handler for system status and health checks"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def get_description(self) -> str:
        return "Show system status and health"

    def add_arguments(self, parser):
        """Add command-specific arguments"""

        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed system information'
        )

        parser.add_argument(
            '--check-dependencies',
            action='store_true',
            help='Check all system dependencies'
        )

        parser.add_argument(
            '--check-database',
            action='store_true',
            help='Test database connectivity'
        )

        parser.add_argument(
            '--check-disk-space',
            action='store_true',
            help='Check available disk space'
        )

        parser.add_argument(
            '--output-format',
            choices=['text', 'json'],
            default='text',
            help='Output format (default: text)'
        )

        parser.description = '''
Display system status, health checks, and dependency validation.

This command provides comprehensive information about the system state,
including Python environment, dependencies, database connectivity,
and resource availability.

Examples:
  python -m src.cli status
  python -m src.cli status --detailed
  python -m src.cli status --check-dependencies --check-database
  python -m src.cli status --output-format json
        '''

    def execute(self, args) -> Dict[str, Any]:
        """Execute the status command"""

        self.logger.info("Checking system status...")

        try:
            # Collect status information
            status_info = {
                'timestamp': datetime.now().isoformat(),
                'system_info': self._get_system_info(),
                'python_info': self._get_python_info(),
                'project_info': self._get_project_info()
            }

            # Add optional checks
            if args.check_dependencies:
                status_info['dependencies'] = self._check_dependencies()

            if args.check_database:
                status_info['database'] = self._check_database_connectivity()

            if args.check_disk_space:
                status_info['disk_space'] = self._check_disk_space()

            if args.detailed:
                status_info['detailed_info'] = self._get_detailed_info()

            # Determine overall health
            overall_health = self._determine_overall_health(status_info)
            status_info['overall_health'] = overall_health

            # Output results
            if args.output_format == 'json':
                print(json.dumps(status_info, indent=2, default=str))
            else:
                self._print_text_status(status_info, args.detailed)

            return {
                'success': True,
                'exit_code': 0,
                'status_info': status_info
            }

        except Exception as e:
            error_msg = f"Error checking system status: {e}"
            self.logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'exit_code': 1,
                'error': error_msg
            }

    def _get_system_info(self) -> Dict[str, Any]:
        """Get basic system information"""

        import platform

        return {
            'platform': platform.system(),
            'platform_version': platform.version(),
            'architecture': platform.architecture()[0],
            'processor': platform.processor(),
            'hostname': platform.node(),
            'current_directory': os.getcwd()
        }

    def _get_python_info(self) -> Dict[str, Any]:
        """Get Python environment information"""

        return {
            'version': sys.version,
            'version_info': {
                'major': sys.version_info.major,
                'minor': sys.version_info.minor,
                'micro': sys.version_info.micro
            },
            'executable': sys.executable,
            'path_entries': len(sys.path),
            'modules_loaded': len(sys.modules)
        }

    def _get_project_info(self) -> Dict[str, Any]:
        """Get project-specific information"""

        project_root = Path.cwd()

        info = {
            'project_root': str(project_root),
            'structure': {
                'src_exists': (project_root / 'src').exists(),
                'tests_exists': (project_root / 'tests').exists(),
                'config_exists': (project_root / 'config').exists(),
                'logs_exists': (project_root / 'logs').exists()
            },
            'key_files': {
                'analise_coletores': (project_root / 'src' / 'analise_coletores.py').exists(),
                'processar_coletores': (project_root / 'src' / 'processar_coletores.py').exists(),
                'gerar_relatorios': (project_root / 'src' / 'gerar_relatorios.py').exists(),
                'validar_canonicalizacao': (project_root / 'src' / 'validar_canonicalizacao.py').exists(),
                'cli_main': (project_root / 'src' / 'cli' / '__main__.py').exists()
            }
        }

        # Check for recent results
        results_info = {}
        for result_type in ['analysis', 'processing', 'reports', 'validation']:
            result_files = list(project_root.glob(f"**/{result_type}*results*.json"))
            if result_files:
                most_recent = max(result_files, key=lambda p: p.stat().st_mtime)
                results_info[result_type] = {
                    'file': str(most_recent),
                    'modified': datetime.fromtimestamp(most_recent.stat().st_mtime).isoformat()
                }

        info['recent_results'] = results_info

        return info

    def _check_dependencies(self) -> Dict[str, Any]:
        """Check Python package dependencies"""

        dependencies = {}

        required_packages = [
            'pymongo',
            'pandas',
            'tqdm',
            'jellyfish',
            'rapidfuzz',
            'psutil'
        ]

        for package in required_packages:
            try:
                __import__(package)
                dependencies[package] = {'status': 'installed'}

                # Try to get version if available
                try:
                    module = __import__(package)
                    if hasattr(module, '__version__'):
                        dependencies[package]['version'] = module.__version__
                except:
                    pass

            except ImportError:
                dependencies[package] = {'status': 'missing'}

        return dependencies

    def _check_database_connectivity(self) -> Dict[str, Any]:
        """Check database connectivity"""

        try:
            # Try to import and test MongoDB connection
            import pymongo
            from pymongo import MongoClient

            # Use default connection (will be overridden by actual config)
            client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=5000)

            # Test connection
            client.admin.command('ping')

            return {
                'status': 'connected',
                'driver_version': pymongo.version
            }

        except ImportError:
            return {
                'status': 'error',
                'error': 'pymongo not installed'
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }

    def _check_disk_space(self) -> Dict[str, Any]:
        """Check available disk space"""

        import shutil

        try:
            total, used, free = shutil.disk_usage('.')

            return {
                'total_gb': round(total / (1024**3), 2),
                'used_gb': round(used / (1024**3), 2),
                'free_gb': round(free / (1024**3), 2),
                'usage_percent': round((used / total) * 100, 1)
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }

    def _get_detailed_info(self) -> Dict[str, Any]:
        """Get detailed system information"""

        detailed = {}

        # Environment variables (selected ones)
        env_vars = {}
        for key in ['PATH', 'PYTHONPATH', 'PYTHON_VERSION', 'HOME', 'USER']:
            if key in os.environ:
                env_vars[key] = os.environ[key]
        detailed['environment'] = env_vars

        # Process information
        try:
            import psutil
            process = psutil.Process()
            detailed['process'] = {
                'pid': process.pid,
                'memory_mb': round(process.memory_info().rss / 1024 / 1024, 2),
                'cpu_percent': process.cpu_percent(),
                'create_time': datetime.fromtimestamp(process.create_time()).isoformat()
            }
        except ImportError:
            detailed['process'] = {'status': 'psutil not available'}
        except Exception as e:
            detailed['process'] = {'error': str(e)}

        return detailed

    def _determine_overall_health(self, status_info: Dict[str, Any]) -> Dict[str, Any]:
        """Determine overall system health"""

        health = {
            'status': 'healthy',
            'issues': [],
            'warnings': []
        }

        # Check Python version
        if sys.version_info < (3, 8):
            health['issues'].append('Python version too old (3.8+ required)')
            health['status'] = 'unhealthy'

        # Check project structure
        project_info = status_info['project_info']
        if not project_info['structure']['src_exists']:
            health['issues'].append('src/ directory missing')
            health['status'] = 'unhealthy'

        # Check key files
        key_files = project_info['key_files']
        missing_files = [name for name, exists in key_files.items() if not exists]
        if missing_files:
            health['warnings'].extend([f'Missing file: {name}' for name in missing_files])
            if len(missing_files) > 2:
                health['status'] = 'unhealthy'

        # Check dependencies
        if 'dependencies' in status_info:
            missing_deps = [
                name for name, info in status_info['dependencies'].items()
                if info['status'] == 'missing'
            ]
            if missing_deps:
                health['issues'].extend([f'Missing dependency: {dep}' for dep in missing_deps])
                health['status'] = 'unhealthy'

        # Check database
        if 'database' in status_info:
            if status_info['database']['status'] != 'connected':
                health['warnings'].append('Database not connected')

        # Check disk space
        if 'disk_space' in status_info:
            disk_info = status_info['disk_space']
            if isinstance(disk_info, dict) and 'usage_percent' in disk_info:
                if disk_info['usage_percent'] > 90:
                    health['warnings'].append('Low disk space')

        return health

    def _print_text_status(self, status_info: Dict[str, Any], detailed: bool = False):
        """Print status information in text format"""

        print("=" * 60)
        print("COLLECTOR CANONICALIZATION SYSTEM STATUS")
        print("=" * 60)
        print(f"Timestamp: {status_info['timestamp']}")
        print()

        # Overall health
        health = status_info['overall_health']
        status_icon = "✅" if health['status'] == 'healthy' else "❌"
        print(f"Overall Health: {health['status'].upper()} {status_icon}")

        if health['issues']:
            print("Issues:")
            for issue in health['issues']:
                print(f"  ❌ {issue}")

        if health['warnings']:
            print("Warnings:")
            for warning in health['warnings']:
                print(f"  ⚠️  {warning}")
        print()

        # System info
        sys_info = status_info['system_info']
        print("SYSTEM INFORMATION")
        print("-" * 30)
        print(f"Platform: {sys_info['platform']} ({sys_info['architecture']})")
        print(f"Directory: {sys_info['current_directory']}")
        print()

        # Python info
        py_info = status_info['python_info']
        print("PYTHON ENVIRONMENT")
        print("-" * 30)
        version_info = py_info['version_info']
        print(f"Version: {version_info['major']}.{version_info['minor']}.{version_info['micro']}")
        print(f"Executable: {py_info['executable']}")
        print()

        # Project info
        proj_info = status_info['project_info']
        print("PROJECT STATUS")
        print("-" * 30)

        structure = proj_info['structure']
        for name, exists in structure.items():
            icon = "✅" if exists else "❌"
            print(f"{name}: {icon}")

        print("\nKey Files:")
        key_files = proj_info['key_files']
        for name, exists in key_files.items():
            icon = "✅" if exists else "❌"
            print(f"  {name}: {icon}")

        if proj_info['recent_results']:
            print("\nRecent Results:")
            for result_type, info in proj_info['recent_results'].items():
                print(f"  {result_type}: {info['modified']}")
        print()

        # Dependencies
        if 'dependencies' in status_info:
            print("DEPENDENCIES")
            print("-" * 30)
            deps = status_info['dependencies']
            for name, info in deps.items():
                icon = "✅" if info['status'] == 'installed' else "❌"
                version = f" ({info['version']})" if 'version' in info else ""
                print(f"{name}: {info['status'].upper()}{version} {icon}")
            print()

        # Database
        if 'database' in status_info:
            print("DATABASE")
            print("-" * 30)
            db_info = status_info['database']
            icon = "✅" if db_info['status'] == 'connected' else "❌"
            print(f"Status: {db_info['status'].upper()} {icon}")
            if 'error' in db_info:
                print(f"Error: {db_info['error']}")
            print()

        # Disk space
        if 'disk_space' in status_info:
            print("DISK SPACE")
            print("-" * 30)
            disk = status_info['disk_space']
            if 'error' not in disk:
                print(f"Total: {disk['total_gb']} GB")
                print(f"Used: {disk['used_gb']} GB ({disk['usage_percent']}%)")
                print(f"Free: {disk['free_gb']} GB")
            else:
                print(f"Error: {disk['error']}")
            print()

        print("=" * 60)