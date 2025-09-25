"""
CLI Error Handling and Execution Order Validation

Provides comprehensive error handling, execution order validation,
and recovery mechanisms for the CLI system.
"""

import logging
import sys
import traceback
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from enum import Enum


class ErrorType(Enum):
    """Types of CLI errors"""
    SYSTEM_ERROR = "system_error"
    CONFIGURATION_ERROR = "configuration_error"
    DEPENDENCY_ERROR = "dependency_error"
    EXECUTION_ORDER_ERROR = "execution_order_error"
    VALIDATION_ERROR = "validation_error"
    DATABASE_ERROR = "database_error"
    FILE_ERROR = "file_error"
    PERMISSION_ERROR = "permission_error"
    RESOURCE_ERROR = "resource_error"
    USER_ERROR = "user_error"


class ExecutionStage(Enum):
    """Pipeline execution stages"""
    ANALYSIS = "analysis"
    PROCESSING = "processing"
    REPORTS = "reports"
    VALIDATION = "validation"


class CLIError(Exception):
    """Base CLI error class"""

    def __init__(self, message: str, error_type: ErrorType, stage: Optional[ExecutionStage] = None,
                 suggestions: Optional[List[str]] = None, recoverable: bool = False):
        super().__init__(message)
        self.error_type = error_type
        self.stage = stage
        self.suggestions = suggestions or []
        self.recoverable = recoverable
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary"""
        return {
            'message': str(self),
            'error_type': self.error_type.value,
            'stage': self.stage.value if self.stage else None,
            'suggestions': self.suggestions,
            'recoverable': self.recoverable,
            'timestamp': self.timestamp.isoformat()
        }


class ExecutionOrderValidator:
    """Validates and enforces correct execution order"""

    # Define mandatory execution order
    MANDATORY_ORDER = [
        ExecutionStage.ANALYSIS,
        ExecutionStage.PROCESSING,
        ExecutionStage.REPORTS,
        ExecutionStage.VALIDATION
    ]

    # Define stage dependencies
    STAGE_DEPENDENCIES = {
        ExecutionStage.PROCESSING: [ExecutionStage.ANALYSIS],
        ExecutionStage.REPORTS: [ExecutionStage.PROCESSING],
        ExecutionStage.VALIDATION: [ExecutionStage.PROCESSING]  # Can run after processing
    }

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def validate_execution_order(self, requested_stage: ExecutionStage,
                                completed_stages: List[ExecutionStage]) -> Tuple[bool, List[str]]:
        """
        Validate if a stage can be executed based on completed stages

        Args:
            requested_stage: Stage to be executed
            completed_stages: List of already completed stages

        Returns:
            Tuple of (is_valid, error_messages)
        """

        errors = []

        # Check if dependencies are met
        if requested_stage in self.STAGE_DEPENDENCIES:
            required_stages = self.STAGE_DEPENDENCIES[requested_stage]
            missing_stages = [stage for stage in required_stages if stage not in completed_stages]

            if missing_stages:
                missing_names = [stage.value for stage in missing_stages]
                errors.append(
                    f"Cannot execute {requested_stage.value} without completing: {', '.join(missing_names)}"
                )

        # Special validation for analysis results requirement
        if requested_stage == ExecutionStage.PROCESSING:
            if ExecutionStage.ANALYSIS not in completed_stages:
                errors.append(
                    "Processing requires analysis results. Run 'python -m src.cli analyze' first."
                )

        return len(errors) == 0, errors

    def get_next_recommended_stage(self, completed_stages: List[ExecutionStage]) -> Optional[ExecutionStage]:
        """Get the next recommended stage based on completed stages"""

        for stage in self.MANDATORY_ORDER:
            if stage not in completed_stages:
                return stage

        return None

    def validate_pipeline_prerequisites(self, skip_analysis: bool = False,
                                      analysis_results_path: Optional[str] = None) -> Tuple[bool, List[str]]:
        """
        Validate prerequisites for pipeline execution

        Args:
            skip_analysis: Whether analysis stage will be skipped
            analysis_results_path: Path to existing analysis results

        Returns:
            Tuple of (is_valid, error_messages)
        """

        errors = []

        if skip_analysis:
            if not analysis_results_path:
                errors.append("Analysis results path required when skipping analysis")
            elif analysis_results_path and not Path(analysis_results_path).exists():
                errors.append(f"Analysis results file not found: {analysis_results_path}")

        return len(errors) == 0, errors


class CLIErrorHandler:
    """Central error handler for CLI operations"""

    def __init__(self, log_errors: bool = True):
        self.logger = logging.getLogger(__name__)
        self.log_errors = log_errors
        self.error_history: List[CLIError] = []

    def handle_error(self, error: Exception, stage: Optional[ExecutionStage] = None,
                    context: Optional[Dict[str, Any]] = None) -> CLIError:
        """
        Handle and classify errors

        Args:
            error: The original exception
            stage: Execution stage where error occurred
            context: Additional context information

        Returns:
            CLIError: Processed CLI error
        """

        # Classify error type and create CLIError
        cli_error = self._classify_error(error, stage, context)

        # Log error if enabled
        if self.log_errors:
            self._log_error(cli_error, error)

        # Store in history
        self.error_history.append(cli_error)

        return cli_error

    def _classify_error(self, error: Exception, stage: Optional[ExecutionStage],
                       context: Optional[Dict[str, Any]]) -> CLIError:
        """Classify error and determine type and suggestions"""

        error_msg = str(error)
        suggestions = []
        recoverable = False

        # Import-related errors
        if isinstance(error, ImportError):
            missing_module = error_msg.split("'")[1] if "'" in error_msg else "unknown"
            return CLIError(
                f"Missing required dependency: {missing_module}",
                ErrorType.DEPENDENCY_ERROR,
                stage,
                [f"Install missing dependency: pip install {missing_module}",
                 "Check requirements.txt for all dependencies"],
                recoverable=True
            )

        # File-related errors
        elif isinstance(error, FileNotFoundError):
            if "analise_coletores.py" in error_msg:
                suggestions = [
                    "Ensure analise_coletores.py exists in src/ directory",
                    "Check if you're running from the correct directory",
                    "Verify project structure is complete"
                ]
            elif "config" in error_msg:
                suggestions = [
                    "Create a configuration file using: python -m src.cli config --create-example",
                    "Check configuration file path and permissions"
                ]

            return CLIError(
                f"File not found: {error_msg}",
                ErrorType.FILE_ERROR,
                stage,
                suggestions,
                recoverable=True
            )

        # Permission errors
        elif isinstance(error, PermissionError):
            return CLIError(
                f"Permission denied: {error_msg}",
                ErrorType.PERMISSION_ERROR,
                stage,
                ["Check file/directory permissions",
                 "Run with appropriate privileges",
                 "Verify write access to output directories"],
                recoverable=True
            )

        # Database-related errors
        elif "pymongo" in error_msg or "mongo" in error_msg.lower():
            suggestions = [
                "Check MongoDB connection settings",
                "Verify MongoDB server is running",
                "Check database credentials and permissions",
                "Test connection with: python -m src.cli status --check-database"
            ]

            return CLIError(
                f"Database error: {error_msg}",
                ErrorType.DATABASE_ERROR,
                stage,
                suggestions,
                recoverable=True
            )

        # Configuration errors
        elif "config" in error_msg.lower() or isinstance(error, ValueError):
            suggestions = [
                "Check configuration file syntax",
                "Validate configuration values",
                "Create fresh config: python -m src.cli config --create-example"
            ]

            return CLIError(
                f"Configuration error: {error_msg}",
                ErrorType.CONFIGURATION_ERROR,
                stage,
                suggestions,
                recoverable=True
            )

        # Memory/Resource errors
        elif isinstance(error, MemoryError) or "memory" in error_msg.lower():
            suggestions = [
                "Reduce batch size in configuration",
                "Enable checkpoints to reduce memory usage",
                "Close other applications to free memory",
                "Consider processing in smaller chunks"
            ]

            return CLIError(
                f"Resource error: {error_msg}",
                ErrorType.RESOURCE_ERROR,
                stage,
                suggestions,
                recoverable=True
            )

        # Subprocess/System errors
        elif "subprocess" in error_msg or "exit code" in error_msg:
            return CLIError(
                f"System execution error: {error_msg}",
                ErrorType.SYSTEM_ERROR,
                stage,
                ["Check system dependencies",
                 "Verify script permissions",
                 "Check available disk space"],
                recoverable=True
            )

        # Generic error
        else:
            return CLIError(
                f"Unexpected error: {error_msg}",
                ErrorType.SYSTEM_ERROR,
                stage,
                ["Check logs for more details",
                 "Verify system requirements",
                 "Report issue if problem persists"],
                recoverable=False
            )

    def _log_error(self, cli_error: CLIError, original_error: Exception):
        """Log error with appropriate level"""

        log_level = logging.ERROR
        if cli_error.error_type in [ErrorType.USER_ERROR, ErrorType.VALIDATION_ERROR]:
            log_level = logging.WARNING

        self.logger.log(
            log_level,
            f"[{cli_error.error_type.value.upper()}] {cli_error}",
            exc_info=original_error if log_level == logging.ERROR else None
        )

        if cli_error.suggestions:
            self.logger.info(f"Suggestions: {'; '.join(cli_error.suggestions)}")

    def format_error_for_user(self, cli_error: CLIError, include_technical_details: bool = False) -> str:
        """Format error message for user display"""

        lines = []

        # Error header
        stage_info = f" ({cli_error.stage.value})" if cli_error.stage else ""
        lines.append(f"❌ {cli_error.error_type.value.replace('_', ' ').title()}{stage_info}")
        lines.append("")

        # Error message
        lines.append(f"Error: {cli_error}")
        lines.append("")

        # Suggestions
        if cli_error.suggestions:
            lines.append("Suggestions:")
            for suggestion in cli_error.suggestions:
                lines.append(f"  • {suggestion}")
            lines.append("")

        # Recovery information
        if cli_error.recoverable:
            lines.append("💡 This error can typically be resolved by following the suggestions above.")
        else:
            lines.append("⚠️  This appears to be a system error. Please check logs and report if needed.")

        # Technical details (if requested)
        if include_technical_details:
            lines.append("")
            lines.append("Technical Details:")
            lines.append(f"  Timestamp: {cli_error.timestamp}")
            lines.append(f"  Error Type: {cli_error.error_type.value}")
            if cli_error.stage:
                lines.append(f"  Stage: {cli_error.stage.value}")

        return "\n".join(lines)

    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of all errors encountered"""

        if not self.error_history:
            return {'total_errors': 0}

        error_counts = {}
        for error in self.error_history:
            error_type = error.error_type.value
            error_counts[error_type] = error_counts.get(error_type, 0) + 1

        return {
            'total_errors': len(self.error_history),
            'error_counts': error_counts,
            'latest_error': self.error_history[-1].to_dict(),
            'recoverable_errors': sum(1 for e in self.error_history if e.recoverable)
        }

    def clear_error_history(self):
        """Clear error history"""
        self.error_history.clear()

    def export_error_log(self, output_path: str):
        """Export error history to file"""

        error_data = {
            'export_timestamp': datetime.now().isoformat(),
            'total_errors': len(self.error_history),
            'errors': [error.to_dict() for error in self.error_history]
        }

        import json
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(error_data, f, indent=2)

        self.logger.info(f"Error log exported to: {output_path}")


# Global instances
execution_validator = ExecutionOrderValidator()
error_handler = CLIErrorHandler()