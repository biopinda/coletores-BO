"""Configuration management using Pydantic for type-safe config loading"""

from pydantic import BaseModel, Field
from typing import Dict
import yaml


class MongoDBConfig(BaseModel):
    """MongoDB configuration"""
    uri: str
    database: str
    collection: str
    filter: Dict[str, str]


class LocalDBConfig(BaseModel):
    """Local database configuration"""
    type: str = Field(description="Database type: duckdb or sqlite")
    path: str


class ProcessingConfig(BaseModel):
    """Processing configuration"""
    batch_size: int = 10000
    workers: int = 8
    confidence_threshold: float = 0.70


class SimilarityWeights(BaseModel):
    """Similarity algorithm weights"""
    levenshtein: float = 0.4
    jaro_winkler: float = 0.4
    phonetic: float = 0.2


class AlgorithmsConfig(BaseModel):
    """Algorithms configuration"""
    similarity_weights: SimilarityWeights


class OutputConfig(BaseModel):
    """Output configuration"""
    csv_path: str
    rules_doc: str


class Config(BaseModel):
    """Main configuration"""
    mongodb: MongoDBConfig
    local_db: LocalDBConfig
    processing: ProcessingConfig
    algorithms: AlgorithmsConfig
    output: OutputConfig

    @classmethod
    def from_yaml(cls, path: str) -> "Config":
        """Load configuration from YAML file"""
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls(**data)
