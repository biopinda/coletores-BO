#!/usr/bin/env python3
"""
Script para validação da canonicalização de coletores
"""

import sys
import os
import logging
import random
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from collections import defaultdict, Counter
import pandas as pd

# Adiciona o diretório pai ao path para importar módulos
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from config.mongodb_config import MONGODB_CONFIG, ALGORITHM_CONFIG
from src.canonicalizador_coletores import GerenciadorMongoDB

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
    Classe para validação da qualidade da canonicalização
    """

    def __init__(self):
        """
        Inicializa o validador
        """
        self.mongo_manager = None
        self.resultados_validacao = {
            'total_coletores_analisados': 0,
            'coletores_alta_qualidade': 0,
            'coletores_qualidade_media': 0,
            'coletores_baixa_qualidade': 0,
            'casos_suspeitos': [],
            'metricas_qualidade': {},
            'recomendacoes': []
        }

        logger.info("ValidadorCanonicalizacao inicializado")

    def validar_canonicalizacao(self, amostra_size: int = 1000) -> Dict:
        """
        Executa validação completa da canonicalização

        Args:
            amostra_size: Tamanho da amostra para validação manual

        Returns:
            Dicionário com resultados da validação
        """
        logger.info("=" * 80)
        logger.info("INICIANDO VALIDAÇÃO DA CANONICALIZAÇÃO")
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
    Função principal
    """
    import argparse

    parser = argparse.ArgumentParser(description='Validador de Canonicalização de Coletores')
    parser.add_argument('--amostra', type=int, default=1000,
                       help='Tamanho da amostra para validação manual (padrão: 1000)')

    args = parser.parse_args()

    try:
        print("Iniciando validação da canonicalização...")

        validador = ValidadorCanonicalizacao()
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