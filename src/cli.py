"""CLI entry point and pipeline orchestrator"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import click
from tqdm import tqdm
import time
from pathlib import Path

from src.config import Config
from src.storage.mongodb_client import MongoDBSource
from src.storage.local_db import LocalDatabase
from src.storage.progress_tracker import ProgressTracker
from src.pipeline.classifier import Classifier
from src.pipeline.atomizer import Atomizer
from src.pipeline.normalizer import Normalizer
from src.pipeline.canonicalizer import Canonicalizer
from src.models.contracts import (
    ClassificationInput,
    AtomizationInput,
    NormalizationInput,
    CanonicalizationInput
)


@click.command()
@click.option('--config', default='config.yaml', help='Path to config YAML file')
@click.option('--max-records', default=None, type=int, help='Max records to process (for testing)')
@click.option('--continue', 'continue_processing', is_flag=True, help='Continue from last saved progress')
def run_pipeline(config: str, max_records: int = None, continue_processing: bool = False):
    """Run the plant collector canonicalization pipeline"""

    # Load configuration
    cfg = Config.from_yaml(config)

    # Initialize progress tracker with DuckDB
    progress = ProgressTracker(db_path="data/progress.duckdb")

    if continue_processing:
        total_processed = progress.get_total_processed()
        click.echo(f"Continuing from previous run (already processed: {total_processed} records)")
    else:
        click.echo("Starting fresh (resetting progress)")
        progress.reset()
    
    # Initialize components
    click.echo("Initializing pipeline components...")
    mongo_source = MongoDBSource(
        uri=cfg.mongodb.uri,
        database=cfg.mongodb.database,
        collection=cfg.mongodb.collection,
        filter_criteria=cfg.mongodb.filter
    )
    
    local_db = LocalDatabase(cfg.local_db.path)

    # Initialize classifier with NER fallback enabled (uses GPU if available)
    # Using bertimbau-ner model: fine-tuned specifically for Portuguese NER
    classifier = Classifier(use_ner_fallback=True, ner_device=None, ner_model="bertimbau-ner")  # None = auto-detect GPU
    atomizer = Atomizer()
    normalizer = Normalizer()
    canonicalizer = Canonicalizer(database=local_db)
    
    # Get total count
    total_records = max_records if max_records else mongo_source.get_total_count()
    click.echo(f"Total records to process: {total_records}")
    
    # Process records
    start_time = time.time()
    processed = 0
    skipped = 0
    batch_number = progress.get_latest_batch_number() + 1

    try:
        initial_count = progress.get_total_processed()
        with tqdm(total=total_records, desc="Processing", initial=initial_count) as pbar:
            try:
                for batch in mongo_source.stream_records(batch_size=cfg.processing.batch_size):
                    batch_processed_ids = []

                    for record in batch:
                        if max_records and processed >= max_records:
                            break

                        # Get record ID for tracking
                        record_id = str(record.get('_id', ''))

                        # Skip if already processed
                        if continue_processing and progress.is_processed(record_id):
                            skipped += 1
                            continue

                        # Extract collector field
                        collector_text = record.get('collector') or record.get('recordedBy', '')
                        if not collector_text:
                            continue

                        try:
                            # Stage 1: Classification
                            class_result = classifier.classify(ClassificationInput(text=collector_text))

                            # Stage 2: Atomization (use sanitized_text instead of original_text)
                            atom_result = atomizer.atomize(AtomizationInput(
                                text=class_result.sanitized_text,
                                category=class_result.category
                            ))

                            # Process each atomized name (or single name)
                            # Use sanitized_text instead of original collector_text to ensure numbers are removed
                            names_to_process = [n.text for n in atom_result.atomized_names] if atom_result.atomized_names else [class_result.sanitized_text]

                            for name in names_to_process:
                                # Stage 3: Normalization
                                norm_result = normalizer.normalize(NormalizationInput(original_name=name))

                                # Stage 4: Canonicalization
                                # Ensure confidence is at least 0.70 with epsilon tolerance
                                confidence = class_result.confidence
                                if confidence < 0.70:
                                    confidence = 0.70
                                elif confidence < 0.701:  # Handle floating point: 0.699999... -> 0.70
                                    confidence = 0.70
                                else:
                                    confidence = round(confidence, 2)

                                canon_result = canonicalizer.canonicalize(CanonicalizationInput(
                                    normalized_name=norm_result.normalized,
                                    original_name=name,  # Pass original format from MongoDB
                                    entityType=class_result.category.value if class_result.category.value != "ConjuntoPessoas" else "Pessoa",
                                    classification_confidence=confidence
                                ))

                                # Store in database
                                local_db.upsert_entity(canon_result.entity)

                            # Add to batch for bulk insert
                            batch_processed_ids.append(record_id)
                            processed += 1
                            pbar.update(1)

                        except Exception as e:
                            click.echo(f"Error processing record: {e}", err=True)
                            continue

                        if max_records and processed >= max_records:
                            break

                    # Batch commit processed IDs to DuckDB (much faster than individual inserts)
                    if batch_processed_ids:
                        progress.mark_batch_processed(batch_processed_ids, batch_number)
                        batch_number += 1

                    if max_records and processed >= max_records:
                        break
            except Exception as e:
                click.echo(f"\nMongoDB error (stopping): {e}", err=True)
                click.echo(f"Successfully processed {processed} records before error")
    finally:
        # Calculate metrics
        elapsed = time.time() - start_time
        rate = processed / elapsed if elapsed > 0 else 0
        total_processed_count = progress.get_total_processed()

        # Summary
        click.echo(f"\nPipeline complete!")
        click.echo(f"   Processed: {processed} records")
        if continue_processing and skipped > 0:
            click.echo(f"   Skipped (already done): {skipped} records")
        click.echo(f"   Total processed so far: {total_processed_count} records")
        click.echo(f"   Time: {elapsed:.1f}s")
        click.echo(f"   Rate: {rate:.1f} rec/sec")
        click.echo(f"   NER fallback used: {classifier.ner_fallback_count} times")

        # Cleanup
        try:
            mongo_source.close()
        except:
            pass
        try:
            local_db.close()
        except:
            pass
        try:
            progress.close()
        except:
            pass


if __name__ == '__main__':
    run_pipeline()
