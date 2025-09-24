"""
CheckpointData model - Recovery state information for large-scale processing

This model supports hierarchical checkpoint recovery for processing
11M+ MongoDB records with interruption tolerance.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import json
import hashlib


@dataclass
class CheckpointData:
    """Recovery checkpoint for large-scale processing operations"""

    # Checkpoint identification
    checkpoint_id: str                       # Unique identifier for this checkpoint
    checkpoint_type: str                     # macro, micro, batch
    process_name: str                        # Name of process being checkpointed

    # Progress tracking
    records_processed: int = 0               # Total records processed so far
    current_batch_number: int = 0            # Current batch being processed
    last_processed_id: Optional[str] = None  # Last MongoDB document ID processed

    # State preservation
    processing_state: Dict[str, Any] = field(default_factory=dict)  # Algorithm state
    configuration: Dict[str, Any] = field(default_factory=dict)     # Processing configuration
    intermediate_results: Dict[str, Any] = field(default_factory=dict)  # Partial results

    # Progress metadata
    total_records: Optional[int] = None      # Total records to process (if known)
    estimated_completion: Optional[datetime] = None  # Estimated completion time
    processing_rate: Optional[float] = None  # Records per second

    # Recovery information
    resume_cursor: Optional[str] = None      # MongoDB cursor state for resumption
    resume_parameters: Dict[str, Any] = field(default_factory=dict)  # Parameters for resume

    # Validation
    state_hash: Optional[str] = None         # Hash for state integrity verification
    validation_errors: List[str] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None    # When checkpoint expires
    process_version: str = "1.0.0"           # Version of processing algorithm

    def __post_init__(self):
        """Validate checkpoint data and calculate state hash"""
        if self.checkpoint_type not in ["macro", "micro", "batch"]:
            raise ValueError(f"Invalid checkpoint_type: {self.checkpoint_type}")

        if not self.checkpoint_id:
            # Generate ID based on process and timestamp
            timestamp = self.created_at.strftime("%Y%m%d_%H%M%S")
            self.checkpoint_id = f"{self.process_name}_{self.checkpoint_type}_{timestamp}"

        # Calculate state hash for integrity verification
        if not self.state_hash:
            self.state_hash = self.calculate_state_hash()

    def calculate_state_hash(self) -> str:
        """Calculate SHA-256 hash of checkpoint state for integrity verification"""
        state_data = {
            "records_processed": self.records_processed,
            "current_batch_number": self.current_batch_number,
            "last_processed_id": self.last_processed_id,
            "processing_state": self.processing_state,
            "configuration": self.configuration
        }
        state_json = json.dumps(state_data, sort_keys=True, default=str)
        return hashlib.sha256(state_json.encode()).hexdigest()

    def validate_integrity(self) -> bool:
        """Validate checkpoint integrity using state hash"""
        current_hash = self.calculate_state_hash()
        if current_hash != self.state_hash:
            self.validation_errors.append(f"State hash mismatch: expected {self.state_hash}, got {current_hash}")
            return False
        return True

    def update_progress(self, records_processed: int, last_id: Optional[str] = None,
                       processing_rate: Optional[float] = None):
        """Update checkpoint progress information"""
        self.records_processed = records_processed
        if last_id:
            self.last_processed_id = last_id
        if processing_rate:
            self.processing_rate = processing_rate

        # Update estimated completion
        if self.total_records and self.processing_rate and self.processing_rate > 0:
            remaining_records = self.total_records - self.records_processed
            remaining_seconds = remaining_records / self.processing_rate
            self.estimated_completion = datetime.now() + timedelta(seconds=remaining_seconds)

        # Recalculate state hash
        self.state_hash = self.calculate_state_hash()

    def get_completion_percentage(self) -> Optional[float]:
        """Get completion percentage if total records is known"""
        if not self.total_records or self.total_records == 0:
            return None
        return min(100.0, (self.records_processed / self.total_records) * 100.0)

    def is_expired(self) -> bool:
        """Check if checkpoint has expired"""
        if not self.expires_at:
            return False
        return datetime.now() > self.expires_at

    def set_expiration(self, hours: int = 24):
        """Set checkpoint expiration time"""
        from datetime import timedelta
        self.expires_at = datetime.now() + timedelta(hours=hours)

    def add_intermediate_result(self, key: str, value: Any):
        """Add intermediate processing result"""
        self.intermediate_results[key] = value
        self.state_hash = self.calculate_state_hash()

    def get_resume_info(self) -> Dict[str, Any]:
        """Get information needed to resume processing"""
        return {
            "last_processed_id": self.last_processed_id,
            "records_processed": self.records_processed,
            "current_batch_number": self.current_batch_number,
            "resume_cursor": self.resume_cursor,
            "resume_parameters": self.resume_parameters,
            "processing_state": self.processing_state,
            "configuration": self.configuration
        }

    def create_recovery_checkpoint(self, interval_records: int = 25000) -> bool:
        """Check if it's time to create a recovery checkpoint"""
        return self.records_processed > 0 and self.records_processed % interval_records == 0

    def get_processing_summary(self) -> Dict[str, Any]:
        """Get summary of processing progress"""
        completion_pct = self.get_completion_percentage()
        return {
            "checkpoint_id": self.checkpoint_id,
            "process_name": self.process_name,
            "records_processed": self.records_processed,
            "total_records": self.total_records,
            "completion_percentage": completion_pct,
            "processing_rate": self.processing_rate,
            "estimated_completion": self.estimated_completion,
            "is_expired": self.is_expired(),
            "validation_status": "valid" if self.validate_integrity() else "invalid"
        }

    def to_dict(self) -> dict:
        """Convert to dictionary for storage"""
        return {
            "checkpoint_id": self.checkpoint_id,
            "checkpoint_type": self.checkpoint_type,
            "process_name": self.process_name,
            "records_processed": self.records_processed,
            "current_batch_number": self.current_batch_number,
            "last_processed_id": self.last_processed_id,
            "processing_state": self.processing_state,
            "configuration": self.configuration,
            "intermediate_results": self.intermediate_results,
            "total_records": self.total_records,
            "estimated_completion": self.estimated_completion,
            "processing_rate": self.processing_rate,
            "resume_cursor": self.resume_cursor,
            "resume_parameters": self.resume_parameters,
            "state_hash": self.state_hash,
            "validation_errors": self.validation_errors,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "process_version": self.process_version,
            "completion_percentage": self.get_completion_percentage(),
            "processing_summary": self.get_processing_summary()
        }

    def __str__(self) -> str:
        """String representation for logging"""
        completion = self.get_completion_percentage()
        completion_str = f"{completion:.1f}%" if completion else "unknown"
        return f"CheckpointData(id={self.checkpoint_id}, process={self.process_name}, progress={self.records_processed}, completion={completion_str})"