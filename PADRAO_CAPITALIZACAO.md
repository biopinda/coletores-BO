# Padrão de Capitalização dos Coletores Canônicos

## Visão Geral

O sistema de canonicalização de coletores aplica um padrão consistente de capitalização para todos os `coletor_canonico` na coleção MongoDB.

## Regras de Capitalização

### 1. **Title Case (Padrão Principal)**
- **Regra**: Primeira letra maiúscula, resto minúsculo
- **Aplicação**: Nomes próprios, sobrenomes, palavras em geral

**Exemplos:**
```
silva → Silva
SANTOS → Santos
oliveira → Oliveira
damasceno-junior → Damasceno-Junior
```

### 2. **Acrônimos Conhecidos**
- **Regra**: Mantêm formato em MAIÚSCULAS
- **Lista**: Universidades, instituições, herbários conhecidos

**Exemplos:**
```
usp → USP
ufpi → UFPI
embrapa → EMBRAPA
inpa → INPA
ibama → IBAMA
cnpq → CNPq
```

**Lista Completa de Acrônimos:**
- Universidades: `USP`, `UFRJ`, `UFC`, `UFMG`, `UFPE`, `UFSC`, `UFPR`, `UFRGS`, `UFPI`
- Instituições: `EMBRAPA`, `INPA`, `IBAMA`, `ICMBIO`, `CNPq`, `CAPES`, `FAPESP`
- Herbários: `RB`, `SP`, `MG`, `HB`, `HUEFS`, `ALCB`, `VIC`, `HRCB`

### 3. **Preposições e Artigos**
- **Regra**: Minúsculas quando não estão no início
- **Lista**: `de`, `da`, `do`, `dos`, `das`, `e`, `em`, `na`, `no`, `nas`, `nos`

**Exemplos:**
```
silva DE santos → Silva de Santos
museu DO estado → Museu do Estado
centro DE pesquisas → Centro de Pesquisas
```

### 4. **Nomes Compostos com Hífen**
- **Regra**: Cada parte segue as regras acima independentemente
- **Aplicação**: Sobrenomes compostos, nomes institucionais

**Exemplos:**
```
damasceno-junior → Damasceno-Junior
costa-lima → Costa-Lima
rio-de-janeiro → Rio-de-Janeiro
```

### 5. **Iniciais**
- **Regra**: Sempre em MAIÚSCULAS com pontos
- **Formato**: `SOBRENOME, I.N.I.C.I.A.I.S.`

**Exemplos:**
```
silva, j.c. → Silva, J.C.
santos, a.b.c.d. → Santos, A.B.C.D.
oliveira, m. → Oliveira, M.
```

## Exemplos Completos

### Pessoas Físicas
```
SILVA, JOÃO CARLOS → Silva, J.C.
oliveira, maria → Oliveira, M.
DAMASCENO-JUNIOR, GERALDO → Damasceno-Junior, G.
santos de oliveira, ana → Santos de Oliveira, A.
```

### Instituições
```
usp → USP
universidade de são paulo → Universidade de São Paulo
lab. de botânica da ufpi → Lab. de Botânica da UFPI
centro de pesquisas → Centro de Pesquisas
environmental company → Environmental Company
```

### Casos Especiais
```
? → ?
sem coletor → Sem Coletor
não identificado → Não Identificado
s.i. → S.I.
```

## Implementação Técnica

A padronização é aplicada pela função `_padronizar_capitalizacao()` no arquivo `src/canonicalizador_coletores.py`:

```python
def _padronizar_capitalizacao(self, texto: str) -> str:
    # 1. Identifica acrônimos conhecidos
    # 2. Aplica Title Case nas demais palavras
    # 3. Mantém preposições em minúsculas
    # 4. Trata nomes compostos com hífen
    # 5. Formata iniciais em maiúsculas
```

## Benefícios

1. **Consistência**: Todos os coletores seguem o mesmo padrão
2. **Legibilidade**: Format claro e profissional
3. **Padronização**: Facilita buscas e comparações
4. **Reconhecimento**: Acrônimos institucionais preservados
5. **Compatibilidade**: Segue convenções bibliográficas

## Casos de Revisão Manual

Coletores com baixa confiança de classificação (< 0.5) devem ser revisados manualmente, incluindo:

- Nomes únicos sem sobrenome (ex: "Edilson")
- Acrônimos não reconhecidos
- Formatos atípicos
- Ambiguidades entre pessoa/instituição

## Monitoramento

O sistema gera métricas de qualidade para acompanhar:
- Distribuição de tipos de coletores
- Confiança média por categoria
- Casos marcados para revisão manual
- Cobertura de acrônimos conhecidos