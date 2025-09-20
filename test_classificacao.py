#!/usr/bin/env python3
"""
Teste rápido para validar as correções na classificação de entidades
"""

import sys
import os

# Adiciona o diretório src ao path para importar módulos
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'config'))

from config.mongodb_config import SEPARATOR_PATTERNS, GROUP_PATTERNS, INSTITUTION_PATTERNS
from src.canonicalizador_coletores import AtomizadorNomes

def test_classificacao():
    """
    Testa a classificação com exemplos problemáticos
    """
    atomizador = AtomizadorNomes(SEPARATOR_PATTERNS, GROUP_PATTERNS, INSTITUTION_PATTERNS)

    # Casos que estavam sendo classificados incorretamente como empresa
    casos_problema = [
        "C.S.A. Martins",
        "Chiea, S.A.C.; et al.",
        "Souza, S.A.O. de",
        "Paciência, M.B.; Frana, S.A.; Areias, G.",
        "Proença, C; Harris, SA",
        "Rodrigues, S.A."
    ]

    # Casos que devem ser classificados como grupo_pessoas
    casos_grupo = [
        "Silva, J.; Santos, M.; et al.",
        "Equipe de pesquisa de campo",
        "Alunos da disciplina de botânica",
        "Pesquisas da Biodiversidade"
    ]

    # Casos que devem ser classificados como empresa_instituicao
    casos_empresa = [
        "EMBRAPA",
        "USP",
        "INPA",
        "Instituto de Botânica S.A.",
        "Universidade Federal do Rio de Janeiro",
        "RB"
    ]

    print("="*80)
    print("TESTE DE CLASSIFICAÇÃO DE ENTIDADES")
    print("="*80)

    print("\n1. CASOS QUE ESTAVAM SENDO CLASSIFICADOS INCORRETAMENTE COMO EMPRESA:")
    print("-" * 70)
    for caso in casos_problema:
        classificacao = atomizador.classify_entity_type(caso)
        tipo = classificacao['tipo']
        confianca = classificacao['confianca_classificacao']

        status = "CORRETO" if tipo == 'pessoa' else "ERRO"
        print(f"{status:<8} | {caso:<35} | {tipo:<20} | {confianca:.3f}")

    print("\n2. CASOS QUE DEVEM SER CLASSIFICADOS COMO GRUPO DE PESSOAS:")
    print("-" * 70)
    for caso in casos_grupo:
        classificacao = atomizador.classify_entity_type(caso)
        tipo = classificacao['tipo']
        confianca = classificacao['confianca_classificacao']

        status = "CORRETO" if tipo == 'grupo_pessoas' else "ERRO"
        print(f"{status:<8} | {caso:<35} | {tipo:<20} | {confianca:.3f}")

    print("\n3. CASOS QUE DEVEM SER CLASSIFICADOS COMO EMPRESA/INSTITUIÇÃO:")
    print("-" * 70)
    for caso in casos_empresa:
        classificacao = atomizador.classify_entity_type(caso)
        tipo = classificacao['tipo']
        confianca = classificacao['confianca_classificacao']

        status = "CORRETO" if tipo == 'empresa_instituicao' else "ERRO"
        print(f"{status:<8} | {caso:<35} | {tipo:<20} | {confianca:.3f}")

    print("\n" + "="*80)

if __name__ == "__main__":
    test_classificacao()