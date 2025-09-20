#!/usr/bin/env python3
"""
Teste para validar o sistema de 5 categorias
"""

import sys
import os

# Adiciona o diretório src ao path para importar módulos
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'config'))

from config.mongodb_config import SEPARATOR_PATTERNS, GROUP_PATTERNS, INSTITUTION_PATTERNS
from src.canonicalizador_coletores import AtomizadorNomes

def test_5_categorias():
    atomizador = AtomizadorNomes(SEPARATOR_PATTERNS, GROUP_PATTERNS, INSTITUTION_PATTERNS)

    print("TESTE DAS 5 CATEGORIAS:")
    print("="*80)

    # 1. Pessoas individuais
    print("\n1. PESSOAS INDIVIDUAIS:")
    print("-" * 50)
    pessoas = [
        "Roncoleta,T",
        "G.A. Damasceno-Junior",
        "Lilian Silva Santos",
        "Andrade-Lima",
        "João Santos"
    ]

    for pessoa in pessoas:
        result = atomizador.classify_entity_type(pessoa)
        status = "OK" if result['tipo'] == 'pessoa' else "ERRO"
        print(f"{status:<4} {pessoa:<30} -> {result['tipo']:<20} ({result['confianca_classificacao']:.3f})")

    # 2. Conjunto de pessoas
    print("\n2. CONJUNTO DE PESSOAS:")
    print("-" * 50)
    conjuntos = [
        "Pessoal do Museu Goeldi",
        "Silva, J.; Santos, M.",
        "Nome1 | Nome2 | Nome3",
        "Equipe do Laboratório",
        "Silva, J.; Santos, M.; et al."
    ]

    for conjunto in conjuntos:
        result = atomizador.classify_entity_type(conjunto)
        status = "OK" if result['tipo'] == 'conjunto_pessoas' else "ERRO"
        print(f"{status:<4} {conjunto:<30} -> {result['tipo']:<20} ({result['confianca_classificacao']:.3f})")

    # 3. Grupos genéricos
    print("\n3. GRUPOS GENÉRICOS:")
    print("-" * 50)
    grupos = [
        "Alunos da disciplina de botânica",
        "Taxonomy Class of Universidade de Brasília",
        "Equipe de pesquisa",
        "Projeto de biodiversidade"
    ]

    for grupo in grupos:
        result = atomizador.classify_entity_type(grupo)
        status = "OK" if result['tipo'] == 'grupo_pessoas' else "ERRO"
        print(f"{status:<4} {grupo:<40} -> {result['tipo']:<20} ({result['confianca_classificacao']:.3f})")

    # 4. Empresas/Instituições
    print("\n4. EMPRESAS/INSTITUIÇÕES:")
    print("-" * 50)
    instituicoes = [
        "EMBRAPA",
        "USP",
        "Universidade de Brasília",
        "Instituto de Botânica"
    ]

    for instituicao in instituicoes:
        result = atomizador.classify_entity_type(instituicao)
        status = "OK" if result['tipo'] == 'empresa_instituicao' else "ERRO"
        print(f"{status:<4} {instituicao:<30} -> {result['tipo']:<20} ({result['confianca_classificacao']:.3f})")

    # 5. Ausência de coletor
    print("\n5. AUSÊNCIA DE COLETOR:")
    print("-" * 50)
    ausencias = [
        "?",
        "s/ coletor",
        "Sem coletor",
        "Não identificado",
        "S.I."
    ]

    for ausencia in ausencias:
        result = atomizador.classify_entity_type(ausencia)
        status = "OK" if result['tipo'] == 'ausencia_coletor' else "ERRO"
        print(f"{status:<4} {ausencia:<30} -> {result['tipo']:<20} ({result['confianca_classificacao']:.3f})")

    print("\n" + "="*80)

if __name__ == "__main__":
    test_5_categorias()