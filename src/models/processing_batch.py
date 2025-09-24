"""
ProcessingBatch model - Batch processing unit for memory-efficient large-scale operations

This model represents a batch of records for processing with
memory management and progress tracking for 11M+ record handling.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from enum import Enum


class BatchStatus(Enum):
    """Possible states for a processing batch"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class ProcessingBatch:
    """Batch processing unit for memory-efficient operations"""

    # Batch identification
    batch_id: str                            # Unique identifier for this batch
    batch_number: int                        # Sequential batch number
    process_name: str                        # Name of the processing operation

    # Batch content
    record_ids: List[str] = field(default_factory=list)    # MongoDB document IDs in this batch
    batch_size: int = 5000                   # Target batch size (research recommendation)
    actual_size: int = 0                     # Actual number of records in batch

    # Processing status
    status: BatchStatus = BatchStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    processing_duration: Optional[timedelta] = None

    # Progress tracking
    records_processed: int = 0               # Records successfully processed
    records_failed: int = 0                  # Records that failed processing
    records_skipped: int = 0                 # Records skipped (e.g., already processed)

    # Results and metadata
    processing_results: Dict[str, Any] = field(default_factory=dict)  # Batch processing results
    error_messages: List[str] = field(default_factory=list)           # Error messages
    performance_metrics: Dict[str, float] = field(default_factory=dict)  # Performance data

    # Memory management
    peak_memory_mb: Optional[float] = None   # Peak memory usage during processing
    memory_efficient: bool = True            # Whether batch stayed within memory limits

    # Retry logic
    retry_count: int = 0                     # Number of retry attempts
    max_retries: int = 3                     # Maximum retry attempts
    last_error: Optional[str] = None         # Last error encountered

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Initialize batch and validate parameters"""
        if self.batch_size <= 0:
            raise ValueError("batch_size must be positive")

        if not self.batch_id:
            # Generate batch ID based on process and batch number
            timestamp = self.created_at.strftime("%Y%m%d_%H%M%S")
            self.batch_id = f"{self.process_name}_batch_{self.batch_number:06d}_{timestamp}"

        self.actual_size = len(self.record_ids)

    def start_processing(self):
        """Mark batch as started and record start time"""
        self.status = BatchStatus.PROCESSING
        self.start_time = datetime.now()
        self.last_updated = datetime.now()

    def complete_processing(self):
        """Mark batch as completed and calculate duration"""
        if self.start_time is None:
            raise ValueError("Cannot complete batch that was never started")

        self.status = BatchStatus.COMPLETED
        self.end_time = datetime.now()
        self.processing_duration = self.end_time - self.start_time
        self.last_updated = datetime.now()

    def fail_processing(self, error_message: str):
        """Mark batch as failed with error message"""
        self.status = BatchStatus.FAILED
        self.last_error = error_message
        self.error_messages.append(error_message)
        if self.start_time and not self.end_time:
            self.end_time = datetime.now()
            self.processing_duration = self.end_time - self.start_time
        self.last_updated = datetime.now()

    def retry_processing(self):
        """Attempt to retry failed batch processing"""
        if self.retry_count >= self.max_retries:
            raise ValueError(f"Maximum retries ({self.max_retries}) exceeded for batch {self.batch_id}")

        self.retry_count += 1
        self.status = BatchStatus.RETRYING
        self.start_time = datetime.now()
        self.end_time = None
        self.processing_duration = None
        self.last_updated = datetime.now()

    def update_progress(self, processed: int, failed: int = 0, skipped: int = 0):
        """Update batch processing progress"""
        self.records_processed = processed
        self.records_failed = failed
        self.records_skipped = skipped
        self.last_updated = datetime.now()

    def add_record_id(self, record_id: str):
        """Add a record ID to this batch"""
        if len(self.record_ids) >= self.batch_size:
            raise ValueError(f"Batch is full (max size: {self.batch_size})")

        self.record_ids.append(record_id)
        self.actual_size = len(self.record_ids)
        self.last_updated = datetime.now()

    def is_full(self) -> bool:
        """Check if batch has reached target size"""
        return len(self.record_ids) >= self.batch_size

    def is_empty(self) -> bool:
        """Check if batch has no records"""
        return len(self.record_ids) == 0

    def get_completion_percentage(self) -> float:
        """Get percentage of records processed in this batch"""
        if self.actual_size == 0:
            return 0.0
        total_handled = self.records_processed + self.records_failed + self.records_skipped
        return min(100.0, (total_handled / self.actual_size) * 100.0)

    def get_processing_rate(self) -> Optional[float]:
        """Get processing rate in records per second"""
        if not self.processing_duration or self.processing_duration.total_seconds() == 0:
            return None
        return self.records_processed / self.processing_duration.total_seconds()

    def get_success_rate(self) -> float:
        """Get success rate percentage"""
        total_attempted = self.records_processed + self.records_failed
        if total_attempted == 0:
            return 0.0
        return (self.records_processed / total_attempted) * 100.0

    def can_retry(self) -> bool:
        """Check if batch can be retried"""
        return (self.status == BatchStatus.FAILED and
                self.retry_count < self.max_retries)

    def add_performance_metric(self, metric_name: str, value: float):
        """Add performance metric for this batch"""
        self.performance_metrics[metric_name] = value
        self.last_updated = datetime.now()

    def set_memory_usage(self, peak_memory_mb: float, limit_mb: float = 200):
        """Set peak memory usage and check efficiency"""
        self.peak_memory_mb = peak_memory_mb
        self.memory_efficient = peak_memory_mb <= limit_mb
        self.last_updated = datetime.now()

    def get_batch_summary(self) -> Dict[str, Any]:
        """Get summary of batch processing"""
        return {
            "batch_id": self.batch_id,
            "batch_number": self.batch_number,
            "status": self.status.value,
            "actual_size": self.actual_size,
            "records_processed": self.records_processed,
            "records_failed": self.records_failed,
            "completion_percentage": self.get_completion_percentage(),
            "processing_rate": self.get_processing_rate(),
            "success_rate": self.get_success_rate(),
            "processing_duration": str(self.processing_duration) if self.processing_duration else None,
            "memory_efficient": self.memory_efficient,
            "peak_memory_mb": self.peak_memory_mb,
            "retry_count": self.retry_count,
            "can_retry": self.can_retry()
        }

    def to_dict(self) -> dict:
        """Convert to dictionary for storage"""
        return {
            "batch_id": self.batch_id,
            "batch_number": self.batch_number,
            "process_name": self.process_name,
            "record_ids": self.record_ids,
            "batch_size": self.batch_size,
            "actual_size": self.actual_size,
            "status": self.status.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "processing_duration": str(self.processing_duration) if self.processing_duration else None,
            "records_processed": self.records_processed,
            "records_failed": self.records_failed,
            "records_skipped": self.records_skipped,
            "processing_results": self.processing_results,
            "error_messages": self.error_messages,
            "performance_metrics": self.performance_metrics,
            "peak_memory_mb": self.peak_memory_mb,
            "memory_efficient": self.memory_efficient,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "last_error": self.last_error,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "batch_summary": self.get_batch_summary()
        }

    def __str__(self) -> str:
        """String representation for logging"""
        return f"ProcessingBatch(id={self.batch_id}, status={self.status.value}, size={self.actual_size}, processed={self.records_processed})"