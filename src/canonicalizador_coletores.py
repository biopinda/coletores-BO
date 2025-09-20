"""
Módulo principal para canonicalização de nomes de coletores
"""

import re
import logging
import unicodedata
from typing import List, Dict, Tuple, Optional, Set
from datetime import datetime
import phonetics
import Levenshtein
from unidecode import unidecode

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AtomizadorNomes:
    """
    Classe responsável por separar múltiplos coletores em strings
    """

    def __init__(self, separator_patterns: List[str], group_patterns: List[str] = None, institution_patterns: List[str] = None):
        """
        Inicializa o atomizador com padrões de separação e identificação de entidades

        Args:
            separator_patterns: Lista de padrões regex para separar nomes
            group_patterns: Lista de padrões regex para identificar grupos de pessoas
            institution_patterns: Lista de padrões regex para identificar empresas/instituições
        """
        self.separator_patterns = separator_patterns
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in separator_patterns]

        self.group_patterns = group_patterns or []
        self.compiled_group_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.group_patterns]

        self.institution_patterns = institution_patterns or []
        self.compiled_institution_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.institution_patterns]

        logger.info(f"AtomizadorNomes inicializado com {len(separator_patterns)} padrões de separação, {len(self.group_patterns)} padrões de grupos e {len(self.institution_patterns)} padrões de instituições")

    def atomizar(self, text: str) -> List[str]:
        """
        Separa uma string em múltiplos nomes de coletores

        Args:
            text: String contendo um ou mais nomes de coletores

        Returns:
            Lista de nomes individuais
        """
        if not text or not isinstance(text, str):
            return []

        # Remove espaços extras e normaliza
        text = re.sub(r'\s+', ' ', text.strip())

        # Se muito curto, retorna como único nome
        if len(text) < 2:
            return []

        # Aplica padrões de separação
        nomes = [text]
        for pattern in self.compiled_patterns:
            nomes_temp = []
            for nome in nomes:
                # Separa baseado no padrão atual
                partes = pattern.split(nome)
                nomes_temp.extend([parte.strip() for parte in partes if parte.strip()])
            nomes = nomes_temp

        # Remove nomes muito curtos ou inválidos
        nomes_validos = []
        for nome in nomes:
            if self._validar_nome(nome):
                nomes_validos.append(nome)

        logger.debug(f"Atomização: '{text}' -> {nomes_validos}")
        return nomes_validos

    def classify_entity_type(self, text: str) -> Dict[str, any]:
        """
        Classifica o tipo de entidade representada pelo texto com score de confiança

        Args:
            text: Texto a ser classificado

        Returns:
            Dicionário com 'tipo' e 'confianca_classificacao'
        """
        if not text or not isinstance(text, str):
            return {
                'tipo': 'pessoa',
                'confianca_classificacao': 0.5
            }

        text = text.strip()

        # Verifica padrões de empresas/instituições com diferentes níveis de confiança
        institution_confidence = self._calculate_institution_confidence(text)
        group_confidence = self._calculate_group_confidence(text)

        # Classifica baseado na maior confiança
        if institution_confidence > group_confidence and institution_confidence > 0.6:
            return {
                'tipo': 'empresa_instituicao',
                'confianca_classificacao': institution_confidence
            }
        elif group_confidence > 0.6:
            return {
                'tipo': 'grupo_pessoas',
                'confianca_classificacao': group_confidence
            }
        else:
            # Confiança para "pessoa" baseada na ausência de padrões organizacionais
            person_confidence = 1.0 - max(institution_confidence, group_confidence)
            return {
                'tipo': 'pessoa',
                'confianca_classificacao': max(person_confidence, 0.3)  # Mínimo de 30%
            }

    def _calculate_institution_confidence(self, text: str) -> float:
        """
        Calcula confiança de que o texto representa uma empresa/instituição
        """
        confidence = 0.0
        text_upper = text.upper()

        # Acrônimos em maiúsculas (alta confiança)
        if re.match(r'^[A-Z]{2,8}$', text):
            confidence = max(confidence, 0.95)
        elif re.match(r'^[A-Z]{2,8}[-_][A-Z]{2,8}$', text):
            confidence = max(confidence, 0.90)

        # Códigos de herbário (alta confiança)
        if re.match(r'^[A-Z]{1,4}$', text) and len(text) <= 4:
            confidence = max(confidence, 0.95)

        # Sufixos corporativos (alta confiança)
        if re.search(r'\b(S\.?A\.?|LTDA\.?|EIRELI\.?|EPP\.?|Ltd\.?|Inc\.?|Corp\.?)\b', text, re.IGNORECASE):
            confidence = max(confidence, 0.95)

        # Palavras-chave institucionais (confiança moderada a alta)
        institutional_keywords = {
            'universidade': 0.90, 'instituto': 0.85, 'laboratorio': 0.80,
            'museu': 0.85, 'fundacao': 0.80, 'empresa': 0.90,
            'centro': 0.75, 'departamento': 0.70, 'faculdade': 0.85,
            'embrapa': 0.95, 'ibama': 0.95, 'icmbio': 0.95
        }

        for keyword, score in institutional_keywords.items():
            if keyword in text.lower():
                confidence = max(confidence, score)

        # Padrões com códigos/números (confiança moderada)
        if re.search(r'[A-Z]{3,}\s*[0-9]+', text):
            confidence = max(confidence, 0.75)

        return confidence

    def _calculate_group_confidence(self, text: str) -> float:
        """
        Calcula confiança de que o texto representa um grupo de pessoas
        """
        confidence = 0.0

        # Palavras-chave de grupos (confiança moderada)
        group_keywords = {
            'equipe': 0.80, 'grupo': 0.75, 'projeto': 0.70,
            'pesquisa': 0.65, 'estudo': 0.60, 'alunos': 0.85,
            'turma': 0.80, 'curso': 0.70, 'disciplina': 0.75
        }

        for keyword, score in group_keywords.items():
            if keyword in text.lower():
                confidence = max(confidence, score)

        # Expressões específicas (alta confiança)
        if 'pesquisas da biodiversidade' in text.lower():
            confidence = max(confidence, 0.90)
        if 'coleta coletiva' in text.lower():
            confidence = max(confidence, 0.95)
        if 'não identificado' in text.lower() or 'anonimo' in text.lower():
            confidence = max(confidence, 0.85)

        return confidence

    def is_group_or_project(self, text: str) -> bool:
        """
        Verifica se o texto representa um grupo/projeto ao invés de uma pessoa
        (Mantido para compatibilidade, mas usa o novo sistema de classificação)

        Args:
            text: Texto a ser verificado

        Returns:
            True se for identificado como grupo/projeto ou empresa/instituição
        """
        classification = self.classify_entity_type(text)
        return classification['tipo'] in ['grupo_pessoas', 'empresa_instituicao']

    def _validar_nome(self, nome: str) -> bool:
        """
        Valida se uma string é um nome válido

        Args:
            nome: String do nome a validar

        Returns:
            True se for um nome válido
        """
        if not nome or len(nome) < 2:
            return False

        # Remove números comuns no final (ex: "Silva 123")
        nome_limpo = re.sub(r'\s*[0-9]+\s*$', '', nome).strip()

        if len(nome_limpo) < 2:
            return False

        # Verifica se tem pelo menos uma letra
        if not re.search(r'[a-zA-ZÀ-ÿ]', nome_limpo):
            return False

        # Rejeita se for apenas "et al.", "e col.", etc.
        if re.match(r'^(et\s+al\.?|e\s+cols?\.?|and\s+others?)$', nome_limpo, re.IGNORECASE):
            return False

        return True


class NormalizadorNome:
    """
    Classe responsável por normalizar nomes individuais
    """

    def __init__(self):
        """
        Inicializa o normalizador
        """
        self.cleanup_patterns = {
            'remove_brackets': re.compile(r'[\[\](){}]'),
            'remove_special_chars': re.compile(r'[^\w\s\.,\-àáâãéêíóôõúçÀÁÂÃÉÊÍÓÔÕÚÇ]'),
            'remove_extra_spaces': re.compile(r'\s+'),
            'remove_collectors_numbers': re.compile(r'\s*[0-9]+\s*$')
        }
        logger.info("NormalizadorNome inicializado")

    def normalizar(self, nome: str) -> Dict[str, any]:
        """
        Normaliza um nome e extrai informações estruturadas

        Args:
            nome: Nome a ser normalizado

        Returns:
            Dicionário com informações estruturadas do nome
        """
        if not nome or not isinstance(nome, str):
            return self._criar_nome_vazio()

        # Limpeza inicial
        nome_limpo = self._limpar_nome(nome)

        if not nome_limpo:
            return self._criar_nome_vazio()

        # Extrai componentes do nome
        componentes = self._extrair_componentes(nome_limpo)

        # Gera formas normalizadas
        nome_normalizado = self._gerar_nome_normalizado(componentes)

        # Gera chaves de busca
        chaves_busca = self._gerar_chaves_busca(componentes)

        resultado = {
            'nome_original': nome,
            'nome_limpo': nome_limpo,
            'nome_normalizado': nome_normalizado,
            'sobrenome': componentes['sobrenome'],
            'sobrenome_normalizado': componentes['sobrenome_normalizado'],
            'iniciais': componentes['iniciais'],
            'tem_inicial': len(componentes['iniciais']) > 0,
            'chaves_busca': chaves_busca
        }

        logger.debug(f"Normalização: '{nome}' -> {resultado['nome_normalizado']}")
        return resultado

    def _limpar_nome(self, nome: str) -> str:
        """
        Limpa um nome removendo caracteres indesejados
        """
        # Remove números no final
        nome = self.cleanup_patterns['remove_collectors_numbers'].sub('', nome)

        # Remove colchetes e parênteses
        nome = self.cleanup_patterns['remove_brackets'].sub('', nome)

        # Remove caracteres especiais (mantém acentos)
        nome = self.cleanup_patterns['remove_special_chars'].sub(' ', nome)

        # Remove espaços extras
        nome = self.cleanup_patterns['remove_extra_spaces'].sub(' ', nome)

        return nome.strip()

    def _extrair_componentes(self, nome: str) -> Dict[str, any]:
        """
        Extrai componentes estruturados de um nome
        """
        componentes = {
            'sobrenome': '',
            'sobrenome_normalizado': '',
            'iniciais': []
        }

        # Padrões comuns de nomes científicos
        # Formato: "Sobrenome, I." ou "Sobrenome, Inicial Inicial"
        match = re.match(r'^([^,]+),\s*(.+)$', nome)
        if match:
            sobrenome = match.group(1).strip()
            resto = match.group(2).strip()

            # Extrai iniciais
            iniciais = re.findall(r'\b([A-ZÀ-Ÿ])\.?\b', resto)

            componentes['sobrenome'] = sobrenome
            componentes['iniciais'] = iniciais

        # Formato: "I. Sobrenome" ou "Inicial Sobrenome"
        elif re.match(r'^[A-ZÀ-Ÿ]\.?\s+', nome):
            partes = nome.split()
            if len(partes) >= 2:
                # Primeira parte são iniciais, última é sobrenome
                sobrenome = partes[-1]
                iniciais_str = ' '.join(partes[:-1])
                iniciais = re.findall(r'\b([A-ZÀ-Ÿ])\.?\b', iniciais_str)

                componentes['sobrenome'] = sobrenome
                componentes['iniciais'] = iniciais

        # Formato: apenas sobrenome
        else:
            # Remove pontos e pega a primeira palavra significativa
            partes = [p for p in nome.split() if len(p) > 1]
            if partes:
                componentes['sobrenome'] = partes[-1]  # Última palavra como sobrenome
                if len(partes) > 1:
                    # Tenta extrair iniciais das outras partes
                    outras_partes = ' '.join(partes[:-1])
                    iniciais = re.findall(r'\b([A-ZÀ-Ÿ])\.?\b', outras_partes)
                    componentes['iniciais'] = iniciais

        # Normaliza sobrenome
        if componentes['sobrenome']:
            componentes['sobrenome_normalizado'] = self._normalizar_sobrenome(componentes['sobrenome'])

        return componentes

    def _normalizar_sobrenome(self, sobrenome: str) -> str:
        """
        Normaliza um sobrenome para comparação
        """
        # Converte para minúscula
        normalizado = sobrenome.lower()

        # Remove acentos
        normalizado = unidecode(normalizado)

        # Remove caracteres especiais
        normalizado = re.sub(r'[^a-z]', '', normalizado)

        return normalizado

    def _gerar_nome_normalizado(self, componentes: Dict[str, any]) -> str:
        """
        Gera uma forma normalizada do nome para canonicalização
        """
        sobrenome = componentes['sobrenome']
        iniciais = componentes['iniciais']

        if not sobrenome:
            return nome

        if iniciais:
            iniciais_str = '.'.join(iniciais) + '.'
            return f"{sobrenome}, {iniciais_str}"
        else:
            return sobrenome

    def _gerar_chaves_busca(self, componentes: Dict[str, any]) -> Dict[str, str]:
        """
        Gera chaves de busca para o nome
        """
        chaves = {}

        if componentes['sobrenome_normalizado']:
            # Soundex
            try:
                chaves['soundex'] = phonetics.soundex(componentes['sobrenome_normalizado'])
            except:
                chaves['soundex'] = ''

            # Metaphone
            try:
                chaves['metaphone'] = phonetics.metaphone(componentes['sobrenome_normalizado'])
            except:
                chaves['metaphone'] = ''

        return chaves

    def _criar_nome_vazio(self) -> Dict[str, any]:
        """
        Cria uma estrutura vazia para nomes inválidos
        """
        return {
            'nome_original': '',
            'nome_limpo': '',
            'nome_normalizado': '',
            'sobrenome': '',
            'sobrenome_normalizado': '',
            'iniciais': [],
            'tem_inicial': False,
            'chaves_busca': {'soundex': '', 'metaphone': ''}
        }


class CanonizadorColetores:
    """
    Classe responsável por agrupar variações do mesmo coletor
    """

    def __init__(self, similarity_threshold: float = 0.85, confidence_threshold: float = 0.7):
        """
        Inicializa o canonizador

        Args:
            similarity_threshold: Limiar de similaridade para agrupamento
            confidence_threshold: Limiar de confiança para canonicalização automática
        """
        self.similarity_threshold = similarity_threshold
        self.confidence_threshold = confidence_threshold
        self.coletores_canonicos = {}  # sobrenome_normalizado -> dados do coletor canônico
        logger.info(f"CanonizadorColetores inicializado (similarity={similarity_threshold}, confidence={confidence_threshold})")

    def processar_nome(self, nome_normalizado: Dict[str, any]) -> Dict[str, any]:
        """
        Processa um nome normalizado e retorna informações de canonicalização

        Args:
            nome_normalizado: Dicionário com informações do nome normalizado

        Returns:
            Dicionário com informações de canonicalização
        """
        if not nome_normalizado['sobrenome_normalizado']:
            return self._criar_resultado_isolado(nome_normalizado)

        sobrenome_norm = nome_normalizado['sobrenome_normalizado']

        # Busca candidatos existentes
        candidatos = self._buscar_candidatos(nome_normalizado)

        if not candidatos:
            # Primeiro registro deste sobrenome
            return self._criar_novo_canonico(nome_normalizado)

        # Avalia similaridade com candidatos
        melhor_match = self._encontrar_melhor_match(nome_normalizado, candidatos)

        if melhor_match['score'] >= self.similarity_threshold:
            # Agrupa com coletor existente
            return self._agrupar_com_existente(nome_normalizado, melhor_match)
        else:
            # Cria novo coletor canônico
            return self._criar_novo_canonico(nome_normalizado)

    def _buscar_candidatos(self, nome_normalizado: Dict[str, any]) -> List[Dict[str, any]]:
        """
        Busca candidatos para agrupamento baseado em similaridade
        """
        candidatos = []
        sobrenome_norm = nome_normalizado['sobrenome_normalizado']

        # Busca exata por sobrenome
        if sobrenome_norm in self.coletores_canonicos:
            candidatos.append(self.coletores_canonicos[sobrenome_norm])

        # Busca por similaridade fonética
        soundex_atual = nome_normalizado['chaves_busca']['soundex']
        metaphone_atual = nome_normalizado['chaves_busca']['metaphone']

        for coletor in self.coletores_canonicos.values():
            if coletor['sobrenome_normalizado'] == sobrenome_norm:
                continue  # Já adicionado acima

            # Verifica se tem mesma chave fonética
            if (soundex_atual and coletor['indices_busca']['soundex'] == soundex_atual) or \
               (metaphone_atual and coletor['indices_busca']['metaphone'] == metaphone_atual):
                candidatos.append(coletor)

        return candidatos

    def _encontrar_melhor_match(self, nome_normalizado: Dict[str, any], candidatos: List[Dict[str, any]]) -> Dict[str, any]:
        """
        Encontra o melhor candidato para agrupamento
        """
        melhor_score = 0.0
        melhor_candidato = None

        for candidato in candidatos:
            score = self._calcular_similaridade(nome_normalizado, candidato)
            if score > melhor_score:
                melhor_score = score
                melhor_candidato = candidato

        return {
            'candidato': melhor_candidato,
            'score': melhor_score
        }

    def _calcular_similaridade(self, nome1: Dict[str, any], coletor2: Dict[str, any]) -> float:
        """
        Calcula score de similaridade entre dois nomes
        """
        score = 0.0
        peso_total = 0.0

        # Similaridade de sobrenome (peso 50%)
        peso_sobrenome = 0.5
        if nome1['sobrenome_normalizado'] and coletor2['sobrenome_normalizado']:
            sim_sobrenome = self._similaridade_string(
                nome1['sobrenome_normalizado'],
                coletor2['sobrenome_normalizado']
            )
            score += sim_sobrenome * peso_sobrenome
            peso_total += peso_sobrenome

        # Compatibilidade de iniciais (peso 30%)
        peso_iniciais = 0.3
        if nome1['iniciais'] or coletor2['iniciais']:
            compat_iniciais = self._compatibilidade_iniciais(nome1['iniciais'], coletor2['iniciais'])
            score += compat_iniciais * peso_iniciais
            peso_total += peso_iniciais

        # Similaridade fonética (peso 20%)
        peso_fonetico = 0.2
        sim_fonetica = self._similaridade_fonetica(nome1['chaves_busca'], coletor2['indices_busca'])
        score += sim_fonetica * peso_fonetico
        peso_total += peso_fonetico

        return score / peso_total if peso_total > 0 else 0.0

    def _similaridade_string(self, str1: str, str2: str) -> float:
        """
        Calcula similaridade entre duas strings usando Levenshtein
        """
        if not str1 or not str2:
            return 0.0

        if str1 == str2:
            return 1.0

        max_len = max(len(str1), len(str2))
        if max_len == 0:
            return 1.0

        distance = Levenshtein.distance(str1, str2)
        return 1.0 - (distance / max_len)

    def _compatibilidade_iniciais(self, iniciais1: List[str], iniciais2: List[str]) -> float:
        """
        Calcula compatibilidade entre conjuntos de iniciais
        """
        if not iniciais1 and not iniciais2:
            return 1.0  # Ambos sem iniciais

        if not iniciais1 or not iniciais2:
            return 0.7  # Um tem iniciais, outro não - parcialmente compatível

        # Verifica se as iniciais são compatíveis
        set1 = set(iniciais1)
        set2 = set(iniciais2)

        # Se um é subconjunto do outro, são compatíveis
        if set1.issubset(set2) or set2.issubset(set1):
            return 1.0

        # Calcula intersecção
        intersecao = len(set1.intersection(set2))
        uniao = len(set1.union(set2))

        return intersecao / uniao if uniao > 0 else 0.0

    def _similaridade_fonetica(self, chaves1: Dict[str, str], chaves2: Dict[str, str]) -> float:
        """
        Calcula similaridade fonética
        """
        score = 0.0
        comparacoes = 0

        if chaves1['soundex'] and chaves2['soundex']:
            score += 1.0 if chaves1['soundex'] == chaves2['soundex'] else 0.0
            comparacoes += 1

        if chaves1['metaphone'] and chaves2['metaphone']:
            score += 1.0 if chaves1['metaphone'] == chaves2['metaphone'] else 0.0
            comparacoes += 1

        return score / comparacoes if comparacoes > 0 else 0.0

    def _criar_novo_canonico(self, nome_normalizado: Dict[str, any]) -> Dict[str, any]:
        """
        Cria um novo coletor canônico
        """
        agora = datetime.now()

        coletor_canonico = {
            'coletor_canonico': nome_normalizado['nome_normalizado'],
            'sobrenome_normalizado': nome_normalizado['sobrenome_normalizado'],
            'iniciais': nome_normalizado['iniciais'],
            'variacoes': [{
                'forma_original': nome_normalizado['nome_original'],
                'frequencia': 1,
                'primeira_ocorrencia': agora,
                'ultima_ocorrencia': agora
            }],
            'total_registros': 1,
            'confianca_canonicalizacao': 1.0,
            'kingdoms': nome_normalizado.get('kingdoms', {}),
            'tipo_coletor': nome_normalizado.get('tipo_coletor', 'pessoa'),
            'confianca_tipo_coletor': nome_normalizado.get('confianca_tipo_coletor', 0.5),
            'metadados': {
                'data_criacao': agora,
                'ultima_atualizacao': agora,
                'algoritmo_versao': '1.0',
                'revisar_manualmente': False
            },
            'indices_busca': nome_normalizado['chaves_busca']
        }

        # Armazena na estrutura interna
        self.coletores_canonicos[nome_normalizado['sobrenome_normalizado']] = coletor_canonico

        logger.debug(f"Novo coletor canônico criado: {coletor_canonico['coletor_canonico']}")

        return {
            'acao': 'criado',
            'coletor_canonico': coletor_canonico,
            'confianca': 1.0
        }

    def _agrupar_com_existente(self, nome_normalizado: Dict[str, any], melhor_match: Dict[str, any]) -> Dict[str, any]:
        """
        Agrupa com um coletor existente
        """
        candidato = melhor_match['candidato']
        score = melhor_match['score']

        # Atualiza variações
        forma_original = nome_normalizado['nome_original']
        variacao_existente = None

        for variacao in candidato['variacoes']:
            if variacao['forma_original'] == forma_original:
                variacao_existente = variacao
                break

        if variacao_existente:
            # Incrementa frequência
            variacao_existente['frequencia'] += 1
            variacao_existente['ultima_ocorrencia'] = datetime.now()
        else:
            # Adiciona nova variação
            candidato['variacoes'].append({
                'forma_original': forma_original,
                'frequencia': 1,
                'primeira_ocorrencia': datetime.now(),
                'ultima_ocorrencia': datetime.now()
            })

        # Atualiza totais
        candidato['total_registros'] += 1
        candidato['metadados']['ultima_atualizacao'] = datetime.now()

        # Atualiza kingdoms
        kingdoms_novos = nome_normalizado.get('kingdoms', {})
        for kingdom, count in kingdoms_novos.items():
            if kingdom in candidato['kingdoms']:
                candidato['kingdoms'][kingdom] += count
            else:
                candidato['kingdoms'][kingdom] = count

        # Atualiza confiança (diminui se score for baixo)
        if score < self.confidence_threshold:
            candidato['confianca_canonicalizacao'] *= 0.95
            candidato['metadados']['revisar_manualmente'] = True

        logger.debug(f"Agrupado com coletor existente: {candidato['coletor_canonico']} (score={score:.3f})")

        return {
            'acao': 'agrupado',
            'coletor_canonico': candidato,
            'confianca': score
        }

    def _criar_resultado_isolado(self, nome_normalizado: Dict[str, any]) -> Dict[str, any]:
        """
        Cria resultado para nomes que não podem ser processados
        """
        return {
            'acao': 'isolado',
            'coletor_canonico': None,
            'confianca': 0.0,
            'motivo': 'Nome sem sobrenome identificável'
        }

    def obter_estatisticas(self) -> Dict[str, any]:
        """
        Retorna estatísticas do processo de canonicalização
        """
        total_canonicos = len(self.coletores_canonicos)
        total_variacoes = sum(len(c['variacoes']) for c in self.coletores_canonicos.values())
        total_registros = sum(c['total_registros'] for c in self.coletores_canonicos.values())

        revisar_manualmente = sum(1 for c in self.coletores_canonicos.values()
                                 if c['metadados']['revisar_manualmente'])

        return {
            'total_coletores_canonicos': total_canonicos,
            'total_variacoes': total_variacoes,
            'total_registros_processados': total_registros,
            'precisam_revisao_manual': revisar_manualmente,
            'taxa_canonicalizacao': total_variacoes / total_canonicos if total_canonicos > 0 else 0
        }


class GerenciadorMongoDB:
    """
    Classe responsável por gerenciar operações com MongoDB
    """

    def __init__(self, connection_string: str, database_name: str, collections: Dict[str, str]):
        """
        Inicializa o gerenciador MongoDB

        Args:
            connection_string: String de conexão MongoDB
            database_name: Nome do banco de dados
            collections: Dicionário com nomes das coleções
        """
        import pymongo
        from pymongo import MongoClient

        self.client = MongoClient(connection_string, serverSelectionTimeoutMS=30000)
        self.db = self.client[database_name]
        self.collections = collections

        # Referências das coleções
        self.ocorrencias = self.db[collections['ocorrencias']]
        self.coletores = self.db[collections['coletores']]

        logger.info(f"GerenciadorMongoDB inicializado para banco '{database_name}'")

        # Testa conexão
        try:
            self.client.admin.command('ping')
            logger.info("Conexão com MongoDB estabelecida com sucesso")
        except Exception as e:
            logger.error(f"Erro ao conectar com MongoDB: {e}")
            raise

    def criar_indices_coletores(self):
        """
        Cria índices necessários na coleção coletores
        """
        try:
            # Índice para sobrenome normalizado
            self.coletores.create_index("sobrenome_normalizado")

            # Índice para formas originais
            self.coletores.create_index("variacoes.forma_original")

            # Índice para chaves fonéticas
            self.coletores.create_index("indices_busca.soundex")
            self.coletores.create_index("indices_busca.metaphone")

            # Índice composto para busca eficiente
            self.coletores.create_index([
                ("sobrenome_normalizado", 1),
                ("indices_busca.soundex", 1)
            ])

            logger.info("Índices da coleção 'coletores' criados com sucesso")

        except Exception as e:
            logger.error(f"Erro ao criar índices: {e}")
            raise

    def obter_amostra_recordedby(self, tamanho: int = 100000) -> List[str]:
        """
        Obtém uma amostra dos valores de recordedBy para análise

        Args:
            tamanho: Tamanho da amostra

        Returns:
            Lista de valores de recordedBy
        """
        try:
            logger.info(f"Obtendo amostra de {tamanho} registros de recordedBy...")

            pipeline = [
                {"$match": {"recordedBy": {"$exists": True, "$ne": None, "$ne": ""}}},
                {"$sample": {"size": tamanho}},
                {"$project": {"recordedBy": 1, "_id": 0}}
            ]

            resultado = list(self.ocorrencias.aggregate(pipeline))
            recordedby_values = [doc['recordedBy'] for doc in resultado if doc.get('recordedBy')]

            logger.info(f"Amostra obtida: {len(recordedby_values)} registros")
            return recordedby_values

        except Exception as e:
            logger.error(f"Erro ao obter amostra: {e}")
            raise

    def obter_amostra_recordedby_por_kingdom(self, tamanho: int = 100000, kingdom: str = "Plantae") -> List[str]:
        """
        Obtém uma amostra dos valores de recordedBy filtrada por kingdom para análise

        Args:
            tamanho: Tamanho da amostra
            kingdom: Kingdom para filtrar (Plantae, Animalia, etc.)

        Returns:
            Lista de valores de recordedBy
        """
        try:
            logger.info(f"Obtendo amostra de {tamanho} registros de recordedBy para kingdom '{kingdom}'...")

            pipeline = [
                {"$match": {
                    "recordedBy": {"$exists": True, "$ne": None, "$ne": ""},
                    "kingdom": kingdom
                }},
                {"$sample": {"size": tamanho}},
                {"$project": {"recordedBy": 1, "kingdom": 1, "_id": 0}}
            ]

            resultado = list(self.ocorrencias.aggregate(pipeline))
            recordedby_values = [doc['recordedBy'] for doc in resultado if doc.get('recordedBy')]

            logger.info(f"Amostra obtida para {kingdom}: {len(recordedby_values)} registros")
            return recordedby_values

        except Exception as e:
            logger.error(f"Erro ao obter amostra por kingdom: {e}")
            raise

    def obter_todos_recordedby(self, batch_size: int = 10000):
        """
        Gerador que retorna todos os valores de recordedBy em lotes

        Args:
            batch_size: Tamanho do lote

        Yields:
            Lotes de documentos com recordedBy
        """
        try:
            total_docs = self.ocorrencias.count_documents(
                {"recordedBy": {"$exists": True, "$ne": None, "$ne": ""}}
            )
            logger.info(f"Total de documentos com recordedBy: {total_docs}")

            processed = 0
            cursor = self.ocorrencias.find(
                {"recordedBy": {"$exists": True, "$ne": None, "$ne": ""}},
                {"recordedBy": 1, "_id": 1}
            ).batch_size(batch_size)

            batch = []
            for doc in cursor:
                batch.append(doc)

                if len(batch) >= batch_size:
                    processed += len(batch)
                    logger.info(f"Processando lote: {processed}/{total_docs} ({processed/total_docs*100:.1f}%)")
                    yield batch
                    batch = []

            # Último lote (se houver)
            if batch:
                processed += len(batch)
                logger.info(f"Processando último lote: {processed}/{total_docs}")
                yield batch

        except Exception as e:
            logger.error(f"Erro ao obter dados: {e}")
            raise

    def salvar_coletor_canonico(self, coletor_canonico: Dict[str, any]) -> bool:
        """
        Salva ou atualiza um coletor canônico no MongoDB

        Args:
            coletor_canonico: Dados do coletor canônico

        Returns:
            True se salvou com sucesso
        """
        try:
            # Usa upsert baseado no sobrenome normalizado
            filtro = {"sobrenome_normalizado": coletor_canonico["sobrenome_normalizado"]}

            resultado = self.coletores.replace_one(
                filtro,
                coletor_canonico,
                upsert=True
            )

            if resultado.upserted_id:
                logger.debug(f"Novo coletor inserido: {coletor_canonico['coletor_canonico']}")
            else:
                logger.debug(f"Coletor atualizado: {coletor_canonico['coletor_canonico']}")

            return True

        except Exception as e:
            logger.error(f"Erro ao salvar coletor canônico: {e}")
            return False

    def buscar_coletor_por_forma(self, forma_original: str) -> Optional[Dict[str, any]]:
        """
        Busca um coletor canônico pela forma original

        Args:
            forma_original: Forma original do nome

        Returns:
            Dados do coletor canônico ou None
        """
        try:
            resultado = self.coletores.find_one({
                "variacoes.forma_original": forma_original
            })
            return resultado

        except Exception as e:
            logger.error(f"Erro ao buscar coletor: {e}")
            return None

    def obter_estatisticas_colecao(self) -> Dict[str, any]:
        """
        Obtém estatísticas da coleção de coletores

        Returns:
            Dicionário com estatísticas
        """
        try:
            pipeline = [
                {
                    "$group": {
                        "_id": None,
                        "total_coletores": {"$sum": 1},
                        "total_registros": {"$sum": "$total_registros"},
                        "total_variacoes": {"$sum": {"$size": "$variacoes"}},
                        "precisam_revisao": {
                            "$sum": {
                                "$cond": ["$metadados.revisar_manualmente", 1, 0]
                            }
                        },
                        "confianca_media": {"$avg": "$confianca_canonicalizacao"}
                    }
                }
            ]

            resultado = list(self.coletores.aggregate(pipeline))

            if resultado:
                stats = resultado[0]
                stats.pop('_id', None)
                return stats
            else:
                return {
                    "total_coletores": 0,
                    "total_registros": 0,
                    "total_variacoes": 0,
                    "precisam_revisao": 0,
                    "confianca_media": 0.0
                }

        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {e}")
            return {}

    def obter_coletores_para_revisao(self, limite: int = 100) -> List[Dict[str, any]]:
        """
        Obtém coletores que precisam de revisão manual

        Args:
            limite: Número máximo de coletores a retornar

        Returns:
            Lista de coletores que precisam revisão
        """
        try:
            resultado = list(self.coletores.find(
                {"metadados.revisar_manualmente": True}
            ).sort("confianca_canonicalizacao", 1).limit(limite))

            logger.info(f"Encontrados {len(resultado)} coletores para revisão")
            return resultado

        except Exception as e:
            logger.error(f"Erro ao obter coletores para revisão: {e}")
            return []

    def salvar_checkpoint(self, checkpoint_data: Dict[str, any]) -> bool:
        """
        Salva dados de checkpoint para recuperação

        Args:
            checkpoint_data: Dados do checkpoint

        Returns:
            True se salvou com sucesso
        """
        try:
            checkpoint_data['timestamp'] = datetime.now()

            self.db.checkpoints.replace_one(
                {"tipo": "canonicalizacao"},
                checkpoint_data,
                upsert=True
            )

            logger.info("Checkpoint salvo com sucesso")
            return True

        except Exception as e:
            logger.error(f"Erro ao salvar checkpoint: {e}")
            return False

    def carregar_checkpoint(self) -> Optional[Dict[str, any]]:
        """
        Carrega dados de checkpoint

        Returns:
            Dados do checkpoint ou None
        """
        try:
            resultado = self.db.checkpoints.find_one({"tipo": "canonicalizacao"})
            if resultado:
                logger.info("Checkpoint carregado com sucesso")
            return resultado

        except Exception as e:
            logger.error(f"Erro ao carregar checkpoint: {e}")
            return None

    def limpar_colecao_coletores(self) -> bool:
        """
        Limpa a coleção de coletores (usado para reiniciar processamento)

        Returns:
            True se limpou com sucesso
        """
        try:
            resultado = self.coletores.delete_many({})
            logger.info(f"Coleção coletores limpa: {resultado.deleted_count} documentos removidos")
            return True

        except Exception as e:
            logger.error(f"Erro ao limpar coleção: {e}")
            return False

    def fechar_conexao(self):
        """
        Fecha a conexão com MongoDB
        """
        try:
            self.client.close()
            logger.info("Conexão com MongoDB fechada")
        except Exception as e:
            logger.error(f"Erro ao fechar conexão: {e}")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.fechar_conexao()