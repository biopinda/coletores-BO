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

# Add src to path for imports (when located in src/archive, parent.parent points to project/src)
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import new data models
from models.collector_record import CollectorRecord
from models.classification_result import ClassificationResult
# CheckpointData import removed: checkpointing disabled
from models.processing_batch import ProcessingBatch

# Import legacy modules (to be replaced gradually)
try:
    from config.mongodb_config import MONGODB_CONFIG, ALGORITHM_CONFIG, SEPARATOR_PATTERNS, GROUP_PATTERNS, INSTITUTION_PATTERNS
    from canonicalizador_coletores import AtomizadorNomes, NormalizadorNome, GerenciadorMongoDB
except ImportError:
    # Fallback configuration if config files don't exist yet
    MONGODB_CONFIG = {'database_name': 'dwc2json', 'collection_name': 'ocorrencias'}
    ALGORITHM_CONFIG = {'batch_size': 5000}
    SEPARATOR_PATTERNS = [r'\s*[&e]\s+', r'\s*;\s*', r'\s*et\s+al\.?\s*']
    GROUP_PATTERNS = []
    INSTITUTION_PATTERNS = []

# Enhanced logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/analise_completa.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Silencia logs do MongoDB (pymongo)
logging.getLogger('pymongo').setLevel(logging.WARNING)
logging.getLogger('pymongo.command').setLevel(logging.WARNING)
logging.getLogger('pymongo.connection').setLevel(logging.WARNING)
logging.getLogger('pymongo.server').setLevel(logging.WARNING)
logging.getLogger('pymongo.topology').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Ensure logs directory exists
os.makedirs('logs', exist_ok=True)
os.makedirs('reports', exist_ok=True)


class AnalisadorColetores:
    """
    Classe para análise exploratória dos dados de coletores
    """

    def __init__(self):
        """
        Inicializa o analisador
        """
        self.atomizador = AtomizadorNomes(SEPARATOR_PATTERNS, GROUP_PATTERNS, INSTITUTION_PATTERNS)
        self.normalizador = NormalizadorNome()

        # Estatísticas
        self.stats = {
            'total_registros': 0,
            'registros_vazios': 0,
            'registros_validos': 0,
            'total_nomes_atomizados': 0,
            'entidades_por_tipo': {
                'pessoa': 0,
                'conjunto_pessoas': 0,
                'grupo_pessoas': 0,
                'empresa_instituicao': 0,
                'ausencia_coletor': 0
            },
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
                'ausencia_coletor': []
            }
        }

        logger.info("AnalisadorColetores inicializado")

    def analisar_amostra(self, amostra: List[str]) -> Dict:
        """
        Analisa uma amostra de dados de recordedBy

        Args:
            amostra: Lista de valores de recordedBy

        Returns:
            Dicionário com resultados da análise
        """
        logger.info(f"Iniciando análise de {len(amostra)} registros...")

        self.stats['total_registros'] = len(amostra)

        for i, recorded_by in enumerate(amostra):
            if i % 10000 == 0:
                logger.info(f"Analisando registro {i}/{len(amostra)} ({i/len(amostra)*100:.1f}%)")

            self._analisar_registro(recorded_by)

        # Calcula estatísticas finais
        self._calcular_estatisticas_finais()

        logger.info("Análise concluída")
        return self.stats

    def _analisar_registro(self, recorded_by: str):
        """
        Analisa um registro individual
        """
        if not recorded_by or not isinstance(recorded_by, str) or not recorded_by.strip():
            self.stats['registros_vazios'] += 1
            return

        recorded_by = recorded_by.strip()
        self.stats['registros_validos'] += 1

        # Classifica o tipo de entidade
        classificacao = self.atomizador.classify_entity_type(recorded_by)
        tipo_entidade = classificacao['tipo']
        confianca = classificacao['confianca_classificacao']

        self.stats['entidades_por_tipo'][tipo_entidade] += 1
        self.stats['confiancas_classificacao'].append(confianca)

        # Coleta exemplos de cada tipo
        if len(self.stats['exemplos_por_tipo'][tipo_entidade]) < 15:
            self.stats['exemplos_por_tipo'][tipo_entidade].append({
                'texto': recorded_by,
                'confianca': confianca
            })

        # Analisa tamanho
        self.stats['distribuicao_tamanhos'][self._categorizar_tamanho(len(recorded_by))] += 1

        # Analisa separadores
        separadores_encontrados = self._detectar_separadores(recorded_by)
        for sep in separadores_encontrados:
            self.stats['distribuicao_separadores'][sep] += 1

        # Analisa caracteres especiais
        chars_especiais = re.findall(r'[^\w\s\.,\-àáâãéêíóôõúçÀÁÂÃÉÊÍÓÔÕÚÇ]', recorded_by)
        for char in chars_especiais:
            self.stats['caracteres_especiais'][char] += 1

        # Atomiza o nome
        try:
            nomes_atomizados = self.atomizador.atomizar(recorded_by)
            self.stats['total_nomes_atomizados'] += len(nomes_atomizados)

            # Analisa formato de cada nome atomizado
            for nome in nomes_atomizados:
                formato = self._detectar_formato(nome)
                self.stats['distribuicao_formatos'][formato] += 1

                # Guarda amostras para cada padrão
                if len(self.stats['amostras_por_padrao'][formato]) < 10:
                    self.stats['amostras_por_padrao'][formato].append(nome)

        except Exception as e:
            logger.warning(f"Erro ao processar '{recorded_by}': {e}")
            self.stats['casos_problematicos'].append({
                'valor': recorded_by,
                'erro': str(e),
                'tipo': 'erro_atomizacao'
            })

    def _categorizar_tamanho(self, tamanho: int) -> str:
        """
        Categoriza o tamanho do texto
        """
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

    def _detectar_separadores(self, texto: str) -> List[str]:
        """
        Detecta separadores presentes no texto
        """
        separadores_encontrados = []

        # Testa cada padrão de separador
        for i, pattern in enumerate(SEPARATOR_PATTERNS):
            if re.search(pattern, texto, re.IGNORECASE):
                # Mapeia padrão para nome legível
                nome_separador = self._mapear_separador(pattern)
                separadores_encontrados.append(nome_separador)

        return separadores_encontrados

    def _mapear_separador(self, pattern: str) -> str:
        """
        Mapeia padrão regex para nome legível
        """
        mapeamento = {
            r'\s*[&e]\s+': '& ou e',
            r'\s*and\s+': 'and',
            r'\s*;\s*': ';',
            r'\s*,\s*(?=[A-Z])': ', + maiúscula',
            r'\s*et\s+al\.?\s*': 'et al.',
            r'\s*e\s+col\.?\s*': 'e col.',
            r'\s*e\s+cols\.?\s*': 'e cols.',
            r'\s*com\s+': 'com',
            r'\s*with\s+': 'with'
        }
        return mapeamento.get(pattern, pattern)

    def _detectar_formato(self, nome: str) -> str:
        """
        Detecta o formato de um nome individual
        """
        nome = nome.strip()

        # Formato: "Sobrenome, I." ou "Sobrenome, Inicial"
        if re.match(r'^[^\s,]+,\s*[A-ZÀ-Ÿ]', nome):
            return 'sobrenome_virgula_inicial'

        # Formato: "I. Sobrenome" ou "Inicial Sobrenome"
        elif re.match(r'^[A-ZÀ-Ÿ]\.?
