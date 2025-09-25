"""
CLI Configuration Management

Handles configuration loading, validation, and default settings
for the collector canonicalization CLI.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
import configparser


@dataclass
class DatabaseConfig:
    """Database connection configuration"""
    connection_string: str = "mongodb://localhost:27017/"
    database_name: str = "coletores"
    collection_name: str = "ocorrencias"
    connection_timeout_ms: int = 30000
    max_pool_size: int = 10
    retry_writes: bool = True


@dataclass
class ProcessingConfig:
    """Processing configuration"""
    batch_size: int = 1000
    max_workers: int = 4
    checkpoint_interval: int = 10
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    enable_checkpoints: bool = True


@dataclass
class AnalysisConfig:
    """Analysis configuration"""
    sample_size: Optional[int] = None  # None = process all records
    enable_pattern_discovery: bool = True
    similarity_threshold: float = 0.8
    phonetic_threshold: float = 0.9
    save_intermediate_results: bool = True


@dataclass
class ReportsConfig:
    """Reports configuration"""
    output_format: str = "html"
    include_charts: bool = True
    detailed_statistics: bool = True
    export_csv: bool = False


@dataclass
class ValidationConfig:
    """Validation configuration"""
    quality_threshold: float = 0.85
    validation_level: str = "comprehensive"  # basic, comprehensive, full
    sample_percentage: float = 10.0
    strict_validation: bool = False


@dataclass
class CLIConfig:
    """Complete CLI configuration"""
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)
    reports: ReportsConfig = field(default_factory=ReportsConfig)
    validation: ValidationConfig = field(default_factory=ValidationConfig)

    # Global settings
    log_level: str = "INFO"
    log_file: str = "logs/cli.log"
    performance_monitoring: bool = False
    output_directory: str = "results"


class ConfigManager:
    """Configuration manager for CLI"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._config: Optional[CLIConfig] = None
        self._config_file: Optional[Path] = None

    def load_config(self, config_file: Optional[str] = None) -> CLIConfig:
        """
        Load configuration from file or create default configuration

        Args:
            config_file: Optional path to configuration file

        Returns:
            CLIConfig: Loaded or default configuration
        """

        if config_file:
            config_path = Path(config_file)
        else:
            # Look for config files in common locations
            config_path = self._find_config_file()

        if config_path and config_path.exists():
            self.logger.info(f"Loading configuration from: {config_path}")
            self._config = self._load_from_file(config_path)
            self._config_file = config_path
        else:
            self.logger.info("Using default configuration")
            self._config = CLIConfig()

        # Validate configuration
        self._validate_config()

        return self._config

    def _find_config_file(self) -> Optional[Path]:
        """Find configuration file in common locations"""

        search_paths = [
            Path("config.json"),
            Path("config/config.json"),
            Path("config/cli.json"),
            Path("cli-config.json"),
            Path.home() / ".coletores" / "config.json"
        ]

        for path in search_paths:
            if path.exists():
                return path

        return None

    def _load_from_file(self, config_path: Path) -> CLIConfig:
        """Load configuration from JSON or INI file"""

        try:
            if config_path.suffix.lower() == '.json':
                return self._load_json_config(config_path)
            elif config_path.suffix.lower() in ['.ini', '.cfg']:
                return self._load_ini_config(config_path)
            else:
                self.logger.warning(f"Unsupported config file format: {config_path.suffix}")
                return CLIConfig()

        except Exception as e:
            self.logger.error(f"Failed to load config from {config_path}: {e}")
            return CLIConfig()

    def _load_json_config(self, config_path: Path) -> CLIConfig:
        """Load configuration from JSON file"""

        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)

        # Create config objects from nested dictionaries
        config = CLIConfig()

        if 'database' in config_data:
            config.database = DatabaseConfig(**config_data['database'])

        if 'processing' in config_data:
            config.processing = ProcessingConfig(**config_data['processing'])

        if 'analysis' in config_data:
            config.analysis = AnalysisConfig(**config_data['analysis'])

        if 'reports' in config_data:
            config.reports = ReportsConfig(**config_data['reports'])

        if 'validation' in config_data:
            config.validation = ValidationConfig(**config_data['validation'])

        # Update global settings
        for key, value in config_data.items():
            if key not in ['database', 'processing', 'analysis', 'reports', 'validation']:
                if hasattr(config, key):
                    setattr(config, key, value)

        return config

    def _load_ini_config(self, config_path: Path) -> CLIConfig:
        """Load configuration from INI file"""

        parser = configparser.ConfigParser()
        parser.read(config_path, encoding='utf-8')

        config = CLIConfig()

        # Database section
        if 'database' in parser:
            db_section = parser['database']
            config.database = DatabaseConfig(
                connection_string=db_section.get('connection_string', config.database.connection_string),
                database_name=db_section.get('database_name', config.database.database_name),
                collection_name=db_section.get('collection_name', config.database.collection_name),
                connection_timeout_ms=db_section.getint('connection_timeout_ms', config.database.connection_timeout_ms),
                max_pool_size=db_section.getint('max_pool_size', config.database.max_pool_size),
                retry_writes=db_section.getboolean('retry_writes', config.database.retry_writes)
            )

        # Processing section
        if 'processing' in parser:
            proc_section = parser['processing']
            config.processing = ProcessingConfig(
                batch_size=proc_section.getint('batch_size', config.processing.batch_size),
                max_workers=proc_section.getint('max_workers', config.processing.max_workers),
                checkpoint_interval=proc_section.getint('checkpoint_interval', config.processing.checkpoint_interval),
                max_retries=proc_section.getint('max_retries', config.processing.max_retries),
                retry_delay_seconds=proc_section.getfloat('retry_delay_seconds', config.processing.retry_delay_seconds),
                enable_checkpoints=proc_section.getboolean('enable_checkpoints', config.processing.enable_checkpoints)
            )

        # Analysis section
        if 'analysis' in parser:
            analysis_section = parser['analysis']
            sample_size = analysis_section.get('sample_size')
            config.analysis = AnalysisConfig(
                sample_size=int(sample_size) if sample_size and sample_size.lower() != 'none' else None,
                enable_pattern_discovery=analysis_section.getboolean('enable_pattern_discovery', config.analysis.enable_pattern_discovery),
                similarity_threshold=analysis_section.getfloat('similarity_threshold', config.analysis.similarity_threshold),
                phonetic_threshold=analysis_section.getfloat('phonetic_threshold', config.analysis.phonetic_threshold),
                save_intermediate_results=analysis_section.getboolean('save_intermediate_results', config.analysis.save_intermediate_results)
            )

        # Global settings
        if 'global' in parser:
            global_section = parser['global']
            config.log_level = global_section.get('log_level', config.log_level)
            config.log_file = global_section.get('log_file', config.log_file)
            config.performance_monitoring = global_section.getboolean('performance_monitoring', config.performance_monitoring)
            config.output_directory = global_section.get('output_directory', config.output_directory)

        return config

    def _validate_config(self):
        """Validate configuration values"""

        if not self._config:
            return

        errors = []

        # Validate database config
        db = self._config.database
        if not db.connection_string:
            errors.append("Database connection string is required")
        if not db.database_name:
            errors.append("Database name is required")
        if not db.collection_name:
            errors.append("Collection name is required")
        if db.connection_timeout_ms <= 0:
            errors.append("Connection timeout must be positive")

        # Validate processing config
        proc = self._config.processing
        if proc.batch_size <= 0:
            errors.append("Batch size must be positive")
        if proc.max_workers <= 0:
            errors.append("Max workers must be positive")
        if proc.checkpoint_interval <= 0:
            errors.append("Checkpoint interval must be positive")

        # Validate analysis config
        analysis = self._config.analysis
        if analysis.similarity_threshold < 0 or analysis.similarity_threshold > 1:
            errors.append("Similarity threshold must be between 0 and 1")
        if analysis.phonetic_threshold < 0 or analysis.phonetic_threshold > 1:
            errors.append("Phonetic threshold must be between 0 and 1")

        # Validate validation config
        validation = self._config.validation
        if validation.quality_threshold < 0 or validation.quality_threshold > 1:
            errors.append("Quality threshold must be between 0 and 1")
        if validation.sample_percentage <= 0 or validation.sample_percentage > 100:
            errors.append("Sample percentage must be between 0 and 100")

        if errors:
            error_msg = "Configuration validation errors:\n" + "\n".join(f"  - {error}" for error in errors)
            raise ValueError(error_msg)

    def save_config(self, output_path: Optional[str] = None) -> Path:
        """
        Save current configuration to file

        Args:
            output_path: Optional path to save config file

        Returns:
            Path: Path where configuration was saved
        """

        if not self._config:
            raise ValueError("No configuration loaded")

        if output_path:
            config_path = Path(output_path)
        else:
            config_path = Path("config.json")

        # Create directory if needed
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dictionary and save as JSON
        config_dict = asdict(self._config)

        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, indent=2, default=str)

        self.logger.info(f"Configuration saved to: {config_path}")
        return config_path

    def get_config(self) -> CLIConfig:
        """Get current configuration"""

        if not self._config:
            return self.load_config()
        return self._config

    def update_from_args(self, args) -> CLIConfig:
        """
        Update configuration with command line arguments

        Args:
            args: Parsed command line arguments

        Returns:
            CLIConfig: Updated configuration
        """

        if not self._config:
            self.load_config()

        # Update global settings from args
        if hasattr(args, 'config') and args.config:
            # Reload with specific config file
            return self.load_config(args.config)

        if hasattr(args, 'verbose') and args.verbose:
            self._config.log_level = "DEBUG"

        if hasattr(args, 'quiet') and args.quiet:
            self._config.log_level = "ERROR"

        if hasattr(args, 'performance_monitoring') and args.performance_monitoring:
            self._config.performance_monitoring = True

        return self._config

    def create_example_config(self, output_path: str = "config-example.json"):
        """Create an example configuration file"""

        example_config = CLIConfig()
        config_path = Path(output_path)

        # Create directory if needed
        config_path.parent.mkdir(parents=True, exist_ok=True)

        config_dict = asdict(example_config)

        # Add comments as a separate dictionary
        comments = {
            "_comments": {
                "database": "MongoDB connection settings",
                "processing": "Batch processing configuration",
                "analysis": "Complete dataset analysis settings",
                "reports": "Report generation options",
                "validation": "Quality validation parameters",
                "log_level": "DEBUG, INFO, WARNING, ERROR",
                "performance_monitoring": "Enable system resource monitoring"
            }
        }

        config_dict.update(comments)

        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, indent=2, default=str)

        self.logger.info(f"Example configuration saved to: {config_path}")
        return config_path

    def get_environment_overrides(self) -> Dict[str, Any]:
        """Get configuration overrides from environment variables"""

        overrides = {}

        # Database overrides
        if 'COLETORES_DB_CONNECTION' in os.environ:
            overrides.setdefault('database', {})['connection_string'] = os.environ['COLETORES_DB_CONNECTION']

        if 'COLETORES_DB_NAME' in os.environ:
            overrides.setdefault('database', {})['database_name'] = os.environ['COLETORES_DB_NAME']

        if 'COLETORES_COLLECTION_NAME' in os.environ:
            overrides.setdefault('database', {})['collection_name'] = os.environ['COLETORES_COLLECTION_NAME']

        # Processing overrides
        if 'COLETORES_BATCH_SIZE' in os.environ:
            try:
                overrides.setdefault('processing', {})['batch_size'] = int(os.environ['COLETORES_BATCH_SIZE'])
            except ValueError:
                self.logger.warning(f"Invalid COLETORES_BATCH_SIZE: {os.environ['COLETORES_BATCH_SIZE']}")

        if 'COLETORES_MAX_WORKERS' in os.environ:
            try:
                overrides.setdefault('processing', {})['max_workers'] = int(os.environ['COLETORES_MAX_WORKERS'])
            except ValueError:
                self.logger.warning(f"Invalid COLETORES_MAX_WORKERS: {os.environ['COLETORES_MAX_WORKERS']}")

        # Global overrides
        if 'COLETORES_LOG_LEVEL' in os.environ:
            overrides['log_level'] = os.environ['COLETORES_LOG_LEVEL']

        return overrides


# Global config manager instance
config_manager = ConfigManager()