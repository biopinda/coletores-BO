#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'config'))

from config.mongodb_config import MONGODB_CONFIG
from src.canonicalizador_coletores import NormalizadorNome, CanonizadorColetores, GerenciadorMongoDB

# Simula o processo de deduplicação
def teste_deduplicacao():
    print("TESTE DE DEDUPLICAÇÃO - FORZZA")
    print("=" * 80)

    # Conecta ao MongoDB
    mongo_manager = GerenciadorMongoDB(
        MONGODB_CONFIG['connection_string'],
        MONGODB_CONFIG['database_name'],
        MONGODB_CONFIG['collections']
    )

    normalizador = NormalizadorNome()
    canonizador = CanonizadorColetores(mongo_manager=mongo_manager)

    # Casos de teste em ordem de aparição real
    casos_teste = [
        "R. Forzza",        # Primeiro aparece
        "R.C. Forzza",      # Depois aparece
        "R.Forzza",         # Depois aparece
        "Forzza",           # Depois aparece
        "R. C. Forzza"      # Depois aparece
    ]

    print("Processando casos de teste em sequência:")
    print("-" * 40)

    resultados = []
    for i, caso in enumerate(casos_teste, 1):
        print(f"\n{i}. Processando: '{caso}'")

        # Normaliza
        nome_normalizado = normalizador.normalizar(caso)
        print(f"   Sobrenome normalizado: '{nome_normalizado['sobrenome_normalizado']}'")

        # Busca candidatos existentes
        candidatos = canonizador._buscar_candidatos(nome_normalizado)
        print(f"   Candidatos encontrados: {len(candidatos)}")

        if candidatos:
            for j, candidato in enumerate(candidatos):
                print(f"     {j+1}. {candidato['coletor_canonico']} (ID: {candidato['_id']})")

        # Processa
        resultado = canonizador.processar_nome(nome_normalizado)
        print(f"   Ação: {resultado['acao']}")
        print(f"   Coletor canônico: {resultado['coletor_canonico']['coletor_canonico']}")

        resultados.append(resultado)

    print("\n" + "=" * 80)
    print("RESUMO DOS RESULTADOS:")
    print("=" * 80)

    coletores_unicos = {}
    for resultado in resultados:
        canonico = resultado['coletor_canonico']['coletor_canonico']
        if canonico not in coletores_unicos:
            coletores_unicos[canonico] = []
        coletores_unicos[canonico].append(resultado)

    for canonico, resultados_grupo in coletores_unicos.items():
        print(f"\nColetor canônico: '{canonico}'")
        print(f"Variações agrupadas: {len(resultados_grupo)}")
        for res in resultados_grupo:
            acao = res['acao']
            original = res['coletor_canonico']['variacoes'][0]['forma_original']
            print(f"  - '{original}' ({acao})")

    total_unicos = len(coletores_unicos)
    print(f"\nTotal de coletores únicos criados: {total_unicos}")

    if total_unicos == 1:
        print("✅ SUCESSO: Todas as variações foram agrupadas!")
    else:
        print("❌ PROBLEMA: Variações não foram deduplicadas corretamente!")

    mongo_manager.fechar_conexao()

if __name__ == "__main__":
    teste_deduplicacao()