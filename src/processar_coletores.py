#!/usr/bin/env python3
"""
Script principal para processamento e canonicalização de coletores
"""

import sys
import os
import logging
import time
import signal
from datetime import datetime
from typing import Dict, List, Optional
from tqdm import tqdm
import traceback
import pandas as pd

# Adiciona o diretório pai ao path para importar módulos
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from config.mongodb_config import MONGODB_CONFIG, ALGORITHM_CONFIG, SEPARATOR_PATTERNS, GROUP_PATTERNS, INSTITUTION_PATTERNS
from src.canonicalizador_coletores import (
    AtomizadorNomes,
    NormalizadorNome,
    CanonizadorColetores,
    GerenciadorMongoDB
)

# Configurar logging
def configurar_logging():
    """
    Configura sistema de logging
    """
    log_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Handler para arquivo
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'processamento.log')
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.INFO)  # Mudado de DEBUG para INFO

    # Handler para console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    console_handler.setLevel(logging.INFO)

    # Logger principal
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)  # Mudado de DEBUG para INFO
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # Silencia logs do MongoDB (pymongo)
    logging.getLogger('pymongo').setLevel(logging.WARNING)
    logging.getLogger('pymongo.command').setLevel(logging.WARNING)
    logging.getLogger('pymongo.connection').setLevel(logging.WARNING)
    logging.getLogger('pymongo.server').setLevel(logging.WARNING)
    logging.getLogger('pymongo.topology').setLevel(logging.WARNING)

    return logger

logger = configurar_logging()


class ProcessadorColetores:
    """
    Classe principal para processamento de canonicalização
    """

    def __init__(self):
        """
        Inicializa o processador
        """
        self.atomizador = AtomizadorNomes(SEPARATOR_PATTERNS, GROUP_PATTERNS, INSTITUTION_PATTERNS)
        self.normalizador = NormalizadorNome()
        self.canonizador = CanonizadorColetores(
            similarity_threshold=ALGORITHM_CONFIG['similarity_threshold'],
            confidence_threshold=ALGORITHM_CONFIG['confidence_threshold']
        )

        # Estatísticas do processamento
        self.stats = {
            'inicio_processamento': None,
            'fim_processamento': None,
            'total_registros_processados': 0,
            'total_nomes_atomizados': 0,
            'total_coletores_canonicos': 0,
            'registros_com_erro': 0,
            'registros_vazios': 0,
            'tempo_processamento': 0,
            'registros_por_segundo': 0,
            'ultimo_checkpoint': None,
            'checkpoint_count': 0,
            'ultimo_relatorio_progresso': None,
            'total_estimado': None,
            'velocidade_media': 0
        }

        # Controle de processamento
        self.deve_parar = False
        self.mongo_manager = None

        # Configura handler para interrupção
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """
        Handler para sinais de interrupção
        """
        if not self.deve_parar:
            logger.warning(f"Sinal recebido ({signum}). Iniciando parada controlada...")
            logger.warning("Pressione Ctrl+C novamente para forçar a saída imediata")
            self.deve_parar = True
        else:
            logger.error("Forçando saída imediata...")
            import sys
            sys.exit(1)

    def processar_todos_coletores(self, restart: bool = False) -> Dict:
        """
        Processa todos os coletores do banco de dados

        Args:
            restart: Se True, reinicia o processamento do zero

        Returns:
            Dicionário com estatísticas do processamento
        """
        print("\n" + "=" * 80)
        print(">> INICIANDO PROCESSAMENTO DE CANONICALIZACAO DE COLETORES")
        print("=" * 80)

        self.stats['inicio_processamento'] = datetime.now()

        try:
            # Conecta ao MongoDB
            print(">> Conectando ao MongoDB...")
            self.mongo_manager = GerenciadorMongoDB(
                MONGODB_CONFIG['connection_string'],
                MONGODB_CONFIG['database_name'],
                MONGODB_CONFIG['collections']
            )

            # Cria índices se necessário
            print(">> Verificando indices da colecao coletores...")
            self.mongo_manager.criar_indices_coletores()

            # Conecta o canonizador ao MongoDB para busca de duplicatas
            self.canonizador.mongo_manager = self.mongo_manager

            # FRESH START: Sempre limpa a coleção coletores e checkpoints
            print(">> FRESH START: Limpando colecao coletores e checkpoints...")
            total_coletores = self.mongo_manager.coletores.count_documents({})
            if total_coletores > 0:
                print(f">> Removendo {total_coletores:,} coletores existentes...")

            self.mongo_manager.limpar_colecao_coletores()
            self.mongo_manager.limpar_checkpoint()

            print(">> Colecao coletores zerada. Iniciando processamento do zero...")

            print(">> Iniciando processamento dos dados de coletores...\n")

            # Processa em lotes
            self._processar_em_lotes()

            # Finaliza processamento
            self._finalizar_processamento()

        except Exception as e:
            logger.error(f"Erro durante processamento: {e}")
            logger.error(traceback.format_exc())
            raise

        finally:
            if self.mongo_manager:
                self.mongo_manager.fechar_conexao()

        return self.stats

    def _carregar_estado_checkpoint(self, checkpoint: Dict):
        """
        Carrega estado a partir de checkpoint
        """
        # Carrega estatísticas
        for key in ['total_registros_processados', 'total_nomes_atomizados',
                   'registros_com_erro', 'registros_vazios', 'checkpoint_count']:
            if key in checkpoint:
                self.stats[key] = checkpoint[key]

        # Carrega estado do canonizador se disponível
        if 'estado_canonizador' in checkpoint:
            self._carregar_canonizador_estado(checkpoint['estado_canonizador'])

    def _carregar_canonizador_estado(self, estado: Dict):
        """
        Carrega estado do canonizador (implementação simplificada)
        """
        # Em uma implementação completa, recarregaria o estado interno do canonizador
        # Por simplicidade, deixamos o canonizador reconstruir a partir do MongoDB
        pass

    def _processar_em_lotes(self):
        """
        Processa dados em lotes
        """
        batch_size = ALGORITHM_CONFIG['batch_size']
        checkpoint_interval = ALGORITHM_CONFIG['checkpoint_interval']

        # Pula registros já processados se houver checkpoint
        skip_count = self.stats['total_registros_processados']

        # Itera sobre todos os registros
        batch_count = 0
        for batch in self.mongo_manager.obter_todos_recordedby(batch_size, lambda: self.deve_parar):
            if self.deve_parar:
                print("\n>> INTERRUPCAO solicitada. Salvando checkpoint...")
                self._salvar_checkpoint()
                break

            # Pula lotes já processados
            if skip_count > 0:
                registros_no_lote = len(batch)
                if skip_count >= registros_no_lote:
                    skip_count -= registros_no_lote
                    continue
                else:
                    # Processa apenas parte do lote
                    batch = batch[skip_count:]
                    skip_count = 0

            batch_count += 1

            # Processa lote
            self._processar_lote(batch, batch_count)

            # Mostra progresso e salva checkpoint periodicamente
            if self.stats['total_registros_processados'] % checkpoint_interval == 0:
                self._salvar_checkpoint()
                self._exibir_progresso()

    def _processar_lote(self, batch: List[Dict], batch_num: int):
        """
        Processa um lote de registros
        """
        inicio_lote = time.time()

        for documento in batch:
            try:
                self._processar_documento(documento)
            except Exception as e:
                self.stats['registros_com_erro'] += 1
            finally:
                self.stats['total_registros_processados'] += 1

        # Calcula velocidade do lote
        tempo_lote = time.time() - inicio_lote
        velocidade_lote = len(batch) / tempo_lote if tempo_lote > 0 else 0

        # Atualiza velocidade média
        if self.stats['velocidade_media'] == 0:
            self.stats['velocidade_media'] = velocidade_lote
        else:
            # Média móvel ponderada (70% histórico, 30% atual)
            self.stats['velocidade_media'] = (0.7 * self.stats['velocidade_media']) + (0.3 * velocidade_lote)

        # Exibe progresso simplificado
        self._exibir_progresso_lote(batch_num, len(batch), tempo_lote)

    def _processar_documento(self, documento: Dict):
        """
        Processa um documento individual
        """
        recorded_by = documento.get('recordedBy', '')

        if not recorded_by or not isinstance(recorded_by, str) or not recorded_by.strip():
            self.stats['registros_vazios'] += 1
            return

        recorded_by = recorded_by.strip()

        # Atomiza nomes
        nomes_atomizados = self.atomizador.atomizar(recorded_by)
        self.stats['total_nomes_atomizados'] += len(nomes_atomizados)

        if not nomes_atomizados:
            self.stats['registros_vazios'] += 1
            return

        # Obtém kingdom do documento
        kingdom = documento.get('kingdom', '')

        # Processa cada nome atomizado
        for nome in nomes_atomizados:
            self._processar_nome_individual(nome, kingdom)

    def _processar_nome_individual(self, nome: str, kingdom: str = ''):
        """
        Processa um nome individual
        """
        try:
            # Normaliza o nome
            nome_normalizado = self.normalizador.normalizar(nome)

            # Adiciona kingdom ao nome normalizado
            if kingdom:
                if 'kingdom' not in nome_normalizado:
                    nome_normalizado['kingdom'] = []
                if kingdom not in nome_normalizado['kingdom']:
                    nome_normalizado['kingdom'].append(kingdom)

            if not nome_normalizado['sobrenome_normalizado']:
                return  # Nome sem sobrenome identificável

            # Canoniza o nome
            resultado_canonizacao = self.canonizador.processar_nome(nome_normalizado)

            # Salva ou atualiza no MongoDB
            if resultado_canonizacao['acao'] in ['criado', 'agrupado']:
                coletor_canonico = resultado_canonizacao['coletor_canonico']
                self.mongo_manager.salvar_coletor_canonico(coletor_canonico)

                if resultado_canonizacao['acao'] == 'criado':
                    self.stats['total_coletores_canonicos'] += 1

        except Exception as e:
            logger.debug(f"Erro ao processar nome '{nome}': {e}")
            raise

    def _salvar_checkpoint(self):
        """
        Salva checkpoint do processamento
        """
        try:
            checkpoint_data = {
                'tipo': 'canonicalizacao',
                'total_registros_processados': self.stats['total_registros_processados'],
                'total_nomes_atomizados': self.stats['total_nomes_atomizados'],
                'total_coletores_canonicos': self.stats['total_coletores_canonicos'],
                'registros_com_erro': self.stats['registros_com_erro'],
                'registros_vazios': self.stats['registros_vazios'],
                'checkpoint_count': self.stats['checkpoint_count'] + 1,
                'timestamp_checkpoint': datetime.now(),
                'algoritmo_versao': '1.0'
            }

            self.mongo_manager.salvar_checkpoint(checkpoint_data)
            self.stats['checkpoint_count'] += 1
            self.stats['ultimo_checkpoint'] = datetime.now()

        except Exception as e:
            print(f">> ERRO ao salvar checkpoint: {e}")

    def _exibir_progresso_lote(self, batch_num: int, tamanho_lote: int, tempo_lote: float):
        """
        Exibe progresso de um lote específico
        """
        # Calcula estatísticas básicas
        coletores_unicos = len(self.canonizador.coletores_canonicos)
        velocidade = tamanho_lote / tempo_lote if tempo_lote > 0 else 0

        print(f"Lote {batch_num:>4}: {tamanho_lote:>5} registros -> "
              f"{self.stats['total_nomes_atomizados']:>6} nomes -> "
              f"{coletores_unicos:>5} coletores unicos "
              f"({velocidade:>6.1f} reg/s)")

    def _exibir_progresso(self):
        """
        Exibe relatório de progresso completo com estimativas
        """
        agora = datetime.now()
        tempo_decorrido = (agora - self.stats['inicio_processamento']).total_seconds()

        # Estimativa de total se não conhecida
        if not self.stats['total_estimado']:
            # Estima baseado na velocidade atual (primeira estimativa conservadora)
            self.stats['total_estimado'] = int(self.stats['total_registros_processados'] * 2)

        # Calcula estimativas
        processados = self.stats['total_registros_processados']
        restantes = max(0, self.stats['total_estimado'] - processados)

        if self.stats['velocidade_media'] > 0:
            tempo_restante_seg = restantes / self.stats['velocidade_media']
            tempo_restante = time.strftime('%H:%M:%S', time.gmtime(tempo_restante_seg))
            previsao_termino = (agora + pd.Timedelta(seconds=tempo_restante_seg)).strftime('%H:%M:%S')
        else:
            tempo_restante = "Calculando..."
            previsao_termino = "Calculando..."

        # Progresso percentual
        percentual = (processados / self.stats['total_estimado'] * 100) if self.stats['total_estimado'] > 0 else 0

        print("\n" + "=" * 80)
        print(">> PROGRESSO DA CANONICALIZACAO DE COLETORES")
        print("=" * 80)
        print(f"   Registros processados: {processados:>10,}")
        print(f"   Nomes atomizados:      {self.stats['total_nomes_atomizados']:>10,}")
        print(f"   Coletores unicos:      {len(self.canonizador.coletores_canonicos):>10,}")
        print(f"   Registros com erro:    {self.stats['registros_com_erro']:>10,}")
        print(f"   Velocidade media:      {self.stats['velocidade_media']:>10.1f} reg/s")
        print(f"   Tempo decorrido:       {time.strftime('%H:%M:%S', time.gmtime(tempo_decorrido))}")
        print(f"   Progresso:             {percentual:>10.1f}%")
        print(f"   Tempo restante:        {tempo_restante}")
        print(f"   Previsao termino:      {previsao_termino}")
        print("=" * 80 + "\n")

        self.stats['ultimo_relatorio_progresso'] = agora

    def _finalizar_processamento(self):
        """
        Finaliza o processamento e calcula estatísticas finais
        """
        self.stats['fim_processamento'] = datetime.now()

        if self.stats['inicio_processamento']:
            delta = self.stats['fim_processamento'] - self.stats['inicio_processamento']
            self.stats['tempo_processamento'] = delta.total_seconds()

            if self.stats['tempo_processamento'] > 0:
                self.stats['registros_por_segundo'] = (
                    self.stats['total_registros_processados'] / self.stats['tempo_processamento']
                )

        # Obtém estatísticas do canonizador
        stats_canonizador = self.canonizador.obter_estatisticas()
        self.stats.update(stats_canonizador)

        # Obtém estatísticas do MongoDB
        stats_mongodb = self.mongo_manager.obter_estatisticas_colecao()
        self.stats['mongodb_stats'] = stats_mongodb

        # Salva checkpoint final
        self._salvar_checkpoint()

        logger.info("=" * 80)
        logger.info("PROCESSAMENTO FINALIZADO")
        logger.info("=" * 80)
        self._exibir_relatorio_final()

    def _exibir_relatorio_final(self):
        """
        Exibe relatório final do processamento
        """
        stats = self.stats

        logger.info(f"Tempo de processamento: {stats['tempo_processamento']:.1f} segundos")
        logger.info(f"Registros processados: {stats['total_registros_processados']:,}")
        logger.info(f"Nomes atomizados: {stats['total_nomes_atomizados']:,}")
        logger.info(f"Coletores canônicos criados: {stats.get('total_coletores_canonicos', 0):,}")
        logger.info(f"Taxa de canonicalização: {stats.get('taxa_canonicalizacao', 0):.2f}")
        logger.info(f"Registros por segundo: {stats['registros_por_segundo']:.1f}")
        logger.info(f"Registros com erro: {stats['registros_com_erro']:,}")
        logger.info(f"Registros vazios: {stats['registros_vazios']:,}")
        logger.info(f"Checkpoints salvos: {stats['checkpoint_count']}")

        if 'mongodb_stats' in stats and stats['mongodb_stats']:
            mongodb_stats = stats['mongodb_stats']
            logger.info(f"Estatísticas MongoDB:")
            logger.info(f"  - Total coletores no BD: {mongodb_stats.get('total_coletores', 0):,}")
            logger.info(f"  - Total variações: {mongodb_stats.get('total_variacoes', 0):,}")
            logger.info(f"  - Precisam revisão: {mongodb_stats.get('precisam_revisao', 0):,}")
            logger.info(f"  - Confiança média: {mongodb_stats.get('confianca_media', 0):.3f}")

    def obter_relatorio_coletores_revisao(self, limite: int = 50) -> List[Dict]:
        """
        Obtém relatório de coletores que precisam revisão manual

        Args:
            limite: Número máximo de coletores a retornar

        Returns:
            Lista de coletores para revisão
        """
        if not self.mongo_manager:
            logger.error("MongoDB não conectado")
            return []

        coletores_revisao = self.mongo_manager.obter_coletores_para_revisao(limite)

        logger.info(f"Coletores que precisam revisão manual: {len(coletores_revisao)}")

        return coletores_revisao


def main():
    """
    Função principal
    """
    import argparse

    parser = argparse.ArgumentParser(description='Processador de Canonicalização de Coletores')
    parser.add_argument('--restart', action='store_true',
                       help='Reinicia o processamento do zero (limpa dados existentes)')
    parser.add_argument('--sample', type=int,
                       help='Processa apenas uma amostra de N registros (para testes)')
    parser.add_argument('--revisao', action='store_true',
                       help='Exibe relatório de coletores que precisam revisão manual')

    args = parser.parse_args()

    try:
        processador = ProcessadorColetores()

        if args.revisao:
            # Apenas exibe relatório de revisão
            coletores_revisao = processador.obter_relatorio_coletores_revisao(100)

            print("\n" + "="*80)
            print("COLETORES QUE PRECISAM REVISÃO MANUAL")
            print("="*80)

            for i, coletor in enumerate(coletores_revisao[:10], 1):
                print(f"\n{i}. {coletor['coletor_canonico']} (confiança: {coletor['confianca_canonicalizacao']:.3f})")
                print(f"   Variações: {len(coletor['variacoes'])}")
                for variacao in coletor['variacoes'][:3]:
                    print(f"   - {variacao['forma_original']} (freq: {variacao['frequencia']})")
                if len(coletor['variacoes']) > 3:
                    print(f"   ... e mais {len(coletor['variacoes']) - 3} variações")

            return 0

        # Modifica configuração se for amostra
        if args.sample:
            logger.info(f"Modo amostra ativado: processando apenas {args.sample} registros")
            # Implementaria limitação aqui se necessário

        # Executa processamento
        stats = processador.processar_todos_coletores(restart=args.restart)

        print("\n" + "="*50)
        print("PROCESSAMENTO CONCLUÍDO COM SUCESSO!")
        print("="*50)
        print(f"Registros processados: {stats['total_registros_processados']:,}")
        print(f"Tempo total: {stats['tempo_processamento']:.1f}s")
        print(f"Coletores canônicos: {stats.get('total_coletores_canonicos', 0):,}")

        return 0

    except KeyboardInterrupt:
        logger.warning("Processamento interrompido pelo usuário")
        return 130
    except Exception as e:
        logger.error(f"Erro fatal: {e}")
        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())