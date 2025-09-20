"""
Configuração centralizada de logging
"""
import logging
import os


def configurar_logging_padrao(nome_arquivo: str = None, nivel_console: str = "INFO", nivel_arquivo: str = "INFO"):
    """
    Configura logging padrão para os scripts

    Args:
        nome_arquivo: Nome do arquivo de log (opcional)
        nivel_console: Nível de log para console (DEBUG, INFO, WARNING, ERROR)
        nivel_arquivo: Nível de log para arquivo (DEBUG, INFO, WARNING, ERROR)
    """
    # Mapeia strings para níveis de logging
    levels = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR
    }

    # Formatter padrão
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Logger principal
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # Nível mais baixo para capturar tudo

    # Remove handlers existentes para evitar duplicação
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Handler para console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(levels.get(nivel_console.upper(), logging.INFO))
    logger.addHandler(console_handler)

    # Handler para arquivo (se especificado)
    if nome_arquivo:
        # Garante que o diretório existe
        log_dir = os.path.dirname(nome_arquivo)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        file_handler = logging.FileHandler(nome_arquivo, encoding='utf-8')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(levels.get(nivel_arquivo.upper(), logging.INFO))
        logger.addHandler(file_handler)

    # Silencia logs verbosos de bibliotecas externas
    silenciar_logs_externos()

    return logger


def silenciar_logs_externos():
    """
    Configura níveis de log para bibliotecas externas verbosas
    """
    # MongoDB/PyMongo
    logging.getLogger('pymongo').setLevel(logging.WARNING)
    logging.getLogger('pymongo.command').setLevel(logging.WARNING)
    logging.getLogger('pymongo.connection').setLevel(logging.WARNING)
    logging.getLogger('pymongo.server').setLevel(logging.WARNING)
    logging.getLogger('pymongo.topology').setLevel(logging.WARNING)
    logging.getLogger('pymongo.pool').setLevel(logging.WARNING)

    # Outras bibliotecas que podem ser verbosas
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)


def configurar_logging_debug():
    """
    Configuração de logging para debug (mais verboso)
    """
    return configurar_logging_padrao(
        nome_arquivo='../logs/debug.log',
        nivel_console="DEBUG",
        nivel_arquivo="DEBUG"
    )


def configurar_logging_producao():
    """
    Configuração de logging para produção (menos verboso)
    """
    return configurar_logging_padrao(
        nome_arquivo='../logs/producao.log',
        nivel_console="INFO",
        nivel_arquivo="INFO"
    )


# Configuração padrão para scripts
def get_logger(nome_script: str):
    """
    Retorna logger configurado para um script específico

    Args:
        nome_script: Nome do script (ex: 'processar_coletores', 'analise_coletores')
    """
    configurar_logging_padrao(f'../logs/{nome_script}.log')
    return logging.getLogger(nome_script)