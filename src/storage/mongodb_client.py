"""MongoDB source client"""

from pymongo import MongoClient
from typing import Iterator, Dict, Any


class MongoDBSource:
    """MongoDB source reader for plant specimens"""
    
    def __init__(self, uri: str, database: str, collection: str, filter_criteria: Dict[str, Any]):
        """Initialize MongoDB connection"""
        self.client = MongoClient(uri)
        self.db = self.client[database]
        self.collection = self.db[collection]
        self.filter_criteria = filter_criteria
    
    def stream_records(self, batch_size: int = 1000) -> Iterator[list]:
        """Stream records where kingdom=='Plantae', yield in batches"""
        cursor = self.collection.find(self.filter_criteria).batch_size(batch_size)
        
        batch = []
        for record in cursor:
            batch.append(record)
            if len(batch) >= batch_size:
                yield batch
                batch = []
        
        if batch:  # Yield remaining records
            yield batch
    
    def get_total_count(self) -> int:
        """Get total count of Plantae records for progress tracking"""
        return self.collection.count_documents(self.filter_criteria)
    
    def close(self) -> None:
        """Close MongoDB connection"""
        self.client.close()
