"""
Batch Processing Service

This service handles batch processing of collector records with progress tracking,
checkpoint management, and error handling. It provides configurable batch sizes
and parallel processing capabilities.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
import json
import threading
from queue import Queue
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed


@dataclass
class BatchConfig:
    """Configuration for batch processing"""
    batch_size: int = 1000
    checkpoint_interval: int = 10  # Save checkpoint every N batches
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    enable_parallel_processing: bool = True
    max_workers: int = 4
    process_timeout_seconds: int = 300


@dataclass
class BatchProgress:
    """Progress tracking for batch processing"""
    total_items: int = 0
    processed_items: int = 0
    successful_items: int = 0
    failed_items: int = 0
    current_batch: int = 0
    start_time: Optional[datetime] = None
    last_checkpoint_time: Optional[datetime] = None
    estimated_completion_time: Optional[datetime] = None


@dataclass
class CheckpointData:
    """Checkpoint data for resuming processing"""
    batch_number: int
    processed_count: int
    timestamp: datetime
    processor_state: Dict[str, Any] = field(default_factory=dict)


class BatchProcessor:
    """
    Generic batch processor with checkpoint management and progress tracking
    """

    def __init__(self, config: BatchConfig, checkpoint_dir: Optional[Path] = None):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.checkpoint_dir = checkpoint_dir or Path("./checkpoints")
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        self.progress = BatchProgress()
        self._stop_requested = False
        self._lock = threading.Lock()

    def process_batches(
        self,
        data_source: Iterator[Any],
        processor_func: Callable[[List[Any]], Dict[str, Any]],
        total_count: Optional[int] = None,
        resume_from_checkpoint: bool = True,
        checkpoint_name: str = "default"
    ) -> Dict[str, Any]:
        """
        Process data in batches with checkpointing

        Args:
            data_source: Iterator providing data items
            processor_func: Function to process each batch
            total_count: Optional total count for progress tracking
            resume_from_checkpoint: Whether to resume from last checkpoint
            checkpoint_name: Name for checkpoint file

        Returns:
            Processing results summary
        """
        self.logger.info(f"Starting batch processing: {checkpoint_name}")

        # Initialize progress
        self.progress = BatchProgress(
            total_items=total_count or 0,
            start_time=datetime.now()
        )

        # Try to resume from checkpoint
        start_batch = 0
        if resume_from_checkpoint:
            checkpoint = self._load_checkpoint(checkpoint_name)
            if checkpoint:
                start_batch = checkpoint.batch_number
                self.progress.processed_items = checkpoint.processed_count
                self.logger.info(f"Resuming from batch {start_batch}")

        try:
            # Process batches
            batch_count = start_batch
            current_batch = []

            for item in data_source:
                if self._stop_requested:
                    self.logger.info("Stop requested, breaking processing loop")
                    break

                current_batch.append(item)

                if len(current_batch) >= self.config.batch_size:
                    # Process batch
                    batch_result = self._process_single_batch(
                        current_batch, processor_func, batch_count
                    )

                    # Update progress
                    with self._lock:
                        self.progress.current_batch = batch_count
                        self.progress.processed_items += len(current_batch)
                        self.progress.successful_items += batch_result.get('successful', 0)
                        self.progress.failed_items += batch_result.get('failed', 0)

                    # Save checkpoint if needed
                    if batch_count % self.config.checkpoint_interval == 0:
                        self._save_checkpoint(checkpoint_name, batch_count)

                    # Update time estimates
                    self._update_time_estimates()

                    batch_count += 1
                    current_batch = []

            # Process remaining items
            if current_batch and not self._stop_requested:
                batch_result = self._process_single_batch(
                    current_batch, processor_func, batch_count
                )

                with self._lock:
                    self.progress.processed_items += len(current_batch)
                    self.progress.successful_items += batch_result.get('successful', 0)
                    self.progress.failed_items += batch_result.get('failed', 0)

            # Final checkpoint
            if not self._stop_requested:
                self._save_checkpoint(checkpoint_name, batch_count)

            # Generate summary
            summary = self._generate_summary()
            self.logger.info(f"Batch processing completed: {summary}")

            return summary

        except Exception as e:
            self.logger.error(f"Error in batch processing: {e}")
            raise

    def _process_single_batch(
        self,
        batch: List[Any],
        processor_func: Callable[[List[Any]], Dict[str, Any]],
        batch_number: int
    ) -> Dict[str, Any]:
        """Process a single batch with retry logic"""

        for attempt in range(self.config.max_retries + 1):
            try:
                start_time = time.time()

                if self.config.enable_parallel_processing and len(batch) > 10:
                    result = self._process_batch_parallel(batch, processor_func)
                else:
                    result = processor_func(batch)

                duration = time.time() - start_time
                self.logger.debug(f"Batch {batch_number} processed in {duration:.2f}s")

                return result

            except Exception as e:
                if attempt < self.config.max_retries:
                    delay = self.config.retry_delay_seconds * (2 ** attempt)
                    self.logger.warning(f"Batch {batch_number} failed (attempt {attempt + 1}), retrying in {delay}s: {e}")
                    time.sleep(delay)
                else:
                    self.logger.error(f"Batch {batch_number} failed after {self.config.max_retries} retries: {e}")
                    return {'successful': 0, 'failed': len(batch), 'error': str(e)}

    def _process_batch_parallel(
        self,
        batch: List[Any],
        processor_func: Callable[[List[Any]], Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Process batch items in parallel"""

        # Split batch into chunks for parallel processing
        chunk_size = max(1, len(batch) // self.config.max_workers)
        chunks = [batch[i:i + chunk_size] for i in range(0, len(batch), chunk_size)]

        results = {'successful': 0, 'failed': 0}

        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            future_to_chunk = {
                executor.submit(processor_func, chunk): chunk
                for chunk in chunks
            }

            for future in as_completed(future_to_chunk, timeout=self.config.process_timeout_seconds):
                try:
                    result = future.result()
                    results['successful'] += result.get('successful', 0)
                    results['failed'] += result.get('failed', 0)
                except Exception as e:
                    chunk = future_to_chunk[future]
                    self.logger.error(f"Parallel processing failed for chunk of {len(chunk)} items: {e}")
                    results['failed'] += len(chunk)

        return results

    def _save_checkpoint(self, checkpoint_name: str, batch_number: int):
        """Save processing checkpoint"""

        checkpoint = CheckpointData(
            batch_number=batch_number,
            processed_count=self.progress.processed_items,
            timestamp=datetime.now()
        )

        checkpoint_file = self.checkpoint_dir / f"{checkpoint_name}.json"

        try:
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'batch_number': checkpoint.batch_number,
                    'processed_count': checkpoint.processed_count,
                    'timestamp': checkpoint.timestamp.isoformat(),
                    'processor_state': checkpoint.processor_state
                }, f, indent=2)

            self.progress.last_checkpoint_time = datetime.now()
            self.logger.debug(f"Checkpoint saved: batch {batch_number}")

        except Exception as e:
            self.logger.error(f"Failed to save checkpoint: {e}")

    def _load_checkpoint(self, checkpoint_name: str) -> Optional[CheckpointData]:
        """Load processing checkpoint"""

        checkpoint_file = self.checkpoint_dir / f"{checkpoint_name}.json"

        if not checkpoint_file.exists():
            return None

        try:
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            return CheckpointData(
                batch_number=data['batch_number'],
                processed_count=data['processed_count'],
                timestamp=datetime.fromisoformat(data['timestamp']),
                processor_state=data.get('processor_state', {})
            )

        except Exception as e:
            self.logger.error(f"Failed to load checkpoint: {e}")
            return None

    def _update_time_estimates(self):
        """Update processing time estimates"""

        if not self.progress.start_time or self.progress.processed_items == 0:
            return

        elapsed = datetime.now() - self.progress.start_time
        items_per_second = self.progress.processed_items / elapsed.total_seconds()

        if self.progress.total_items > 0 and items_per_second > 0:
            remaining_items = self.progress.total_items - self.progress.processed_items
            remaining_seconds = remaining_items / items_per_second
            self.progress.estimated_completion_time = datetime.now() + timedelta(seconds=remaining_seconds)

    def _generate_summary(self) -> Dict[str, Any]:
        """Generate processing summary"""

        duration = timedelta(seconds=0)
        if self.progress.start_time:
            duration = datetime.now() - self.progress.start_time

        return {
            'total_processed': self.progress.processed_items,
            'successful': self.progress.successful_items,
            'failed': self.progress.failed_items,
            'success_rate': (self.progress.successful_items / self.progress.processed_items * 100
                           if self.progress.processed_items > 0 else 0),
            'duration_seconds': duration.total_seconds(),
            'items_per_second': (self.progress.processed_items / duration.total_seconds()
                               if duration.total_seconds() > 0 else 0),
            'batches_processed': self.progress.current_batch,
            'stopped_early': self._stop_requested
        }

    def get_progress(self) -> BatchProgress:
        """Get current processing progress"""
        return self.progress

    def stop_processing(self):
        """Request processing to stop"""
        self._stop_requested = True
        self.logger.info("Stop requested")

    def cleanup_checkpoints(self, older_than_days: int = 7):
        """Clean up old checkpoint files"""

        cutoff_date = datetime.now() - timedelta(days=older_than_days)

        for checkpoint_file in self.checkpoint_dir.glob("*.json"):
            try:
                if checkpoint_file.stat().st_mtime < cutoff_date.timestamp():
                    checkpoint_file.unlink()
                    self.logger.debug(f"Removed old checkpoint: {checkpoint_file}")
            except Exception as e:
                self.logger.error(f"Error cleaning up checkpoint {checkpoint_file}: {e}")