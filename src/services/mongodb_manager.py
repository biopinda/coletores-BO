"""
MongoDB Connection Manager Service

This service provides centralized MongoDB connection management with connection pooling,
error handling, retry logic, and performance monitoring for the collector canonicalization
system. It replaces direct MongoDB usage throughout the system with a managed service
approach.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from contextlib import contextmanager
import threading
from collections import defaultdict

from pymongo import MongoClient, errors
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.results import InsertOneResult, InsertManyResult, UpdateResult, DeleteResult


@dataclass
class ConnectionConfig:
    """Configuration for MongoDB connections"""

    connection_string: str
    database_name: str

    # Connection pool settings
    max_pool_size: int = 50
    min_pool_size: int = 5
    max_idle_time_ms: int = 30000

    # Timeout settings
    connect_timeout_ms: int = 5000
    server_selection_timeout_ms: int = 5000
    socket_timeout_ms: int = 30000

    # Retry settings
    retry_writes: bool = True
    retry_reads: bool = True
    max_retries: int = 3
    retry_delay_seconds: float = 1.0

    # Performance settings
    read_concern_level: str = "majority"
    write_concern_w: Union[int, str] = "majority"
    write_concern_j: bool = True

    # Monitoring
    enable_monitoring: bool = True
    slow_operation_threshold_ms: int = 1000


@dataclass
class OperationStats:
    """Statistics for database operations"""

    operation_count: int = 0
    total_duration_ms: float = 0.0
    average_duration_ms: float = 0.0
    max_duration_ms: float = 0.0
    error_count: int = 0
    last_operation_time: Optional[datetime] = None


@dataclass
class ConnectionStats:
    """Connection pool and performance statistics"""

    active_connections: int = 0
    total_connections_created: int = 0
    connection_errors: int = 0

    # Operation statistics by type
    operation_stats: Dict[str, OperationStats] = field(default_factory=dict)

    # Collection-level statistics
    collection_stats: Dict[str, Dict[str, OperationStats]] = field(default_factory=lambda: defaultdict(dict))


class MongoDBManager:
    """
    Centralized MongoDB connection manager with pooling, monitoring, and error handling
    """

    def __init__(self, config: ConnectionConfig):
        """
        Initialize MongoDB manager with configuration

        Args:
            config: MongoDB connection configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Connection management
        self._client: Optional[MongoClient] = None
        self._database: Optional[Database] = None
        self._lock = threading.RLock()

        # Statistics and monitoring
        self.stats = ConnectionStats()
        self._operation_history: List[Dict[str, Any]] = []
        self._last_health_check: Optional[datetime] = None

        # Initialize connection
        self._initialize_connection()

    def _initialize_connection(self):
        """Initialize MongoDB connection with configured settings"""

        try:
            self.logger.info("Initializing MongoDB connection...")

            # Create client with configuration
            client_options = {
                'maxPoolSize': self.config.max_pool_size,
                'minPoolSize': self.config.min_pool_size,
                'maxIdleTimeMS': self.config.max_idle_time_ms,
                'connectTimeoutMS': self.config.connect_timeout_ms,
                'serverSelectionTimeoutMS': self.config.server_selection_timeout_ms,
                'socketTimeoutMS': self.config.socket_timeout_ms,
                'retryWrites': self.config.retry_writes,
                'retryReads': self.config.retry_reads,
                'readConcernLevel': self.config.read_concern_level,
                'w': self.config.write_concern_w,
                'j': self.config.write_concern_j
            }

            self._client = MongoClient(self.config.connection_string, **client_options)

            # Get database
            self._database = self._client[self.config.database_name]

            # Test connection
            self._test_connection()

            self.stats.total_connections_created += 1
            self.logger.info(f"MongoDB connection established to database: {self.config.database_name}")

        except Exception as e:
            self.stats.connection_errors += 1
            self.logger.error(f"Failed to initialize MongoDB connection: {e}")
            raise

    def _test_connection(self):
        """Test MongoDB connection health"""

        try:
            # Simple ping to test connectivity
            self._client.admin.command('ping')
            self._last_health_check = datetime.now()

        except Exception as e:
            raise ConnectionError(f"MongoDB connection test failed: {e}")

    @contextmanager
    def get_collection(self, collection_name: str):
        """
        Context manager to get a collection with automatic connection management

        Args:
            collection_name: Name of the collection

        Yields:
            Collection: MongoDB collection object
        """
        with self._lock:
            if not self._is_connection_healthy():
                self._reconnect()

            try:
                collection = self._database[collection_name]
                yield collection

            except errors.AutoReconnect as e:
                self.logger.warning(f"Auto-reconnecting to MongoDB: {e}")
                self._reconnect()
                collection = self._database[collection_name]
                yield collection

            except Exception as e:
                self.logger.error(f"Error accessing collection {collection_name}: {e}")
                raise

    def execute_with_retry(
        self,
        operation: str,
        collection_name: str,
        func,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute database operation with retry logic and monitoring

        Args:
            operation: Operation name for logging/monitoring
            collection_name: Target collection name
            func: Function to execute
            *args, **kwargs: Arguments for the function

        Returns:
            Result of the operation
        """
        start_time = time.time()
        last_exception = None

        for attempt in range(self.config.max_retries + 1):
            try:
                with self.get_collection(collection_name) as collection:
                    result = func(collection, *args, **kwargs)

                # Record successful operation
                duration_ms = (time.time() - start_time) * 1000
                self._record_operation(operation, collection_name, duration_ms, success=True)

                return result

            except (errors.AutoReconnect, errors.NetworkTimeout, errors.ServerSelectionTimeoutError) as e:
                last_exception = e

                if attempt < self.config.max_retries:
                    delay = self.config.retry_delay_seconds * (2 ** attempt)  # Exponential backoff
                    self.logger.warning(f"Retrying {operation} on {collection_name} in {delay}s (attempt {attempt + 1}/{self.config.max_retries}): {e}")
                    time.sleep(delay)
                else:
                    self.logger.error(f"Max retries exceeded for {operation} on {collection_name}: {e}")

            except Exception as e:
                # Non-retryable error
                duration_ms = (time.time() - start_time) * 1000
                self._record_operation(operation, collection_name, duration_ms, success=False)
                self.logger.error(f"Non-retryable error in {operation} on {collection_name}: {e}")
                raise

        # All retries exhausted
        duration_ms = (time.time() - start_time) * 1000
        self._record_operation(operation, collection_name, duration_ms, success=False)
        raise last_exception

    def find_documents(
        self,
        collection_name: str,
        filter_dict: Dict[str, Any],
        projection: Optional[Dict[str, Any]] = None,
        sort: Optional[List[tuple]] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Find documents with managed connection and monitoring

        Args:
            collection_name: Collection to search
            filter_dict: Query filter
            projection: Fields to include/exclude
            sort: Sort specification
            limit: Maximum number of documents

        Returns:
            List of matching documents
        """
        def _find_operation(collection, filter_dict, projection, sort, limit):
            cursor = collection.find(filter_dict, projection)

            if sort:
                cursor = cursor.sort(sort)
            if limit:
                cursor = cursor.limit(limit)

            return list(cursor)

        return self.execute_with_retry(
            "find",
            collection_name,
            _find_operation,
            filter_dict,
            projection,
            sort,
            limit
        )

    def find_one_document(
        self,
        collection_name: str,
        filter_dict: Dict[str, Any],
        projection: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Find single document with managed connection"""

        def _find_one_operation(collection, filter_dict, projection):
            return collection.find_one(filter_dict, projection)

        return self.execute_with_retry(
            "find_one",
            collection_name,
            _find_one_operation,
            filter_dict,
            projection
        )

    def insert_document(
        self,
        collection_name: str,
        document: Dict[str, Any]
    ) -> InsertOneResult:
        """Insert single document with managed connection"""

        def _insert_operation(collection, document):
            return collection.insert_one(document)

        return self.execute_with_retry(
            "insert_one",
            collection_name,
            _insert_operation,
            document
        )

    def insert_documents(
        self,
        collection_name: str,
        documents: List[Dict[str, Any]],
        ordered: bool = True
    ) -> InsertManyResult:
        """Insert multiple documents with managed connection"""

        def _insert_many_operation(collection, documents, ordered):
            return collection.insert_many(documents, ordered=ordered)

        return self.execute_with_retry(
            "insert_many",
            collection_name,
            _insert_many_operation,
            documents,
            ordered
        )

    def update_document(
        self,
        collection_name: str,
        filter_dict: Dict[str, Any],
        update_dict: Dict[str, Any],
        upsert: bool = False
    ) -> UpdateResult:
        """Update single document with managed connection"""

        def _update_operation(collection, filter_dict, update_dict, upsert):
            return collection.update_one(filter_dict, update_dict, upsert=upsert)

        return self.execute_with_retry(
            "update_one",
            collection_name,
            _update_operation,
            filter_dict,
            update_dict,
            upsert
        )

    def update_documents(
        self,
        collection_name: str,
        filter_dict: Dict[str, Any],
        update_dict: Dict[str, Any]
    ) -> UpdateResult:
        """Update multiple documents with managed connection"""

        def _update_many_operation(collection, filter_dict, update_dict):
            return collection.update_many(filter_dict, update_dict)

        return self.execute_with_retry(
            "update_many",
            collection_name,
            _update_many_operation,
            filter_dict,
            update_dict
        )

    def delete_document(
        self,
        collection_name: str,
        filter_dict: Dict[str, Any]
    ) -> DeleteResult:
        """Delete single document with managed connection"""

        def _delete_operation(collection, filter_dict):
            return collection.delete_one(filter_dict)

        return self.execute_with_retry(
            "delete_one",
            collection_name,
            _delete_operation,
            filter_dict
        )

    def delete_documents(
        self,
        collection_name: str,
        filter_dict: Dict[str, Any]
    ) -> DeleteResult:
        """Delete multiple documents with managed connection"""

        def _delete_many_operation(collection, filter_dict):
            return collection.delete_many(filter_dict)

        return self.execute_with_retry(
            "delete_many",
            collection_name,
            _delete_many_operation,
            filter_dict
        )

    def count_documents(
        self,
        collection_name: str,
        filter_dict: Dict[str, Any] = None
    ) -> int:
        """Count documents with managed connection"""

        if filter_dict is None:
            filter_dict = {}

        def _count_operation(collection, filter_dict):
            return collection.count_documents(filter_dict)

        return self.execute_with_retry(
            "count_documents",
            collection_name,
            _count_operation,
            filter_dict
        )

    def aggregate(
        self,
        collection_name: str,
        pipeline: List[Dict[str, Any]],
        allow_disk_use: bool = False
    ) -> List[Dict[str, Any]]:
        """Execute aggregation pipeline with managed connection"""

        def _aggregate_operation(collection, pipeline, allow_disk_use):
            return list(collection.aggregate(pipeline, allowDiskUse=allow_disk_use))

        return self.execute_with_retry(
            "aggregate",
            collection_name,
            _aggregate_operation,
            pipeline,
            allow_disk_use
        )

    def create_index(
        self,
        collection_name: str,
        index_spec: Union[str, List[tuple]],
        **kwargs
    ):
        """Create index with managed connection"""

        def _create_index_operation(collection, index_spec, **kwargs):
            return collection.create_index(index_spec, **kwargs)

        return self.execute_with_retry(
            "create_index",
            collection_name,
            _create_index_operation,
            index_spec,
            **kwargs
        )

    def drop_collection(self, collection_name: str):
        """Drop collection with managed connection"""

        def _drop_operation(collection):
            collection.drop()

        return self.execute_with_retry(
            "drop_collection",
            collection_name,
            _drop_operation
        )

    def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """Get collection statistics"""

        def _stats_operation(collection):
            return self._database.command("collStats", collection_name)

        return self.execute_with_retry(
            "collection_stats",
            collection_name,
            _stats_operation
        )

    def _is_connection_healthy(self) -> bool:
        """Check if connection is healthy"""

        if not self._client or not self._database:
            return False

        # Check if last health check was recent
        if (self._last_health_check and
            datetime.now() - self._last_health_check < timedelta(minutes=5)):
            return True

        try:
            # Perform health check
            self._client.admin.command('ping')
            self._last_health_check = datetime.now()
            return True

        except Exception as e:
            self.logger.warning(f"Connection health check failed: {e}")
            return False

    def _reconnect(self):
        """Reconnect to MongoDB"""

        self.logger.info("Reconnecting to MongoDB...")

        try:
            if self._client:
                self._client.close()

            self._initialize_connection()

        except Exception as e:
            self.stats.connection_errors += 1
            self.logger.error(f"Reconnection failed: {e}")
            raise

    def _record_operation(
        self,
        operation: str,
        collection_name: str,
        duration_ms: float,
        success: bool
    ):
        """Record operation statistics"""

        if not self.config.enable_monitoring:
            return

        # Update overall operation stats
        if operation not in self.stats.operation_stats:
            self.stats.operation_stats[operation] = OperationStats()

        op_stats = self.stats.operation_stats[operation]
        op_stats.operation_count += 1
        op_stats.total_duration_ms += duration_ms
        op_stats.average_duration_ms = op_stats.total_duration_ms / op_stats.operation_count
        op_stats.max_duration_ms = max(op_stats.max_duration_ms, duration_ms)
        op_stats.last_operation_time = datetime.now()

        if not success:
            op_stats.error_count += 1

        # Update collection-specific stats
        if operation not in self.stats.collection_stats[collection_name]:
            self.stats.collection_stats[collection_name][operation] = OperationStats()

        coll_stats = self.stats.collection_stats[collection_name][operation]
        coll_stats.operation_count += 1
        coll_stats.total_duration_ms += duration_ms
        coll_stats.average_duration_ms = coll_stats.total_duration_ms / coll_stats.operation_count
        coll_stats.max_duration_ms = max(coll_stats.max_duration_ms, duration_ms)
        coll_stats.last_operation_time = datetime.now()

        if not success:
            coll_stats.error_count += 1

        # Log slow operations
        if duration_ms > self.config.slow_operation_threshold_ms:
            self.logger.warning(
                f"Slow operation detected: {operation} on {collection_name} "
                f"took {duration_ms:.1f}ms (threshold: {self.config.slow_operation_threshold_ms}ms)"
            )

        # Keep operation history (limited)
        self._operation_history.append({
            'operation': operation,
            'collection': collection_name,
            'duration_ms': duration_ms,
            'success': success,
            'timestamp': datetime.now()
        })

        # Keep only recent history
        if len(self._operation_history) > 1000:
            self._operation_history = self._operation_history[-1000:]

    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report"""

        report = {
            'connection_stats': {
                'total_connections_created': self.stats.total_connections_created,
                'connection_errors': self.stats.connection_errors,
                'last_health_check': self._last_health_check.isoformat() if self._last_health_check else None,
                'connection_healthy': self._is_connection_healthy()
            },
            'operation_performance': {},
            'collection_performance': {},
            'recent_slow_operations': []
        }

        # Overall operation performance
        for operation, stats in self.stats.operation_stats.items():
            report['operation_performance'][operation] = {
                'total_count': stats.operation_count,
                'error_count': stats.error_count,
                'error_rate': stats.error_count / stats.operation_count if stats.operation_count > 0 else 0,
                'average_duration_ms': stats.average_duration_ms,
                'max_duration_ms': stats.max_duration_ms,
                'last_operation': stats.last_operation_time.isoformat() if stats.last_operation_time else None
            }

        # Collection-specific performance
        for collection, operations in self.stats.collection_stats.items():
            report['collection_performance'][collection] = {}

            for operation, stats in operations.items():
                report['collection_performance'][collection][operation] = {
                    'total_count': stats.operation_count,
                    'error_count': stats.error_count,
                    'average_duration_ms': stats.average_duration_ms,
                    'max_duration_ms': stats.max_duration_ms
                }

        # Recent slow operations
        now = datetime.now()
        recent_slow = [
            op for op in self._operation_history
            if (now - op['timestamp']).total_seconds() < 3600  # Last hour
            and op['duration_ms'] > self.config.slow_operation_threshold_ms
        ]

        report['recent_slow_operations'] = [
            {
                'operation': op['operation'],
                'collection': op['collection'],
                'duration_ms': op['duration_ms'],
                'timestamp': op['timestamp'].isoformat()
            }
            for op in sorted(recent_slow, key=lambda x: x['duration_ms'], reverse=True)[:10]
        ]

        return report

    def close(self):
        """Close MongoDB connection"""

        if self._client:
            self.logger.info("Closing MongoDB connection...")
            self._client.close()
            self._client = None
            self._database = None