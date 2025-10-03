"""Configuration management"""

from pathlib import Path
from typing import Any, Dict

import yaml
from pydantic import BaseModel, Field


class MongoDBConfig(BaseModel):
    """MongoDB connection configuration"""

    uri: str
    database: str
    collection: str
    filter: Dict[str, Any]


class LocalDBConfig(BaseModel):
    """Local database configuration"""

    type: str = Field(pattern="^(duckdb|sqlite)$")
    path: str


class ProcessingConfig(BaseModel):
    """Processing configuration"""

    batch_size: int = Field(gt=0)
    confidence_threshold: float = Field(ge=0.70, le=1.0)


class SimilarityWeights(BaseModel):
    """Algorithm similarity weights"""

    levenshtein: float = Field(ge=0.0, le=1.0)
    jaro_winkler: float = Field(ge=0.0, le=1.0)
    phonetic: float = Field(ge=0.0, le=1.0)


class AlgorithmsConfig(BaseModel):
    """Algorithm configuration"""

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
