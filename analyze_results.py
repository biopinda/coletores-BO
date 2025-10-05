"""Analisa os resultados do processamento no DuckDB"""

import duckdb

# Conectar ao banco de dados
conn = duckdb.connect('data/canonicalentities.db')

print("="*80)
print("ANALISE DOS RESULTADOS - DuckDB")
print("="*80)
print()

# 1. Total de entidades
result = conn.execute("SELECT COUNT(*) as total FROM canonical_entities").fetchone()
print(f"Total de entidades canonicas: {result[0]}")
print()

# 2. Distribuição por tipo
print("Distribuicao por tipo:")
print("-"*80)
results = conn.execute("""
    SELECT entityType, COUNT(*) as count
    FROM canonical_entities
    GROUP BY entityType
    ORDER BY count DESC
""").fetchall()
for row in results:
    print(f"  {row[0]}: {row[1]}")
print()

# 3. Exemplos de pessoas com variações
print("Exemplos de pessoas com variacoes (top 5):")
print("-"*80)
results = conn.execute("""
    SELECT canonicalName, entityType, json_array_length(variations) as num_variations
    FROM canonical_entities
    WHERE entityType = 'Pessoa'
    ORDER BY num_variations DESC
    LIMIT 5
""").fetchall()
for row in results:
    print(f"  {row[0]} ({row[1]}): {row[2]} variacoes")
print()

# 4. Verificar se há números em canonicalName (problema original)
print("Verificando presenca de numeros em canonicalName:")
print("-"*80)
results = conn.execute("""
    SELECT canonicalName, entityType
    FROM canonical_entities
    WHERE canonicalName LIKE '%0%' OR canonicalName LIKE '%1%'
       OR canonicalName LIKE '%2%' OR canonicalName LIKE '%3%'
       OR canonicalName LIKE '%4%' OR canonicalName LIKE '%5%'
       OR canonicalName LIKE '%6%' OR canonicalName LIKE '%7%'
       OR canonicalName LIKE '%8%' OR canonicalName LIKE '%9%'
    LIMIT 10
""").fetchall()

if results:
    print(f"  ATENÇÃO: Encontrados {len(results)} registros com numeros em canonicalName:")
    for row in results:
        print(f"    - {row[0]} ({row[1]})")
else:
    print("  OK: Nenhum canonicalName contém numeros!")
print()

# 5. Confiança média
print("Confianca media:")
print("-"*80)
results = conn.execute("""
    SELECT
        AVG(classification_confidence) as avg_classification,
        AVG(grouping_confidence) as avg_grouping
    FROM canonical_entities
""").fetchone()
print(f"  Classificacao: {results[0]:.3f}")
print(f"  Agrupamento: {results[1]:.3f}")
print()

# 6. Sample de 5 registros
print("Amostra de 5 registros:")
print("-"*80)
results = conn.execute("""
    SELECT canonicalName, entityType, classification_confidence
    FROM canonical_entities
    LIMIT 5
""").fetchall()
for row in results:
    print(f"  {row[0]} ({row[1]}, conf: {row[2]:.2f})")
print()

print("="*80)
print("ANALISE COMPLETA")
print("="*80)

conn.close()
