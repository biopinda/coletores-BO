#!/usr/bin/env python3
"""
Script para análise exploratória dos dados de coletores
"""

import sys
import os
import re
import logging
from collections import Counter, defaultdict
from datetime import datetime
import pandas as pd
from typing import Dict, List, Tuple
import json

# Adiciona o diretório pai ao path para importar módulos
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from config.mongodb_config import MONGODB_CONFIG, ALGORITHM_CONFIG, SEPARATOR_PATTERNS, GROUP_PATTERNS, INSTITUTION_PATTERNS
from src.canonicalizador_coletores import AtomizadorNomes, NormalizadorNome, GerenciadorMongoDB

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('../logs/analise_exploratoria.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


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
                'grupo_pessoas': 0,
                'empresa_instituicao': 0
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
                'grupo_pessoas': [],
                'empresa_instituicao': []
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
        elif re.match(r'^[A-ZÀ-Ÿ]\.?\s+[^\s]+', nome):
            return 'inicial_sobrenome'

        # Formato: apenas letras maiúsculas
        elif re.match(r'^[A-ZÀ-Ÿ\s]+$', nome) and len(nome) > 3:
            return 'maiusculo'

        # Formato: nome com múltiplas palavras
        elif len(nome.split()) > 2:
            return 'multiplas_palavras'

        # Formato: uma ou duas palavras
        elif len(nome.split()) <= 2:
            return 'nome_simples'

        # Formato: contém números
        elif re.search(r'\d', nome):
            return 'com_numeros'

        # Formato: muitos caracteres especiais
        elif len(re.findall(r'[^\w\s]', nome)) > 2:
            return 'muitos_especiais'

        else:
            return 'outro'

    def _calcular_estatisticas_finais(self):
        """
        Calcula estatísticas finais da análise
        """
        # Taxa de atomização
        if self.stats['registros_validos'] > 0:
            self.stats['taxa_atomizacao'] = self.stats['total_nomes_atomizados'] / self.stats['registros_validos']
        else:
            self.stats['taxa_atomizacao'] = 0

        # Ordena contadores
        self.stats['distribuicao_separadores'] = dict(self.stats['distribuicao_separadores'].most_common())
        self.stats['distribuicao_tamanhos'] = dict(self.stats['distribuicao_tamanhos'].most_common())
        self.stats['distribuicao_formatos'] = dict(self.stats['distribuicao_formatos'].most_common())
        self.stats['caracteres_especiais'] = dict(self.stats['caracteres_especiais'].most_common(20))

        # Converte amostras por padrão para dict normal
        self.stats['amostras_por_padrao'] = dict(self.stats['amostras_por_padrao'])

        # Calcula estatísticas de confiança por tipo
        if self.stats['confiancas_classificacao']:
            import statistics
            self.stats['confianca_classificacao_media'] = statistics.mean(self.stats['confiancas_classificacao'])
            self.stats['confianca_classificacao_mediana'] = statistics.median(self.stats['confiancas_classificacao'])

            # Calcula confiança baixa (< 0.7)
            baixa_confianca = [c for c in self.stats['confiancas_classificacao'] if c < 0.7]
            self.stats['casos_baixa_confianca_classificacao'] = len(baixa_confianca)
        else:
            self.stats['confianca_classificacao_media'] = 0
            self.stats['confianca_classificacao_mediana'] = 0
            self.stats['casos_baixa_confianca_classificacao'] = 0

    def gerar_relatorio(self, arquivo_saida: str = None) -> str:
        """
        Gera relatório detalhado da análise

        Args:
            arquivo_saida: Caminho do arquivo de saída (opcional)

        Returns:
            Texto do relatório
        """
        relatorio = []
        relatorio.append("=" * 80)
        relatorio.append("RELATÓRIO DE ANÁLISE EXPLORATÓRIA - COLETORES")
        relatorio.append("=" * 80)
        relatorio.append(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        relatorio.append("")

        # Estatísticas gerais
        relatorio.append("ESTATÍSTICAS GERAIS")
        relatorio.append("-" * 40)
        relatorio.append(f"Total de registros analisados: {self.stats['total_registros']:,}")
        relatorio.append(f"Registros válidos: {self.stats['registros_validos']:,}")
        relatorio.append(f"Registros vazios: {self.stats['registros_vazios']:,}")
        relatorio.append(f"Total de nomes atomizados: {self.stats['total_nomes_atomizados']:,}")
        relatorio.append(f"Taxa de atomização: {self.stats['taxa_atomizacao']:.2f} nomes/registro")
        relatorio.append("")

        # Distribuição por tipo de entidade
        relatorio.append("DISTRIBUIÇÃO POR TIPO DE ENTIDADE")
        relatorio.append("-" * 40)
        total_entidades = sum(self.stats['entidades_por_tipo'].values())
        for tipo, count in self.stats['entidades_por_tipo'].items():
            porcentagem = (count / total_entidades) * 100 if total_entidades > 0 else 0
            tipo_formatado = tipo.replace('_', ' ').title()
            relatorio.append(f"{tipo_formatado}: {count:,} ({porcentagem:.1f}%)")

        relatorio.append("")

        # Estatísticas de confiança
        relatorio.append("CONFIANÇA NA CLASSIFICAÇÃO")
        relatorio.append("-" * 40)
        relatorio.append(f"Confiança média: {self.stats.get('confianca_classificacao_media', 0):.3f}")
        relatorio.append(f"Confiança mediana: {self.stats.get('confianca_classificacao_mediana', 0):.3f}")
        relatorio.append(f"Casos com baixa confiança (<0.7): {self.stats.get('casos_baixa_confianca_classificacao', 0):,}")
        relatorio.append("")

        # Distribuição por tamanho
        relatorio.append("DISTRIBUIÇÃO POR TAMANHO")
        relatorio.append("-" * 40)
        for tamanho, count in self.stats['distribuicao_tamanhos'].items():
            porcentagem = (count / self.stats['registros_validos']) * 100 if self.stats['registros_validos'] > 0 else 0
            relatorio.append(f"{tamanho}: {count:,} ({porcentagem:.1f}%)")
        relatorio.append("")

        # Separadores mais comuns
        relatorio.append("SEPARADORES MAIS COMUNS")
        relatorio.append("-" * 40)
        for separador, count in list(self.stats['distribuicao_separadores'].items())[:10]:
            porcentagem = (count / self.stats['registros_validos']) * 100 if self.stats['registros_validos'] > 0 else 0
            relatorio.append(f"{separador}: {count:,} ({porcentagem:.1f}%)")
        relatorio.append("")

        # Formatos mais comuns
        relatorio.append("FORMATOS DE NOMES MAIS COMUNS")
        relatorio.append("-" * 40)
        for formato, count in list(self.stats['distribuicao_formatos'].items())[:10]:
            porcentagem = (count / self.stats['total_nomes_atomizados']) * 100 if self.stats['total_nomes_atomizados'] > 0 else 0
            relatorio.append(f"{formato}: {count:,} ({porcentagem:.1f}%)")
        relatorio.append("")

        # Caracteres especiais
        relatorio.append("CARACTERES ESPECIAIS MAIS COMUNS")
        relatorio.append("-" * 40)
        for char, count in list(self.stats['caracteres_especiais'].items())[:15]:
            relatorio.append(f"'{char}': {count:,}")
        relatorio.append("")

        # Exemplos por tipo de entidade
        relatorio.append("EXEMPLOS POR TIPO DE ENTIDADE")
        relatorio.append("-" * 40)

        for tipo, exemplos in self.stats['exemplos_por_tipo'].items():
            if exemplos:
                tipo_formatado = tipo.replace('_', ' ').title()
                relatorio.append(f"\n{tipo_formatado.upper()}:")
                for exemplo in exemplos[:10]:  # Máximo 10 exemplos
                    texto = exemplo['texto']
                    confianca = exemplo['confianca']
                    relatorio.append(f"  - {texto} (confiança: {confianca:.2f})")
        relatorio.append("")

        # Amostras por padrão
        relatorio.append("AMOSTRAS POR PADRÃO")
        relatorio.append("-" * 40)
        for formato, amostras in self.stats['amostras_por_padrao'].items():
            relatorio.append(f"\n{formato.upper()}:")
            for amostra in amostras[:5]:  # Apenas 5 amostras por padrão
                relatorio.append(f"  - {amostra}")
        relatorio.append("")

        # Casos problemáticos
        if self.stats['casos_problematicos']:
            relatorio.append("CASOS PROBLEMÁTICOS (PRIMEIROS 10)")
            relatorio.append("-" * 40)
            for caso in self.stats['casos_problematicos'][:10]:
                relatorio.append(f"Valor: {caso['valor']}")
                relatorio.append(f"Erro: {caso['erro']}")
                relatorio.append(f"Tipo: {caso['tipo']}")
                relatorio.append("")

        relatorio_texto = "\n".join(relatorio)

        # Salva em arquivo se especificado
        if arquivo_saida:
            try:
                with open(arquivo_saida, 'w', encoding='utf-8') as f:
                    f.write(relatorio_texto)
                logger.info(f"Relatório salvo em: {arquivo_saida}")
            except Exception as e:
                logger.error(f"Erro ao salvar relatório: {e}")

        return relatorio_texto

    def salvar_dados_json(self, arquivo_saida: str):
        """
        Salva os dados da análise em formato JSON

        Args:
            arquivo_saida: Caminho do arquivo JSON
        """
        try:
            # Prepara dados para serialização JSON
            dados_json = dict(self.stats)

            # Converte objetos datetime para string
            if 'casos_problematicos' in dados_json:
                for caso in dados_json['casos_problematicos']:
                    if 'timestamp' in caso and isinstance(caso['timestamp'], datetime):
                        caso['timestamp'] = caso['timestamp'].isoformat()

            with open(arquivo_saida, 'w', encoding='utf-8') as f:
                json.dump(dados_json, f, indent=2, ensure_ascii=False)

            logger.info(f"Dados salvos em JSON: {arquivo_saida}")

        except Exception as e:
            logger.error(f"Erro ao salvar dados JSON: {e}")


def main():
    """
    Função principal para executar a análise exploratória
    """
    print("Iniciando análise exploratória dos dados de coletores...")
    print(f"Conectando ao MongoDB: {MONGODB_CONFIG['database_name']}")

    try:
        # Conecta ao MongoDB
        with GerenciadorMongoDB(
            MONGODB_CONFIG['connection_string'],
            MONGODB_CONFIG['database_name'],
            MONGODB_CONFIG['collections']
        ) as mongo_manager:

            print("Conexão estabelecida com sucesso!")

            # Obtém amostra estratificada por kingdom
            print("Obtendo amostra estratificada por kingdom...")
            print("- 100,000 registros de Plantae")
            print("- 100,000 registros de Animalia")

            amostra_plantae = mongo_manager.obter_amostra_recordedby_por_kingdom(100000, "Plantae")
            print(f"Amostra Plantae obtida: {len(amostra_plantae):,} registros")

            amostra_animalia = mongo_manager.obter_amostra_recordedby_por_kingdom(100000, "Animalia")
            print(f"Amostra Animalia obtida: {len(amostra_animalia):,} registros")

            # Combina as amostras
            amostra = amostra_plantae + amostra_animalia
            print(f"Amostra total: {len(amostra):,} registros")

            # Executa análise
            analisador = AnalisadorColetores()
            resultados = analisador.analisar_amostra(amostra)

            # Gera relatórios
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

            # Garante que o diretório reports existe
            os.makedirs("../reports", exist_ok=True)

            # Relatório texto
            arquivo_relatorio = f"../reports/analise_exploratoria_{timestamp}.txt"
            relatorio = analisador.gerar_relatorio(arquivo_relatorio)
            print("\n" + "="*50)
            print("RESUMO DA ANÁLISE")
            print("="*50)
            print(relatorio[:2000] + "...\n[Relatório completo salvo em arquivo]")

            # Dados JSON
            arquivo_json = f"../reports/dados_analise_{timestamp}.json"
            analisador.salvar_dados_json(arquivo_json)

            print(f"\nArquivos gerados:")
            print(f"- Relatório: {arquivo_relatorio}")
            print(f"- Dados JSON: {arquivo_json}")

            print("\nAnálise exploratória concluída com sucesso!")

    except Exception as e:
        logger.error(f"Erro durante a análise: {e}")
        print(f"ERRO: {e}")
        return 1

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())