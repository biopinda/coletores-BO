#!/usr/bin/env python3
"""
Exemplo de uso do algoritmo de canonicalização de coletores
"""

import sys
import os
from datetime import datetime

# Adiciona o diretório do projeto ao path
sys.path.append(os.path.dirname(__file__))

from config.mongodb_config import SEPARATOR_PATTERNS
from src.canonicalizador_coletores import AtomizadorNomes, NormalizadorNome, CanonizadorColetores


def exemplo_atomizacao():
    """
    Demonstra a atomização de nomes múltiplos
    """
    print("=" * 60)
    print("EXEMPLO: ATOMIZAÇÃO DE NOMES")
    print("=" * 60)

    atomizador = AtomizadorNomes(SEPARATOR_PATTERNS)

    exemplos = [
        "Silva, J. & Santos, M.",
        "FORZZA; Almeida, R.",
        "R.C. Forzza et al.",
        "Silva, J. and Jones, P.",
        "Lima, A. e col.",
        "Santos, M., Silva, J.",
        "Rodriguez, A. with Martinez, C."
    ]

    for exemplo in exemplos:
        nomes_atomizados = atomizador.atomizar(exemplo)
        print(f"Original: '{exemplo}'")
        print(f"Atomizado: {nomes_atomizados}")
        print(f"Quantidade: {len(nomes_atomizados)} nome(s)")
        print("-" * 40)


def exemplo_normalizacao():
    """
    Demonstra a normalização de nomes individuais
    """
    print("\n" + "=" * 60)
    print("EXEMPLO: NORMALIZAÇÃO DE NOMES")
    print("=" * 60)

    normalizador = NormalizadorNome()

    exemplos = [
        "FORZZA",
        "Forzza, R.",
        "R.C. Forzza",
        "Silva, João Carlos",
        "A. B. Santos",
        "OLIVEIRA SANTOS",
        "Martinez-Lopez, C.",
        "da Silva, M.A."
    ]

    for exemplo in exemplos:
        resultado = normalizador.normalizar(exemplo)
        print(f"Original: '{exemplo}'")
        print(f"Normalizado: '{resultado['nome_normalizado']}'")
        print(f"Sobrenome: '{resultado['sobrenome']}'")
        print(f"Iniciais: {resultado['iniciais']}")
        print(f"Chaves de busca: {resultado['chaves_busca']}")
        print("-" * 40)


def exemplo_canonicalizacao():
    """
    Demonstra a canonicalização de múltiplas variações
    """
    print("\n" + "=" * 60)
    print("EXEMPLO: CANONICALIZAÇÃO DE COLETORES")
    print("=" * 60)

    # Inicializa componentes
    atomizador = AtomizadorNomes(SEPARATOR_PATTERNS)
    normalizador = NormalizadorNome()
    canonizador = CanonizadorColetores(similarity_threshold=0.85, confidence_threshold=0.7)

    # Simula processamento de várias formas do mesmo coletor
    variacoes_forzza = [
        "FORZZA",
        "Forzza, R.",
        "R.C. Forzza",
        "Forzza, R.C.",
        "Rafael C. Forzza",
        "FORZZA, R",
        "R. Forzza"
    ]

    print("Processando variações de 'Forzza':")
    print(f"Variações: {variacoes_forzza}")
    print()

    # Processa cada variação
    for i, variacao in enumerate(variacoes_forzza, 1):
        print(f"Processando {i}: '{variacao}'")

        # Normaliza
        nome_normalizado = normalizador.normalizar(variacao)
        print(f"  Normalizado: {nome_normalizado['nome_normalizado']}")

        # Canoniza
        resultado = canonizador.processar_nome(nome_normalizado)
        print(f"  Ação: {resultado['acao']}")
        print(f"  Confiança: {resultado['confianca']:.3f}")

        if resultado['coletor_canonico']:
            canonico = resultado['coletor_canonico']
            print(f"  Coletor canônico: {canonico['coletor_canonico']}")
            print(f"  Total variações: {len(canonico['variacoes'])}")

        print()

    # Mostra resultado final
    print("RESULTADO FINAL:")
    stats = canonizador.obter_estatisticas()
    print(f"Coletores canônicos criados: {stats['total_coletores_canonicos']}")
    print(f"Total de variações: {stats['total_variacoes']}")
    print(f"Taxa de canonicalização: {stats['taxa_canonicalizacao']:.2f}")

    # Mostra detalhes do coletor canônico criado
    if canonizador.coletores_canonicos:
        coletor = list(canonizador.coletores_canonicos.values())[0]
        print(f"\nDetalhes do coletor '{coletor['coletor_canonico']}':")
        print(f"  Confiança: {coletor['confianca_canonicalizacao']:.3f}")
        print(f"  Total registros: {coletor['total_registros']}")
        print("  Variações encontradas:")
        for variacao in coletor['variacoes']:
            print(f"    - '{variacao['forma_original']}' (freq: {variacao['frequencia']})")


def exemplo_caso_complexo():
    """
    Demonstra processamento de caso complexo com múltiplos coletores
    """
    print("\n" + "=" * 60)
    print("EXEMPLO: CASO COMPLEXO - MÚLTIPLOS COLETORES")
    print("=" * 60)

    # Inicializa componentes
    atomizador = AtomizadorNomes(SEPARATOR_PATTERNS)
    normalizador = NormalizadorNome()
    canonizador = CanonizadorColetores()

    caso_complexo = "Silva, J.A. & R.C. Forzza; Santos, M. et al."

    print(f"Processando: '{caso_complexo}'")
    print()

    # Atomiza
    nomes_atomizados = atomizador.atomizar(caso_complexo)
    print(f"Nomes atomizados: {nomes_atomizados}")
    print()

    # Processa cada nome
    for i, nome in enumerate(nomes_atomizados, 1):
        print(f"Nome {i}: '{nome}'")

        # Normaliza
        nome_normalizado = normalizador.normalizar(nome)
        print(f"  Normalizado: {nome_normalizado['nome_normalizado']}")
        print(f"  Sobrenome: {nome_normalizado['sobrenome']}")
        print(f"  Iniciais: {nome_normalizado['iniciais']}")

        # Canoniza
        if nome_normalizado['sobrenome_normalizado']:
            resultado = canonizador.processar_nome(nome_normalizado)
            print(f"  Ação: {resultado['acao']}")
            if resultado['coletor_canonico']:
                print(f"  Coletor canônico: {resultado['coletor_canonico']['coletor_canonico']}")
        else:
            print("  Nome sem sobrenome identificável - ignorado")

        print()

    # Estatísticas finais
    stats = canonizador.obter_estatisticas()
    print("ESTATÍSTICAS:")
    print(f"  Coletores canônicos: {stats['total_coletores_canonicos']}")
    print(f"  Total variações: {stats['total_variacoes']}")


def exemplo_similaridade():
    """
    Demonstra como o algoritmo lida com nomes similares mas diferentes
    """
    print("\n" + "=" * 60)
    print("EXEMPLO: TESTE DE SIMILARIDADE")
    print("=" * 60)

    # Inicializa componentes
    normalizador = NormalizadorNome()
    canonizador = CanonizadorColetores(similarity_threshold=0.85)

    # Casos teste: alguns devem ser agrupados, outros não
    casos_teste = [
        # Grupo 1: Silva (devem ser agrupados)
        "Silva, J.",
        "J. Silva",
        "SILVA",
        "Silva, João",

        # Grupo 2: Santos (devem ser agrupados)
        "Santos, M.",
        "M. Santos",
        "SANTOS, M",

        # Caso 3: Similar mas diferente (não deve ser agrupado)
        "Silveira, J.",  # Similar a Silva mas diferente

        # Caso 4: Typo (pode ou não ser agrupado dependendo do threshold)
        "Silv, J."  # Possível typo de Silva
    ]

    print("Processando casos teste de similaridade:")
    print()

    for caso in casos_teste:
        print(f"Processando: '{caso}'")
        nome_normalizado = normalizador.normalizar(caso)
        resultado = canonizador.processar_nome(nome_normalizado)

        print(f"  Ação: {resultado['acao']}")
        print(f"  Confiança: {resultado['confianca']:.3f}")
        if resultado['coletor_canonico']:
            print(f"  Agrupado com: {resultado['coletor_canonico']['coletor_canonico']}")
        print()

    # Mostra resultado final
    print("COLETORES CANÔNICOS CRIADOS:")
    for sobrenome, coletor in canonizador.coletores_canonicos.items():
        print(f"  {coletor['coletor_canonico']}:")
        for variacao in coletor['variacoes']:
            print(f"    - {variacao['forma_original']}")


def main():
    """
    Executa todos os exemplos
    """
    print("DEMONSTRAÇÃO DO ALGORITMO DE CANONICALIZAÇÃO DE COLETORES")
    print("=" * 80)
    print(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        exemplo_atomizacao()
        exemplo_normalizacao()
        exemplo_canonicalizacao()
        exemplo_caso_complexo()
        exemplo_similaridade()

        print("\n" + "=" * 80)
        print("DEMONSTRAÇÃO CONCLUÍDA COM SUCESSO!")
        print("=" * 80)

    except Exception as e:
        print(f"\nERRO durante demonstração: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()