#!/usr/bin/env python3
"""
Script para validação da canonicalização de coletores

IMPORTANTE: Este script agora valida resultados contra baseline da análise completa
do dataset para detectar desvios de qualidade e conformidade com padrões esperados
descobertos no processamento de todos os registros (11M+).
"""

import sys
import os
import logging
import random
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from collections import defaultdict, Counter
import pandas as pd

# Adiciona o diretório pai ao path para importar módulos
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from config.mongodb_config import MONGODB_CONFIG, ALGORITHM_CONFIG
from src.canonicalizador_coletores import GerenciadorMongoDB
from src.services.analysis_persistence import AnalysisPersistenceService

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('../logs/validacao.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ValidadorCanonicalizacao:
    """
    Classe para validação da qualidade da canonicalização contra baseline da análise completa

    Esta classe compara resultados atuais com padrões esperados descobertos
    na análise completa do dataset para detectar desvios de qualidade.
    """

    def __init__(self, analysis_results_path: Optional[str] = None):
        """
        Inicializa o validador com integração de análise completa

        Args:
            analysis_results_path: Caminho para resultados da análise completa
        """
        self.mongo_manager = None
        self.analysis_service = AnalysisPersistenceService()

        # Carrega baseline da análise completa
        self.analysis_baseline = self._load_analysis_baseline(analysis_results_path)
        self.has_baseline = bool(self.analysis_baseline)

        self.resultados_validacao = {
            'total_coletores_analisados': 0,
            'coletores_alta_qualidade': 0,
            'coletores_qualidade_media': 0,
            'coletores_baixa_qualidade': 0,
            'casos_suspeitos': [],
            'metricas_qualidade': {},
            'recomendacoes': [],
            'baseline_comparison': {},
            'baseline_available': self.has_baseline
        }

        logger.info(f"ValidadorCanonicalizacao inicializado - Baseline: {'✓' if self.has_baseline else '✗'}")

    def _load_analysis_baseline(self, analysis_results_path: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        Carrega baseline da análise completa do dataset para validação

        Args:
            analysis_results_path: Caminho específico para análise (opcional)

        Returns:
            Dicionário com baseline da análise ou None
        """
        try:
            if analysis_results_path and Path(analysis_results_path).exists():
                logger.info(f"Carregando baseline específico: {analysis_results_path}")
                with open(analysis_results_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # Try to load latest analysis
                logger.info("Tentando carregar última análise completa como baseline...")
                latest_analysis = self.analysis_service.load_latest_analysis_results()

                if latest_analysis:
                    logger.info("Baseline da análise completa carregado para validação")
                    return latest_analysis
                else:
                    logger.warning("Baseline da análise completa não encontrado. Validação terá escopo limitado.")
                    return None

        except Exception as e:
            logger.warning(f"Erro ao carregar baseline: {e}. Validação sem baseline de análise completa.")
            return None

    def validar_canonicalizacao(self, amostra_size: int = 1000) -> Dict:
        """
        Executa validação completa da canonicalização contra baseline da análise completa

        Args:
            amostra_size: Tamanho da amostra para validação manual

        Returns:
            Dicionário com resultados da validação
        """
        logger.info("=" * 80)
        logger.info("INICIANDO VALIDAÇÃO DA CANONICALIZAÇÃO CONTRA BASELINE COMPLETO")
        logger.info("=" * 80)

        try:
            # Conecta ao MongoDB
            self.mongo_manager = GerenciadorMongoDB(
                MONGODB_CONFIG['connection_string'],
                MONGODB_CONFIG['database_name'],
                MONGODB_CONFIG['collections']
            )

            # Executa validações
            self._validar_qualidade_geral()
            self._validar_consistencia_interna()
            self._validar_casos_suspeitos()
            self._validar_amostra_manual(amostra_size)

            # Validação contra baseline da análise completa
            if self.has_baseline:
                self._validar_contra_baseline_analise()
                self._validar_distribuicao_esperada()
                self._validar_padroes_descobertos()

            self._gerar_metricas_qualidade()
            self._gerar_recomendacoes()

            logger.info("Validação concluída com sucesso")

        except Exception as e:
            logger.error(f"Erro durante validação: {e}")
            raise

        finally:
            if self.mongo_manager:
                self.mongo_manager.fechar_conexao()

        return self.resultados_validacao

    def _validar_qualidade_geral(self):
        """
        Valida qualidade geral da canonicalização
        """
        logger.info("Validando qualidade geral...")

        # Obtém estatísticas gerais
        stats = self.mongo_manager.obter_estatisticas_colecao()

        if not stats:
            logger.warning("Nenhuma estatística encontrada")
            return

        self.resultados_validacao['total_coletores_analisados'] = stats.get('total_coletores', 0)

        # Analisa distribuição de confiança
        pipeline = [
            {
                "$group": {
                    "_id": {
                        "$switch": {
                            "branches": [
                                {"case": {"$gte": ["$confianca_canonicalizacao", 0.9]}, "then": "alta"},
                                {"case": {"$gte": ["$confianca_canonicalizacao", 0.7]}, "then": "media"},
                                {"case": {"$lt": ["$confianca_canonicalizacao", 0.7]}, "then": "baixa"}
                            ],
                            "default": "indefinida"
                        }
                    },
                    "count": {"$sum": 1}
                }
            }
        ]

        distribuicao = list(self.mongo_manager.coletores.aggregate(pipeline))

        for item in distribuicao:
            qualidade = item['_id']
            count = item['count']

            if qualidade == 'alta':
                self.resultados_validacao['coletores_alta_qualidade'] = count
            elif qualidade == 'media':
                self.resultados_validacao['coletores_qualidade_media'] = count
            elif qualidade == 'baixa':
                self.resultados_validacao['coletores_baixa_qualidade'] = count

        logger.info(f"Qualidade alta: {self.resultados_validacao['coletores_alta_qualidade']}")
        logger.info(f"Qualidade média: {self.resultados_validacao['coletores_qualidade_media']}")
        logger.info(f"Qualidade baixa: {self.resultados_validacao['coletores_baixa_qualidade']}")

    def _validar_consistencia_interna(self):
        """
        Valida consistência interna dos dados
        """
        logger.info("Validando consistência interna...")

        inconsistencias = []

        # Busca coletores com variações inconsistentes
        pipeline = [
            {
                "$match": {
                    "$expr": {
                        "$ne": [
                            {"$size": "$variacoes"},
                            {"$sum": "$variacoes.frequencia"}
                        ]
                    }
                }
            },
            {"$limit": 100}
        ]

        coletores_inconsistentes = list(self.mongo_manager.coletores.aggregate(pipeline))

        for coletor in coletores_inconsistentes:
            inconsistencias.append({
                'tipo': 'frequencia_inconsistente',
                'coletor': coletor['coletor_canonico'],
                'detalhes': 'Soma das frequências não confere com número de variações'
            })

        # Busca coletores com sobrenomes muito diferentes
        for coletor in self._buscar_amostra_coletores(100):
            if self._detectar_sobrenomes_inconsistentes(coletor):
                inconsistencias.append({
                    'tipo': 'sobrenomes_inconsistentes',
                    'coletor': coletor['coletor_canonico'],
                    'detalhes': 'Variações com sobrenomes muito diferentes'
                })

        self.resultados_validacao['inconsistencias'] = inconsistencias
        logger.info(f"Inconsistências encontradas: {len(inconsistencias)}")

    def _detectar_sobrenomes_inconsistentes(self, coletor: Dict) -> bool:
        """
        Detecta se um coletor tem sobrenomes inconsistentes nas variações
        """
        sobrenomes = []

        for variacao in coletor['variacoes']:
            # Extrai possível sobrenome da variação
            forma = variacao['forma_original']

            # Diferentes padrões para extrair sobrenome
            if ',' in forma:
                sobrenome = forma.split(',')[0].strip()
            else:
                partes = forma.split()
                if partes:
                    sobrenome = partes[-1]  # Última palavra como sobrenome
                else:
                    continue

            sobrenomes.append(sobrenome.lower())

        # Verifica se há sobrenomes muito diferentes
        if len(set(sobrenomes)) > 1:
            # Usa uma heurística simples: se a primeira letra é diferente, pode ser inconsistente
            primeiras_letras = set(s[0] for s in sobrenomes if s)
            if len(primeiras_letras) > 1:
                return True

        return False

    def _validar_casos_suspeitos(self):
        """
        Identifica casos suspeitos que precisam revisão
        """
        logger.info("Identificando casos suspeitos...")

        casos_suspeitos = []

        # Coletores com muitas variações mas baixa confiança
        pipeline = [
            {
                "$match": {
                    "$and": [
                        {"$expr": {"$gte": [{"$size": "$variacoes"}, 5]}},
                        {"confianca_canonicalizacao": {"$lt": 0.8}}
                    ]
                }
            },
            {"$limit": 50}
        ]

        for coletor in self.mongo_manager.coletores.aggregate(pipeline):
            casos_suspeitos.append({
                'tipo': 'muitas_variacoes_baixa_confianca',
                'coletor': coletor['coletor_canonico'],
                'variacoes': len(coletor['variacoes']),
                'confianca': coletor['confianca_canonicalizacao'],
                'amostras': [v['forma_original'] for v in coletor['variacoes'][:3]]
            })

        # Coletores com variações muito diferentes
        for coletor in self._buscar_amostra_coletores(200):
            if self._tem_variacoes_muito_diferentes(coletor):
                casos_suspeitos.append({
                    'tipo': 'variacoes_muito_diferentes',
                    'coletor': coletor['coletor_canonico'],
                    'variacoes': len(coletor['variacoes']),
                    'amostras': [v['forma_original'] for v in coletor['variacoes'][:3]]
                })

        self.resultados_validacao['casos_suspeitos'] = casos_suspeitos
        logger.info(f"Casos suspeitos encontrados: {len(casos_suspeitos)}")

    def _tem_variacoes_muito_diferentes(self, coletor: Dict) -> bool:
        """
        Verifica se um coletor tem variações muito diferentes entre si
        """
        if len(coletor['variacoes']) < 2:
            return False

        formas = [v['forma_original'] for v in coletor['variacoes']]

        # Verifica diferença de tamanho
        tamanhos = [len(f) for f in formas]
        if max(tamanhos) - min(tamanhos) > 20:
            return True

        # Verifica se contém caracteres muito diferentes
        tem_maiuscula = any(f.isupper() for f in formas)
        tem_minuscula = any(f.islower() for f in formas)
        tem_numeros = any(any(c.isdigit() for c in f) for f in formas)

        diferenca_count = sum([tem_maiuscula, tem_minuscula, tem_numeros])
        if diferenca_count > 2:
            return True

        return False

    def _validar_amostra_manual(self, amostra_size: int):
        """
        Seleciona amostra para validação manual
        """
        logger.info(f"Selecionando amostra para validação manual ({amostra_size} casos)...")

        # Seleciona casos diversos para validação manual
        pipeline = [
            {"$sample": {"size": amostra_size}},
            {
                "$project": {
                    "coletor_canonico": 1,
                    "variacoes": {"$slice": ["$variacoes", 5]},  # Primeiras 5 variações
                    "confianca_canonicalizacao": 1,
                    "total_registros": 1
                }
            }
        ]

        amostra = list(self.mongo_manager.coletores.aggregate(pipeline))

        self.resultados_validacao['amostra_validacao_manual'] = amostra
        logger.info(f"Amostra para validação manual preparada: {len(amostra)} casos")

    def _validar_contra_baseline_analise(self):
        """
        Valida resultados atuais contra baseline da análise completa do dataset
        """
        logger.info("Validando contra baseline da análise completa...")

        if not self.has_baseline:
            return

        baseline_comparison = {}

        try:
            # Extrai métricas da análise baseline
            baseline_total = self.analysis_baseline.get('total_records', 0)
            baseline_collector_analysis = self.analysis_baseline.get('collector_analysis', {})
            baseline_quality = self.analysis_baseline.get('quality_metrics', {})

            # Obtém estatísticas atuais
            current_stats = self.mongo_manager.obter_estatisticas_colecao()
            current_processed = current_stats.get('total_registros', 0) if current_stats else 0
            current_collectors = current_stats.get('total_coletores', 0) if current_stats else 0

            # 1. Cobertura do dataset
            if baseline_total > 0:
                coverage = (current_processed / baseline_total) * 100
                baseline_comparison['dataset_coverage'] = {
                    'baseline_total': baseline_total,
                    'current_processed': current_processed,
                    'coverage_percentage': coverage,
                    'status': 'OK' if coverage >= 90 else 'WARNING' if coverage >= 70 else 'CRITICAL'
                }

            # 2. Eficiência de canonicalização
            expected_collectors = baseline_collector_analysis.get('unique_collectors_estimate', 0)
            if expected_collectors > 0:
                efficiency = (current_collectors / expected_collectors) * 100
                baseline_comparison['canonicalization_efficiency'] = {
                    'expected_collectors': expected_collectors,
                    'actual_collectors': current_collectors,
                    'efficiency_percentage': efficiency,
                    'status': 'OK' if 85 <= efficiency <= 115 else 'WARNING' if 70 <= efficiency <= 130 else 'CRITICAL'
                }

            # 3. Qualidade vs. expectativas
            expected_completeness = baseline_quality.get('completeness_score', 0.8)
            expected_consistency = baseline_quality.get('consistency_score', 0.7)
            current_confidence = current_stats.get('confianca_media', 0) if current_stats else 0

            baseline_comparison['quality_metrics'] = {
                'expected_completeness': expected_completeness,
                'expected_consistency': expected_consistency,
                'current_confidence': current_confidence,
                'quality_deviation': abs(current_confidence - expected_consistency),
                'status': 'OK' if current_confidence >= expected_consistency * 0.9 else 'WARNING'
            }

            # 4. Distribuição de kingdoms
            expected_kingdom_dist = self.analysis_baseline.get('kingdom_distribution', {})
            if expected_kingdom_dist:
                # Get current kingdom distribution from MongoDB
                pipeline = [
                    {"$unwind": "$variacoes"},
                    {"$unwind": "$variacoes.kingdom"},
                    {
                        "$group": {
                            "_id": "$variacoes.kingdom",
                            "count": {"$sum": "$variacoes.frequencia"}
                        }
                    }
                ]

                current_kingdom_dist = {}
                for result in self.mongo_manager.coletores.aggregate(pipeline):
                    if result['_id']:  # Skip empty kingdoms
                        current_kingdom_dist[result['_id']] = result['count']

                baseline_comparison['kingdom_distribution'] = {
                    'expected': expected_kingdom_dist,
                    'current': current_kingdom_dist,
                    'deviation_analysis': self._analyze_distribution_deviation(expected_kingdom_dist, current_kingdom_dist)
                }

            self.resultados_validacao['baseline_comparison'] = baseline_comparison
            logger.info("Comparação com baseline completa")

        except Exception as e:
            logger.error(f"Erro na validação contra baseline: {e}")
            self.resultados_validacao['baseline_comparison'] = {'error': str(e)}

    def _validar_distribuicao_esperada(self):
        """
        Valida se a distribuição de tipos de entidade está conforme esperado
        """
        logger.info("Validando distribuição esperada de tipos de entidade...")

        if not self.has_baseline:
            return

        try:
            pattern_analysis = self.analysis_baseline.get('pattern_analysis', {})
            expected_entity_dist = pattern_analysis.get('entity_type_distribution', {})

            if not expected_entity_dist:
                logger.warning("Distribuição esperada não encontrada na análise")
                return

            # Get current entity type distribution (approximation from collector patterns)
            # Since we don't store entity types directly, we'll analyze naming patterns
            current_entity_analysis = self._analyze_current_entity_distribution()

            distribution_validation = {
                'expected_distribution': expected_entity_dist,
                'current_approximation': current_entity_analysis,
                'validation_status': 'completed',
                'deviations': []
            }

            # Check for significant deviations
            total_expected = sum(expected_entity_dist.values())
            for entity_type, expected_count in expected_entity_dist.items():
                expected_pct = (expected_count / total_expected * 100) if total_expected > 0 else 0
                current_pct = current_entity_analysis.get(entity_type, {}).get('percentage', 0)

                if abs(expected_pct - current_pct) > 10:  # More than 10% deviation
                    distribution_validation['deviations'].append({
                        'entity_type': entity_type,
                        'expected_percentage': expected_pct,
                        'current_percentage': current_pct,
                        'deviation': abs(expected_pct - current_pct)
                    })

            self.resultados_validacao['distribution_validation'] = distribution_validation

        except Exception as e:
            logger.error(f"Erro na validação de distribuição: {e}")

    def _validar_padroes_descobertos(self):
        """
        Valida se os padrões descobertos na análise estão sendo respeitados
        """
        logger.info("Validando padrões descobertos na análise...")

        if not self.has_baseline:
            return

        try:
            pattern_analysis = self.analysis_baseline.get('pattern_analysis', {})
            validation_results = {}

            # 1. Validação de padrões de separadores
            separator_analysis = pattern_analysis.get('separator_analysis', {})
            if separator_analysis:
                common_separators = separator_analysis.get('common_separators', {})
                validation_results['separator_patterns'] = self._validate_separator_usage(common_separators)

            # 2. Validação de sobrenomes frequentes
            collector_analysis = self.analysis_baseline.get('collector_analysis', {})
            surname_freq = collector_analysis.get('surname_frequency', {})
            if surname_freq:
                validation_results['surname_patterns'] = self._validate_surname_frequencies(surname_freq)

            # 3. Validação de padrões institucionais
            institutional_analysis = pattern_analysis.get('institutional_analysis', {})
            if institutional_analysis:
                institutional_keywords = institutional_analysis.get('common_keywords', {})
                validation_results['institutional_patterns'] = self._validate_institutional_patterns(institutional_keywords)

            self.resultados_validacao['pattern_validation'] = validation_results

        except Exception as e:
            logger.error(f"Erro na validação de padrões: {e}")

    def _analyze_distribution_deviation(self, expected: Dict[str, int], current: Dict[str, int]) -> Dict[str, Any]:
        """Analisa desvio entre distribuições esperadas e atuais"""

        total_expected = sum(expected.values())
        total_current = sum(current.values())

        if total_expected == 0 or total_current == 0:
            return {'error': 'Distribuições vazias'}

        deviations = {}
        for key in set(expected.keys()) | set(current.keys()):
            exp_pct = (expected.get(key, 0) / total_expected) * 100
            cur_pct = (current.get(key, 0) / total_current) * 100
            deviation = abs(exp_pct - cur_pct)

            deviations[key] = {
                'expected_percentage': exp_pct,
                'current_percentage': cur_pct,
                'absolute_deviation': deviation,
                'status': 'OK' if deviation <= 5 else 'WARNING' if deviation <= 15 else 'CRITICAL'
            }

        return deviations

    def _analyze_current_entity_distribution(self) -> Dict[str, Any]:
        """Analisa distribuição aproximada de tipos de entidade nos resultados atuais"""

        entity_analysis = {}

        try:
            # Sample collectors to analyze patterns
            sample = list(self.mongo_manager.coletores.aggregate([{"$sample": {"size": 1000}}]))

            entity_counts = {
                'pessoa': 0,
                'conjunto_pessoas': 0,
                'grupo_pessoas': 0,
                'empresa_instituicao': 0,
                'coletor_indeterminado': 0,
                'representacao_insuficiente': 0
            }

            # Simple heuristics to classify collectors
            for collector in sample:
                canonical_name = collector.get('coletor_canonico', '')

                # Basic pattern matching (simplified)
                if any(sep in canonical_name for sep in [' & ', ' et ', ', ']):
                    entity_counts['conjunto_pessoas'] += 1
                elif any(word in canonical_name.lower() for word in ['et al', 'equipe', 'grupo']):
                    entity_counts['grupo_pessoas'] += 1
                elif any(word in canonical_name.lower() for word in ['herbario', 'museu', 'instituto', 'universidade']):
                    entity_counts['empresa_instituicao'] += 1
                elif canonical_name in ['?', 'sem coletor', 'indeterminado']:
                    entity_counts['coletor_indeterminado'] += 1
                elif len(canonical_name.split()) == 1:
                    entity_counts['representacao_insuficiente'] += 1
                else:
                    entity_counts['pessoa'] += 1

            total = sum(entity_counts.values())
            for entity_type in entity_counts:
                entity_analysis[entity_type] = {
                    'count': entity_counts[entity_type],
                    'percentage': (entity_counts[entity_type] / total * 100) if total > 0 else 0
                }

        except Exception as e:
            logger.error(f"Erro ao analisar distribuição atual: {e}")

        return entity_analysis

    def _validate_separator_usage(self, expected_separators: Dict[str, int]) -> Dict[str, Any]:
        """Valida uso de separadores conforme padrões descobertos"""

        validation = {'status': 'completed', 'findings': []}

        try:
            # Sample multi-person collectors
            pipeline = [
                {"$match": {"$or": [
                    {"coletor_canonico": {"$regex": " & "}},
                    {"coletor_canonico": {"$regex": " et "}},
                    {"coletor_canonico": {"$regex": ", "}}
                ]}},
                {"$sample": {"size": 500}}
            ]

            multi_person_collectors = list(self.mongo_manager.coletores.aggregate(pipeline))
            separator_usage = defaultdict(int)

            for collector in multi_person_collectors:
                name = collector.get('coletor_canonico', '')
                for sep in [' & ', ' et ', ', ']:
                    if sep in name:
                        separator_usage[sep] += 1

            # Compare with expected patterns
            for sep, expected_count in list(expected_separators.items())[:5]:  # Top 5
                current_usage = separator_usage.get(sep, 0)
                if current_usage == 0 and expected_count > 100:
                    validation['findings'].append(f"Separador '{sep}' esperado não encontrado nos resultados")

        except Exception as e:
            validation['error'] = str(e)

        return validation

    def _validate_surname_frequencies(self, expected_surnames: Dict[str, int]) -> Dict[str, Any]:
        """Valida frequências de sobrenomes conforme análise"""

        validation = {'status': 'completed', 'top_surnames_check': []}

        try:
            # Get top surnames from current results
            pipeline = [
                {"$project": {
                    "surname": {
                        "$arrayElemAt": [
                            {"$split": ["$sobrenome_normalizado", " "]}, 0
                        ]
                    },
                    "total_registros": 1
                }},
                {"$group": {
                    "_id": "$surname",
                    "total": {"$sum": "$total_registros"}
                }},
                {"$sort": {"total": -1}},
                {"$limit": 20}
            ]

            current_top_surnames = {
                result['_id']: result['total']
                for result in self.mongo_manager.coletores.aggregate(pipeline)
                if result['_id']
            }

            # Check if top expected surnames appear in current results
            sorted_expected = sorted(expected_surnames.items(), key=lambda x: x[1], reverse=True)

            for surname, expected_count in sorted_expected[:10]:  # Top 10
                current_count = current_top_surnames.get(surname, 0)
                validation['top_surnames_check'].append({
                    'surname': surname,
                    'expected_rank': 'high',
                    'found_in_results': current_count > 0,
                    'current_count': current_count
                })

        except Exception as e:
            validation['error'] = str(e)

        return validation

    def _validate_institutional_patterns(self, expected_keywords: Dict[str, int]) -> Dict[str, Any]:
        """Valida padrões institucionais descobertos"""

        validation = {'status': 'completed', 'institutional_presence': []}

        try:
            # Check for institutional collectors
            institutional_terms = list(expected_keywords.keys())[:10]  # Top 10

            for term in institutional_terms:
                count = self.mongo_manager.coletores.count_documents({
                    "coletor_canonico": {"$regex": term, "$options": "i"}
                })

                validation['institutional_presence'].append({
                    'keyword': term,
                    'expected_frequency': expected_keywords[term],
                    'found_in_results': count,
                    'status': 'OK' if count > 0 else 'MISSING'
                })

        except Exception as e:
            validation['error'] = str(e)

        return validation

    def _buscar_amostra_coletores(self, tamanho: int) -> List[Dict]:
        """
        Busca uma amostra aleatória de coletores
        """
        pipeline = [
            {"$sample": {"size": tamanho}}
        ]
        return list(self.mongo_manager.coletores.aggregate(pipeline))

    def _gerar_metricas_qualidade(self):
        """
        Gera métricas de qualidade da canonicalização
        """
        logger.info("Calculando métricas de qualidade...")

        total = self.resultados_validacao['total_coletores_analisados']

        if total == 0:
            logger.warning("Nenhum coletor para calcular métricas")
            return

        metricas = {
            'taxa_alta_qualidade': self.resultados_validacao['coletores_alta_qualidade'] / total,
            'taxa_qualidade_media': self.resultados_validacao['coletores_qualidade_media'] / total,
            'taxa_baixa_qualidade': self.resultados_validacao['coletores_baixa_qualidade'] / total,
            'total_casos_suspeitos': len(self.resultados_validacao['casos_suspeitos']),
            'taxa_casos_suspeitos': len(self.resultados_validacao['casos_suspeitos']) / total,
        }

        # Calcula taxa de canonicalização
        stats_mongodb = self.mongo_manager.obter_estatisticas_colecao()
        if stats_mongodb:
            total_variacoes = stats_mongodb.get('total_variacoes', 0)
            total_coletores = stats_mongodb.get('total_coletores', 0)

            if total_coletores > 0:
                metricas['taxa_canonicalizacao'] = total_variacoes / total_coletores
            else:
                metricas['taxa_canonicalizacao'] = 0

            metricas['confianca_media'] = stats_mongodb.get('confianca_media', 0)

        self.resultados_validacao['metricas_qualidade'] = metricas

        logger.info("Métricas de qualidade calculadas:")
        for metrica, valor in metricas.items():
            if 'taxa' in metrica:
                logger.info(f"  {metrica}: {valor:.3f}")
            else:
                logger.info(f"  {metrica}: {valor}")

    def _gerar_recomendacoes(self):
        """
        Gera recomendações baseadas na validação
        """
        logger.info("Gerando recomendações...")

        recomendacoes = []
        metricas = self.resultados_validacao['metricas_qualidade']

        # Recomendações baseadas na qualidade
        taxa_baixa_qualidade = metricas.get('taxa_baixa_qualidade', 0)
        if taxa_baixa_qualidade > 0.15:  # Mais de 15% com baixa qualidade
            recomendacoes.append({
                'tipo': 'ajuste_algoritmo',
                'prioridade': 'alta',
                'descricao': f'Alta taxa de baixa qualidade ({taxa_baixa_qualidade:.1%}). Considere ajustar thresholds de similaridade.',
                'parametros_sugeridos': {
                    'similarity_threshold': 0.80,
                    'confidence_threshold': 0.65
                }
            })

        # Recomendações baseadas em casos suspeitos
        taxa_casos_suspeitos = metricas.get('taxa_casos_suspeitos', 0)
        if taxa_casos_suspeitos > 0.05:  # Mais de 5% suspeitos
            recomendacoes.append({
                'tipo': 'revisao_manual',
                'prioridade': 'media',
                'descricao': f'Alta taxa de casos suspeitos ({taxa_casos_suspeitos:.1%}). Recomenda-se revisão manual.',
                'casos_para_revisar': min(100, int(len(self.resultados_validacao['casos_suspeitos'])))
            })

        # Recomendações baseadas na taxa de canonicalização
        taxa_canonicalizacao = metricas.get('taxa_canonicalizacao', 0)
        if taxa_canonicalizacao < 2.0:  # Menos de 2 variações por coletor canônico
            recomendacoes.append({
                'tipo': 'melhoria_atomizacao',
                'prioridade': 'baixa',
                'descricao': f'Baixa taxa de canonicalização ({taxa_canonicalizacao:.2f}). Verifique padrões de separação.',
                'sugestao': 'Revisar SEPARATOR_PATTERNS e adicionar novos padrões se necessário'
            })

        # Recomendações baseadas na confiança média
        confianca_media = metricas.get('confianca_media', 0)
        if confianca_media < 0.85:
            recomendacoes.append({
                'tipo': 'melhoria_algoritmo',
                'prioridade': 'media',
                'descricao': f'Confiança média baixa ({confianca_media:.3f}). Considere melhorar algoritmo de similaridade.',
                'sugestao': 'Implementar algoritmos de similaridade mais sofisticados'
            })

        self.resultados_validacao['recomendacoes'] = recomendacoes

        logger.info(f"Geradas {len(recomendacoes)} recomendações")
        for rec in recomendacoes:
            logger.info(f"  [{rec['prioridade'].upper()}] {rec['descricao']}")

    def gerar_relatorio_validacao(self, arquivo_saida: str = None) -> str:
        """
        Gera relatório detalhado da validação

        Args:
            arquivo_saida: Caminho do arquivo de saída (opcional)

        Returns:
            Texto do relatório
        """
        relatorio = []
        relatorio.append("=" * 100)
        relatorio.append("RELATÓRIO DE VALIDAÇÃO DA CANONICALIZAÇÃO DE COLETORES")
        relatorio.append("=" * 100)
        relatorio.append(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        relatorio.append("")

        # Resumo geral
        relatorio.append("RESUMO GERAL")
        relatorio.append("-" * 50)
        relatorio.append(f"Total de coletores analisados: {self.resultados_validacao['total_coletores_analisados']:,}")
        relatorio.append(f"Coletores de alta qualidade: {self.resultados_validacao['coletores_alta_qualidade']:,}")
        relatorio.append(f"Coletores de qualidade média: {self.resultados_validacao['coletores_qualidade_media']:,}")
        relatorio.append(f"Coletores de baixa qualidade: {self.resultados_validacao['coletores_baixa_qualidade']:,}")
        relatorio.append("")

        # Métricas de qualidade
        if 'metricas_qualidade' in self.resultados_validacao:
            relatorio.append("MÉTRICAS DE QUALIDADE")
            relatorio.append("-" * 50)
            metricas = self.resultados_validacao['metricas_qualidade']

            for metrica, valor in metricas.items():
                if 'taxa' in metrica:
                    relatorio.append(f"{metrica.replace('_', ' ').title()}: {valor:.1%}")
                else:
                    relatorio.append(f"{metrica.replace('_', ' ').title()}: {valor:.3f}")
            relatorio.append("")

        # Comparação com baseline da análise completa
        if self.has_baseline and 'baseline_comparison' in self.resultados_validacao:
            relatorio.append("🔍 COMPARAÇÃO COM BASELINE DA ANÁLISE COMPLETA")
            relatorio.append("=" * 60)
            baseline_comp = self.resultados_validacao['baseline_comparison']

            # Cobertura do dataset
            if 'dataset_coverage' in baseline_comp:
                cov = baseline_comp['dataset_coverage']
                relatorio.append("📊 COBERTURA DO DATASET")
                relatorio.append(f"   Total na análise completa: {cov['baseline_total']:,}")
                relatorio.append(f"   Processados agora: {cov['current_processed']:,}")
                relatorio.append(f"   Cobertura: {cov['coverage_percentage']:.1f}% [{cov['status']}]")
                relatorio.append("")

            # Eficiência de canonicalização
            if 'canonicalization_efficiency' in baseline_comp:
                eff = baseline_comp['canonicalization_efficiency']
                relatorio.append("⚡ EFICIÊNCIA DE CANONICALIZAÇÃO")
                relatorio.append(f"   Coletores únicos esperados: {eff['expected_collectors']:,}")
                relatorio.append(f"   Coletores canônicos criados: {eff['actual_collectors']:,}")
                relatorio.append(f"   Eficiência: {eff['efficiency_percentage']:.1f}% [{eff['status']}]")
                relatorio.append("")

            # Qualidade vs. expectativas
            if 'quality_metrics' in baseline_comp:
                qual = baseline_comp['quality_metrics']
                relatorio.append("✅ QUALIDADE VS. EXPECTATIVAS")
                relatorio.append(f"   Completude esperada: {qual['expected_completeness']:.1%}")
                relatorio.append(f"   Consistência esperada: {qual['expected_consistency']:.1%}")
                relatorio.append(f"   Confiança atual: {qual['current_confidence']:.1%}")
                relatorio.append(f"   Status: [{qual['status']}]")
                relatorio.append("")

        # Validação de padrões descobertos
        if 'pattern_validation' in self.resultados_validacao:
            relatorio.append("🔍 VALIDAÇÃO DE PADRÕES DESCOBERTOS")
            relatorio.append("-" * 50)
            pattern_val = self.resultados_validacao['pattern_validation']

            if 'separator_patterns' in pattern_val:
                sep_val = pattern_val['separator_patterns']
                relatorio.append("Validação de separadores:")
                if 'findings' in sep_val and sep_val['findings']:
                    for finding in sep_val['findings'][:3]:
                        relatorio.append(f"   ⚠️  {finding}")
                else:
                    relatorio.append("   ✅ Separadores conforme esperado")

            if 'surname_patterns' in pattern_val:
                sur_val = pattern_val['surname_patterns']
                relatorio.append("Validação de sobrenomes:")
                if 'top_surnames_check' in sur_val:
                    found_count = sum(1 for check in sur_val['top_surnames_check'] if check['found_in_results'])
                    total_count = len(sur_val['top_surnames_check'])
                    relatorio.append(f"   📈 Top sobrenomes encontrados: {found_count}/{total_count}")

            relatorio.append("")

        # Casos suspeitos
        if self.resultados_validacao['casos_suspeitos']:
            relatorio.append("CASOS SUSPEITOS (PRIMEIROS 10)")
            relatorio.append("-" * 50)
            for i, caso in enumerate(self.resultados_validacao['casos_suspeitos'][:10], 1):
                relatorio.append(f"{i}. {caso['coletor']} ({caso['tipo']})")
                if 'variacoes' in caso:
                    relatorio.append(f"   Variações: {caso['variacoes']}")
                if 'confianca' in caso:
                    relatorio.append(f"   Confiança: {caso['confianca']:.3f}")
                if 'amostras' in caso:
                    relatorio.append(f"   Amostras: {', '.join(caso['amostras'])}")
                relatorio.append("")

        # Recomendações
        if self.resultados_validacao['recomendacoes']:
            relatorio.append("RECOMENDAÇÕES")
            relatorio.append("-" * 50)
            for i, rec in enumerate(self.resultados_validacao['recomendacoes'], 1):
                relatorio.append(f"{i}. [{rec['prioridade'].upper()}] {rec['descricao']}")
                if 'parametros_sugeridos' in rec:
                    relatorio.append(f"   Parâmetros sugeridos: {rec['parametros_sugeridos']}")
                if 'sugestao' in rec:
                    relatorio.append(f"   Sugestão: {rec['sugestao']}")
                relatorio.append("")

        relatorio_texto = "\n".join(relatorio)

        # Salva em arquivo se especificado
        if arquivo_saida:
            try:
                with open(arquivo_saida, 'w', encoding='utf-8') as f:
                    f.write(relatorio_texto)
                logger.info(f"Relatório de validação salvo em: {arquivo_saida}")
            except Exception as e:
                logger.error(f"Erro ao salvar relatório: {e}")

        return relatorio_texto



def main():
    """
    Função principal com integração de análise completa
    """
    import argparse

    parser = argparse.ArgumentParser(
        description='Validador de Canonicalização de Coletores com Análise Completa',
        epilog='IMPORTANTE: Para validação completa, execute analise_coletores.py primeiro'
    )
    parser.add_argument('--amostra', type=int, default=1000,
                       help='Tamanho da amostra para validação manual (padrão: 1000)')
    parser.add_argument('--analysis-results', type=str,
                       help='Caminho para arquivo JSON com resultados da análise completa')
    parser.add_argument('--no-baseline-validation', action='store_true',
                       help='Desabilita validação contra baseline da análise completa')

    args = parser.parse_args()

    try:
        print("Iniciando validação da canonicalização com baseline completo...")

        # Initialize with baseline analysis
        analysis_path = args.analysis_results if not args.no_baseline_validation else None
        validador = ValidadorCanonicalizacao(analysis_results_path=analysis_path)
        resultados = validador.validar_canonicalizacao(args.amostra)

        # Gera relatório
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Garante que o diretório reports existe
        os.makedirs("../reports", exist_ok=True)

        arquivo_relatorio = f"../reports/validacao_{timestamp}.txt"

        relatorio = validador.gerar_relatorio_validacao(arquivo_relatorio)

        # Exibe resumo
        print("\n" + "="*80)
        print("RESUMO DA VALIDAÇÃO")
        print("="*80)
        print(relatorio[:1500] + "...")
        print(f"\nRelatório completo: {arquivo_relatorio}")


        print("\nValidação concluída com sucesso!")
        return 0

    except Exception as e:
        logger.error(f"Erro durante validação: {e}")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())