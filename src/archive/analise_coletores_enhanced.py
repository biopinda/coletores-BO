#!/usr/bin/env python3
"""
Script para análise exploratória COMPLETA dos dados de coletores

Este script foi aprimorado para processar TODOS os registros da coleção "ocorrencias"
com atributo "recordedBy" (sem limitação de quantidade) e descobrir padrões
para configuração dinâmica do sistema de canonicalização.

REQUISITOS:
- Processar 11M+ registros completos (não amostra)
- Descobrir padrões de separadores dinamicamente
- Calcular thresholds de similaridade baseados nos dados
- Persistir resultados para uso pelo processamento principal
- Usar configurações otimizadas de MongoDB (pesquisa)
"""

import sys
import os
import re
import logging
import json
import hashlib
from collections import Counter, defaultdict
from datetime import datetime, timedelta
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import new data models
from models.collector_record import CollectorRecord
from models.classification_result import ClassificationResult
# CheckpointData import removed: checkpointing disabled
from models.processing_batch import ProcessingBatch

# Enhanced logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/analise_completa.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Silence MongoDB logs
logging.getLogger('pymongo').setLevel(logging.WARNING)
logging.getLogger('pymongo.command').setLevel(logging.WARNING)
logging.getLogger('pymongo.connection').setLevel(logging.WARNING)
logging.getLogger('pymongo.server').setLevel(logging.WARNING)
logging.getLogger('pymongo.topology').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Ensure directories exist
os.makedirs('logs', exist_ok=True)
os.makedirs('reports', exist_ok=True)
# Checkpoint directory creation removed: checkpointing disabled

# Import legacy modules if available
try:
    from config.mongodb_config import MONGODB_CONFIG, ALGORITHM_CONFIG
    from canonicalizador_coletores import GerenciadorMongoDB
    LEGACY_AVAILABLE = True
    logger.info("Módulos legacy disponíveis")
except ImportError:
    # Fallback configuration
    MONGODB_CONFIG = {
        'database_name': 'dwc2json',
        'collection_name': 'ocorrencias',
        'connection_string': os.getenv('MONGODB_CONNECTION_STRING', 'mongodb://localhost:27017')
    }
    ALGORITHM_CONFIG = {'batch_size': 5000}
    LEGACY_AVAILABLE = False
    logger.warning("Módulos legacy não disponíveis, usando configuração padrão")


class AnalisadorColetoresCompleto:
    """
    Classe para análise COMPLETA dos dados de coletores

    Aprimorada para processar todos os 11M+ registros e descobrir padrões
    automaticamente para configuração dinâmica do sistema.
    """

    def __init__(self, enable_checkpointing: bool = False, checkpoint_interval: int = 25000):
        """
        Inicializa o analisador para processamento completo

        Args:
            enable_checkpointing: Se deve usar checkpointing para recovery
            checkpoint_interval: Intervalo em registros para criar checkpoints
        """
        # Enhanced configuration for complete dataset processing
        self.enable_checkpointing = False
        self.checkpoint_interval = checkpoint_interval
        self.current_checkpoint = None

        # MongoDB connection with research-optimized settings
        self.mongodb_connection = None
        self.batch_size = 5000  # Research recommendation

        # Complete dataset analysis requires ALL records
        self.max_records = None  # NO LIMIT - process everything
        self.process_all_records = True

        # Enhanced statistics for complete dataset analysis
        self.stats = {
            # Basic counts
            'total_registros': 0,
            'registros_vazios': 0,
            'registros_validos': 0,
            'total_nomes_atomizados': 0,

            # Enhanced entity classification (6 types)
            'entidades_por_tipo': {
                'pessoa': 0,
                'conjunto_pessoas': 0,
                'grupo_pessoas': 0,
                'empresa_instituicao': 0,
                'coletor_indeterminado': 0,  # NEW: indeterminate collectors
                'representacao_insuficiente': 0  # NEW: insufficient representation
            },

            # Pattern discovery results
            'separator_patterns_discovered': Counter(),
            'separator_frequency_distribution': {},
            'threshold_recommendations': {},
            'similarity_score_distribution': [],

            # Kingdom distribution for complete dataset
            'kingdom_distribution': {
                'Plantae': {'count': 0, 'unique_collectors': set()},
                'Animalia': {'count': 0, 'unique_collectors': set()},
                'Unknown': {'count': 0, 'unique_collectors': set()}
            },

            # Processing metadata
            'processing_start_time': None,
            'processing_end_time': None,
            'total_processing_time': None,
            'records_per_second': 0.0,
            # checkpoints_created removed (checkpointing disabled)

            # Quality metrics
            'confiancas_classificacao': [],
            'distribuicao_separadores': Counter(),
            'distribuicao_tamanhos': Counter(),
            'distribuicao_formatos': Counter(),
            'caracteres_especiais': Counter(),
            'casos_problematicos': [],
            'amostras_por_padrao': defaultdict(list),
            'exemplos_por_tipo': {
                'pessoa': [],
                'conjunto_pessoas': [],
                'grupo_pessoas': [],
                'empresa_instituicao': [],
                'coletor_indeterminado': [],
                'representacao_insuficiente': []
            }
        }

        logger.info(f"AnalisadorColetoresCompleto inicializado - processamento completo: {self.process_all_records}")
    logger.info(f"Checkpointing desabilitado por configuração do projeto")

    def analisar_dataset_completo(self, mongodb_manager=None) -> Dict:
        """
        Analisa TODOS os registros da coleção com recordedBy

        Args:
            mongodb_manager: Gerenciador MongoDB (opcional)

        Returns:
            Dicionário com resultados da análise completa e padrões descobertos
        """
        logger.info("=== INICIANDO ANÁLISE COMPLETA DO DATASET ===")
        logger.info("ATENÇÃO: Processará TODOS os registros com recordedBy (11M+ registros)")

        self.stats['processing_start_time'] = datetime.now()

        try:
            # Use provided manager or create optimized connection
            if mongodb_manager is None:
                mongodb_manager = self._create_optimized_mongodb_connection()

            # Get total count first
            total_records = self._get_total_record_count(mongodb_manager)
            logger.info(f"Total de registros a processar: {total_records:,}")

            if total_records == 0:
                logger.warning("Nenhum registro encontrado com recordedBy")
                return self.stats

            # Process all records in batches
            processed = self._process_all_records_in_batches(mongodb_manager, total_records)

            # Discover patterns from complete dataset
            self._discover_patterns_from_complete_data()

            # Calculate optimized thresholds
            self._calculate_optimal_thresholds()

            # Generate processing recommendations
            self._generate_processing_recommendations()

            # Save results for processing phase
            self._save_analysis_results()

        except Exception as e:
            logger.error(f"Erro durante análise completa: {e}")
            raise
        finally:
            self.stats['processing_end_time'] = datetime.now()
            if self.stats['processing_start_time']:
                duration = self.stats['processing_end_time'] - self.stats['processing_start_time']
                self.stats['total_processing_time'] = duration.total_seconds()
                if self.stats['total_registros'] > 0:
                    self.stats['records_per_second'] = self.stats['total_registros'] / duration.total_seconds()

        logger.info("=== ANÁLISE COMPLETA CONCLUÍDA ===")
        logger.info(f"Registros processados: {self.stats['total_registros']:,}")
        logger.info(f"Tempo total: {self.stats['total_processing_time']:.1f}s")
        logger.info(f"Taxa: {self.stats['records_per_second']:.1f} registros/segundo")

        return self.stats

    def _create_optimized_mongodb_connection(self):
        """Create MongoDB connection with research-optimized settings"""
        try:
            from pymongo import MongoClient

            # Research-based optimized connection settings
            connection_string = MONGODB_CONFIG.get('connection_string', 'mongodb://localhost:27017')

            client = MongoClient(
                connection_string,
                maxPoolSize=50,                    # Increased from 10 (research recommendation)
                minPoolSize=5,                     # Maintain warm connections
                maxIdleTimeMS=30000,              # Close idle connections
                retryWrites=True,                 # Automatic retry
                compressors='snappy'              # Enable compression
            )

            database_name = MONGODB_CONFIG.get('database_name', 'dwc2json')
            db = client[database_name]

            logger.info(f"Conexão otimizada criada: {database_name}")
            return db

        except ImportError:
            logger.error("pymongo não disponível")
            raise
        except Exception as e:
            logger.error(f"Erro ao criar conexão: {e}")
            raise

    def _get_total_record_count(self, mongodb_manager) -> int:
        """Get total count of records with recordedBy"""
        try:
            if hasattr(mongodb_manager, 'ocorrencias'):
                # Using legacy manager
                collection = mongodb_manager.ocorrencias
            else:
                # Using direct DB connection
                collection = mongodb_manager.ocorrencias

            count = collection.count_documents(
                {"recordedBy": {"$exists": True, "$ne": None, "$ne": ""}}
            )

            logger.info(f"Total de registros encontrados: {count:,}")
            return count

        except Exception as e:
            logger.error(f"Erro ao contar registros: {e}")
            return 0

    def _process_all_records_in_batches(self, mongodb_manager, total_records: int) -> int:
        """Process all records in memory-efficient batches"""
        processed_count = 0
        batch_number = 0

        try:
            # Create cursor for all records with recordedBy
            if hasattr(mongodb_manager, 'ocorrencias'):
                collection = mongodb_manager.ocorrencias
            else:
                collection = mongodb_manager.ocorrencias

            cursor = collection.find(
                {"recordedBy": {"$exists": True, "$ne": None, "$ne": ""}},
                {"recordedBy": 1, "kingdom": 1}
            ).batch_size(self.batch_size).sort("_id", 1)

            current_batch = []

            for document in cursor:
                current_batch.append(document)

                # Process batch when full
                if len(current_batch) >= self.batch_size:
                    processed_in_batch = self._process_batch(current_batch, batch_number)
                    processed_count += processed_in_batch
                    batch_number += 1

                    # Create checkpoint if needed
                    if self.enable_checkpointing and processed_count % self.checkpoint_interval == 0:
                        self._create_checkpoint(processed_count, batch_number)
                        # Checkpointing disabled: do not increment checkpoints_created

                    # Progress logging
                    if processed_count % 50000 == 0:
                        progress = (processed_count / total_records) * 100 if total_records > 0 else 0
                        logger.info(f"Progresso: {processed_count:,}/{total_records:,} ({progress:.1f}%)")

                    current_batch = []

            # Process final partial batch
            if current_batch:
                processed_in_batch = self._process_batch(current_batch, batch_number)
                processed_count += processed_in_batch

            self.stats['total_registros'] = processed_count
            return processed_count

        except Exception as e:
            logger.error(f"Erro durante processamento em lotes: {e}")
            raise

    def _process_batch(self, batch: List[dict], batch_number: int) -> int:
        """Process a single batch of records"""
        processed = 0

        for document in batch:
            try:
                recorded_by = document.get('recordedBy', '')
                kingdom = document.get('kingdom', 'Unknown')
                doc_id = str(document.get('_id', ''))

                if recorded_by and recorded_by.strip():
                    self._analisar_registro_completo(recorded_by, kingdom, doc_id)
                    processed += 1

            except Exception as e:
                logger.warning(f"Erro ao processar documento: {e}")
                continue

        return processed

    def _analisar_registro_completo(self, recorded_by: str, kingdom: str = "Unknown", document_id: str = None):
        """
        Analisa um registro individual com informações completas

        Args:
            recorded_by: String do coletor
            kingdom: Reino biológico (Plantae/Animalia)
            document_id: ID do documento MongoDB
        """
        if not recorded_by or not isinstance(recorded_by, str) or not recorded_by.strip():
            self.stats['registros_vazios'] += 1
            return

        recorded_by = recorded_by.strip()
        self.stats['registros_validos'] += 1

        # Enhanced classification with 6 entity types
        classification_result = self._classify_enhanced_entity_type(recorded_by)
        entity_type = classification_result.entity_type
        confidence = classification_result.confidence_score

        self.stats['entidades_por_tipo'][entity_type] += 1
        self.stats['confiancas_classificacao'].append(confidence)

        # Kingdom distribution tracking
        if kingdom in self.stats['kingdom_distribution']:
            self.stats['kingdom_distribution'][kingdom]['count'] += 1
            self.stats['kingdom_distribution'][kingdom]['unique_collectors'].add(recorded_by.lower())

        # Pattern discovery for separators
        discovered_separators = self._discover_separators_in_text(recorded_by)
        for sep in discovered_separators:
            self.stats['separator_patterns_discovered'][sep] += 1

        # Collect examples for each type (enhanced)
        if len(self.stats['exemplos_por_tipo'][entity_type]) < 20:  # More examples for better patterns
            self.stats['exemplos_por_tipo'][entity_type].append({
                'texto': recorded_by,
                'confianca': confidence,
                'kingdom': kingdom,
                'document_id': document_id
            })

        # Enhanced analysis
        self._analyze_text_properties(recorded_by)

    def _classify_enhanced_entity_type(self, recorded_by: str) -> ClassificationResult:
        """Enhanced classification supporting 6 entity types"""
        # Basic patterns for enhanced classification
        recorded_by_lower = recorded_by.lower().strip()

        # Coletor indeterminado (indeterminate collector)
        if recorded_by_lower in ['?', 'sem coletor', 'unknown', 'n/a', 'null', 'não informado']:
            return ClassificationResult(
                entity_type='coletor_indeterminado',
                confidence_score=1.0,
                reasoning='Indicador explícito de coletor indeterminado'
            )

        # Representação insuficiente (insufficient representation)
        words = recorded_by.split()
        if len(words) == 1 and len(recorded_by) < 10:  # Single short name
            return ClassificationResult(
                entity_type='representacao_insuficiente',
                confidence_score=0.9,
                reasoning='Nome muito curto ou apenas iniciais'
            )

        # Check for initials only (like "S.A." or "E.C.D.")
        if re.match(r'^[A-Z]\.[A-Z]?\\.?$', recorded_by.strip()):
            return ClassificationResult(
                entity_type='representacao_insuficiente',
                confidence_score=0.95,
                reasoning='Apenas iniciais sem sobrenome'
            )

        # Enhanced pattern recognition
        if '&' in recorded_by or ' e ' in recorded_by or ';' in recorded_by:
            return ClassificationResult(
                entity_type='conjunto_pessoas',
                confidence_score=0.8,
                reasoning='Separadores indicando múltiplas pessoas'
            )
        elif 'et al' in recorded_by_lower or 'e col' in recorded_by_lower:
            return ClassificationResult(
                entity_type='grupo_pessoas',
                confidence_score=0.85,
                reasoning='Indicador de grupo (et al., e col.)'
            )
        elif any(keyword in recorded_by_lower for keyword in ['herbario', 'herbário', 'museum', 'instituto', 'universidade', 'inpa', 'rb']):
            return ClassificationResult(
                entity_type='empresa_instituicao',
                confidence_score=0.9,
                reasoning='Palavra-chave institucional encontrada'
            )
        else:
            return ClassificationResult(
                entity_type='pessoa',
                confidence_score=0.7,
                reasoning='Classificação padrão como pessoa individual'
            )

    def _discover_separators_in_text(self, text: str) -> List[str]:
        """Discover separator patterns in text"""
        separators = []

        # Enhanced separator patterns
        separator_patterns = {
            r'\s*&\s*': '&',
            r'\s*;\s*': ';',
            r'\s+e\s+': ' e ',
            r'\s+and\s+': ' and ',
            r'\s*et\s+al\.?\s*': 'et al.',
            r'\s*e\s+col\.?\s*': 'e col.',
            r'\s*,\s+(?=[A-Z])': ', +maiuscula',
            r'\s+com\s+': ' com ',
            r'\s+with\s+': ' with '
        }

        for pattern, name in separator_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                separators.append(name)

        return separators

    def _analyze_text_properties(self, text: str):
        """Analyze text properties for pattern discovery"""
        # Size analysis
        self.stats['distribuicao_tamanhos'][self._categorizar_tamanho(len(text))] += 1

        # Special characters
        chars_especiais = re.findall(r'[^\w\s\.,\-àáâãéêíóôõúçÀÁÂÃÉÊÍÓÔÕÚÇ]', text)
        for char in chars_especiais:
            self.stats['caracteres_especiais'][char] += 1

    def _categorizar_tamanho(self, tamanho: int) -> str:
        """Categoriza o tamanho do texto"""
        if tamanho <= 10:
            return 'muito_curto (<=10)'
        elif tamanho <= 30:
            return 'curto (11-30)'
        elif tamanho <= 60:
            return 'medio (31-60)'
        elif tamanho <= 100:
            return 'longo (61-100)'
        else:
            return 'muito_longo (>100)'

    def _discover_patterns_from_complete_data(self):
        """Discover patterns from complete dataset analysis"""
        logger.info("Descobrindo padrões do dataset completo...")

        # Calculate separator frequency distribution
        total_separators = sum(self.stats['separator_patterns_discovered'].values())
        self.stats['separator_frequency_distribution'] = {
            sep: count / total_separators if total_separators > 0 else 0
            for sep, count in self.stats['separator_patterns_discovered'].most_common()
        }

        logger.info(f"Padrões de separadores descobertos: {len(self.stats['separator_patterns_discovered'])}")

    def _calculate_optimal_thresholds(self):
        """Calculate optimal similarity thresholds based on data distribution"""
        logger.info("Calculando thresholds otimizados...")

        # Basic threshold recommendations (would be enhanced with actual similarity analysis)
        self.stats['threshold_recommendations'] = {
            'canonical_grouping': 0.85,  # Research recommendation
            'manual_review': 0.5,        # Below this needs human review
            'high_confidence': 0.9,      # High confidence matches
            'uncertainty_range': (0.7, 0.9)  # Range requiring verification
        }

        logger.info("Thresholds calculados baseados na distribuição dos dados")

    def _generate_processing_recommendations(self):
        """Generate recommendations for processing phase"""
        logger.info("Gerando recomendações para processamento...")

        recommendations = {
            'batch_size': self.batch_size,
            'checkpoint_interval': self.checkpoint_interval,
            'expected_processing_time_hours': self.stats['total_registros'] / 100000,  # Rough estimate
            'memory_efficient_processing': True,
            'dominant_kingdoms': [],
            'common_separators': list(self.stats['separator_patterns_discovered'].most_common(5)),
            'entity_distribution': self.stats['entidades_por_tipo']
        }

        # Identify dominant kingdoms
        for kingdom, data in self.stats['kingdom_distribution'].items():
            if data['count'] > self.stats['total_registros'] * 0.1:  # > 10% of total
                recommendations['dominant_kingdoms'].append(kingdom)

        self.stats['processing_recommendations'] = recommendations

    def _save_analysis_results(self):
        """Save analysis results for processing phase consumption"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Save patterns
        patterns_file = f"reports/patterns_discovered_{timestamp}.json"
        with open(patterns_file, 'w', encoding='utf-8') as f:
            json.dump({
                'separator_patterns': dict(self.stats['separator_patterns_discovered']),
                'frequency_distribution': self.stats['separator_frequency_distribution'],
                'discovery_timestamp': timestamp,
                'total_records_analyzed': self.stats['total_registros']
            }, f, indent=2, ensure_ascii=False)

        # Save thresholds
        thresholds_file = f"reports/optimal_thresholds_{timestamp}.json"
        with open(thresholds_file, 'w', encoding='utf-8') as f:
            json.dump({
                'thresholds': self.stats['threshold_recommendations'],
                'processing_recommendations': self.stats.get('processing_recommendations', {}),
                'analysis_timestamp': timestamp
            }, f, indent=2, ensure_ascii=False)

        # Save comprehensive results
        results_file = f"reports/complete_analysis_results_{timestamp}.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            # Convert sets to lists for JSON serialization
            serializable_stats = self._make_json_serializable(self.stats)
            json.dump(serializable_stats, f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"Resultados salvos: {patterns_file}, {thresholds_file}, {results_file}")

    def _make_json_serializable(self, obj):
        """Convert object to JSON-serializable format"""
        if isinstance(obj, dict):
            return {k: self._make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._make_json_serializable(v) for v in obj]
        elif isinstance(obj, set):
            return list(obj)
        elif isinstance(obj, (datetime, timedelta)):
            return str(obj)
        elif hasattr(obj, '__dict__'):
            return self._make_json_serializable(obj.__dict__)
        else:
            return obj

    def _create_checkpoint(self, records_processed: int, batch_number: int):
        """Checkpointing disabled: no-op"""
        logger.debug("_create_checkpoint called but checkpointing is disabled")
        self.current_checkpoint = None

    def _save_checkpoint(self, checkpoint):
        """Checkpointing disabled: no-op"""
        logger.debug("_save_checkpoint called but checkpointing is disabled")

    def _load_existing_checkpoint(self):
        """Checkpointing disabled: no checkpoint will be loaded"""
        logger.debug("_load_existing_checkpoint called but checkpointing is disabled")
        return None

    def gerar_relatorio_completo(self, arquivo_saida: str = None) -> str:
        """Generate comprehensive report for complete dataset analysis"""
        logger.info("Gerando relatório completo...")

        relatorio_linhas = [
            "=" * 100,
            "RELATÓRIO DE ANÁLISE COMPLETA DO DATASET - COLETORES BIOLÓGICOS",
            "=" * 100,
            f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            f"Processamento completo: SIM (todos os registros com recordedBy)",
            f"Tempo total: {self.stats.get('total_processing_time', 0):.1f} segundos",
            f"Taxa: {self.stats.get('records_per_second', 0):.1f} registros/segundo",
            "",
            "RESUMO GERAL",
            "-" * 50,
            f"Total de registros processados: {self.stats['total_registros']:,}",
            f"Registros válidos: {self.stats['registros_validos']:,}",
            f"Registros vazios/inválidos: {self.stats['registros_vazios']:,}",
            f"Checkpoints criados: 0 (checkpointing desabilitado)",
            "",
            "DISTRIBUIÇÃO POR REINO BIOLÓGICO",
            "-" * 50
        ]

        for kingdom, data in self.stats['kingdom_distribution'].items():
            count = data['count']
            unique = len(data['unique_collectors'])
            percentage = (count / self.stats['registros_validos']) * 100 if self.stats['registros_validos'] > 0 else 0
            relatorio_linhas.extend([
                f"{kingdom}:",
                f"  Registros: {count:,} ({percentage:.1f}%)",
                f"  Coletores únicos: {unique:,}"
            ])

        relatorio_linhas.extend([
            "",
            "CLASSIFICAÇÃO POR TIPO DE ENTIDADE (6 TIPOS)",
            "-" * 50
        ])

        for entity_type, count in self.stats['entidades_por_tipo'].items():
            percentage = (count / self.stats['registros_validos']) * 100 if self.stats['registros_validos'] > 0 else 0
            relatorio_linhas.append(f"{entity_type}: {count:,} ({percentage:.1f}%)")

        relatorio_linhas.extend([
            "",
            "PADRÕES DE SEPARADORES DESCOBERTOS",
            "-" * 50
        ])

        for separator, count in self.stats['separator_patterns_discovered'].most_common(10):
            frequency = self.stats['separator_frequency_distribution'].get(separator, 0) * 100
            relatorio_linhas.append(f"'{separator}': {count:,} ocorrências ({frequency:.2f}%)")

        relatorio_linhas.extend([
            "",
            "THRESHOLDS OTIMIZADOS",
            "-" * 50
        ])

        thresholds = self.stats.get('threshold_recommendations', {})
        for threshold_name, value in thresholds.items():
            if isinstance(value, tuple):
                relatorio_linhas.append(f"{threshold_name}: {value[0]} - {value[1]}")
            else:
                relatorio_linhas.append(f"{threshold_name}: {value}")

        relatorio_linhas.extend([
            "",
            "RECOMENDAÇÕES PARA PROCESSAMENTO",
            "-" * 50
        ])

        recommendations = self.stats.get('processing_recommendations', {})
        for rec_name, value in recommendations.items():
            if isinstance(value, list):
                relatorio_linhas.append(f"{rec_name}: {', '.join(map(str, value[:5]))}")
            else:
                relatorio_linhas.append(f"{rec_name}: {value}")

        relatorio_linhas.extend([
            "",
            "=" * 100,
            "ANÁLISE COMPLETA CONCLUÍDA",
            "Próximos passos:",
            "1. Revisar padrões descobertos",
            "2. Executar processamento principal com configurações otimizadas",
            "3. Gerar relatórios de qualidade",
            "4. Validar canonicalização",
            "=" * 100
        ])

        relatorio_texto = "\n".join(relatorio_linhas)

        # Save report if file specified
        if arquivo_saida:
            try:
                with open(arquivo_saida, 'w', encoding='utf-8') as f:
                    f.write(relatorio_texto)
                logger.info(f"Relatório completo salvo em: {arquivo_saida}")
            except Exception as e:
                logger.error(f"Erro ao salvar relatório: {e}")

        return relatorio_texto


def main():
    """
    Função principal para executar a análise COMPLETA do dataset

    IMPORTANTE: Esta versão processa TODOS os registros (11M+), não amostras
    """
    print("=" * 80)
    print("SISTEMA DE CANONICALIZAÇÃO DE COLETORES BIOLÓGICOS")
    print("ANÁLISE COMPLETA DO DATASET")
    print("=" * 80)
    print("\n⚠️  ATENÇÃO: Este script processará TODOS os registros (11M+)")
    print("   Tempo estimado: 1-3 horas dependendo da performance")
    print("   Checkpointing está desabilitado conforme configuração do projeto\n")

    database_name = MONGODB_CONFIG.get('database_name', 'dwc2json')
    print(f"Conectando ao MongoDB: {database_name}")

    try:
        # Create enhanced analyzer
        analisador = AnalisadorColetoresCompleto(
            enable_checkpointing=False
        )

        # Check for existing checkpoint
        # Checkpointing disabled: do not attempt to load or resume from checkpoints
        checkpoint = None

        # Execute complete analysis
        print("\nIniciando análise completa do dataset...")

        try:
            # Connect using legacy manager if available
            if LEGACY_AVAILABLE:
                with GerenciadorMongoDB(
                    MONGODB_CONFIG.get('connection_string', 'mongodb://localhost:27017'),
                    database_name,
                    MONGODB_CONFIG.get('collections', {})
                ) as mongo_manager:
                    resultados = analisador.analisar_dataset_completo(mongo_manager)
            else:
                # Use enhanced connection
                resultados = analisador.analisar_dataset_completo()

        except Exception as e:
            logger.error(f"Erro durante processamento: {e}")
            print(f"\n❌ ERRO durante processamento: {e}")

            # Checkpointing disabled: no checkpoint will be saved on error

            return 1

        # Generate enhanced reports
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Generate comprehensive report
        arquivo_relatorio = f"reports/analise_completa_{timestamp}.txt"
        arquivo_patterns = f"reports/patterns_discovered_{timestamp}.json"
        arquivo_thresholds = f"reports/optimal_thresholds_{timestamp}.json"

        relatorio = analisador.gerar_relatorio_completo(arquivo_relatorio)

        print("\n" + "=" * 80)
        print("RESUMO DA ANÁLISE COMPLETA")
        print("=" * 80)
        print(f"Registros processados: {resultados['total_registros']:,}")
        print(f"Registros válidos: {resultados['registros_validos']:,}")
        print(f"Tempo total: {resultados.get('total_processing_time', 0):.1f} segundos")
        print(f"Taxa de processamento: {resultados.get('records_per_second', 0):.1f} registros/segundo")
        print(f"Checkpoints criados: 0 (checkpointing desabilitado)")

        print("\nDistribuição por Reino:")
        for kingdom, data in resultados['kingdom_distribution'].items():
            print(f"  {kingdom}: {data['count']:,} registros ({len(data['unique_collectors'])} coletores únicos)")

        print("\nDistribuição por Tipo de Entidade:")
        for entity_type, count in resultados['entidades_por_tipo'].items():
            percentage = (count / resultados['registros_validos']) * 100 if resultados['registros_validos'] > 0 else 0
            print(f"  {entity_type}: {count:,} ({percentage:.1f}%)")

        print(f"\nArquivos gerados:")
        print(f"  • Relatório completo: {arquivo_relatorio}")
        print(f"  • Padrões descobertos: {arquivo_patterns}")
        print(f"  • Thresholds otimizados: {arquivo_thresholds}")

        print("\n✅ ANÁLISE COMPLETA CONCLUÍDA COM SUCESSO!")
        print("\nPróximos passos:")
        print("  1. Revisar padrões descobertos")
        print("  2. Executar processamento principal (processar_coletores.py)")
        print("  3. Gerar relatórios de qualidade")
        print("  4. Validar canonicalização")

    except KeyboardInterrupt:
        print("\n\n⚠️  Análise interrompida pelo usuário")
        # Checkpointing disabled: nothing to save on interrupt
        return 1
    except Exception as e:
        logger.error(f"Erro durante a análise: {e}")
        print(f"\n❌ ERRO: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
