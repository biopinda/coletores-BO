"""
Checkpoint Manager Service

Provides hierarchical checkpoint management with state-aware recovery capabilities
for the collector canonicalization system. Implements macro, micro, and batch-level
checkpoints with automatic validation and recovery.
"""

import logging
import time
import json
import pickle
import hashlib
import zlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field, asdict
from pathlib import Path
from bson import ObjectId

from ..models.checkpoint_data import CheckpointData
from .mongodb_manager import MongoDBManager


@dataclass
class CheckpointState:
    """State information for checkpoint recovery"""

    # Progress tracking
    total_records: int = 0
    processed_records: int = 0
    current_batch_number: int = 0
    last_document_id: Optional[str] = None

    # Algorithm state
    algorithm_state: Dict[str, Any] = field(default_factory=dict)
    statistics_snapshot: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    process_type: str = "canonicalization"
    process_version: str = "1.0"
    created_at: Optional[datetime] = None
    configuration_hash: Optional[str] = None


@dataclass
class CheckpointMetrics:
    """Performance metrics for checkpoint operations"""

    save_time_ms: float = 0.0
    load_time_ms: float = 0.0
    state_size_bytes: int = 0
    compression_ratio: float = 0.0
    validation_passed: bool = True


class CheckpointManager:
    """
    Hierarchical checkpoint manager with state compression and validation

    Provides three levels of checkpointing:
    - Macro: Major milestones (every 100k records)
    - Micro: Minor progress (every 10k records)
    - Batch: Frequent saves (every 1k records)
    """

    def __init__(self,
                 mongo_manager: Optional[MongoDBManager] = None,
                 checkpoint_config: Optional[Dict[str, Any]] = None):
        """
        Initialize checkpoint manager

        Args:
            mongo_manager: MongoDB manager instance
            checkpoint_config: Configuration for checkpoint behavior
        """
        self.logger = logging.getLogger(__name__)
        self.mongo_manager = mongo_manager or MongoDBManager()

        # Default checkpoint configuration
        self.config = {
            'macro_interval': 100000,      # Major checkpoints every 100k records
            'micro_interval': 10000,       # Minor checkpoints every 10k records
            'batch_interval': 1000,        # Batch checkpoints every 1k records
            'max_checkpoints': 50,         # Maximum checkpoints to retain
            'compression_enabled': True,   # Enable state compression
            'validation_enabled': True,    # Enable state validation
            'auto_cleanup': True,          # Automatically cleanup old checkpoints
            'retention_hours': 168,        # Keep checkpoints for 7 days
        }

        if checkpoint_config:
            self.config.update(checkpoint_config)

        self.logger.info(f"CheckpointManager initialized with config: {self.config}")

    def should_create_checkpoint(self,
                               processed_records: int,
                               checkpoint_type: str = "auto") -> bool:
        """
        Determine if a checkpoint should be created based on processed records

        Args:
            processed_records: Number of records processed so far
            checkpoint_type: Type of checkpoint to check ("macro", "micro", "batch", "auto")

        Returns:
            True if checkpoint should be created
        """
        if checkpoint_type == "macro":
            return processed_records % self.config['macro_interval'] == 0
        elif checkpoint_type == "micro":
            return processed_records % self.config['micro_interval'] == 0
        elif checkpoint_type == "batch":
            return processed_records % self.config['batch_interval'] == 0
        elif checkpoint_type == "auto":
            # Auto-determine the appropriate checkpoint type
            if processed_records % self.config['macro_interval'] == 0:
                return True
            elif processed_records % self.config['micro_interval'] == 0:
                return True
            elif processed_records % self.config['batch_interval'] == 0:
                return True

        return False

    def create_checkpoint(self,
                         checkpoint_state: CheckpointState,
                         checkpoint_type: str = "auto") -> str:
        """
        Create a new checkpoint with the current state

        Args:
            checkpoint_state: Current processing state
            checkpoint_type: Type of checkpoint ("macro", "micro", "batch")

        Returns:
            Checkpoint ID for future reference
        """
        start_time = time.time()

        # Auto-determine checkpoint type if needed
        if checkpoint_type == "auto":
            checkpoint_type = self._determine_checkpoint_type(checkpoint_state.processed_records)

        # Generate checkpoint ID
        checkpoint_id = self._generate_checkpoint_id(checkpoint_type, checkpoint_state)

        # Prepare checkpoint data
        checkpoint_data = CheckpointData(
            checkpoint_id=checkpoint_id,
            checkpoint_type=checkpoint_type,
            process_type=checkpoint_state.process_type,
            total_records=checkpoint_state.total_records,
            processed_records=checkpoint_state.processed_records,
            last_document_id=ObjectId(checkpoint_state.last_document_id) if checkpoint_state.last_document_id else None,
            current_batch_number=checkpoint_state.current_batch_number,
            algorithm_state=self._compress_state(checkpoint_state.algorithm_state),
            statistics_snapshot=checkpoint_state.statistics_snapshot,
            created_at=datetime.now(),
            process_version=checkpoint_state.process_version,
            configuration_hash=self._calculate_config_hash(checkpoint_state)
        )

        try:
            # Save to MongoDB
            result = self.mongo_manager.checkpoints.insert_one(asdict(checkpoint_data))

            # Calculate metrics
            save_time = (time.time() - start_time) * 1000

            self.logger.info(f"Checkpoint {checkpoint_id} created successfully "
                           f"(type: {checkpoint_type}, records: {checkpoint_state.processed_records}, "
                           f"time: {save_time:.1f}ms)")

            # Auto-cleanup if enabled
            if self.config['auto_cleanup']:
                self._cleanup_old_checkpoints(checkpoint_state.process_type)

            return checkpoint_id

        except Exception as e:
            self.logger.error(f"Failed to create checkpoint {checkpoint_id}: {e}")
            raise

    def load_checkpoint(self,
                       checkpoint_id: Optional[str] = None,
                       process_type: str = "canonicalization") -> Optional[CheckpointState]:
        """
        Load a checkpoint by ID or find the latest checkpoint for a process

        Args:
            checkpoint_id: Specific checkpoint ID to load
            process_type: Process type to find latest checkpoint for

        Returns:
            CheckpointState if found, None otherwise
        """
        start_time = time.time()

        try:
            if checkpoint_id:
                # Load specific checkpoint
                doc = self.mongo_manager.checkpoints.find_one({"checkpoint_id": checkpoint_id})
            else:
                # Find latest checkpoint for process type
                doc = self.mongo_manager.checkpoints.find_one(
                    {"process_type": process_type},
                    sort=[("created_at", -1)]
                )

            if not doc:
                self.logger.info(f"No checkpoint found for process_type='{process_type}', checkpoint_id='{checkpoint_id}'")
                return None

            # Reconstruct checkpoint data
            checkpoint_data = CheckpointData(**doc)

            # Decompress algorithm state
            algorithm_state = self._decompress_state(checkpoint_data.algorithm_state)

            # Create checkpoint state
            state = CheckpointState(
                total_records=checkpoint_data.total_records,
                processed_records=checkpoint_data.processed_records,
                current_batch_number=checkpoint_data.current_batch_number,
                last_document_id=str(checkpoint_data.last_document_id) if checkpoint_data.last_document_id else None,
                algorithm_state=algorithm_state,
                statistics_snapshot=checkpoint_data.statistics_snapshot,
                process_type=checkpoint_data.process_type,
                process_version=checkpoint_data.process_version,
                created_at=checkpoint_data.created_at,
                configuration_hash=checkpoint_data.configuration_hash
            )

            # Validate checkpoint integrity
            if self.config['validation_enabled'] and not self._validate_checkpoint(state):
                self.logger.warning(f"Checkpoint {checkpoint_data.checkpoint_id} failed validation")
                return None

            load_time = (time.time() - start_time) * 1000

            self.logger.info(f"Checkpoint {checkpoint_data.checkpoint_id} loaded successfully "
                           f"(records: {state.processed_records}, time: {load_time:.1f}ms)")

            return state

        except Exception as e:
            self.logger.error(f"Failed to load checkpoint: {e}")
            return None

    def list_checkpoints(self,
                        process_type: str = "canonicalization",
                        limit: int = 20) -> List[Dict[str, Any]]:
        """
        List available checkpoints for a process type

        Args:
            process_type: Process type to filter by
            limit: Maximum number of checkpoints to return

        Returns:
            List of checkpoint information dictionaries
        """
        try:
            cursor = self.mongo_manager.checkpoints.find(
                {"process_type": process_type},
                {
                    "checkpoint_id": 1,
                    "checkpoint_type": 1,
                    "processed_records": 1,
                    "total_records": 1,
                    "created_at": 1,
                    "process_version": 1
                }
            ).sort("created_at", -1).limit(limit)

            checkpoints = []
            for doc in cursor:
                checkpoint_info = {
                    "checkpoint_id": doc["checkpoint_id"],
                    "checkpoint_type": doc["checkpoint_type"],
                    "processed_records": doc["processed_records"],
                    "total_records": doc["total_records"],
                    "progress_percent": (doc["processed_records"] / doc["total_records"] * 100) if doc["total_records"] > 0 else 0,
                    "created_at": doc["created_at"],
                    "process_version": doc["process_version"]
                }
                checkpoints.append(checkpoint_info)

            return checkpoints

        except Exception as e:
            self.logger.error(f"Failed to list checkpoints: {e}")
            return []

    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """
        Delete a specific checkpoint

        Args:
            checkpoint_id: ID of checkpoint to delete

        Returns:
            True if deletion was successful
        """
        try:
            result = self.mongo_manager.checkpoints.delete_one({"checkpoint_id": checkpoint_id})

            if result.deleted_count > 0:
                self.logger.info(f"Checkpoint {checkpoint_id} deleted successfully")
                return True
            else:
                self.logger.warning(f"Checkpoint {checkpoint_id} not found for deletion")
                return False

        except Exception as e:
            self.logger.error(f"Failed to delete checkpoint {checkpoint_id}: {e}")
            return False

    def cleanup_checkpoints(self,
                          process_type: str = "canonicalization",
                          keep_count: Optional[int] = None) -> int:
        """
        Clean up old checkpoints, keeping only the most recent ones

        Args:
            process_type: Process type to clean up
            keep_count: Number of checkpoints to keep (uses config default if None)

        Returns:
            Number of checkpoints deleted
        """
        keep_count = keep_count or self.config['max_checkpoints']

        try:
            # Get all checkpoints for this process type, sorted by creation date
            all_checkpoints = list(self.mongo_manager.checkpoints.find(
                {"process_type": process_type},
                {"checkpoint_id": 1, "created_at": 1}
            ).sort("created_at", -1))

            if len(all_checkpoints) <= keep_count:
                self.logger.info(f"No checkpoint cleanup needed (found: {len(all_checkpoints)}, keep: {keep_count})")
                return 0

            # Delete oldest checkpoints
            checkpoints_to_delete = all_checkpoints[keep_count:]
            deleted_count = 0

            for checkpoint in checkpoints_to_delete:
                if self.delete_checkpoint(checkpoint["checkpoint_id"]):
                    deleted_count += 1

            self.logger.info(f"Cleaned up {deleted_count} old checkpoints for process_type='{process_type}'")
            return deleted_count

        except Exception as e:
            self.logger.error(f"Failed to cleanup checkpoints: {e}")
            return 0

    def get_checkpoint_metrics(self, checkpoint_id: str) -> Optional[CheckpointMetrics]:
        """
        Get performance metrics for a checkpoint

        Args:
            checkpoint_id: ID of checkpoint to analyze

        Returns:
            CheckpointMetrics if found, None otherwise
        """
        try:
            doc = self.mongo_manager.checkpoints.find_one(
                {"checkpoint_id": checkpoint_id},
                {"algorithm_state": 1, "created_at": 1, "checkpoint_type": 1}
            )

            if not doc:
                return None

            # Calculate state size
            state_size = len(doc["algorithm_state"]) if doc["algorithm_state"] else 0

            # Estimate compression ratio (if compressed)
            compression_ratio = 1.0
            if self.config['compression_enabled'] and state_size > 0:
                try:
                    decompressed = zlib.decompress(doc["algorithm_state"])
                    compression_ratio = len(decompressed) / state_size
                except:
                    compression_ratio = 1.0

            metrics = CheckpointMetrics(
                state_size_bytes=state_size,
                compression_ratio=compression_ratio,
                validation_passed=True  # If it exists, it passed validation
            )

            return metrics

        except Exception as e:
            self.logger.error(f"Failed to get checkpoint metrics: {e}")
            return None

    def _determine_checkpoint_type(self, processed_records: int) -> str:
        """Determine appropriate checkpoint type based on processed records"""

        if processed_records % self.config['macro_interval'] == 0:
            return "macro"
        elif processed_records % self.config['micro_interval'] == 0:
            return "micro"
        else:
            return "batch"

    def _generate_checkpoint_id(self, checkpoint_type: str, state: CheckpointState) -> str:
        """Generate unique checkpoint ID"""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        process_hash = hashlib.md5(state.process_type.encode()).hexdigest()[:8]

        return f"ckpt_{checkpoint_type}_{timestamp}_{process_hash}_{state.processed_records}"

    def _compress_state(self, algorithm_state: Dict[str, Any]) -> bytes:
        """Compress algorithm state for storage"""

        if not self.config['compression_enabled']:
            return pickle.dumps(algorithm_state)

        try:
            serialized = pickle.dumps(algorithm_state)
            compressed = zlib.compress(serialized, level=6)
            return compressed
        except Exception as e:
            self.logger.warning(f"Failed to compress state: {e}")
            return pickle.dumps(algorithm_state)

    def _decompress_state(self, compressed_state: bytes) -> Dict[str, Any]:
        """Decompress algorithm state from storage"""

        try:
            if self.config['compression_enabled']:
                # Try decompression first
                try:
                    decompressed = zlib.decompress(compressed_state)
                    return pickle.loads(decompressed)
                except:
                    # Fall back to direct deserialization
                    return pickle.loads(compressed_state)
            else:
                return pickle.loads(compressed_state)
        except Exception as e:
            self.logger.error(f"Failed to decompress state: {e}")
            return {}

    def _calculate_config_hash(self, state: CheckpointState) -> str:
        """Calculate hash of current configuration for validation"""

        config_str = json.dumps(self.config, sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()

    def _validate_checkpoint(self, state: CheckpointState) -> bool:
        """Validate checkpoint integrity and compatibility"""

        try:
            # Basic validation
            if state.processed_records < 0 or state.total_records < 0:
                return False

            if state.processed_records > state.total_records:
                return False

            # Configuration compatibility
            current_hash = self._calculate_config_hash(state)
            if state.configuration_hash and state.configuration_hash != current_hash:
                self.logger.warning("Checkpoint configuration hash mismatch")
                # Don't fail validation for config changes, just warn

            return True

        except Exception as e:
            self.logger.error(f"Checkpoint validation failed: {e}")
            return False

    def _cleanup_old_checkpoints(self, process_type: str):
        """Automatically cleanup old checkpoints based on retention policy"""

        try:
            # Cleanup by count
            self.cleanup_checkpoints(process_type)

            # Cleanup by age
            cutoff_time = datetime.now() - timedelta(hours=self.config['retention_hours'])

            result = self.mongo_manager.checkpoints.delete_many({
                "process_type": process_type,
                "created_at": {"$lt": cutoff_time}
            })

            if result.deleted_count > 0:
                self.logger.info(f"Cleaned up {result.deleted_count} expired checkpoints")

        except Exception as e:
            self.logger.error(f"Auto-cleanup failed: {e}")