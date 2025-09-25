#!/usr/bin/env python3
"""
Script para geração de relatórios da canonicalização de coletores

IMPORTANTE: Este script agora integra insights da análise completa do dataset
para gerar relatórios mais informativos e contextualizados com base nos
padrões descobertos no processamento de todos os registros.
"""

import sys
import os
import logging
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from collections import Counter, defaultdict
import pandas as pd

# Adiciona o diretório pai ao path para importar módulos
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from config.mongodb_config import MONGODB_CONFIG
from src.canonicalizador_coletores import GerenciadorMongoDB
from src.services.analysis_persistence import AnalysisPersistenceService

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('../logs/relatorios.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class GeradorRelatorios:
    """
    Classe para geração de relatórios da canonicalização com integração de análise completa

    Esta classe agora integra insights da análise completa do dataset para
    gerar relatórios enriquecidos com contexto e comparações baseadas nos
    padrões descobertos no processamento de todos os registros.
    """

    def __init__(self, analysis_results_path: Optional[str] = None):
        """
        Inicializa o gerador de relatórios com integração de análise completa

        Args:
            analysis_results_path: Caminho para arquivo de resultados da análise completa
        """
        self.mongo_manager = None
        self.analysis_service = AnalysisPersistenceService()

        # Carrega análise completa
        self.analysis_results = self._load_analysis_results(analysis_results_path)
        self.has_analysis = bool(self.analysis_results)

        logger.info(f"GeradorRelatorios inicializado - Análise completa: {'✓' if self.has_analysis else '✗'}")

    def _load_analysis_results(self, analysis_results_path: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        Carrega resultados da análise completa do dataset

        Args:
            analysis_results_path: Caminho específico para análise (opcional)

        Returns:
            Dicionário com resultados da análise ou None
        """
        try:
            if analysis_results_path and Path(analysis_results_path).exists():
                logger.info(f"Carregando análise específica: {analysis_results_path}")
                with open(analysis_results_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # Try to load latest analysis
                logger.info("Tentando carregar última análise completa disponível...")
                latest_analysis = self.analysis_service.load_latest_analysis_results()

                if latest_analysis:
                    logger.info("Análise completa carregada com sucesso para relatórios")
                    return latest_analysis
                else:
                    logger.warning("Nenhuma análise completa encontrada. Relatórios terão informação limitada.")
                    return None

        except Exception as e:
            logger.warning(f"Erro ao carregar análise completa: {e}. Gerando relatórios sem contexto de análise.")
            return None

    def gerar_todos_relatorios(self, diretorio_saida: str = "../reports") -> Dict[str, str]:
        """
        Gera todos os relatórios disponíveis com integração de análise completa

        Args:
            diretorio_saida: Diretório onde salvar os relatórios

        Returns:
            Dicionário com caminhos dos arquivos gerados
        """
        logger.info("=" * 80)
        logger.info("GERANDO RELATÓRIOS DA CANONICALIZAÇÃO COM ANÁLISE COMPLETA")
        logger.info("=" * 80)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        arquivos_gerados = {}

        try:
            # Conecta ao MongoDB
            self.mongo_manager = GerenciadorMongoDB(
                MONGODB_CONFIG['connection_string'],
                MONGODB_CONFIG['database_name'],
                MONGODB_CONFIG['collections']
            )

            # Garante que o diretório existe
            os.makedirs(diretorio_saida, exist_ok=True)

            # Relatório de estatísticas gerais
            arquivo_stats = os.path.join(diretorio_saida, f"estatisticas_gerais_{timestamp}.txt")
            self.gerar_relatorio_estatisticas(arquivo_stats)
            arquivos_gerados['estatisticas'] = arquivo_stats

            # Relatório de top coletores
            arquivo_top = os.path.join(diretorio_saida, f"top_coletores_{timestamp}.txt")
            self.gerar_relatorio_top_coletores(arquivo_top)
            arquivos_gerados['top_coletores'] = arquivo_top

            # Relatório de qualidade
            arquivo_qualidade = os.path.join(diretorio_saida, f"relatorio_qualidade_{timestamp}.txt")
            self.gerar_relatorio_qualidade(arquivo_qualidade)
            arquivos_gerados['qualidade'] = arquivo_qualidade


            # Relatório de variações
            arquivo_variacoes = os.path.join(diretorio_saida, f"relatorio_variacoes_{timestamp}.txt")
            self.gerar_relatorio_variacoes(arquivo_variacoes)
            arquivos_gerados['variacoes'] = arquivo_variacoes

            # Relatório de análise completa (novo - com insights)
            if self.has_analysis:
                arquivo_analise = os.path.join(diretorio_saida, f"relatorio_analise_completa_{timestamp}.txt")
                self.gerar_relatorio_analise_completa(arquivo_analise)
                arquivos_gerados['analise_completa'] = arquivo_analise

            logger.info("Todos os relatórios gerados com sucesso")

        except Exception as e:
            logger.error(f"Erro ao gerar relatórios: {e}")
            raise

        finally:
            if self.mongo_manager:
                self.mongo_manager.fechar_conexao()

        return arquivos_gerados

    def gerar_relatorio_estatisticas(self, arquivo_saida: str):
        """
        Gera relatório de estatísticas gerais com contexto de análise completa
        """
        logger.info("Gerando relatório de estatísticas gerais com análise completa...")

        stats = self.mongo_manager.obter_estatisticas_colecao()

        relatorio = []
        relatorio.append("=" * 80)
        relatorio.append("RELATÓRIO DE ESTATÍSTICAS GERAIS - CANONICALIZAÇÃO DE COLETORES")
        if self.has_analysis:
            relatorio.append("COM CONTEXTO DA ANÁLISE COMPLETA DO DATASET")
        relatorio.append("=" * 80)
        relatorio.append(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        relatorio.append("")

        # Adiciona status de integração com análise
        if self.has_analysis:
            relatorio.append("🔍 STATUS DA ANÁLISE COMPLETA")
            relatorio.append("-" * 40)
            total_records_analyzed = self.analysis_results.get('total_records', 0)
            relatorio.append(f"✅ Análise completa disponível")
            relatorio.append(f"📊 Registros analisados: {total_records_analyzed:,}")
            relatorio.append(f"📈 Contexto de padrões: Integrado")
            relatorio.append("")
        else:
            relatorio.append("⚠️  STATUS DA ANÁLISE COMPLETA")
            relatorio.append("-" * 40)
            relatorio.append("❌ Análise completa não encontrada")
            relatorio.append("📊 Relatório baseado apenas em dados processados")
            relatorio.append("💡 Recomendação: Execute analise_coletores.py primeiro")
            relatorio.append("")

        if not stats:
            relatorio.append("ERRO: Nenhuma estatística encontrada no banco de dados")
            with open(arquivo_saida, 'w', encoding='utf-8') as f:
                f.write("\n".join(relatorio))
            return

        # Estatísticas principais
        relatorio.append("ESTATÍSTICAS PRINCIPAIS")
        relatorio.append("-" * 50)
        relatorio.append(f"Total de coletores canônicos: {stats.get('total_coletores', 0):,}")
        relatorio.append(f"Total de variações: {stats.get('total_variacoes', 0):,}")
        relatorio.append(f"Total de registros processados: {stats.get('total_registros', 0):,}")
        relatorio.append(f"Precisam revisão manual: {stats.get('precisam_revisao', 0):,}")
        relatorio.append(f"Confiança média: {stats.get('confianca_media', 0):.3f}")

        if stats.get('total_coletores', 0) > 0:
            taxa_canonicalizacao = stats.get('total_variacoes', 0) / stats.get('total_coletores', 1)
            relatorio.append(f"Taxa de canonicalização: {taxa_canonicalizacao:.2f} variações/coletor")

        relatorio.append("")

        # Distribuição por confiança
        relatorio.append("DISTRIBUIÇÃO POR CONFIANÇA")
        relatorio.append("-" * 50)

        pipeline_confianca = [
            {
                "$group": {
                    "_id": {
                        "$switch": {
                            "branches": [
                                {"case": {"$gte": ["$confianca_canonicalizacao", 0.95]}, "then": "Muito Alta (>=0.95)"},
                                {"case": {"$gte": ["$confianca_canonicalizacao", 0.85]}, "then": "Alta (0.85-0.94)"},
                                {"case": {"$gte": ["$confianca_canonicalizacao", 0.70]}, "then": "Média (0.70-0.84)"},
                                {"case": {"$gte": ["$confianca_canonicalizacao", 0.50]}, "then": "Baixa (0.50-0.69)"}
                            ],
                            "default": "Muito Baixa (<0.50)"
                        }
                    },
                    "count": {"$sum": 1},
                    "registros_total": {"$sum": "$total_registros"}
                }
            },
            {"$sort": {"_id": 1}}
        ]

        distribuicao_confianca = list(self.mongo_manager.coletores.aggregate(pipeline_confianca))

        for item in distribuicao_confianca:
            categoria = item['_id']
            count = item['count']
            registros = item['registros_total']
            percentual = (count / stats.get('total_coletores', 1)) * 100

            relatorio.append(f"{categoria}: {count:,} coletores ({percentual:.1f}%) - {registros:,} registros")

        relatorio.append("")

        # Distribuição por número de variações
        relatorio.append("DISTRIBUIÇÃO POR NÚMERO DE VARIAÇÕES")
        relatorio.append("-" * 50)

        pipeline_variacoes = [
            {
                "$group": {
                    "_id": {
                        "$switch": {
                            "branches": [
                                {"case": {"$eq": [{"$size": "$variacoes"}, 1]}, "then": "1 variação"},
                                {"case": {"$lte": [{"$size": "$variacoes"}, 3]}, "then": "2-3 variações"},
                                {"case": {"$lte": [{"$size": "$variacoes"}, 5]}, "then": "4-5 variações"},
                                {"case": {"$lte": [{"$size": "$variacoes"}, 10]}, "then": "6-10 variações"},
                                {"case": {"$lte": [{"$size": "$variacoes"}, 20]}, "then": "11-20 variações"}
                            ],
                            "default": "Mais de 20 variações"
                        }
                    },
                    "count": {"$sum": 1}
                }
            },
            {"$sort": {"_id": 1}}
        ]

        distribuicao_variacoes = list(self.mongo_manager.coletores.aggregate(pipeline_variacoes))

        for item in distribuicao_variacoes:
            categoria = item['_id']
            count = item['count']
            percentual = (count / stats.get('total_coletores', 1)) * 100

            relatorio.append(f"{categoria}: {count:,} coletores ({percentual:.1f}%)")

        relatorio.append("")

        # Adiciona comparação com baseline da análise completa se disponível
        if self.has_analysis:
            relatorio.extend(self._generate_analysis_comparison(stats))

        # Salva relatório
        with open(arquivo_saida, 'w', encoding='utf-8') as f:
            f.write("\n".join(relatorio))

        logger.info(f"Relatório de estatísticas salvo: {arquivo_saida}")

    def gerar_relatorio_top_coletores(self, arquivo_saida: str, top_n: int = 100):
        """
        Gera relatório dos coletores mais frequentes
        """
        logger.info(f"Gerando relatório dos top {top_n} coletores...")

        pipeline = [
            {"$sort": {"total_registros": -1}},
            {"$limit": top_n},
            {
                "$project": {
                    "coletor_canonico": 1,
                    "total_registros": 1,
                    "num_variacoes": {"$size": "$variacoes"},
                    "confianca_canonicalizacao": 1,
                    "variacoes": {"$slice": ["$variacoes", 3]}  # Primeiras 3 variações
                }
            }
        ]

        top_coletores = list(self.mongo_manager.coletores.aggregate(pipeline))

        relatorio = []
        relatorio.append("=" * 100)
        relatorio.append(f"TOP {top_n} COLETORES MAIS FREQUENTES")
        relatorio.append("=" * 100)
        relatorio.append(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        relatorio.append("")

        for i, coletor in enumerate(top_coletores, 1):
            relatorio.append(f"{i:3d}. {coletor['coletor_canonico']}")
            relatorio.append(f"     Registros: {coletor['total_registros']:,}")
            relatorio.append(f"     Variações: {coletor['num_variacoes']}")
            relatorio.append(f"     Confiança: {coletor['confianca_canonicalizacao']:.3f}")

            if coletor['variacoes']:
                relatorio.append("     Principais variações:")
                for variacao in coletor['variacoes']:
                    relatorio.append(f"       - {variacao['forma_original']} (freq: {variacao['frequencia']})")

            relatorio.append("")

        # Salva relatório
        with open(arquivo_saida, 'w', encoding='utf-8') as f:
            f.write("\n".join(relatorio))

        logger.info(f"Relatório de top coletores salvo: {arquivo_saida}")

    def gerar_relatorio_qualidade(self, arquivo_saida: str):
        """
        Gera relatório de qualidade da canonicalização
        """
        logger.info("Gerando relatório de qualidade...")

        relatorio = []
        relatorio.append("=" * 80)
        relatorio.append("RELATÓRIO DE QUALIDADE DA CANONICALIZAÇÃO")
        relatorio.append("=" * 80)
        relatorio.append(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        relatorio.append("")

        # Casos que precisam revisão manual
        coletores_revisao = self.mongo_manager.obter_coletores_para_revisao(50)

        relatorio.append(f"CASOS PARA REVISÃO MANUAL ({len(coletores_revisao)} casos)")
        relatorio.append("-" * 60)

        for i, coletor in enumerate(coletores_revisao[:20], 1):
            relatorio.append(f"{i:2d}. {coletor['coletor_canonico']} (confiança: {coletor['confianca_canonicalizacao']:.3f})")
            relatorio.append(f"    Variações ({len(coletor['variacoes'])}):")

            for variacao in coletor['variacoes'][:3]:
                relatorio.append(f"      - {variacao['forma_original']} (freq: {variacao['frequencia']})")

            if len(coletor['variacoes']) > 3:
                relatorio.append(f"      ... e mais {len(coletor['variacoes']) - 3} variações")

            relatorio.append("")

        # Problemas de qualidade detectados
        relatorio.append("PROBLEMAS DE QUALIDADE DETECTADOS")
        relatorio.append("-" * 60)

        # Coletores com muitas variações e baixa confiança
        pipeline_problematicos = [
            {
                "$match": {
                    "$and": [
                        {"$expr": {"$gte": [{"$size": "$variacoes"}, 5]}},
                        {"confianca_canonicalizacao": {"$lt": 0.7}}
                    ]
                }
            },
            {"$sort": {"confianca_canonicalizacao": 1}},
            {"$limit": 20}
        ]

        coletores_problematicos = list(self.mongo_manager.coletores.aggregate(pipeline_problematicos))

        relatorio.append(f"Coletores com muitas variações e baixa confiança: {len(coletores_problematicos)}")
        for coletor in coletores_problematicos[:10]:
            relatorio.append(f"  - {coletor['coletor_canonico']} ({len(coletor['variacoes'])} var., conf: {coletor['confianca_canonicalizacao']:.3f})")

        relatorio.append("")

        # Salva relatório
        with open(arquivo_saida, 'w', encoding='utf-8') as f:
            f.write("\n".join(relatorio))

        logger.info(f"Relatório de qualidade salvo: {arquivo_saida}")

    def gerar_relatorio_variacoes(self, arquivo_saida: str):
        """
        Gera relatório de análise de variações
        """
        logger.info("Gerando relatório de variações...")

        relatorio = []
        relatorio.append("=" * 80)
        relatorio.append("RELATÓRIO DE ANÁLISE DE VARIAÇÕES")
        relatorio.append("=" * 80)
        relatorio.append(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        relatorio.append("")

        # Variações mais comuns
        relatorio.append("PADRÕES DE VARIAÇÕES MAIS COMUNS")
        relatorio.append("-" * 50)

        pipeline_variacoes_comuns = [
            {"$unwind": "$variacoes"},
            {
                "$group": {
                    "_id": "$variacoes.forma_original",
                    "count": {"$sum": 1},
                    "freq_total": {"$sum": "$variacoes.frequencia"}
                }
            },
            {"$sort": {"freq_total": -1}},
            {"$limit": 50}
        ]

        variacoes_comuns = list(self.mongo_manager.coletores.aggregate(pipeline_variacoes_comuns))

        relatorio.append("Top 30 formas originais mais frequentes:")
        for i, variacao in enumerate(variacoes_comuns[:30], 1):
            relatorio.append(f"{i:2d}. '{variacao['_id']}' - {variacao['freq_total']:,} registros ({variacao['count']} coletores)")

        relatorio.append("")

        # Análise de padrões
        relatorio.append("ANÁLISE DE PADRÕES DE NOMES")
        relatorio.append("-" * 50)

        padroes = {
            'maiusculo': 0,
            'com_virgula': 0,
            'com_ponto': 0,
            'com_numeros': 0,
            'muito_longo': 0,
            'muito_curto': 0
        }

        # Analisa padrões nas variações
        for variacao in variacoes_comuns:
            forma = variacao['_id']

            if forma.isupper():
                padroes['maiusculo'] += variacao['count']
            if ',' in forma:
                padroes['com_virgula'] += variacao['count']
            if '.' in forma:
                padroes['com_ponto'] += variacao['count']
            if any(c.isdigit() for c in forma):
                padroes['com_numeros'] += variacao['count']
            if len(forma) > 50:
                padroes['muito_longo'] += variacao['count']
            if len(forma) < 5:
                padroes['muito_curto'] += variacao['count']

        total_analisado = sum(v['count'] for v in variacoes_comuns)

        for padrao, count in padroes.items():
            if total_analisado > 0:
                percentual = (count / total_analisado) * 100
                relatorio.append(f"{padrao.replace('_', ' ').title()}: {count:,} ({percentual:.1f}%)")

        relatorio.append("")

        # Salva relatório
        with open(arquivo_saida, 'w', encoding='utf-8') as f:
            f.write("\n".join(relatorio))

        logger.info(f"Relatório de variações salvo: {arquivo_saida}")

    def _generate_analysis_comparison(self, current_stats: Dict[str, Any]) -> List[str]:
        """
        Gera comparação entre resultados atuais e baseline da análise completa

        Args:
            current_stats: Estatísticas atuais do MongoDB

        Returns:
            Lista de linhas do relatório de comparação
        """
        comparison = []
        comparison.append("📊 COMPARAÇÃO COM BASELINE DA ANÁLISE COMPLETA")
        comparison.append("=" * 60)

        try:
            # Extrai métricas da análise completa
            analysis_total = self.analysis_results.get('total_records', 0)
            collector_analysis = self.analysis_results.get('collector_analysis', {})
            pattern_analysis = self.analysis_results.get('pattern_analysis', {})

            # Análise de cobertura
            current_processed = current_stats.get('total_registros', 0)
            if analysis_total > 0:
                coverage_pct = (current_processed / analysis_total) * 100
                comparison.append(f"📈 COBERTURA DO PROCESSAMENTO")
                comparison.append(f"   Registros na análise completa: {analysis_total:,}")
                comparison.append(f"   Registros processados agora: {current_processed:,}")
                comparison.append(f"   Cobertura: {coverage_pct:.1f}%")
                comparison.append("")

            # Análise de eficiência de canonicalização
            expected_unique = collector_analysis.get('unique_collectors_estimate', 0)
            current_unique = current_stats.get('total_coletores', 0)

            if expected_unique > 0:
                comparison.append(f"🎯 EFICIÊNCIA DE CANONICALIZAÇÃO")
                comparison.append(f"   Coletores únicos esperados (análise): {expected_unique:,}")
                comparison.append(f"   Coletores canônicos criados: {current_unique:,}")

                efficiency = (current_unique / expected_unique) * 100
                if efficiency <= 110:  # Within reasonable range
                    comparison.append(f"   Eficiência: {efficiency:.1f}% ✅")
                else:
                    comparison.append(f"   Eficiência: {efficiency:.1f}% ⚠️ (pode indicar sub-canonicalização)")
                comparison.append("")

            # Análise de qualidade baseada em padrões descobertos
            quality_metrics = self.analysis_results.get('quality_metrics', {})
            if quality_metrics:
                comparison.append(f"🔍 QUALIDADE VS. EXPECTATIVAS DA ANÁLISE")

                expected_completeness = quality_metrics.get('completeness_score', 0) * 100
                expected_consistency = quality_metrics.get('consistency_score', 0) * 100

                current_confidence = current_stats.get('confianca_media', 0) * 100

                comparison.append(f"   Completude esperada: {expected_completeness:.1f}%")
                comparison.append(f"   Consistência esperada: {expected_consistency:.1f}%")
                comparison.append(f"   Confiança média atual: {current_confidence:.1f}%")

                if current_confidence >= expected_consistency * 0.9:
                    comparison.append(f"   Status qualidade: ✅ Dentro do esperado")
                else:
                    comparison.append(f"   Status qualidade: ⚠️ Abaixo do esperado")
                comparison.append("")

        except Exception as e:
            comparison.append(f"❌ Erro na comparação: {e}")
            comparison.append("")

        return comparison

    def gerar_relatorio_analise_completa(self, arquivo_saida: str):
        """
        Gera relatório abrangente com insights da análise completa do dataset
        """
        if not self.has_analysis:
            logger.warning("Análise completa não disponível para relatório detalhado")
            return

        logger.info("Gerando relatório de análise completa com insights do dataset...")

        relatorio = []
        relatorio.append("=" * 90)
        relatorio.append("RELATÓRIO COMPLETO: INSIGHTS DA ANÁLISE DO DATASET INTEGRAL")
        relatorio.append("=" * 90)
        relatorio.append(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        relatorio.append("")

        try:
            # Seção 1: Visão Geral da Análise
            relatorio.append("📋 VISÃO GERAL DA ANÁLISE COMPLETA")
            relatorio.append("-" * 50)

            total_analyzed = self.analysis_results.get('total_records', 0)
            relatorio.append(f"Total de registros analisados: {total_analyzed:,}")

            kingdom_dist = self.analysis_results.get('kingdom_distribution', {})
            for kingdom, count in kingdom_dist.items():
                pct = (count / total_analyzed * 100) if total_analyzed > 0 else 0
                relatorio.append(f"  {kingdom}: {count:,} ({pct:.1f}%)")

            relatorio.append("")

            # Seção 2: Padrões Descobertos
            pattern_analysis = self.analysis_results.get('pattern_analysis', {})
            if pattern_analysis:
                relatorio.append("🔍 PADRÕES DESCOBERTOS NO DATASET")
                relatorio.append("-" * 50)

                # Padrões de entidade
                entity_dist = pattern_analysis.get('entity_type_distribution', {})
                if entity_dist:
                    relatorio.append("Distribuição por tipo de entidade:")
                    for entity_type, count in entity_dist.items():
                        pct = (count / total_analyzed * 100) if total_analyzed > 0 else 0
                        relatorio.append(f"  {entity_type}: {count:,} ({pct:.1f}%)")

                # Padrões de separadores
                separator_analysis = pattern_analysis.get('separator_analysis', {})
                if separator_analysis:
                    relatorio.append("")
                    relatorio.append("Separadores mais comuns:")
                    common_seps = separator_analysis.get('common_separators', {})
                    for sep, count in list(common_seps.items())[:10]:
                        relatorio.append(f"  '{sep}': {count:,} ocorrências")

                relatorio.append("")

            # Seção 3: Análise de Coletores
            collector_analysis = self.analysis_results.get('collector_analysis', {})
            if collector_analysis:
                relatorio.append("👥 ANÁLISE DE COLETORES")
                relatorio.append("-" * 50)

                unique_estimate = collector_analysis.get('unique_collectors_estimate', 0)
                relatorio.append(f"Estimativa de coletores únicos: {unique_estimate:,}")

                # Nomes de coletores mais frequentes
                name_stats = collector_analysis.get('name_statistics', {})
                if name_stats:
                    avg_length = name_stats.get('average_length', 0)
                    relatorio.append(f"Comprimento médio dos nomes: {avg_length:.1f} caracteres")

                # Top sobrenomes
                surname_freq = collector_analysis.get('surname_frequency', {})
                if surname_freq:
                    relatorio.append("")
                    relatorio.append("Top 15 sobrenomes mais frequentes:")
                    sorted_surnames = sorted(surname_freq.items(), key=lambda x: x[1], reverse=True)
                    for i, (surname, count) in enumerate(sorted_surnames[:15], 1):
                        pct = (count / total_analyzed * 100) if total_analyzed > 0 else 0
                        relatorio.append(f"  {i:2d}. {surname}: {count:,} ({pct:.2f}%)")

                relatorio.append("")

            # Seção 4: Métricas de Qualidade
            quality_metrics = self.analysis_results.get('quality_metrics', {})
            if quality_metrics:
                relatorio.append("✅ MÉTRICAS DE QUALIDADE DO DATASET")
                relatorio.append("-" * 50)

                completeness = quality_metrics.get('completeness_score', 0) * 100
                consistency = quality_metrics.get('consistency_score', 0) * 100
                anomalies = quality_metrics.get('anomaly_indicators', [])

                relatorio.append(f"Score de completude: {completeness:.1f}%")
                relatorio.append(f"Score de consistência: {consistency:.1f}%")
                relatorio.append(f"Anomalias detectadas: {len(anomalies)}")

                if anomalies:
                    relatorio.append("")
                    relatorio.append("Principais indicadores de anomalia:")
                    for anomaly in anomalies[:10]:
                        relatorio.append(f"  • {anomaly}")

                relatorio.append("")

            # Seção 5: Recomendações Baseadas na Análise
            relatorio.append("💡 RECOMENDAÇÕES BASEADAS NA ANÁLISE")
            relatorio.append("-" * 50)

            relatorio.append("Com base na análise completa do dataset:")
            relatorio.append("")

            # Recomendações específicas baseadas nos dados
            if kingdom_dist.get('Plantae', 0) > kingdom_dist.get('Animalia', 0):
                relatorio.append("• Dataset com predominância de dados botânicos - configurações")
                relatorio.append("  de canonicalização podem ser otimizadas para este contexto")
            else:
                relatorio.append("• Dataset balanceado ou com predominância zoológica")

            if entity_dist.get('pessoa', 0) > total_analyzed * 0.6:
                relatorio.append("• Alta proporção de coletores individuais - algoritmos de")
                relatorio.append("  similaridade de nomes podem ser priorizados")

            if len(anomalies) > total_analyzed * 0.05:
                relatorio.append("• Alta taxa de anomalias detectada - recomenda-se revisão")
                relatorio.append("  manual dos casos mais críticos")

            relatorio.append("")
            relatorio.append("🔧 Para otimizar o processamento:")
            relatorio.append("• Use os thresholds descobertos na análise")
            relatorio.append("• Priorize revisão manual dos casos de baixa confiança")
            relatorio.append("• Monitore a eficiência de canonicalização vs. expectativas")

        except Exception as e:
            relatorio.append(f"❌ Erro ao processar análise completa: {e}")

        relatorio.append("")
        relatorio.append("=" * 90)

        # Salva relatório
        with open(arquivo_saida, 'w', encoding='utf-8') as f:
            f.write("\n".join(relatorio))

        logger.info(f"Relatório de análise completa salvo: {arquivo_saida}")


def main():
    """
    Função principal com integração de análise completa
    """
    import argparse

    parser = argparse.ArgumentParser(
        description='Gerador de Relatórios de Canonicalização com Análise Completa',
        epilog='IMPORTANTE: Para relatórios enriquecidos, execute analise_coletores.py primeiro'
    )
    parser.add_argument('--tipo', choices=['todos', 'estatisticas', 'top', 'qualidade', 'variacoes', 'analise_completa'],
                       default='todos', help='Tipo de relatório a gerar')
    parser.add_argument('--saida', type=str, default='../reports',
                       help='Diretório de saída (padrão: ../reports)')
    parser.add_argument('--top-n', type=int, default=100,
                       help='Número de top coletores no relatório (padrão: 100)')
    parser.add_argument('--analysis-results', type=str,
                       help='Caminho para arquivo JSON com resultados da análise completa')
    parser.add_argument('--no-analysis-integration', action='store_true',
                       help='Desabilita integração com análise completa')

    args = parser.parse_args()

    try:
        print("Iniciando geração de relatórios com análise completa...")

        # Initialize with analysis integration
        analysis_path = args.analysis_results if not args.no_analysis_integration else None
        gerador = GeradorRelatorios(analysis_results_path=analysis_path)

        if args.tipo == 'todos':
            arquivos = gerador.gerar_todos_relatorios(args.saida)
            print("\nArquivos gerados:")
            for tipo, arquivo in arquivos.items():
                print(f"  {tipo}: {arquivo}")

        else:
            # Gera relatório específico
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

            if args.tipo == 'estatisticas':
                arquivo = os.path.join(args.saida, f"estatisticas_{timestamp}.txt")
                gerador.gerar_relatorio_estatisticas(arquivo)
            elif args.tipo == 'top':
                arquivo = os.path.join(args.saida, f"top_coletores_{timestamp}.txt")
                gerador.gerar_relatorio_top_coletores(arquivo, args.top_n)
            elif args.tipo == 'qualidade':
                arquivo = os.path.join(args.saida, f"qualidade_{timestamp}.txt")
                gerador.gerar_relatorio_qualidade(arquivo)
            elif args.tipo == 'variacoes':
                arquivo = os.path.join(args.saida, f"variacoes_{timestamp}.txt")
                gerador.gerar_relatorio_variacoes(arquivo)
            elif args.tipo == 'analise_completa':
                arquivo = os.path.join(args.saida, f"analise_completa_{timestamp}.txt")
                gerador.gerar_relatorio_analise_completa(arquivo)

            print(f"Relatório gerado: {arquivo}")

        print("\nGeração de relatórios concluída!")
        return 0

    except Exception as e:
        logger.error(f"Erro ao gerar relatórios: {e}")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())