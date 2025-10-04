"""CLI entry point and pipeline orchestrator"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import click
from tqdm import tqdm
import time

from src.config import Config
from src.storage.mongodb_client import MongoDBSource
from src.storage.local_db import LocalDatabase
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
def run_pipeline(config: str, max_records: int = None):
    """Run the plant collector canonicalization pipeline"""
    
    # Load configuration
    cfg = Config.from_yaml(config)
    
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
    classifier = Classifier(use_ner_fallback=True, ner_device=None)  # None = auto-detect GPU
    atomizer = Atomizer()
    normalizer = Normalizer()
    canonicalizer = Canonicalizer(local_db=local_db)
    
    # Get total count
    total_records = max_records if max_records else mongo_source.get_total_count()
    click.echo(f"Total records to process: {total_records}")
    
    # Process records
    start_time = time.time()
    processed = 0

    try:
        with tqdm(total=total_records, desc="Processing") as pbar:
            try:
                for batch in mongo_source.stream_records(batch_size=cfg.processing.batch_size):
                    for record in batch:
                        if max_records and processed >= max_records:
                            break

                        # Extract collector field
                        collector_text = record.get('collector') or record.get('recordedBy', '')
                        if not collector_text:
                            continue

                        try:
                            # Stage 1: Classification
                            class_result = classifier.classify(ClassificationInput(text=collector_text))

                            # Stage 2: Atomization
                            atom_result = atomizer.atomize(AtomizationInput(
                                text=class_result.original_text,
                                category=class_result.category
                            ))

                            # Process each atomized name (or single name)
                            names_to_process = [n.text for n in atom_result.atomized_names] if atom_result.atomized_names else [collector_text]

                            for name in names_to_process:
                                # Stage 3: Normalization
                                norm_result = normalizer.normalize(NormalizationInput(original_name=name))

                                # Stage 4: Canonicalization
                                # Round confidence to avoid floating point precision issues
                                confidence = round(class_result.confidence, 2)
                                canon_result = canonicalizer.canonicalize(CanonicalizationInput(
                                    normalized_name=norm_result.normalized,
                                    original_name=name,  # Pass original format from MongoDB
                                    entityType=class_result.category.value if class_result.category.value != "ConjuntoPessoas" else "Pessoa",
                                    classification_confidence=max(0.70, confidence)  # Ensure minimum 0.70
                                ))

                                # Store in database
                                local_db.upsert_entity(canon_result.entity)

                            processed += 1
                            pbar.update(1)

                        except Exception as e:
                            click.echo(f"Error processing record: {e}", err=True)
                            continue

                        if max_records and processed >= max_records:
                            break
            except Exception as e:
                click.echo(f"\nMongoDB error (stopping): {e}", err=True)
                click.echo(f"Successfully processed {processed} records before error")
    finally:
        # Calculate metrics
        elapsed = time.time() - start_time
        rate = processed / elapsed if elapsed > 0 else 0

        # ALWAYS export to CSV, even if there was an error
        click.echo("\nExporting to CSV...")
        try:
            local_db.export_to_csv(cfg.output.csv_path)
            click.echo(f"✓ CSV exported: {cfg.output.csv_path}")
        except Exception as e:
            click.echo(f"Error exporting CSV: {e}", err=True)

        # Summary
        click.echo(f"\n✅ Pipeline complete!")
        click.echo(f"   Processed: {processed} records")
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


if __name__ == '__main__':
    run_pipeline()
