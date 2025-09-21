#!/usr/bin/env python3
"""
Script para testar a correção da classificação de coletores
"""

import sys
import os

# Adiciona o diretório do projeto ao path
sys.path.append(os.path.dirname(__file__))

from config.mongodb_config import SEPARATOR_PATTERNS, GROUP_PATTERNS, INSTITUTION_PATTERNS
from src.canonicalizador_coletores import AtomizadorNomes

def test_classification_fixes():
    """
    Testa os casos problemáticos que foram corrigidos
    """
    print("=" * 60)
    print("TESTE: CORREÇÃO DA CLASSIFICAÇÃO DE COLETORES")
    print("=" * 60)

    atomizador = AtomizadorNomes(SEPARATOR_PATTERNS, GROUP_PATTERNS, INSTITUTION_PATTERNS)

    # Casos problemáticos identificados
    casos_teste = [
        "Labiak, P.H.",
        "Paulo Henrique Labiak Evangelista",
        "Lucena Neto, SA",
        "Silva, J.A.",
        "Santos, M.C.",
        "Oliveira, R.S.",
        "USP",  # Este deve continuar sendo instituição
        "EMBRAPA",  # Este deve continuar sendo instituição
        "Universidade Federal",  # Este deve continuar sendo instituição
        "Equipe de campo",  # Este deve ser grupo
    ]

    print("Testando classificação dos casos corrigidos:")
    print()

    for caso in casos_teste:
        resultado = atomizador.classify_entity_type(caso)
        tipo = resultado['tipo']
        confianca = resultado['confianca_classificacao']

        # Determina se o resultado está correto
        if caso in ["Labiak, P.H.", "Paulo Henrique Labiak Evangelista", "Lucena Neto, SA",
                   "Silva, J.A.", "Santos, M.C.", "Oliveira, R.S."]:
            esperado = "pessoa"
        elif caso in ["USP", "EMBRAPA"]:
            esperado = "empresa_instituicao"
        elif caso == "Universidade Federal":
            esperado = "empresa_instituicao"
        elif caso == "Equipe de campo":
            esperado = "grupo_pessoas"
        else:
            esperado = "desconhecido"

        status = "CORRETO" if tipo == esperado else "INCORRETO"

        print(f"'{caso}' -> {tipo} (confiança: {confianca:.2f}) {status}")
        if tipo != esperado and esperado != "desconhecido":
            print(f"  Esperado: {esperado}")
        print()

    print("=" * 60)
    print("TESTE CONCLUÍDO")
    print("=" * 60)

if __name__ == "__main__":
    test_classification_fixes()