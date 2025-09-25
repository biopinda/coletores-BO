"""
Performance Monitoring Service

This service monitors system performance, tracks processing metrics,
and provides performance analytics for the canonicalization pipeline.
"""

import logging
import time
import threading
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import deque, defaultdict


@dataclass
class PerformanceMetrics:
    """Performance metrics snapshot"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    disk_io_read_mb: float
    disk_io_write_mb: float
    network_sent_mb: float
    network_recv_mb: float
    active_threads: int
    processing_rate: float = 0.0  # items per second


@dataclass
class ProcessingStats:
    """Processing statistics"""
    total_items: int = 0
    successful_items: int = 0
    failed_items: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    avg_processing_rate: float = 0.0
    peak_memory_mb: float = 0.0
    peak_cpu_percent: float = 0.0


class PerformanceMonitor:
    """
    System and application performance monitor
    """

    def __init__(self, sampling_interval: float = 1.0, history_size: int = 1000):
        self.sampling_interval = sampling_interval
        self.history_size = history_size
        self.logger = logging.getLogger(__name__)

        # Metrics storage
        self._metrics_history = deque(maxlen=history_size)
        self._processing_stats = ProcessingStats()

        # Monitoring control
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Initialize baseline measurements
        self._baseline_io = psutil.disk_io_counters()
        self._baseline_network = psutil.net_io_counters()

    def start_monitoring(self):
        """Start performance monitoring"""
        if self._monitoring:
            return

        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        self.logger.info("Performance monitoring started")

    def stop_monitoring(self):
        """Stop performance monitoring"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)
        self.logger.info("Performance monitoring stopped")

    def _monitor_loop(self):
        """Main monitoring loop"""
        while self._monitoring:
            try:
                metrics = self._collect_metrics()
                with self._lock:
                    self._metrics_history.append(metrics)
                time.sleep(self.sampling_interval)
            except Exception as e:
                self.logger.error(f"Error collecting metrics: {e}")

    def _collect_metrics(self) -> PerformanceMetrics:
        """Collect current performance metrics"""

        # CPU and memory
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used_mb = memory.used / 1024 / 1024

        # Disk I/O
        disk_io = psutil.disk_io_counters()
        disk_read_mb = (disk_io.read_bytes - self._baseline_io.read_bytes) / 1024 / 1024 if self._baseline_io else 0
        disk_write_mb = (disk_io.write_bytes - self._baseline_io.write_bytes) / 1024 / 1024 if self._baseline_io else 0

        # Network I/O
        network = psutil.net_io_counters()
        network_sent_mb = (network.bytes_sent - self._baseline_network.bytes_sent) / 1024 / 1024 if self._baseline_network else 0
        network_recv_mb = (network.bytes_recv - self._baseline_network.bytes_recv) / 1024 / 1024 if self._baseline_network else 0

        # Thread count
        active_threads = threading.active_count()

        return PerformanceMetrics(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_used_mb=memory_used_mb,
            disk_io_read_mb=disk_read_mb,
            disk_io_write_mb=disk_write_mb,
            network_sent_mb=network_sent_mb,
            network_recv_mb=network_recv_mb,
            active_threads=active_threads
        )

    def get_current_metrics(self) -> Optional[PerformanceMetrics]:
        """Get the most recent performance metrics"""
        with self._lock:
            return self._metrics_history[-1] if self._metrics_history else None

    def get_metrics_history(self, duration_minutes: Optional[int] = None) -> List[PerformanceMetrics]:
        """Get metrics history for specified duration"""
        with self._lock:
            if duration_minutes is None:
                return list(self._metrics_history)

            cutoff_time = datetime.now() - timedelta(minutes=duration_minutes)
            return [m for m in self._metrics_history if m.timestamp >= cutoff_time]

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary statistics"""
        with self._lock:
            if not self._metrics_history:
                return {}

            metrics_list = list(self._metrics_history)

            return {
                'monitoring_duration_minutes': (
                    (metrics_list[-1].timestamp - metrics_list[0].timestamp).total_seconds() / 60
                    if len(metrics_list) > 1 else 0
                ),
                'cpu_percent': {
                    'current': metrics_list[-1].cpu_percent,
                    'average': sum(m.cpu_percent for m in metrics_list) / len(metrics_list),
                    'peak': max(m.cpu_percent for m in metrics_list)
                },
                'memory_mb': {
                    'current': metrics_list[-1].memory_used_mb,
                    'average': sum(m.memory_used_mb for m in metrics_list) / len(metrics_list),
                    'peak': max(m.memory_used_mb for m in metrics_list)
                },
                'memory_percent': {
                    'current': metrics_list[-1].memory_percent,
                    'average': sum(m.memory_percent for m in metrics_list) / len(metrics_list),
                    'peak': max(m.memory_percent for m in metrics_list)
                },
                'active_threads': {
                    'current': metrics_list[-1].active_threads,
                    'average': sum(m.active_threads for m in metrics_list) / len(metrics_list),
                    'peak': max(m.active_threads for m in metrics_list)
                }
            }

    def start_processing_timer(self):
        """Start timing a processing operation"""
        self._processing_stats.start_time = datetime.now()
        self._processing_stats.total_items = 0
        self._processing_stats.successful_items = 0
        self._processing_stats.failed_items = 0

    def update_processing_stats(self, successful: int = 0, failed: int = 0):
        """Update processing statistics"""
        self._processing_stats.successful_items += successful
        self._processing_stats.failed_items += failed
        self._processing_stats.total_items += successful + failed

    def end_processing_timer(self):
        """End processing timer and calculate final stats"""
        self._processing_stats.end_time = datetime.now()

        if self._processing_stats.start_time:
            delta = self._processing_stats.end_time - self._processing_stats.start_time
            self._processing_stats.duration_seconds = delta.total_seconds()

            if self._processing_stats.duration_seconds > 0:
                self._processing_stats.avg_processing_rate = (
                    self._processing_stats.total_items / self._processing_stats.duration_seconds
                )

        # Get peak metrics from history
        if self._metrics_history:
            recent_metrics = [m for m in self._metrics_history
                            if self._processing_stats.start_time and
                            m.timestamp >= self._processing_stats.start_time]

            if recent_metrics:
                self._processing_stats.peak_memory_mb = max(m.memory_used_mb for m in recent_metrics)
                self._processing_stats.peak_cpu_percent = max(m.cpu_percent for m in recent_metrics)

    def get_processing_stats(self) -> ProcessingStats:
        """Get current processing statistics"""
        return self._processing_stats

    def check_resource_limits(self, max_memory_percent: float = 85.0, max_cpu_percent: float = 90.0) -> Dict[str, Any]:
        """Check if system resources are approaching limits"""

        current_metrics = self.get_current_metrics()
        if not current_metrics:
            return {'status': 'unknown', 'warnings': ['No metrics available']}

        warnings = []
        status = 'ok'

        if current_metrics.memory_percent > max_memory_percent:
            warnings.append(f"Memory usage high: {current_metrics.memory_percent:.1f}%")
            status = 'warning'

        if current_metrics.cpu_percent > max_cpu_percent:
            warnings.append(f"CPU usage high: {current_metrics.cpu_percent:.1f}%")
            status = 'warning'

        return {
            'status': status,
            'warnings': warnings,
            'current_memory_percent': current_metrics.memory_percent,
            'current_cpu_percent': current_metrics.cpu_percent,
            'memory_limit': max_memory_percent,
            'cpu_limit': max_cpu_percent
        }

    def generate_performance_report(self) -> str:
        """Generate human-readable performance report"""

        summary = self.get_performance_summary()
        processing_stats = self.get_processing_stats()
        resource_check = self.check_resource_limits()

        report_lines = [
            "=" * 60,
            "PERFORMANCE REPORT",
            "=" * 60,
            f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "SYSTEM METRICS",
            "-" * 30,
        ]

        if summary:
            report_lines.extend([
                f"Monitoring duration: {summary['monitoring_duration_minutes']:.1f} minutes",
                f"CPU usage - Current: {summary['cpu_percent']['current']:.1f}%, Peak: {summary['cpu_percent']['peak']:.1f}%",
                f"Memory usage - Current: {summary['memory_percent']['current']:.1f}%, Peak: {summary['memory_percent']['peak']:.1f}%",
                f"Memory used - Current: {summary['memory_mb']['current']:.0f}MB, Peak: {summary['memory_mb']['peak']:.0f}MB",
                f"Active threads - Current: {summary['active_threads']['current']}, Peak: {summary['active_threads']['peak']}",
                ""
            ])

        report_lines.extend([
            "PROCESSING STATISTICS",
            "-" * 30,
            f"Total items processed: {processing_stats.total_items:,}",
            f"Successful: {processing_stats.successful_items:,}",
            f"Failed: {processing_stats.failed_items:,}",
            f"Success rate: {(processing_stats.successful_items / processing_stats.total_items * 100) if processing_stats.total_items > 0 else 0:.1f}%",
            f"Processing duration: {processing_stats.duration_seconds:.1f} seconds",
            f"Average rate: {processing_stats.avg_processing_rate:.1f} items/second",
            ""
        ])

        report_lines.extend([
            "RESOURCE STATUS",
            "-" * 30,
            f"Status: {resource_check['status'].upper()}",
        ])

        if resource_check['warnings']:
            report_lines.append("Warnings:")
            for warning in resource_check['warnings']:
                report_lines.append(f"  ⚠️  {warning}")

        report_lines.append("=" * 60)

        return "\n".join(report_lines)

    def export_metrics_csv(self, filepath: str, duration_hours: Optional[int] = None):
        """Export metrics to CSV file"""
        import csv

        metrics = self.get_metrics_history(duration_hours * 60 if duration_hours else None)

        if not metrics:
            self.logger.warning("No metrics to export")
            return

        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'timestamp', 'cpu_percent', 'memory_percent', 'memory_used_mb',
                'disk_io_read_mb', 'disk_io_write_mb', 'network_sent_mb',
                'network_recv_mb', 'active_threads', 'processing_rate'
            ]

            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for metric in metrics:
                writer.writerow({
                    'timestamp': metric.timestamp.isoformat(),
                    'cpu_percent': metric.cpu_percent,
                    'memory_percent': metric.memory_percent,
                    'memory_used_mb': metric.memory_used_mb,
                    'disk_io_read_mb': metric.disk_io_read_mb,
                    'disk_io_write_mb': metric.disk_io_write_mb,
                    'network_sent_mb': metric.network_sent_mb,
                    'network_recv_mb': metric.network_recv_mb,
                    'active_threads': metric.active_threads,
                    'processing_rate': metric.processing_rate
                })

        self.logger.info(f"Metrics exported to {filepath}")

    def reset_monitoring(self):
        """Reset monitoring history and statistics"""
        with self._lock:
            self._metrics_history.clear()
            self._processing_stats = ProcessingStats()

            # Reset baselines
            self._baseline_io = psutil.disk_io_counters()
            self._baseline_network = psutil.net_io_counters()

        self.logger.info("Performance monitoring reset")