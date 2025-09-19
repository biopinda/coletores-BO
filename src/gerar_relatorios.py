#!/usr/bin/env python3
"""
Script para geração de relatórios da canonicalização de coletores
"""

import sys
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from collections import Counter, defaultdict
import json
import csv
import pandas as pd

# Adiciona o diretório pai ao path para importar módulos
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from config.mongodb_config import MONGODB_CONFIG
from src.canonicalizador_coletores import GerenciadorMongoDB

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/relatorios.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class GeradorRelatorios:
    """
    Classe para geração de relatórios da canonicalização
    """

    def __init__(self):
        """
        Inicializa o gerador de relatórios
        """
        self.mongo_manager = None
        logger.info("GeradorRelatorios inicializado")

    def gerar_todos_relatorios(self, diretorio_saida: str = "reports") -> Dict[str, str]:
        """
        Gera todos os relatórios disponíveis

        Args:
            diretorio_saida: Diretório onde salvar os relatórios

        Returns:
            Dicionário com caminhos dos arquivos gerados
        """
        logger.info("=" * 80)
        logger.info("GERANDO RELATÓRIOS DA CANONICALIZAÇÃO")
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

            # Exportação de dados em CSV
            arquivo_csv = os.path.join(diretorio_saida, f"coletores_canonicos_{timestamp}.csv")
            self.exportar_coletores_csv(arquivo_csv)
            arquivos_gerados['csv_coletores'] = arquivo_csv

            # Relatório de variações
            arquivo_variacoes = os.path.join(diretorio_saida, f"relatorio_variacoes_{timestamp}.txt")
            self.gerar_relatorio_variacoes(arquivo_variacoes)
            arquivos_gerados['variacoes'] = arquivo_variacoes

            # Dados em JSON para análises adicionais
            arquivo_json = os.path.join(diretorio_saida, f"dados_completos_{timestamp}.json")
            self.exportar_dados_json(arquivo_json)
            arquivos_gerados['json_dados'] = arquivo_json

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
        Gera relatório de estatísticas gerais
        """
        logger.info("Gerando relatório de estatísticas gerais...")

        stats = self.mongo_manager.obter_estatisticas_colecao()

        relatorio = []
        relatorio.append("=" * 80)
        relatorio.append("RELATÓRIO DE ESTATÍSTICAS GERAIS - CANONICALIZAÇÃO DE COLETORES")
        relatorio.append("=" * 80)
        relatorio.append(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
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
                                {"case": {"$gte": ["$confianca_canonicalizacao", 0.95]}, "then": "Muito Alta (≥0.95)"},
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

    def exportar_coletores_csv(self, arquivo_saida: str, limite: int = 10000):
        """
        Exporta dados dos coletores para CSV
        """
        logger.info(f"Exportando dados para CSV (limite: {limite})...")

        pipeline = [
            {"$sort": {"total_registros": -1}},
            {"$limit": limite},
            {
                "$project": {
                    "coletor_canonico": 1,
                    "sobrenome_normalizado": 1,
                    "nome_completo": 1,
                    "iniciais": 1,
                    "total_registros": 1,
                    "num_variacoes": {"$size": "$variacoes"},
                    "confianca_canonicalizacao": 1,
                    "primeira_variacao": {"$arrayElemAt": ["$variacoes.forma_original", 0]},
                    "freq_primeira_variacao": {"$arrayElemAt": ["$variacoes.frequencia", 0]},
                    "data_criacao": "$metadados.data_criacao",
                    "revisar_manualmente": "$metadados.revisar_manualmente"
                }
            }
        ]

        coletores = list(self.mongo_manager.coletores.aggregate(pipeline))

        if not coletores:
            logger.warning("Nenhum coletor encontrado para exportar")
            return

        # Prepara dados para CSV
        dados_csv = []
        for coletor in coletores:
            dados_csv.append({
                'coletor_canonico': coletor.get('coletor_canonico', ''),
                'sobrenome_normalizado': coletor.get('sobrenome_normalizado', ''),
                'nome_completo': coletor.get('nome_completo', ''),
                'iniciais': ','.join(coletor.get('iniciais', [])),
                'total_registros': coletor.get('total_registros', 0),
                'num_variacoes': coletor.get('num_variacoes', 0),
                'confianca': coletor.get('confianca_canonicalizacao', 0),
                'primeira_variacao': coletor.get('primeira_variacao', ''),
                'freq_primeira_variacao': coletor.get('freq_primeira_variacao', 0),
                'data_criacao': coletor.get('data_criacao', ''),
                'revisar_manualmente': coletor.get('revisar_manualmente', False)
            })

        # Salva CSV
        df = pd.DataFrame(dados_csv)
        df.to_csv(arquivo_saida, index=False, encoding='utf-8')

        logger.info(f"Dados exportados para CSV: {arquivo_saida} ({len(dados_csv)} registros)")

    def exportar_dados_json(self, arquivo_saida: str):
        """
        Exporta dados completos em JSON para análises adicionais
        """
        logger.info("Exportando dados completos para JSON...")

        # Estatísticas gerais
        stats = self.mongo_manager.obter_estatisticas_colecao()

        # Top coletores
        pipeline_top = [
            {"$sort": {"total_registros": -1}},
            {"$limit": 100},
            {
                "$project": {
                    "coletor_canonico": 1,
                    "total_registros": 1,
                    "confianca_canonicalizacao": 1,
                    "num_variacoes": {"$size": "$variacoes"}
                }
            }
        ]
        top_coletores = list(self.mongo_manager.coletores.aggregate(pipeline_top))

        # Casos para revisão
        casos_revisao = self.mongo_manager.obter_coletores_para_revisao(50)

        # Compila dados
        dados_completos = {
            'metadata': {
                'data_geracao': datetime.now().isoformat(),
                'banco_dados': MONGODB_CONFIG['database_name'],
                'colecao': MONGODB_CONFIG['collections']['coletores']
            },
            'estatisticas_gerais': stats,
            'top_coletores': top_coletores,
            'casos_revisao': [{
                'coletor_canonico': c['coletor_canonico'],
                'confianca': c['confianca_canonicalizacao'],
                'num_variacoes': len(c['variacoes']),
                'variacoes_amostra': [v['forma_original'] for v in c['variacoes'][:3]]
            } for c in casos_revisao]
        }

        # Salva JSON
        with open(arquivo_saida, 'w', encoding='utf-8') as f:
            json.dump(dados_completos, f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"Dados completos exportados para JSON: {arquivo_saida}")


def main():
    """
    Função principal
    """
    import argparse

    parser = argparse.ArgumentParser(description='Gerador de Relatórios de Canonicalização')
    parser.add_argument('--tipo', choices=['todos', 'estatisticas', 'top', 'qualidade', 'variacoes', 'csv'],
                       default='todos', help='Tipo de relatório a gerar')
    parser.add_argument('--saida', type=str, default='reports',
                       help='Diretório de saída (padrão: reports)')
    parser.add_argument('--top-n', type=int, default=100,
                       help='Número de top coletores no relatório (padrão: 100)')

    args = parser.parse_args()

    try:
        print("Iniciando geração de relatórios...")

        gerador = GeradorRelatorios()

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
            elif args.tipo == 'csv':
                arquivo = os.path.join(args.saida, f"coletores_{timestamp}.csv")
                gerador.exportar_coletores_csv(arquivo)

            print(f"Relatório gerado: {arquivo}")

        print("\nGeração de relatórios concluída!")
        return 0

    except Exception as e:
        logger.error(f"Erro ao gerar relatórios: {e}")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())