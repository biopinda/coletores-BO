"""
Analysis Results Persistence and Loading Service

This service handles the persistence and loading of complete dataset analysis results
from analise_coletores.py. It manages the storage of analysis insights, pattern
discovery results, and configuration recommendations to support the downstream
processing pipeline.

The service ensures that the complete dataset analysis (all 11M+ records) results
are properly stored and can be efficiently loaded by subsequent processing stages.
"""

import json
import logging
import pickle
import gzip
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
import tempfile
import shutil

import pandas as pd
import numpy as np
from pymongo import MongoClient
from pymongo.collection import Collection
from bson import ObjectId

from ..models.checkpoint_data import CheckpointData
from .pattern_discovery import DatasetInsights, DiscoveredPattern, ThresholdRecommendation


@dataclass
class AnalysisMetadata:
    """Metadata for analysis results"""

    analysis_id: str
    creation_timestamp: datetime
    analysis_version: str
    dataset_source: str

    # Dataset characteristics
    total_records_analyzed: int
    analysis_duration_seconds: float
    analysis_config_hash: str

    # File information
    file_paths: Dict[str, str] = field(default_factory=dict)
    file_sizes: Dict[str, int] = field(default_factory=dict)
    compression_used: bool = False

    # Quality metrics
    completeness_percentage: float = 0.0
    data_quality_score: float = 0.0
    anomaly_count: int = 0


@dataclass
class PersistenceConfig:
    """Configuration for analysis persistence"""

    # Storage locations
    base_storage_path: Path = Path("./analysis_results")
    backup_storage_path: Optional[Path] = None

    # File format options
    use_compression: bool = True
    json_indent: int = 2
    preserve_original: bool = True

    # MongoDB persistence
    use_mongodb_persistence: bool = True
    mongodb_collection: str = "analysis_results"

    # Cleanup options
    max_stored_analyses: int = 10
    auto_cleanup_old_results: bool = True


class AnalysisPersistenceService:
    """Service for persisting and loading analysis results from complete dataset analysis"""

    def __init__(
        self,
        config: Optional[PersistenceConfig] = None,
        mongo_client: Optional[MongoClient] = None
    ):
        self.config = config or PersistenceConfig()
        self.mongo_client = mongo_client
        self.logger = logging.getLogger(__name__)

        # Create storage directories
        self.config.base_storage_path.mkdir(parents=True, exist_ok=True)
        if self.config.backup_storage_path:
            self.config.backup_storage_path.mkdir(parents=True, exist_ok=True)

        # MongoDB collection for persistence
        self._mongo_collection: Optional[Collection] = None
        if self.mongo_client and self.config.use_mongodb_persistence:
            try:
                self._mongo_collection = self.mongo_client.get_database().get_collection(
                    self.config.mongodb_collection
                )
            except Exception as e:
                self.logger.warning(f"Failed to initialize MongoDB collection: {e}")

    def persist_analysis_results(
        self,
        analysis_results: Dict[str, Any],
        analysis_config: Dict[str, Any],
        analysis_duration: float
    ) -> str:
        """
        Persist complete dataset analysis results to multiple storage backends

        Args:
            analysis_results: Complete analysis results from analise_coletores.py
            analysis_config: Configuration used for the analysis
            analysis_duration: Time taken for analysis in seconds

        Returns:
            Analysis ID for later retrieval
        """
        # Generate unique analysis ID
        analysis_id = self._generate_analysis_id(analysis_results, analysis_config)

        self.logger.info(f"Persisting analysis results with ID: {analysis_id}")

        try:
            # Create analysis metadata
            metadata = self._create_analysis_metadata(
                analysis_id, analysis_results, analysis_config, analysis_duration
            )

            # Store to file system
            file_paths = self._persist_to_filesystem(analysis_id, analysis_results, metadata)

            # Store to MongoDB if available
            if self._mongo_collection:
                self._persist_to_mongodb(analysis_id, analysis_results, metadata)

            # Update metadata with file paths
            metadata.file_paths = file_paths
            self._save_metadata(analysis_id, metadata)

            # Cleanup old analyses if configured
            if self.config.auto_cleanup_old_results:
                self._cleanup_old_analyses()

            self.logger.info(f"Analysis results successfully persisted: {analysis_id}")

            return analysis_id

        except Exception as e:
            self.logger.error(f"Failed to persist analysis results: {e}")
            raise

    def load_analysis_results(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """
        Load analysis results by ID

        Args:
            analysis_id: The analysis ID to load

        Returns:
            Analysis results dictionary or None if not found
        """
        self.logger.info(f"Loading analysis results: {analysis_id}")

        try:
            # Try loading from file system first
            results = self._load_from_filesystem(analysis_id)

            if results:
                self.logger.info(f"Loaded analysis results from filesystem: {analysis_id}")
                return results

            # Try loading from MongoDB if filesystem fails
            if self._mongo_collection:
                results = self._load_from_mongodb(analysis_id)
                if results:
                    self.logger.info(f"Loaded analysis results from MongoDB: {analysis_id}")
                    return results

            self.logger.warning(f"Analysis results not found: {analysis_id}")
            return None

        except Exception as e:
            self.logger.error(f"Failed to load analysis results {analysis_id}: {e}")
            return None

    def load_latest_analysis_results(self) -> Optional[Dict[str, Any]]:
        """Load the most recent analysis results"""

        try:
            # Get list of available analyses
            available_analyses = self.list_available_analyses()

            if not available_analyses:
                self.logger.warning("No analysis results available")
                return None

            # Sort by creation timestamp and get latest
            latest_metadata = max(
                available_analyses,
                key=lambda x: x.creation_timestamp
            )

            return self.load_analysis_results(latest_metadata.analysis_id)

        except Exception as e:
            self.logger.error(f"Failed to load latest analysis results: {e}")
            return None

    def list_available_analyses(self) -> List[AnalysisMetadata]:
        """List all available analysis results with metadata"""

        analyses = []

        try:
            # Get analyses from filesystem
            filesystem_analyses = self._list_filesystem_analyses()
            analyses.extend(filesystem_analyses)

            # Get analyses from MongoDB
            if self._mongo_collection:
                mongodb_analyses = self._list_mongodb_analyses()
                # Merge with filesystem analyses (avoid duplicates)
                filesystem_ids = {a.analysis_id for a in analyses}
                for mongo_analysis in mongodb_analyses:
                    if mongo_analysis.analysis_id not in filesystem_ids:
                        analyses.append(mongo_analysis)

            # Sort by creation time
            analyses.sort(key=lambda x: x.creation_timestamp, reverse=True)

            self.logger.info(f"Found {len(analyses)} available analyses")

            return analyses

        except Exception as e:
            self.logger.error(f"Failed to list available analyses: {e}")
            return []

    def get_analysis_summary(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """Get summary information about an analysis without loading full results"""

        try:
            metadata = self._load_metadata(analysis_id)
            if not metadata:
                return None

            return {
                'analysis_id': metadata.analysis_id,
                'creation_timestamp': metadata.creation_timestamp.isoformat(),
                'analysis_version': metadata.analysis_version,
                'total_records_analyzed': metadata.total_records_analyzed,
                'analysis_duration_seconds': metadata.analysis_duration_seconds,
                'completeness_percentage': metadata.completeness_percentage,
                'data_quality_score': metadata.data_quality_score,
                'anomaly_count': metadata.anomaly_count,
                'file_sizes': metadata.file_sizes
            }

        except Exception as e:
            self.logger.error(f"Failed to get analysis summary {analysis_id}: {e}")
            return None

    def export_analysis_results(
        self,
        analysis_id: str,
        export_path: Path,
        export_format: str = "json"
    ) -> bool:
        """
        Export analysis results to a specific location and format

        Args:
            analysis_id: Analysis ID to export
            export_path: Destination path for export
            export_format: Export format ('json', 'pickle', 'csv')

        Returns:
            True if export successful, False otherwise
        """
        try:
            results = self.load_analysis_results(analysis_id)
            if not results:
                self.logger.error(f"Analysis results not found for export: {analysis_id}")
                return False

            export_path.parent.mkdir(parents=True, exist_ok=True)

            if export_format.lower() == "json":
                self._export_to_json(results, export_path)
            elif export_format.lower() == "pickle":
                self._export_to_pickle(results, export_path)
            elif export_format.lower() == "csv":
                self._export_to_csv(results, export_path)
            else:
                raise ValueError(f"Unsupported export format: {export_format}")

            self.logger.info(f"Analysis results exported successfully: {export_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to export analysis results: {e}")
            return False

    def delete_analysis_results(self, analysis_id: str) -> bool:
        """Delete analysis results from all storage backends"""

        try:
            success = True

            # Delete from filesystem
            filesystem_success = self._delete_from_filesystem(analysis_id)
            success = success and filesystem_success

            # Delete from MongoDB
            if self._mongo_collection:
                mongodb_success = self._delete_from_mongodb(analysis_id)
                success = success and mongodb_success

            if success:
                self.logger.info(f"Analysis results deleted successfully: {analysis_id}")
            else:
                self.logger.warning(f"Partial deletion of analysis results: {analysis_id}")

            return success

        except Exception as e:
            self.logger.error(f"Failed to delete analysis results {analysis_id}: {e}")
            return False

    def validate_analysis_results(self, analysis_id: str) -> Dict[str, Any]:
        """Validate the integrity of stored analysis results"""

        validation_results = {
            'analysis_id': analysis_id,
            'is_valid': True,
            'issues': [],
            'metadata_valid': False,
            'data_integrity_valid': False,
            'file_accessibility_valid': False
        }

        try:
            # Check metadata
            metadata = self._load_metadata(analysis_id)
            if metadata:
                validation_results['metadata_valid'] = True
            else:
                validation_results['is_valid'] = False
                validation_results['issues'].append("Metadata not found or corrupted")

            # Check data integrity
            results = self.load_analysis_results(analysis_id)
            if results:
                # Validate required fields
                required_fields = ['total_records', 'collector_analysis', 'pattern_analysis']
                missing_fields = [field for field in required_fields if field not in results]

                if missing_fields:
                    validation_results['is_valid'] = False
                    validation_results['issues'].append(f"Missing required fields: {missing_fields}")
                else:
                    validation_results['data_integrity_valid'] = True

            else:
                validation_results['is_valid'] = False
                validation_results['issues'].append("Analysis results not loadable")

            # Check file accessibility
            if metadata and metadata.file_paths:
                inaccessible_files = []
                for file_type, file_path in metadata.file_paths.items():
                    if not Path(file_path).exists():
                        inaccessible_files.append(f"{file_type}: {file_path}")

                if inaccessible_files:
                    validation_results['is_valid'] = False
                    validation_results['issues'].append(f"Inaccessible files: {inaccessible_files}")
                else:
                    validation_results['file_accessibility_valid'] = True

        except Exception as e:
            validation_results['is_valid'] = False
            validation_results['issues'].append(f"Validation error: {str(e)}")

        return validation_results

    # Private methods

    def _generate_analysis_id(self, results: Dict[str, Any], config: Dict[str, Any]) -> str:
        """Generate unique analysis ID based on results and config"""

        # Create hash from key components
        hash_components = {
            'timestamp': datetime.now().isoformat(),
            'total_records': results.get('total_records', 0),
            'config_hash': hashlib.md5(json.dumps(config, sort_keys=True).encode()).hexdigest()[:8]
        }

        hash_str = json.dumps(hash_components, sort_keys=True).encode()
        analysis_hash = hashlib.sha256(hash_str).hexdigest()[:16]

        return f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{analysis_hash}"

    def _create_analysis_metadata(
        self,
        analysis_id: str,
        results: Dict[str, Any],
        config: Dict[str, Any],
        duration: float
    ) -> AnalysisMetadata:
        """Create analysis metadata"""

        config_hash = hashlib.md5(json.dumps(config, sort_keys=True).encode()).hexdigest()

        # Calculate quality metrics
        total_records = results.get('total_records', 0)
        quality_metrics = results.get('quality_metrics', {})

        return AnalysisMetadata(
            analysis_id=analysis_id,
            creation_timestamp=datetime.now(),
            analysis_version="1.0.0",
            dataset_source=config.get('database_name', 'unknown'),
            total_records_analyzed=total_records,
            analysis_duration_seconds=duration,
            analysis_config_hash=config_hash,
            completeness_percentage=quality_metrics.get('completeness_score', 0.0) * 100,
            data_quality_score=quality_metrics.get('consistency_score', 0.0),
            anomaly_count=len(quality_metrics.get('anomaly_indicators', []))
        )

    def _persist_to_filesystem(
        self,
        analysis_id: str,
        results: Dict[str, Any],
        metadata: AnalysisMetadata
    ) -> Dict[str, str]:
        """Persist analysis results to filesystem"""

        analysis_dir = self.config.base_storage_path / analysis_id
        analysis_dir.mkdir(parents=True, exist_ok=True)

        file_paths = {}

        # Main results file
        main_results_path = analysis_dir / "analysis_results.json"
        if self.config.use_compression:
            main_results_path = analysis_dir / "analysis_results.json.gz"
            with gzip.open(main_results_path, 'wt', encoding='utf-8') as f:
                json.dump(results, f, indent=self.config.json_indent, ensure_ascii=False, default=str)
        else:
            with open(main_results_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=self.config.json_indent, ensure_ascii=False, default=str)

        file_paths['main_results'] = str(main_results_path)
        metadata.file_sizes['main_results'] = main_results_path.stat().st_size

        # Separate files for major components
        components = {
            'collector_analysis': results.get('collector_analysis', {}),
            'pattern_analysis': results.get('pattern_analysis', {}),
            'similarity_analysis': results.get('similarity_analysis', {}),
            'quality_metrics': results.get('quality_metrics', {})
        }

        for component_name, component_data in components.items():
            if component_data:
                component_path = analysis_dir / f"{component_name}.json"
                if self.config.use_compression:
                    component_path = analysis_dir / f"{component_name}.json.gz"
                    with gzip.open(component_path, 'wt', encoding='utf-8') as f:
                        json.dump(component_data, f, indent=self.config.json_indent, ensure_ascii=False, default=str)
                else:
                    with open(component_path, 'w', encoding='utf-8') as f:
                        json.dump(component_data, f, indent=self.config.json_indent, ensure_ascii=False, default=str)

                file_paths[component_name] = str(component_path)
                metadata.file_sizes[component_name] = component_path.stat().st_size

        # Create backup if configured
        if self.config.backup_storage_path:
            backup_dir = self.config.backup_storage_path / analysis_id
            shutil.copytree(analysis_dir, backup_dir, dirs_exist_ok=True)

        metadata.compression_used = self.config.use_compression

        return file_paths

    def _persist_to_mongodb(
        self,
        analysis_id: str,
        results: Dict[str, Any],
        metadata: AnalysisMetadata
    ):
        """Persist analysis results to MongoDB"""

        if not self._mongo_collection:
            return

        try:
            # Create MongoDB document
            document = {
                '_id': analysis_id,
                'metadata': self._metadata_to_dict(metadata),
                'analysis_results': results,
                'created_at': datetime.now()
            }

            # Insert or update
            self._mongo_collection.replace_one(
                {'_id': analysis_id},
                document,
                upsert=True
            )

            self.logger.info(f"Analysis results persisted to MongoDB: {analysis_id}")

        except Exception as e:
            self.logger.error(f"Failed to persist to MongoDB: {e}")
            raise

    def _load_from_filesystem(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """Load analysis results from filesystem"""

        analysis_dir = self.config.base_storage_path / analysis_id

        if not analysis_dir.exists():
            return None

        try:
            # Try compressed format first
            main_results_path = analysis_dir / "analysis_results.json.gz"
            if main_results_path.exists():
                with gzip.open(main_results_path, 'rt', encoding='utf-8') as f:
                    return json.load(f)

            # Try uncompressed format
            main_results_path = analysis_dir / "analysis_results.json"
            if main_results_path.exists():
                with open(main_results_path, 'r', encoding='utf-8') as f:
                    return json.load(f)

            return None

        except Exception as e:
            self.logger.error(f"Failed to load from filesystem: {e}")
            return None

    def _load_from_mongodb(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """Load analysis results from MongoDB"""

        if not self._mongo_collection:
            return None

        try:
            document = self._mongo_collection.find_one({'_id': analysis_id})

            if document:
                return document.get('analysis_results')

            return None

        except Exception as e:
            self.logger.error(f"Failed to load from MongoDB: {e}")
            return None

    def _save_metadata(self, analysis_id: str, metadata: AnalysisMetadata):
        """Save analysis metadata to filesystem"""

        analysis_dir = self.config.base_storage_path / analysis_id
        metadata_path = analysis_dir / "metadata.json"

        metadata_dict = self._metadata_to_dict(metadata)

        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata_dict, f, indent=2, ensure_ascii=False, default=str)

    def _load_metadata(self, analysis_id: str) -> Optional[AnalysisMetadata]:
        """Load analysis metadata from filesystem"""

        analysis_dir = self.config.base_storage_path / analysis_id
        metadata_path = analysis_dir / "metadata.json"

        if not metadata_path.exists():
            return None

        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata_dict = json.load(f)

            return self._dict_to_metadata(metadata_dict)

        except Exception as e:
            self.logger.error(f"Failed to load metadata: {e}")
            return None

    def _metadata_to_dict(self, metadata: AnalysisMetadata) -> Dict[str, Any]:
        """Convert metadata dataclass to dictionary"""

        return {
            'analysis_id': metadata.analysis_id,
            'creation_timestamp': metadata.creation_timestamp.isoformat(),
            'analysis_version': metadata.analysis_version,
            'dataset_source': metadata.dataset_source,
            'total_records_analyzed': metadata.total_records_analyzed,
            'analysis_duration_seconds': metadata.analysis_duration_seconds,
            'analysis_config_hash': metadata.analysis_config_hash,
            'file_paths': metadata.file_paths,
            'file_sizes': metadata.file_sizes,
            'compression_used': metadata.compression_used,
            'completeness_percentage': metadata.completeness_percentage,
            'data_quality_score': metadata.data_quality_score,
            'anomaly_count': metadata.anomaly_count
        }

    def _dict_to_metadata(self, metadata_dict: Dict[str, Any]) -> AnalysisMetadata:
        """Convert dictionary to metadata dataclass"""

        return AnalysisMetadata(
            analysis_id=metadata_dict['analysis_id'],
            creation_timestamp=datetime.fromisoformat(metadata_dict['creation_timestamp']),
            analysis_version=metadata_dict.get('analysis_version', '1.0.0'),
            dataset_source=metadata_dict.get('dataset_source', 'unknown'),
            total_records_analyzed=metadata_dict.get('total_records_analyzed', 0),
            analysis_duration_seconds=metadata_dict.get('analysis_duration_seconds', 0.0),
            analysis_config_hash=metadata_dict.get('analysis_config_hash', ''),
            file_paths=metadata_dict.get('file_paths', {}),
            file_sizes=metadata_dict.get('file_sizes', {}),
            compression_used=metadata_dict.get('compression_used', False),
            completeness_percentage=metadata_dict.get('completeness_percentage', 0.0),
            data_quality_score=metadata_dict.get('data_quality_score', 0.0),
            anomaly_count=metadata_dict.get('anomaly_count', 0)
        )

    def _list_filesystem_analyses(self) -> List[AnalysisMetadata]:
        """List analyses available in filesystem"""

        analyses = []

        try:
            for analysis_dir in self.config.base_storage_path.iterdir():
                if analysis_dir.is_dir() and analysis_dir.name.startswith('analysis_'):
                    metadata = self._load_metadata(analysis_dir.name)
                    if metadata:
                        analyses.append(metadata)

        except Exception as e:
            self.logger.error(f"Failed to list filesystem analyses: {e}")

        return analyses

    def _list_mongodb_analyses(self) -> List[AnalysisMetadata]:
        """List analyses available in MongoDB"""

        analyses = []

        if not self._mongo_collection:
            return analyses

        try:
            documents = self._mongo_collection.find({}, {'metadata': 1})

            for doc in documents:
                metadata_dict = doc.get('metadata', {})
                if metadata_dict:
                    metadata = self._dict_to_metadata(metadata_dict)
                    analyses.append(metadata)

        except Exception as e:
            self.logger.error(f"Failed to list MongoDB analyses: {e}")

        return analyses

    def _cleanup_old_analyses(self):
        """Remove old analyses beyond the configured limit"""

        try:
            analyses = self.list_available_analyses()

            if len(analyses) <= self.config.max_stored_analyses:
                return

            # Sort by creation time and remove oldest
            analyses_to_remove = analyses[self.config.max_stored_analyses:]

            for old_analysis in analyses_to_remove:
                self.delete_analysis_results(old_analysis.analysis_id)

            self.logger.info(f"Cleaned up {len(analyses_to_remove)} old analyses")

        except Exception as e:
            self.logger.error(f"Failed to cleanup old analyses: {e}")

    def _delete_from_filesystem(self, analysis_id: str) -> bool:
        """Delete analysis results from filesystem"""

        analysis_dir = self.config.base_storage_path / analysis_id

        try:
            if analysis_dir.exists():
                shutil.rmtree(analysis_dir)

            # Also remove from backup if exists
            if self.config.backup_storage_path:
                backup_dir = self.config.backup_storage_path / analysis_id
                if backup_dir.exists():
                    shutil.rmtree(backup_dir)

            return True

        except Exception as e:
            self.logger.error(f"Failed to delete from filesystem: {e}")
            return False

    def _delete_from_mongodb(self, analysis_id: str) -> bool:
        """Delete analysis results from MongoDB"""

        if not self._mongo_collection:
            return True

        try:
            result = self._mongo_collection.delete_one({'_id': analysis_id})
            return result.deleted_count > 0

        except Exception as e:
            self.logger.error(f"Failed to delete from MongoDB: {e}")
            return False

    def _export_to_json(self, results: Dict[str, Any], export_path: Path):
        """Export results to JSON format"""

        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)

    def _export_to_pickle(self, results: Dict[str, Any], export_path: Path):
        """Export results to pickle format"""

        with open(export_path, 'wb') as f:
            pickle.dump(results, f)

    def _export_to_csv(self, results: Dict[str, Any], export_path: Path):
        """Export results to CSV format (selected data only)"""

        # Export collector analysis as CSV
        collector_data = results.get('collector_analysis', {}).get('collector_summary', [])

        if collector_data:
            df = pd.DataFrame(collector_data)
            csv_path = export_path.with_suffix('.csv')
            df.to_csv(csv_path, index=False, encoding='utf-8')