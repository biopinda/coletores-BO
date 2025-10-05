"""Unit tests for DuckDB-based progress tracker"""

import pytest
from pathlib import Path
import tempfile
import os

from src.storage.progress_tracker import ProgressTracker


@pytest.fixture
def temp_db():
    """Create temporary database for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_progress.duckdb")
        yield db_path


def test_initialization(temp_db):
    """Test tracker initialization"""
    tracker = ProgressTracker(db_path=temp_db)
    assert tracker.get_total_processed() == 0
    tracker.close()


def test_mark_single_processed(temp_db):
    """Test marking a single record as processed"""
    tracker = ProgressTracker(db_path=temp_db)

    tracker.mark_processed("record_1", batch_number=1)
    assert tracker.is_processed("record_1")
    assert tracker.get_total_processed() == 1

    tracker.close()


def test_mark_batch_processed(temp_db):
    """Test batch marking of records"""
    tracker = ProgressTracker(db_path=temp_db)

    record_ids = [f"record_{i}" for i in range(1000)]
    tracker.mark_batch_processed(record_ids, batch_number=1)

    assert tracker.get_total_processed() == 1000
    assert tracker.is_processed("record_500")
    assert not tracker.is_processed("record_1001")

    tracker.close()


def test_large_batch_processing(temp_db):
    """Test processing large batches (simulating millions of records)"""
    tracker = ProgressTracker(db_path=temp_db)

    # Simulate 100k records in batches of 1000
    batch_size = 1000
    total_batches = 100

    for batch_num in range(total_batches):
        start_id = batch_num * batch_size
        record_ids = [f"record_{start_id + i}" for i in range(batch_size)]
        tracker.mark_batch_processed(record_ids, batch_number=batch_num)

    assert tracker.get_total_processed() == 100000
    assert tracker.get_latest_batch_number() == total_batches - 1

    # Verify random samples
    assert tracker.is_processed("record_0")
    assert tracker.is_processed("record_50000")
    assert tracker.is_processed("record_99999")
    assert not tracker.is_processed("record_100000")

    tracker.close()


def test_reset(temp_db):
    """Test resetting progress"""
    tracker = ProgressTracker(db_path=temp_db)

    tracker.mark_processed("record_1", batch_number=1)
    tracker.mark_processed("record_2", batch_number=1)
    assert tracker.get_total_processed() == 2

    tracker.reset()
    assert tracker.get_total_processed() == 0
    assert not tracker.is_processed("record_1")

    tracker.close()


def test_metadata(temp_db):
    """Test metadata storage and retrieval"""
    tracker = ProgressTracker(db_path=temp_db)

    tracker.set_metadata("run_id", "test_run_123")
    tracker.set_metadata("start_time", "2025-10-05T10:00:00")

    assert tracker.get_metadata("run_id") == "test_run_123"
    assert tracker.get_metadata("start_time") == "2025-10-05T10:00:00"
    assert tracker.get_metadata("nonexistent") is None

    tracker.close()


def test_persistence(temp_db):
    """Test that progress persists across sessions"""
    # First session
    tracker1 = ProgressTracker(db_path=temp_db)
    tracker1.mark_processed("record_1", batch_number=1)
    tracker1.mark_processed("record_2", batch_number=1)
    tracker1.set_metadata("test_key", "test_value")
    tracker1.close()

    # Second session - should reload data
    tracker2 = ProgressTracker(db_path=temp_db)
    assert tracker2.get_total_processed() == 2
    assert tracker2.is_processed("record_1")
    assert tracker2.is_processed("record_2")
    assert tracker2.get_metadata("test_key") == "test_value"
    tracker2.close()


def test_batch_count(temp_db):
    """Test counting processed records by batch"""
    tracker = ProgressTracker(db_path=temp_db)

    batch1_ids = [f"batch1_record_{i}" for i in range(100)]
    batch2_ids = [f"batch2_record_{i}" for i in range(200)]

    tracker.mark_batch_processed(batch1_ids, batch_number=1)
    tracker.mark_batch_processed(batch2_ids, batch_number=2)

    assert tracker.get_processed_count_by_batch(1) == 100
    assert tracker.get_processed_count_by_batch(2) == 200
    assert tracker.get_processed_count_by_batch(3) == 0

    tracker.close()


def test_context_manager(temp_db):
    """Test using tracker as context manager"""
    with ProgressTracker(db_path=temp_db) as tracker:
        tracker.mark_processed("record_1", batch_number=1)
        assert tracker.is_processed("record_1")

    # Verify connection was closed properly
    with ProgressTracker(db_path=temp_db) as tracker:
        assert tracker.get_total_processed() == 1


def test_duplicate_records(temp_db):
    """Test that duplicate record IDs are handled correctly"""
    tracker = ProgressTracker(db_path=temp_db)

    tracker.mark_processed("record_1", batch_number=1)
    tracker.mark_processed("record_1", batch_number=1)  # Duplicate

    # Should only count once
    assert tracker.get_total_processed() == 1

    tracker.close()
