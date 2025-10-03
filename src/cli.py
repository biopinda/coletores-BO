"""CLI orchestrator for the collector canonicalization pipeline"""

import logging
import time
from typing import Any, Dict

import click
from tqdm import tqdm

from src.config import Config
from src.models.entities import ClassificationCategory, EntityType
from src.models.schemas import (
    AtomizationInput,
    CanonicalizationInput,
    ClassificationInput,
    NormalizationInput,
)
from src.pipeline.atomizer import Atomizer
from src.pipeline.canonicalizer import Canonicalizer
from src.pipeline.classifier import Classifier
from src.pipeline.normalizer import Normalizer
from src.storage.local_db import LocalDatabase
from src.storage.mongodb_client import MongoDBSource

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PipelineResult:
    """Results from pipeline execution"""

    def __init__(self):
        self.total_records = 0
        self.processed_records = 0
        self.elapsed_time_seconds = 0.0
        self.canonical_entities_count = 0
        self.classification_complete = False
        self.atomization_complete = False
        self.normalization_complete = False
        self.canonicalization_complete = False


def process_single_record(
    record: Dict[str, Any],
    classifier: Classifier,
    atomizer: Atomizer,
    normalizer: Normalizer,
    canonicalizer: Canonicalizer,
    collector_field: str = "recordedBy",
    ) -> bool:
    """Processa um único documento MongoDB através de todas as etapas.

    Retorna True se pelo menos um nome foi processado.
    """
    collector_text = record.get(collector_field, "")
    if not collector_text:
        return False
    # Stage 1: Classification
    classification_result = classifier.classify(ClassificationInput(text=collector_text))

    # Stage 2: Atomization (if needed)
    if classification_result.should_atomize:
        atomization_result = atomizer.atomize(
            AtomizationInput(
                text=classification_result.original_text, category=classification_result.category
            )
        )
        names_to_process = [atom.text for atom in atomization_result.atomized_names]
    else:
        names_to_process = [classification_result.original_text]

    # Process each name
    for name in names_to_process:
        normalization_result = normalizer.normalize(NormalizationInput(original_name=name))
        entityType_map = {
            ClassificationCategory.PESSOA: EntityType.PESSOA,
            ClassificationCategory.CONJUNTO_PESSOAS: EntityType.PESSOA,
            ClassificationCategory.GRUPO_PESSOAS: EntityType.GRUPO_PESSOAS,
            ClassificationCategory.EMPRESA: EntityType.EMPRESA,
            ClassificationCategory.NAO_DETERMINADO: EntityType.NAO_DETERMINADO,
        }
        entityType = entityType_map[classification_result.category]
        canonicalizer.canonicalize(
            CanonicalizationInput(
                normalized_name=normalization_result.normalized,
                entityType=entityType,
                classification_confidence=classification_result.confidence,
            )
        )
    return True


@click.command()
@click.option("--config", default="config.yaml", help="Path to configuration file")
@click.option("--batch-size", default=None, type=int, help="Batch size for processing")
@click.option("--max-records", default=None, type=int, help="Maximum records to process (for testing)")
def main(config: str, batch_size: int | None, max_records: int | None):
    """Run the collector canonicalization pipeline"""
    # Load configuration
    cfg = Config.from_yaml(config)

    # Override with CLI arguments
    if batch_size is None:
        batch_size = cfg.processing.batch_size

    logger.info(f"Starting pipeline with batch size {batch_size}")

    # Initialize MongoDB source
    mongo_source = MongoDBSource(
        uri=cfg.mongodb.uri,
        database=cfg.mongodb.database,
        collection=cfg.mongodb.collection,
        filter_query=cfg.mongodb.filter,
    )

    # Get total count from source
    total_count = mongo_source.get_total_count()
    if max_records:
        total_count = min(total_count, max_records)
    logger.info(f"Total records to process: {total_count}")

    # Initialize shared components once
    db = LocalDatabase(cfg.local_db.path)
    classifier = Classifier()
    atomizer = Atomizer()
    normalizer = Normalizer()
    canonicalizer = Canonicalizer(db)

    # Process records
    start_time = time.time()
    processed_count = 0

    with tqdm(total=total_count, desc="Processing records") as pbar:
        for batch in mongo_source.stream_records(batch_size=batch_size):
            if max_records and processed_count >= max_records:
                break

            if max_records:
                batch = batch[: max_records - processed_count]

            for record in batch:
                if process_single_record(
                    record,
                    classifier,
                    atomizer,
                    normalizer,
                    canonicalizer,
                ):
                    processed_count += 1
                    pbar.update(1)

                    # Update rate display
                    elapsed = time.time() - start_time
                    rate = processed_count / elapsed if elapsed > 0 else 0
                    pbar.set_postfix({"rate": f"{rate:.1f} rec/s"})

            if processed_count >= total_count:
                break

    elapsed_time = time.time() - start_time
    rate = processed_count / elapsed_time if elapsed_time > 0 else 0

    logger.info(f"Processing complete: {processed_count} records in {elapsed_time:.1f}s")
    logger.info(f"Processing rate: {rate:.1f} records/sec")

    # Consolidate duplicates before export (Item A)
    consolidated = db.consolidate_duplicates() if hasattr(db, 'consolidate_duplicates') else 0
    if consolidated:
        logger.info(f"Consolidated duplicate groups: {consolidated}")

    # Export to CSV (after consolidation)
    logger.info(f"Exporting to CSV: {cfg.output.csv_path}")
    # Export deduplicado
    if hasattr(db, 'export_deduplicated_to_csv'):
        db.export_deduplicated_to_csv(cfg.output.csv_path)
    else:
        db.export_to_csv(cfg.output.csv_path)

    # Get final statistics after consolidation
    entity_count = len(db.get_all_entities())
    logger.info(f"Total canonical entities: {entity_count}")

    # Close connections
    db.close()
    mongo_source.close()
