"""MongoDB source reader for plant specimen records"""

from typing import Any, Dict, Generator, List

from pymongo import MongoClient
from pymongo.collection import Collection


class MongoDBSource:
    """MongoDB source reader (FR-017, FR-018)"""

    def __init__(self, uri: str, database: str, collection: str, filter_query: Dict[str, Any]):
        """
        Initialize MongoDB connection with UTF-8 encoding.

        Args:
            uri: MongoDB connection URI
            database: Database name
            collection: Collection name
            filter_query: Filter criteria (e.g., {"kingdom": "Plantae"})
        """
        # Connect with UTF-8 encoding support
        self.client = MongoClient(uri, unicode_decode_error_handler='strict')
        self.db = self.client[database]
        self.collection: Collection = self.db[collection]
        self.filter_query = filter_query

    def stream_records(self, batch_size: int = 1000) -> Generator[List[Dict[str, Any]], None, None]:
        """
        Stream records where kingdom=='Plantae', yield in batches.

        Args:
            batch_size: Number of records per batch

        Yields:
            Batches of records matching the filter
        """
        cursor = self.collection.find(self.filter_query).batch_size(batch_size)

        batch = []
        for record in cursor:
            batch.append(record)

            if len(batch) >= batch_size:
                yield batch
                batch = []

        # Yield remaining records
        if batch:
            yield batch

    def get_total_count(self) -> int:
        """
        Get total count of Plantae records for progress tracking.

        Returns:
            Number of records matching filter
        """
        return self.collection.count_documents(self.filter_query)

    def close(self) -> None:
        """Close MongoDB connection"""
        self.client.close()
