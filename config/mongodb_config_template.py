"""
Configuração para conexão com MongoDB
Template de configuração - copie para mongodb_config.py e configure suas credenciais
"""
import os

# Configurações do MongoDB
MONGODB_CONFIG = {
    'connection_string': os.getenv('MONGODB_CONNECTION_STRING', 'mongodb://usuario:senha@host:porta/?authSource=admin'),
    'database_name': 'dwc2json',
    'collections': {
        'ocorrencias': 'ocorrencias',
        'coletores': 'coletores'
    },
    'timeout': 30000,  # 30 segundos
    'max_pool_size': 100
}

# Configurações do algoritmo
ALGORITHM_CONFIG = {
    'batch_size': 10000,
    'similarity_threshold': 0.85,
    'confidence_threshold': 0.7,
    'levenshtein_max_distance': 3,
    'sample_size': 100000,  # Para análise exploratória
    'checkpoint_interval': 50000  # Salvar checkpoint a cada N registros
}

# Configurações de logging
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file_path': 'logs/canonicalizacao.log',
    'max_bytes': 10485760,  # 10MB
    'backup_count': 5
}

# Padrões regex para separação de múltiplos coletores
SEPARATOR_PATTERNS = [
    r'\s*[&e]\s+',           # & ou e
    r'\s*and\s+',            # and
    r'\s*;\s*',              # ;
    r'\s*,\s*(?=[A-Z])',     # , seguido de letra maiúscula
    r'\s*et\s+al\.?\s*',     # et al.
    r'\s*e\s+col\.?\s*',     # e col.
    r'\s*e\s+cols\.?\s*',    # e cols.
    r'\s*com\s+',            # com
    r'\s*with\s+',           # with
]

# Padrões para limpeza de nomes
CLEANUP_PATTERNS = {
    'remove_collectors_numbers': r'\s*[0-9]+\s*$',  # Números no final
    'remove_extra_spaces': r'\s+',                   # Múltiplos espaços
    'remove_brackets': r'[\[\](){}]',               # Colchetes e parênteses
    'remove_special_chars': r'[^\w\s\.,\-]',        # Caracteres especiais exceto vírgula, ponto e hífen
}

# Configurações para canonicalização
CANONICALIZATION_CONFIG = {
    'min_surname_length': 2,
    'max_initials': 5,
    'use_soundex': True,
    'use_metaphone': True,
    'manual_review_threshold': 0.5,  # Casos com confiança menor que isso precisam revisão manual
}