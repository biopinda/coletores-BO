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

        Tipos possíveis:
        - 'pessoa': um único nome próprio de pessoa
        - 'conjunto_pessoas': múltiplos nomes próprios (para atomização)
        - 'grupo_pessoas': denominações genéricas sem nomes próprios
        - 'empresa_instituicao': organizações, empresas, instituições
        - 'ausencia_coletor': ausência de informação sobre o coletor

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

        # Verifica primeiro se é ausência de coletor (prioridade máxima)
        ausencia_confidence = self._calculate_ausencia_coletor_confidence(text)

        # Verifica se é conjunto de pessoas (múltiplos nomes próprios)
        conjunto_confidence = self._calculate_conjunto_pessoas_confidence(text)

        # Verifica padrões de empresas/instituições
        institution_confidence = self._calculate_institution_confidence(text)

        # Verifica padrões de grupos genéricos (sem nomes próprios)
        group_confidence = self._calculate_group_confidence(text)

        # Classifica baseado na maior confiança com prioridades específicas
        # Prioridade 1: Ausência de coletor (prioridade máxima)
        if ausencia_confidence > 0.8:
            return {
                'tipo': 'ausencia_coletor',
                'confianca_classificacao': ausencia_confidence
            }
        # Prioridade 2: Conjunto de pessoas com alta confiança
        elif conjunto_confidence > 0.7 and conjunto_confidence >= max(institution_confidence, group_confidence):
            return {
                'tipo': 'conjunto_pessoas',
                'confianca_classificacao': conjunto_confidence
            }
        # Prioridade 3: Grupos com alta confiança
        elif group_confidence >= 0.8:
            return {
                'tipo': 'grupo_pessoas',
                'confianca_classificacao': group_confidence
            }
        # Prioridade 4: Instituições
        elif institution_confidence > 0.6 and institution_confidence >= max(conjunto_confidence, group_confidence):
            return {
                'tipo': 'empresa_instituicao',
                'confianca_classificacao': institution_confidence
            }
        # Prioridade 5: Grupos com confiança moderada
        elif group_confidence > 0.6:
            return {
                'tipo': 'grupo_pessoas',
                'confianca_classificacao': group_confidence
            }
        else:
            # Verifica se é um nome único (problemático)
            single_name_pattern = r'^[A-ZÀ-Ý][a-zà-ÿç]+$'
            if re.match(single_name_pattern, text.strip()):
                # Nomes únicos têm baixa confiança - devem ser revisados
                return {
                    'tipo': 'pessoa',
                    'confianca_classificacao': 0.3  # Baixa confiança para revisão manual
                }

            # Confiança para "pessoa" baseada na ausência de outros padrões
            max_other = max(institution_confidence, conjunto_confidence, group_confidence, ausencia_confidence)
            person_confidence = 1.0 - max_other
            return {
                'tipo': 'pessoa',
                'confianca_classificacao': max(person_confidence, 0.3)  # Mínimo de 30%
            }

    def _calculate_institution_confidence(self, text: str) -> float:
        """
        Calcula confiança de que o texto representa uma empresa/instituição
        """
        confidence = 0.0
        text_lower = text.lower()

        # Verifica se parece com nome de pessoa (reduz confiança)
        if self._looks_like_person_name(text):
            return 0.0

        # Lista de sobrenomes comuns que não devem ser considerados acrônimos
        common_surnames = {
            'silva', 'santos', 'oliveira', 'souza', 'rodrigues', 'ferreira',
            'alves', 'pereira', 'lima', 'gomes', 'ribeiro', 'carvalho',
            'almeida', 'lopes', 'soares', 'fernandes', 'vieira', 'barbosa',
            'rocha', 'dias', 'monteiro', 'cardoso', 'reis', 'sacco', 'orth',
            'ramos', 'moreira', 'jesus', 'martins', 'araujo', 'costa',
            'cruz', 'castro', 'pinto', 'teixeira', 'correia', 'andrade'
        }

        # Verifica se é um sobrenome comum (não deve ser instituição)
        if text_lower in common_surnames:
            return 0.0

        # Verifica se é nome com hífen (geralmente sobrenome composto)
        if '-' in text and not text.isupper():
            # Se contém letras minúsculas, provavelmente é nome de pessoa
            if re.search(r'[a-z]', text):
                return 0.0

        # Acrônimos em maiúsculas - ser mais restritivo
        if re.match(r'^[A-Z]{2,8}$', text) and '.' not in text:
            # Só considera se tem 3+ letras OU se é um acrônimo conhecido
            known_institutions = {
                'USP', 'UFRJ', 'UFC', 'UFMG', 'UFPE', 'UFSC', 'UFPR', 'UFRGS',
                'EMBRAPA', 'INPA', 'IBAMA', 'ICMBIO', 'CNPq', 'CAPES', 'FAPESP',
                'RB', 'SP', 'MG', 'HB', 'HUEFS', 'ALCB', 'VIC', 'HRCB'
            }

            if text in known_institutions:
                confidence = max(confidence, 0.95)
            elif len(text) >= 4:  # Acrônimos com 4+ letras têm maior chance de serem instituições
                confidence = max(confidence, 0.80)
            elif len(text) == 3:  # Mais cauteloso com 3 letras
                confidence = max(confidence, 0.60)
            # Ignora acrônimos de 2 letras (muito provavelmente são iniciais)

        # Códigos com hífen/underscore - mais restritivo
        elif re.match(r'^[A-Z]{3,8}[-_][A-Z]{3,8}$', text):
            confidence = max(confidence, 0.85)

        # Sufixos corporativos específicos (alta confiança)
        # Mais restritivos para evitar iniciais como "S.A."
        corporate_patterns = [
            r'\bS\.?A\.?\s*$',  # Final da string
            r'\bLTDA\.?\s*$',
            r'\bEIRELI\.?\s*$',
            r'\bEPP\.?\s*$',
            r'\bLtd\.?\s*$',
            r'\bInc\.?\s*$',
            r'\bCorp\.?\s*$',
            r'\bS\.?L\.?\s*$'
        ]

        for pattern in corporate_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                # Verifica se é realmente um sufixo corporativo e não iniciais
                if not self._is_person_initials_context(text):
                    confidence = max(confidence, 0.95)

        # Palavras-chave institucionais (confiança moderada a alta)
        institutional_keywords = {
            'universidade': 0.90, 'instituto': 0.85, 'laboratorio': 0.80,
            'museu': 0.85, 'fundacao': 0.80, 'empresa': 0.90,
            'centro': 0.75, 'departamento': 0.70, 'faculdade': 0.85,
            'embrapa': 0.95, 'ibama': 0.95, 'icmbio': 0.95,
            'secretaria': 0.85, 'ministerio': 0.90, 'federal': 0.80,
            'estadual': 0.80, 'municipal': 0.75, 'laboratory': 0.80,
            'company': 0.90, 'corporation': 0.90, 'institute': 0.85,
            'university': 0.90, 'college': 0.85, 'school': 0.75,
            'organization': 0.85, 'foundation': 0.80, 'society': 0.80,
            'association': 0.80, 'lab': 0.75, 'lab.': 0.80
        }

        for keyword, score in institutional_keywords.items():
            if keyword in text_lower:
                # Verifica se a palavra-chave está em contexto institucional
                if self._is_institutional_context(text_lower, keyword):
                    confidence = max(confidence, score)

        # Padrões com códigos/números (confiança moderada)
        if re.search(r'[A-Z]{3,}\s*[0-9]+', text):
            confidence = max(confidence, 0.75)

        return confidence

    def _calculate_conjunto_pessoas_confidence(self, text: str) -> float:
        """
        Calcula confiança de que o texto representa múltiplos nomes próprios de pessoas
        """
        confidence = 0.0

        # Conta separadores que indicam múltiplos nomes
        separators_count = 0

        # Padrão de múltiplos nomes separados por separadores
        if ';' in text:
            separators_count += text.count(';')
            confidence = max(confidence, 0.8)

        if '|' in text:
            separators_count += text.count('|')
            confidence = max(confidence, 0.8)

        # Padrão "et al." indica múltiplas pessoas
        if re.search(r'et\s+al\.?|et\s+alli', text, re.IGNORECASE):
            confidence = max(confidence, 0.9)

        # Múltiplos padrões de nomes de pessoas
        person_patterns = [
            r'[A-ZÀ-Ý][a-zà-ÿç]+,\s*[A-Z]\.([A-Z]\.)*',  # "Silva, J.C."
            r'[A-ZÀ-Ý][a-zà-ÿç]+,\s*[A-Z]{2,4}',         # "Amaral, AG"
            r'[A-Z]\.([A-Z]\.)*\s+[A-ZÀ-Ý][a-zà-ÿç]+',   # "J.C. Silva"
        ]

        matches = 0
        for pattern in person_patterns:
            matches += len(re.findall(pattern, text))

        # Se há múltiplas correspondências de nomes, é conjunto
        if matches > 1:
            confidence = max(confidence, 0.85)

        # Se há múltiplos separadores E padrões de nomes
        if separators_count > 0 and matches > 0:
            confidence = max(confidence, 0.9)

        # Palavras que indicam conjuntos de pessoas específicas
        conjunto_keywords = [
            r'pessoal\s+(do|da|de)\s+.+',        # "Pessoal do Museu Goeldi"
            r'equipe\s+(do|da|de)\s+.+',         # "Equipe do Laboratório"
            r'funcionários\s+(do|da|de)\s+.+',   # "Funcionários do Instituto"
        ]

        text_lower = text.lower()
        for pattern in conjunto_keywords:
            if re.search(pattern, text_lower):
                confidence = max(confidence, 0.85)

        return confidence

    def _calculate_ausencia_coletor_confidence(self, text: str) -> float:
        """
        Calcula confiança de que o texto representa ausência de coletor
        """
        confidence = 0.0
        text_lower = text.lower().strip()

        # Casos específicos de ausência de coletor (alta confiança)
        ausencia_patterns = [
            r'^\?+$',                           # "?" ou "???"
            r'^s/\s*coletor',                   # "s/ coletor", "s/coletor"
            r'^sem\s+coletor',                  # "Sem coletor"
            r'^coletor\s+não\s+identificado',   # "Coletor não identificado"
            r'^não\s+identificado',             # "Não identificado"
            r'^sem\s+informação',               # "Sem informação"
            r'^não\s+informado',                # "Não informado"
            r'^anônimo$',                       # "Anônimo"
            r'^anonimo$',                       # "Anonimo"
            r'^s\.?i\.?$',                      # "S.I." ou "SI"
            r'^n\.?i\.?$',                      # "N.I." ou "NI"
            r'^desconhecido$',                  # "Desconhecido"
            r'^ignorado$',                      # "Ignorado"
            r'^vazio$',                         # "Vazio"
            r'^indefinido$',                    # "Indefinido"
            r'^sem\s+dados',                    # "Sem dados"
            r'^não\s+disponível',               # "Não disponível"
            r'^nd$',                            # "ND"
            r'^na$',                            # "NA"
        ]

        for pattern in ausencia_patterns:
            if re.search(pattern, text_lower):
                return 0.95

        return confidence

    def _is_institutional_context(self, text_lower: str, keyword: str) -> bool:
        """
        Verifica se uma palavra-chave está em contexto institucional válido
        """
        # Palavras que indicam contexto institucional quando próximas da palavra-chave
        institutional_context = [
            'universidade', 'instituto', 'fundacao', 'centro', 'museu',
            'departamento', 'faculdade', 'laboratorio', 'secretaria',
            'ministerio', 'empresa', 'federal', 'estadual', 'municipal',
            'nacional', 'pesquisa', 'ciencias', 'botanica', 'zoologia'
        ]

        # Encontra a posição da palavra-chave
        keyword_pos = text_lower.find(keyword)
        if keyword_pos == -1:
            return False

        # Verifica contexto antes e depois (janela de 50 caracteres)
        context_start = max(0, keyword_pos - 50)
        context_end = min(len(text_lower), keyword_pos + len(keyword) + 50)
        context = text_lower[context_start:context_end]

        # Se encontrar palavras de contexto institucional, é válido
        for ctx_word in institutional_context:
            if ctx_word in context:
                return True

        # Se a palavra-chave está no início ou tem maiúsculas, pode ser institucional
        if keyword_pos <= 5 or keyword.upper() in text_lower.upper():
            return True

        return False

    def _looks_like_person_name(self, text: str) -> bool:
        """
        Verifica se o texto parece ser um nome de pessoa
        """
        # Primeiro verifica se contém palavras que claramente indicam instituições
        institutional_words = [
            'universidade', 'instituto', 'laboratorio', 'centro', 'museu',
            'departamento', 'faculdade', 'empresa', 'fundacao', 'secretaria',
            'ministerio', 'federal', 'estadual', 'municipal', 'nacional',
            'company', 'corporation', 'institute', 'university', 'college',
            'school', 'organization', 'foundation', 'society', 'association',
            'laboratory', 'lab', 'lab.'
        ]

        text_lower = text.lower()
        for word in institutional_words:
            if word in text_lower:
                return False

        # Padrões que indicam nomes de pessoas (incluindo caracteres acentuados)
        person_patterns = [
            r'^[A-ZÀ-Ý][a-zà-ÿç]+,\s*[A-Z]\.([A-Z]\.)*',  # "Silva, J.C."
            r'^[A-ZÀ-Ý][a-zà-ÿç]+,[A-Z]$',                # "Roncoleta,T" (sem espaço)
            r'^[A-Z]\.([A-Z]\.)*\s+[A-ZÀ-Ý][a-zà-ÿç]+',   # "J.C. Silva"
            r'[A-ZÀ-Ý][a-zà-ÿç]+,\s*[A-ZÀ-Ý][a-zà-ÿç]+',  # "Silva, João"
            r'^[A-ZÀ-Ý][a-zà-ÿç]+,\s*[A-Z]{2,4}$',        # "Amaral, AG", "Castro, BM", "Faria, JEQ", "Proença, CEB"
            r'^[A-Z]\.[A-Z]\.\s+[A-ZÀ-Ý][a-zà-ÿç]+(-[A-ZÀ-Ý][a-zà-ÿç]+)?$',  # "G.A. Damasceno-Junior"
            r'^[A-Z]\.([A-Z]\.)*\s+(dos?\s+|das?\s+|de\s+)?[A-ZÀ-Ý][a-zà-ÿç]+$',  # "M.C.F. dos Santos"
            r'^[A-ZÀ-Ý][a-zà-ÿç]+-[A-ZÀ-Ý][a-zà-ÿç]+$',   # "Andrade-Lima"
            r'^[A-ZÀ-Ý][a-zà-ÿç]+\s+[A-ZÀ-Ý][a-zà-ÿç]+\s+[A-ZÀ-Ý][a-zà-ÿç]+$',  # "Lilian Silva Santos"
            r';.*et\s+al\.?',                       # Contém "et al."
            r';\s*[A-ZÀ-Ý][a-zà-ÿç]+',             # Lista de nomes separados por ;
        ]

        # Padrão para nomes simples (dois nomes próprios)
        simple_name_pattern = r'^[A-ZÀ-Ý][a-zà-ÿç]+\s+[A-ZÀ-Ý][a-zà-ÿç]+$'
        if re.match(simple_name_pattern, text):
            # Se já passou pela verificação de palavras institucionais acima, é válido
            return True

        # Verifica padrões especiais de nomes
        # Sobrenomes compostos com hífen
        if re.match(r'^[A-ZÀ-Ý][a-zà-ÿç]+-[A-ZÀ-Ý][a-zà-ÿç]+$', text):
            return True

        # Três nomes (nome + sobrenome + sobrenome)
        if re.match(r'^[A-ZÀ-Ý][a-zà-ÿç]+\s+[A-ZÀ-Ý][a-zà-ÿç]+\s+[A-ZÀ-Ý][a-zà-ÿç]+$', text):
            return True

        for pattern in person_patterns:
            if re.search(pattern, text):
                return True

        # IMPORTANTE: Nomes únicos (sem sobrenome/iniciais) são problemáticos
        # Exemplo: "Edilson", "Maria", "João" sozinhos não são confiáveis
        single_name_pattern = r'^[A-ZÀ-Ý][a-zà-ÿç]+$'
        if re.match(single_name_pattern, text):
            # Nome único - muito baixa confiabilidade para ser pessoa
            return False

        return False

    def _is_person_initials_context(self, text: str) -> bool:
        """
        Verifica se as iniciais estão em contexto de nome de pessoa
        """
        # Padrões que indicam que S.A., etc. são iniciais de pessoa
        initials_context_patterns = [
            r'[A-Z][a-z]+,\s*[A-Z]\.([A-Z]\.)*',  # "Martins, S.A."
            r'^[A-Z]\.([A-Z]\.)*\s+[A-Z][a-z]+',  # "S.A. Martins"
            r';\s*[A-Z][a-z]+,\s*[A-Z]\.([A-Z]\.)*',  # "; Souza, S.A.O."
        ]

        for pattern in initials_context_patterns:
            if re.search(pattern, text):
                return True

        return False

    def _calculate_group_confidence(self, text: str) -> float:
        """
        Calcula confiança de que o texto representa um grupo genérico de pessoas
        (SEM nomes próprios - apenas denominações genéricas)
        """
        confidence = 0.0
        text_lower = text.lower()

        # Grupos de instituições (ex: "Taxonomy Class of Universidade de Brasília")
        institutional_group_patterns = [
            r'.+\s+(of|da|de|do)\s+(universidade|instituto|laboratorio|centro)',
            r'(classe|class|turma|grupo|equipe)\s+.+\s+(universidade|instituto)',
            r'.+\s+(universidade|instituto)\s+(de|do|da)',
        ]

        for pattern in institutional_group_patterns:
            if re.search(pattern, text_lower):
                return 0.90

        # Se contém nomes próprios, NÃO é grupo genérico
        if self._contains_proper_names(text):
            return 0.0

        # Palavras-chave de grupos genéricos (usando word boundaries para evitar falsos positivos)
        group_keywords = [
            (r'\bequipe\b', 0.85), (r'\bgrupo\b', 0.80), (r'\bprojeto\b', 0.75),
            (r'\bpesquisa\b', 0.70), (r'\bestudo\b', 0.65), (r'\balunos\b', 0.90),
            (r'\bturma\b', 0.85), (r'\bcurso\b', 0.75), (r'\bdisciplina\b', 0.80),
            (r'\bcoleta\s+(coletiva|de\s+campo)\b', 0.65), (r'\bcampo\b', 0.60),
            (r'\bcoletor\s+(não\s+identificado|desconhecido)\b', 0.70),
            (r'\bcoletores\s+(não\s+identificados|desconhecidos)\b', 0.75),
            (r'\bbotanica\b', 0.70), (r'\bbotanicos\b', 0.75),
            (r'\bpesquisadores\b', 0.80), (r'\bexpedição\b', 0.75)
        ]

        for pattern, score in group_keywords:
            if re.search(pattern, text_lower):
                confidence = max(confidence, score)

        # Expressões específicas de grupos genéricos (alta confiança)
        generic_expressions = [
            ('pesquisas da biodiversidade', 0.95),
            ('coleta coletiva', 0.95),
            ('não identificado', 0.90),
            ('sem informação', 0.90),
            ('não informado', 0.90),
            ('anônimo', 0.90),
            ('anonimo', 0.90),
            ('equipe de pesquisa', 0.95),
            ('grupo de estudos', 0.95),
            ('alunos da disciplina', 0.95),
            ('projeto de pesquisa', 0.90)
        ]

        for expr, score in generic_expressions:
            if expr in text_lower:
                confidence = max(confidence, score)

        return confidence

    def _contains_proper_names(self, text: str) -> bool:
        """
        Verifica se o texto contém nomes próprios de pessoas
        """
        # Primeiro verifica se contém palavras institucionais
        institutional_words = [
            'universidade', 'instituto', 'laboratorio', 'centro', 'museu',
            'departamento', 'faculdade', 'empresa', 'fundacao', 'secretaria',
            'ministerio', 'federal', 'estadual', 'municipal', 'nacional'
        ]

        text_lower = text.lower()
        for word in institutional_words:
            if word in text_lower:
                return False

        # Padrões que indicam presença de nomes próprios
        proper_name_patterns = [
            r'[A-ZÀ-Ý][a-zà-ÿç]+,\s*[A-Z]\.([A-Z]\.)*',  # "Silva, J.C."
            r'[A-ZÀ-Ý][a-zà-ÿç]+,\s*[A-Z]{2,4}',         # "Amaral, AG"
            r'[A-Z]\.([A-Z]\.)*\s+[A-ZÀ-Ý][a-zà-ÿç]+',   # "J.C. Silva"
            r'^[A-Z]\.[A-Z]\.\s+[A-ZÀ-Ý][a-zà-ÿç]+',     # "G.A. Damasceno"
            r'[A-ZÀ-Ý][a-zà-ÿç]+,\s*[A-ZÀ-Ý][a-zà-ÿç]+', # "Silva, João"
            r'^[A-ZÀ-Ý][a-zà-ÿç]+\s+[A-ZÀ-Ý][a-zà-ÿç]+$', # "João Santos"
        ]

        for pattern in proper_name_patterns:
            if re.search(pattern, text):
                return True

        # Verifica se há múltiplos nomes separados por ;
        if ';' in text:
            parts = text.split(';')
            for part in parts:
                part = part.strip()
                # Se qualquer parte parece um nome próprio
                if re.search(r'[A-ZÀ-Ý][a-zà-ÿç]+', part):
                    return True

        return False

    def _has_multiple_person_names(self, text: str) -> bool:
        """
        Verifica se o texto contém múltiplos nomes de pessoas
        """
        # Padrões que indicam múltiplos nomes
        multiple_names_patterns = [
            r'[A-Z][a-z]+,\s*[A-Z]\.([A-Z]\.)*;\s*[A-Z][a-z]+',  # "Silva, J.; Santos"
            r'[A-Z][a-z]+;\s*[A-Z][a-z]+',                        # "Silva; Santos"
            r'[A-Z][a-z]+,\s*[A-Z]\.([A-Z]\.)*;\s*[A-Z][a-z]+,\s*[A-Z]\.([A-Z]\.)*',  # Múltiplos com iniciais
        ]

        for pattern in multiple_names_patterns:
            if re.search(pattern, text):
                return True

        # Conta vírgulas e pontos-e-vírgulas que separam nomes
        semicolon_count = text.count(';')
        if semicolon_count >= 1:
            # Verifica se há nomes após o ponto-e-vírgula
            parts = text.split(';')
            person_parts = 0
            for part in parts:
                part = part.strip()
                if re.search(r'^[A-Z][a-z]+', part):  # Começa com nome próprio
                    person_parts += 1

            return person_parts >= 2

        return False

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

        # Formato: iniciais coladas com sobrenome (ex: "R.C.Forzza", "R.Forzza")
        elif re.match(r'^[A-ZÀ-Ÿ]\.([A-ZÀ-Ÿ]\.)*[A-ZÀ-Ÿ][a-zà-ÿ]+$', nome):
            # Separa iniciais do sobrenome
            # Encontra onde começam as letras minúsculas (início do sobrenome)
            match = re.match(r'^([A-ZÀ-Ÿ]\.(?:[A-ZÀ-Ÿ]\.)*)([A-ZÀ-Ÿ][a-zà-ÿ]+)$', nome)
            if match:
                iniciais_str = match.group(1)
                sobrenome = match.group(2)

                # Extrai iniciais
                iniciais = re.findall(r'([A-ZÀ-Ÿ])\.?', iniciais_str)

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

        PADRÃO DE CAPITALIZAÇÃO:
        - Title Case: primeira letra maiúscula, resto minúsculo
        - Acrônimos conhecidos mantêm formato original
        - Preposições ficam minúsculas (de, da, do, dos, das)
        """
        sobrenome = componentes['sobrenome']
        iniciais = componentes['iniciais']

        if not sobrenome:
            return ""

        # Aplica padronização de capitalização
        sobrenome_padronizado = self._padronizar_capitalizacao(sobrenome)

        if iniciais:
            iniciais_str = '.'.join([i.upper() for i in iniciais]) + '.'
            return f"{sobrenome_padronizado}, {iniciais_str}"
        else:
            return sobrenome_padronizado

    def _padronizar_capitalizacao(self, texto: str) -> str:
        """
        Padroniza a capitalização de um texto

        REGRAS:
        - Title Case geral
        - Acrônimos conhecidos mantêm maiúsculas
        - Preposições em minúsculas
        - Nomes compostos com hífen mantêm cada parte
        """
        if not texto:
            return ""

        # Acrônimos conhecidos que devem ficar em maiúsculas
        acronimos_conhecidos = {
            'USP', 'UFRJ', 'UFC', 'UFMG', 'UFPE', 'UFSC', 'UFPR', 'UFRGS',
            'EMBRAPA', 'INPA', 'IBAMA', 'ICMBIO', 'CNPQ', 'CAPES', 'FAPESP',
            'RB', 'SP', 'MG', 'HB', 'HUEFS', 'ALCB', 'VIC', 'HRCB', 'UFPI'
        }

        # Se é um acrônimo conhecido, mantém maiúsculo
        if texto.upper() in acronimos_conhecidos:
            return texto.upper()

        # Preposições que ficam minúsculas
        preposicoes = {'de', 'da', 'do', 'dos', 'das', 'e', 'em', 'na', 'no', 'nas', 'nos'}

        # Divide em palavras
        palavras = texto.split()
        palavras_formatadas = []

        for i, palavra in enumerate(palavras):
            # Remove pontuação para verificação
            palavra_limpa = re.sub(r'[^\w\-]', '', palavra)

            # Se contém hífen, trata cada parte separadamente
            if '-' in palavra:
                partes = palavra.split('-')
                partes_formatadas = []
                for parte in partes:
                    if parte.upper() in acronimos_conhecidos:
                        partes_formatadas.append(parte.upper())
                    elif parte.lower() in preposicoes and i > 0:  # Preposições não no início
                        partes_formatadas.append(parte.lower())
                    else:
                        partes_formatadas.append(parte.capitalize())
                palavras_formatadas.append('-'.join(partes_formatadas))
            # Se é acrônimo conhecido
            elif palavra_limpa.upper() in acronimos_conhecidos:
                palavras_formatadas.append(palavra_limpa.upper())
            # Se é preposição e não é a primeira palavra
            elif palavra.lower() in preposicoes and i > 0:
                palavras_formatadas.append(palavra.lower())
            # Caso geral: Title Case
            else:
                palavras_formatadas.append(palavra.capitalize())

        return ' '.join(palavras_formatadas)

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

    def __init__(self, similarity_threshold: float = 0.85, confidence_threshold: float = 0.7, mongo_manager=None):
        """
        Inicializa o canonizador

        Args:
            similarity_threshold: Limiar de similaridade para agrupamento
            confidence_threshold: Limiar de confiança para canonicalização automática
            mongo_manager: Gerenciador MongoDB para consultas persistentes
        """
        self.similarity_threshold = similarity_threshold
        self.confidence_threshold = confidence_threshold
        self.mongo_manager = mongo_manager
        self.coletores_canonicos = {}  # Cache em memória para performance
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
        Consulta tanto cache em memória quanto MongoDB para encontrar coletores existentes
        """
        candidatos = []
        sobrenome_norm = nome_normalizado['sobrenome_normalizado']
        soundex_atual = nome_normalizado['chaves_busca']['soundex']
        metaphone_atual = nome_normalizado['chaves_busca']['metaphone']

        # 1. Busca no cache em memória (mais rápido)
        if sobrenome_norm in self.coletores_canonicos:
            candidatos.append(self.coletores_canonicos[sobrenome_norm])

        # 2. Busca no MongoDB por sobrenome exato
        if self.mongo_manager:
            try:
                # Busca por sobrenome normalizado exato
                mongo_candidatos = self.mongo_manager.buscar_coletores_por_sobrenome(sobrenome_norm)
                for candidato in mongo_candidatos:
                    # Evita duplicatas
                    if not any(c.get('_id') == candidato.get('_id') for c in candidatos):
                        candidatos.append(candidato)
                        # Adiciona ao cache para próximas consultas
                        self.coletores_canonicos[candidato['sobrenome_normalizado']] = candidato

                # 3. Busca por similaridade fonética no MongoDB
                if soundex_atual or metaphone_atual:
                    mongo_foneticos = self.mongo_manager.buscar_coletores_por_fonetica(soundex_atual, metaphone_atual)
                    for candidato in mongo_foneticos:
                        # Evita duplicatas e auto-match
                        if (candidato['sobrenome_normalizado'] != sobrenome_norm and
                            not any(c.get('_id') == candidato.get('_id') for c in candidatos)):
                            candidatos.append(candidato)
                            # Adiciona ao cache
                            self.coletores_canonicos[candidato['sobrenome_normalizado']] = candidato

            except Exception as e:
                logger.warning(f"Erro ao buscar candidatos no MongoDB: {e}")

        # 4. Busca fonética no cache em memória (fallback)
        for coletor in self.coletores_canonicos.values():
            if coletor['sobrenome_normalizado'] == sobrenome_norm:
                continue  # Já adicionado acima

            # Verifica se tem mesma chave fonética
            if (soundex_atual and coletor['indices_busca']['soundex'] == soundex_atual) or \
               (metaphone_atual and coletor['indices_busca']['metaphone'] == metaphone_atual):
                if not any(c.get('_id') == coletor.get('_id') for c in candidatos):
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
            'kingdom': nome_normalizado.get('kingdom', []),
            'tipo_coletor': self._classificar_tipo_coletor(nome_normalizado),
            'confianca_tipo_coletor': self._calcular_confianca_tipo_coletor(nome_normalizado),
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

        # Atualiza kingdom
        kingdom_novos = nome_normalizado.get('kingdom', [])
        if not isinstance(candidato['kingdom'], list):
            candidato['kingdom'] = []

        for kingdom in kingdom_novos:
            if kingdom and kingdom not in candidato['kingdom']:
                candidato['kingdom'].append(kingdom)

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

    def _classificar_tipo_coletor(self, nome_normalizado: Dict[str, any]) -> str:
        """
        Classifica o tipo de coletor baseado nas características do nome
        """
        nome_limpo = nome_normalizado.get('nome_limpo', '').lower()
        sobrenome = nome_normalizado.get('sobrenome', '').lower()
        iniciais = nome_normalizado.get('iniciais', [])

        # Palavras que indicam empresa/instituição (usar word boundaries)
        palavras_instituicao_exatas = {
            'universidade', 'university', 'faculdade', 'college', 'instituto', 'institute',
            'laboratório', 'laboratory', 'lab.', 'museu', 'museum', 'herbário', 'herbarium',
            'empresa', 'company', 'corporation', 'ltda.', 'ltd.', 'inc.', ' sa ', ' cia ',
            'embrapa', 'inpa', 'ibama', 'icmbio', 'cnpq', 'capes', 'fapesp'
        }

        # Acrônimos de universidades (busca exata)
        acronimos_universidades = {
            'usp', 'ufrj', 'ufmg', 'ufpe', 'ufc', 'ufsc', 'ufpr', 'ufrgs', 'ufpi'
        }

        # Palavras que indicam múltiplas pessoas
        palavras_multiplas = {'&', 'e', 'and', 'com', 'with', 'et al', 'etal', 'al.'}

        # Palavras que indicam ausência
        palavras_ausencia = {'?', 'sem coletor', 'não identificado', 's.i.', 'unknown', 'anonymous'}

        # Verifica ausência de coletor
        for palavra in palavras_ausencia:
            if palavra in nome_limpo:
                return 'ausencia_coletor'

        # Verifica acrônimos de universidades primeiro (match exato de palavras)
        palavras = nome_limpo.split()
        for palavra in palavras:
            if palavra in acronimos_universidades:
                return 'empresa_instituicao'

        # Verifica empresa/instituição
        for palavra in palavras_instituicao_exatas:
            if palavra in nome_limpo or palavra in sobrenome:
                return 'empresa_instituicao'

        # Verifica múltiplas pessoas (deve vir depois de instituição)
        for palavra in palavras_multiplas:
            if palavra in nome_limpo:
                if palavra in ['et al', 'etal', 'al.']:
                    return 'grupo_pessoas'
                else:
                    return 'conjunto_pessoas'

        # Se tem iniciais, provavelmente é pessoa
        if iniciais:
            return 'pessoa'

        # Padrões que indicam pessoa (sobrenome conhecido)
        if len(sobrenome) > 2 and sobrenome.isalpha():
            return 'pessoa'

        # Default para pessoa
        return 'pessoa'

    def _calcular_confianca_tipo_coletor(self, nome_normalizado: Dict[str, any]) -> float:
        """
        Calcula a confiança na classificação do tipo de coletor
        """
        nome_limpo = nome_normalizado.get('nome_limpo', '').lower()
        sobrenome = nome_normalizado.get('sobrenome', '').lower()
        iniciais = nome_normalizado.get('iniciais', [])
        tipo = self._classificar_tipo_coletor(nome_normalizado)

        if tipo == 'ausencia_coletor':
            # Alta confiança para casos óbvios
            if any(palavra in nome_limpo for palavra in ['?', 'sem coletor', 'não identificado']):
                return 0.95
            return 0.8

        elif tipo == 'empresa_instituicao':
            # Alta confiança para acrônimos conhecidos
            acromimos_conhecidos = {'usp', 'embrapa', 'inpa', 'ibama', 'cnpq'}
            if any(acr in nome_limpo for acr in acromimos_conhecidos):
                return 0.98

            # Boa confiança para palavras explícitas
            palavras_explicitas = {'universidade', 'laboratório', 'museu', 'empresa'}
            if any(palavra in nome_limpo for palavra in palavras_explicitas):
                return 0.85

            return 0.7

        elif tipo == 'conjunto_pessoas':
            # Confiança baseada em indicadores claros
            if '&' in nome_limpo or ' e ' in nome_limpo:
                return 0.9
            return 0.75

        elif tipo == 'grupo_pessoas':
            # Alta confiança para "et al"
            if 'et al' in nome_limpo or 'etal' in nome_limpo:
                return 0.95
            return 0.8

        elif tipo == 'pessoa':
            # Confiança baseada na qualidade do nome
            base_confianca = 0.6

            # Tem iniciais: +0.2
            if iniciais:
                base_confianca += 0.2

            # Sobrenome bem formado: +0.1
            if len(sobrenome) > 2 and sobrenome.isalpha():
                base_confianca += 0.1

            # Nome completo bem formado: +0.1
            if len(nome_limpo.split()) >= 2:
                base_confianca += 0.1

            return min(base_confianca, 0.95)

        return 0.5


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

        self.client = MongoClient(
            connection_string,
            serverSelectionTimeoutMS=60000,  # 60 segundos para seleção de servidor
            socketTimeoutMS=60000,           # 60 segundos para operações de socket
            connectTimeoutMS=30000,          # 30 segundos para conectar
            maxPoolSize=10,                  # Pool de conexões
            retryWrites=True                 # Retry automático para writes
        )
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

    def obter_todos_recordedby(self, batch_size: int = 10000, deve_parar_callback=None):
        """
        Gerador que retorna todos os valores de recordedBy em lotes

        Args:
            batch_size: Tamanho do lote
            deve_parar_callback: Função que retorna True se deve parar

        Yields:
            Lotes de documentos com recordedBy
        """
        try:
            logger.info("Iniciando processamento de documentos com recordedBy...")

            processed = 0
            batch_count = 0

            # Adiciona timeout para evitar travamento
            cursor = self.ocorrencias.find(
                {"recordedBy": {"$exists": True, "$ne": None, "$ne": ""}},
                {"recordedBy": 1, "kingdom": 1, "_id": 1}
            ).batch_size(batch_size).max_time_ms(30000)  # Timeout de 30 segundos

            batch = []
            doc_count = 0

            for doc in cursor:
                # Verifica se deve parar a cada 1000 documentos
                if deve_parar_callback and doc_count % 1000 == 0:
                    if deve_parar_callback():
                        logger.warning("Interrupção detectada durante leitura de documentos")
                        if batch:  # Retorna lote parcial se houver
                            yield batch
                        return

                batch.append(doc)
                doc_count += 1

                if len(batch) >= batch_size:
                    processed += len(batch)
                    batch_count += 1
                    logger.info(f"Processando lote {batch_count}: {processed} registros processados")
                    yield batch
                    batch = []

            # Último lote (se houver)
            if batch:
                processed += len(batch)
                batch_count += 1
                logger.info(f"Processando último lote {batch_count}: {processed} registros processados")
                yield batch

            logger.info(f"Processamento concluído: {processed} registros em {batch_count} lotes")

        except Exception as e:
            logger.error(f"Erro ao obter dados: {e}")
            raise

    def salvar_coletor_canonico(self, coletor_canonico: Dict[str, any]) -> bool:
        """
        Salva ou atualiza um coletor canônico no MongoDB
        Implementa merge inteligente de variações para deduplicação com retry logic

        Args:
            coletor_canonico: Dados do coletor canônico

        Returns:
            True se salvou com sucesso
        """
        import time
        import random
        from pymongo.errors import OperationFailure, NetworkTimeout, ServerSelectionTimeoutError

        max_retries = 3
        base_delay = 1.0

        for tentativa in range(max_retries):
            try:
                # Sanitiza dados antes de salvar
                coletor_canonico_sanitizado = self._sanitizar_dados_mongodb(coletor_canonico)

                filtro = {"sobrenome_normalizado": coletor_canonico_sanitizado["sobrenome_normalizado"]}

                # Verifica se já existe um coletor com o mesmo sobrenome normalizado
                # Adiciona timeout explícito para find_one
                existente = self.coletores.find_one(filtro, max_time_ms=10000)

                if existente:
                    # Faz merge das variações
                    self._merge_variacoes(existente, coletor_canonico_sanitizado)

                    # Sanitiza dados existentes antes de salvar
                    existente_sanitizado = self._sanitizar_dados_mongodb(existente)

                    # Atualiza o documento existente
                    resultado = self.coletores.replace_one(
                        {"_id": existente["_id"]},
                        existente_sanitizado
                    )
                    logger.debug(f"Coletor atualizado (merge): {existente['coletor_canonico']}")
                else:
                    # Insere novo documento
                    resultado = self.coletores.insert_one(coletor_canonico_sanitizado)
                    logger.debug(f"Novo coletor inserido: {coletor_canonico_sanitizado['coletor_canonico']}")

                return True

            except (OperationFailure, NetworkTimeout, ServerSelectionTimeoutError) as e:
                if "operation cancelled" in str(e).lower() or "timeout" in str(e).lower():
                    if tentativa < max_retries - 1:
                        # Backoff exponencial com jitter
                        delay = base_delay * (2 ** tentativa) + random.uniform(0, 1)
                        logger.warning(f"Timeout na tentativa {tentativa + 1}/{max_retries}. Tentando novamente em {delay:.1f}s...")
                        time.sleep(delay)
                        continue
                    else:
                        logger.error(f"Falhou após {max_retries} tentativas. Erro: {e}")
                        return False
                else:
                    # Erro não relacionado a timeout, não tenta novamente
                    logger.error(f"Erro não recuperável ao salvar coletor: {e}")
                    return False
            except Exception as e:
                logger.error(f"Erro inesperado ao salvar coletor canônico: {e}")
                return False

        return False

    def _sanitizar_dados_mongodb(self, dados: Dict[str, any]) -> Dict[str, any]:
        """
        Sanitiza dados para compatibilidade com MongoDB
        Converte tipos problemáticos que podem causar erro de 8-byte ints
        """
        import copy
        from datetime import datetime

        dados_limpos = copy.deepcopy(dados)

        def sanitizar_recursivo(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    obj[key] = sanitizar_recursivo(value)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    obj[i] = sanitizar_recursivo(item)
            elif isinstance(obj, datetime):
                # Converte datetime para timestamp Unix (segundos) como float
                return obj.timestamp()
            elif isinstance(obj, int):
                # Verifica se o inteiro está dentro do limite de 64 bits
                if obj > 9223372036854775807 or obj < -9223372036854775808:
                    # Converte para float se exceder o limite
                    return float(obj)
            return obj

        return sanitizar_recursivo(dados_limpos)

    def _merge_variacoes(self, existente: Dict[str, any], novo: Dict[str, any]):
        """
        Faz merge das variações entre um coletor existente e um novo
        """
        from datetime import datetime

        # Merge das variações
        variacoes_existentes = {v['forma_original']: v for v in existente['variacoes']}

        for nova_variacao in novo['variacoes']:
            forma = nova_variacao['forma_original']

            if forma in variacoes_existentes:
                # Atualiza variação existente
                var_existente = variacoes_existentes[forma]

                # VALIDAÇÃO: Garante que frequência é um inteiro pequeno
                freq_existente = var_existente.get('frequencia', 1)
                freq_nova = nova_variacao.get('frequencia', 1)

                # Se valores suspeitos (muito grandes), reseta para 1
                if isinstance(freq_existente, (int, float)) and freq_existente > 1000000:
                    logger.warning(f"Frequência suspeita detectada: {freq_existente}. Resetando para 1.")
                    freq_existente = 1

                if isinstance(freq_nova, (int, float)) and freq_nova > 1000000:
                    logger.warning(f"Frequência nova suspeita detectada: {freq_nova}. Resetando para 1.")
                    freq_nova = 1

                var_existente['frequencia'] = freq_existente + freq_nova
                var_existente['ultima_ocorrencia'] = nova_variacao['ultima_ocorrencia']
            else:
                # Valida nova variação antes de adicionar
                nova_var_copy = nova_variacao.copy()
                freq = nova_var_copy.get('frequencia', 1)
                if isinstance(freq, (int, float)) and freq > 1000000:
                    logger.warning(f"Frequência suspeita em nova variação: {freq}. Resetando para 1.")
                    nova_var_copy['frequencia'] = 1

                # Adiciona nova variação
                existente['variacoes'].append(nova_var_copy)

        # Atualiza totais
        existente['total_registros'] = sum(v['frequencia'] for v in existente['variacoes'])

        # Atualiza metadados
        existente['metadados']['ultima_atualizacao'] = datetime.now()

        # Escolhe o melhor nome canônico (mais específico ganha)
        if self._nome_mais_especifico(novo['coletor_canonico'], existente['coletor_canonico']):
            existente['coletor_canonico'] = novo['coletor_canonico']
            if 'iniciais' in novo:
                existente['iniciais'] = novo['iniciais']

    def _nome_mais_especifico(self, nome1: str, nome2: str) -> bool:
        """
        Determina se nome1 é mais específico que nome2
        """
        # Conta iniciais e informações
        iniciais1 = len([c for c in nome1 if c.isupper() and c != nome1[0]])
        iniciais2 = len([c for c in nome2 if c.isupper() and c != nome2[0]])

        # Mais iniciais = mais específico
        if iniciais1 != iniciais2:
            return iniciais1 > iniciais2

        # Formato "Sobrenome, I." é mais específico que só "Sobrenome"
        tem_virgula1 = ',' in nome1
        tem_virgula2 = ',' in nome2

        if tem_virgula1 != tem_virgula2:
            return tem_virgula1

        # Por último, o mais longo
        return len(nome1) > len(nome2)

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

    def limpar_checkpoint(self) -> bool:
        """
        Remove dados de checkpoint (usado para reiniciar processamento)

        Returns:
            True se removeu com sucesso
        """
        try:
            resultado = self.db.checkpoints.delete_many({"tipo": "canonicalizacao"})
            logger.info(f"Checkpoints removidos: {resultado.deleted_count} documentos")
            return True

        except Exception as e:
            logger.error(f"Erro ao limpar checkpoint: {e}")
            return False

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

    def buscar_coletores_por_sobrenome(self, sobrenome_normalizado: str) -> List[Dict[str, any]]:
        """
        Busca coletores por sobrenome normalizado exato

        Args:
            sobrenome_normalizado: Sobrenome normalizado para busca

        Returns:
            Lista de coletores encontrados
        """
        try:
            cursor = self.coletores.find(
                {"sobrenome_normalizado": sobrenome_normalizado}
            )
            return list(cursor)
        except Exception as e:
            logger.error(f"Erro ao buscar coletores por sobrenome '{sobrenome_normalizado}': {e}")
            return []

    def buscar_coletores_por_fonetica(self, soundex: str = None, metaphone: str = None) -> List[Dict[str, any]]:
        """
        Busca coletores por similaridade fonética

        Args:
            soundex: Código Soundex para busca
            metaphone: Código Metaphone para busca

        Returns:
            Lista de coletores encontrados
        """
        try:
            filtros = []

            if soundex:
                filtros.append({"indices_busca.soundex": soundex})

            if metaphone:
                filtros.append({"indices_busca.metaphone": metaphone})

            if not filtros:
                return []

            # Busca por qualquer dos códigos fonéticos
            query = {"$or": filtros} if len(filtros) > 1 else filtros[0]

            cursor = self.coletores.find(query).limit(20)  # Limita resultados para performance
            return list(cursor)

        except Exception as e:
            logger.error(f"Erro ao buscar coletores por fonética (soundex={soundex}, metaphone={metaphone}): {e}")
            return []

    def buscar_coletor_por_id(self, coletor_id) -> Dict[str, any]:
        """
        Busca um coletor específico por ID

        Args:
            coletor_id: ID do coletor

        Returns:
            Dados do coletor ou None se não encontrado
        """
        try:
            return self.coletores.find_one({"_id": coletor_id})
        except Exception as e:
            logger.error(f"Erro ao buscar coletor por ID '{coletor_id}': {e}")
            return None

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