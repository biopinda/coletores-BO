"""
Checkpoint Manager (disabled)

This module provides a minimal, no-op compatibility layer for existing imports.
The project has checkpointing disabled globally per user request; therefore the
real checkpointing behavior was intentionally removed. The classes and methods
below are lightweight stubs that keep the public API but perform no file or DB
operations. This preserves compatibility with code that imports these symbols
without performing any checkpointing side-effects.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime


@dataclass
class CheckpointState:
    """Lightweight state container (no persistence)."""
    total_records: int = 0
    processed_records: int = 0
    current_batch_number: int = 0
    last_document_id: Optional[str] = None
    algorithm_state: Dict[str, Any] = field(default_factory=dict)
    statistics_snapshot: Dict[str, Any] = field(default_factory=dict)
    process_type: str = "canonicalization"
    process_version: str = "1.0"
    created_at: Optional[datetime] = None
    configuration_hash: Optional[str] = None


@dataclass
class CheckpointMetrics:
    """No-op metrics placeholder."""
    save_time_ms: float = 0.0
    load_time_ms: float = 0.0
    state_size_bytes: int = 0
    compression_ratio: float = 1.0
    validation_passed: bool = True


class CheckpointManager:
    """Compatibility stub: checkpointing disabled intentionally."""

    def __init__(self, *args, **kwargs):
        self.logger = logging.getLogger(__name__)
        self.logger.info("CheckpointManager loaded in disabled mode. No checkpoints will be created.")
        # Keep a minimal config for compatibility
        self.config = {
            'macro_interval': 100000,
            'micro_interval': 10000,
            'batch_interval': 1000,
            'max_checkpoints': 0,
            'auto_cleanup': False
        }

    def should_create_checkpoint(self, *args, **kwargs) -> bool:
        return False

    def create_checkpoint(self, *args, **kwargs) -> Optional[str]:
        self.logger.debug("create_checkpoint called but checkpointing is disabled.")
        return None

    def load_checkpoint(self, *args, **kwargs) -> Optional[CheckpointState]:
        self.logger.debug("load_checkpoint called but checkpointing is disabled.")
        return None

    def list_checkpoints(self, *args, **kwargs) -> List[Dict[str, Any]]:
        return []

    def delete_checkpoint(self, *args, **kwargs) -> bool:
        return False

    def cleanup_checkpoints(self, *args, **kwargs) -> int:
        return 0

    def get_checkpoint_metrics(self, *args, **kwargs) -> Optional[CheckpointMetrics]:
        return None
    # All advanced checkpoint operations removed in disabled mode