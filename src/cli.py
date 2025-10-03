"""CLI orchestrator for the collector canonicalization pipeline"""

import logging
import time
from datetime import datetime
from multiprocessing import Pool
from pathlib import Path
from typing import Any, Dict, List

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
    record: Dict[str, Any], db_path: str, collector_field: str = "collector"
) -> bool:
    """
    Process a single record through the full pipeline.

    Args:
        record: MongoDB record
        db_path: Path to local database
        collector_field: Field name containing collector string

    Returns:
        True if processed successfully
    """
    try:
        collector_text = record.get(collector_field, "")
        if not collector_text:
            return False

        # Initialize pipeline components
        classifier = Classifier()
        atomizer = Atomizer()
        normalizer = Normalizer()

        # Database connection per worker
        db = LocalDatabase(db_path)
        canonicalizer = Canonicalizer(db)

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
            # Stage 3: Normalization
            normalization_result = normalizer.normalize(NormalizationInput(original_name=name))

            # Map classification category to entity type
            entity_type_map = {
                ClassificationCategory.PESSOA: EntityType.PESSOA,
                ClassificationCategory.CONJUNTO_PESSOAS: EntityType.PESSOA,  # Individual names
                ClassificationCategory.GRUPO_PESSOAS: EntityType.GRUPO_PESSOAS,
                ClassificationCategory.EMPRESA: EntityType.EMPRESA,
                ClassificationCategory.NAO_DETERMINADO: EntityType.NAO_DETERMINADO,
            }
            entity_type = entity_type_map[classification_result.category]

            # Stage 4: Canonicalization
            canonicalization_result = canonicalizer.canonicalize(
                CanonicalizationInput(
                    normalized_name=normalization_result.normalized,
                    entity_type=entity_type,
                    classification_confidence=classification_result.confidence,
                )
            )

        db.close()
        return True

    except Exception as e:
        logger.error(f"Error processing record: {e}")
        return False


@click.command()
@click.option("--config", default="config.yaml", help="Path to configuration file")
@click.option("--workers", default=None, type=int, help="Number of parallel workers")
@click.option("--batch-size", default=None, type=int, help="Batch size for processing")
@click.option("--max-records", default=None, type=int, help="Maximum records to process (for testing)")
def main(config: str, workers: int | None, batch_size: int | None, max_records: int | None):
    """Run the collector canonicalization pipeline"""
    # Load configuration
    cfg = Config.from_yaml(config)

    # Override with CLI arguments
    if workers is None:
        workers = cfg.processing.workers
    if batch_size is None:
        batch_size = cfg.processing.batch_size

    logger.info(f"Starting pipeline with {workers} workers, batch size {batch_size}")

    # Initialize MongoDB source
    mongo_source = MongoDBSource(
        uri=cfg.mongodb.uri,
        database=cfg.mongodb.database,
        collection=cfg.mongodb.collection,
        filter_query=cfg.mongodb.filter,
    )

    # Get total count
    total_count = mongo_source.get_total_count()
    if max_records:
        total_count = min(total_count, max_records)

    logger.info(f"Total records to process: {total_count}")

    # Initialize local database
    db = LocalDatabase(cfg.local_db.path)

    # Process records
    start_time = time.time()
    processed_count = 0

    with tqdm(total=total_count, desc="Processing records") as pbar:
        for batch in mongo_source.stream_records(batch_size=batch_size):
            if max_records and processed_count >= max_records:
                break

            # Limit batch if max_records specified
            if max_records:
                batch = batch[: max_records - processed_count]

            # Process batch in parallel
            if workers > 1:
                with Pool(processes=workers) as pool:
                    args = [(record, cfg.local_db.path) for record in batch]
                    results = pool.starmap(process_single_record, args)
                    successful = sum(results)
            else:
                # Single-threaded processing
                successful = 0
                for record in batch:
                    if process_single_record(record, cfg.local_db.path):
                        successful += 1

            processed_count += len(batch)
            pbar.update(len(batch))

            # Calculate and display rate
            elapsed = time.time() - start_time
            rate = processed_count / elapsed if elapsed > 0 else 0
            pbar.set_postfix({"rate": f"{rate:.1f} rec/s"})

    elapsed_time = time.time() - start_time
    rate = processed_count / elapsed_time if elapsed_time > 0 else 0

    logger.info(f"Processing complete: {processed_count} records in {elapsed_time:.1f}s")
    logger.info(f"Processing rate: {rate:.1f} records/sec")

    # Export to CSV
    logger.info(f"Exporting to CSV: {cfg.output.csv_path}")
    db.export_to_csv(cfg.output.csv_path)

    # Get final statistics
    entity_count = len(db.get_all_entities())
    logger.info(f"Total canonical entities: {entity_count}")

    # Close connections
    db.close()
    mongo_source.close()

    # Check if performance target met
    if rate >= 213.0:
        logger.info(" Performance target met (e213 rec/sec)")
    else:
        logger.warning(f" Performance below target: {rate:.1f} rec/sec < 213 rec/sec")

    logger.info("Pipeline complete!")


if __name__ == "__main__":
    main()
