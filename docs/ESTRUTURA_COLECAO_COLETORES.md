# Estrutura da Coleção Coletores

## Visão Geral

Este documento descreve a estrutura completa dos documentos na coleção MongoDB "coletores", que armazena os coletores canônicos processados pelo sistema de canonicalização.

## Estrutura do Documento

```json
{
  "_id": "ObjectId(...)",
  "coletor_canonico": "Silva, J.C.",
  "sobrenome_normalizado": "silva",
  "iniciais": ["J", "C"],
  "variacoes": [
    {
      "forma_original": "J.C. Silva",
      "frequencia": 15,
      "primeira_ocorrencia": 1758378801.620274,
      "ultima_ocorrencia": 1758378901.234567
    },
    {
      "forma_original": "Silva, J.C.",
      "frequencia": 8,
      "primeira_ocorrencia": 1758378701.123456,
      "ultima_ocorrencia": 1758378801.620274
    }
  ],
  "total_registros": 23,
  "confianca_canonicalizacao": 0.95,
  "kingdom": ["Plantae", "Animalia"],
  "tipo_coletor": "pessoa",
  "confianca_tipo_coletor": 0.85,
  "indices_busca": {
    "soundex": "S412",
    "metaphone": "SLF"
  },
  "metadados": {
    "data_criacao": 1758378601.123456,
    "ultima_atualizacao": 1758378901.234567,
    "algoritmo_versao": "1.0",
    "revisar_manualmente": false
  }
}
```

## Campos Principais

### `coletor_canonico` (string)
Nome canônico padronizado do coletor seguindo as [regras de capitalização](../PADRAO_CAPITALIZACAO.md).

**Exemplos:**
- `"Silva, J.C."`
- `"Santos de Oliveira, M."`
- `"USP"`
- `"Lab. de Botânica da UFPI"`

### `sobrenome_normalizado` (string)
Chave primária para agrupamento. Sobrenome em minúsculas, sem acentos.

**Formato:** Apenas letras minúsculas, sem espaços ou pontuação
**Exemplos:**
- `"silva"`
- `"santasdeoliveira"`
- `"usp"`

### `iniciais` (array de strings)
Lista das iniciais extraídas do nome.

**Exemplos:**
- `["J", "C"]` para "J.C. Silva"
- `["M"]` para "Maria Santos"
- `[]` para instituições

### `variacoes` (array de objetos)
Lista de todas as formas originais encontradas para este coletor.

**Estrutura de cada variação:**
```json
{
  "forma_original": "string",     // Forma exata como apareceu nos dados
  "frequencia": number,           // Quantas vezes foi encontrada
  "primeira_ocorrencia": float,   // Timestamp da primeira vez
  "ultima_ocorrencia": float      // Timestamp da última vez
}
```

### `kingdom` (array de strings) ⭐ **NOVA ESTRUTURA**
**IMPORTANTE:** Lista dos kingdoms onde este coletor tem coletas registradas.

**Formato:** Array de strings com kingdoms únicos
**Valores possíveis:** `["Plantae"]`, `["Animalia"]`, `["Plantae", "Animalia"]`, etc.

**Exemplos:**
```json
// Coletor apenas de plantas
"kingdom": ["Plantae"]

// Coletor apenas de animais
"kingdom": ["Animalia"]

// Coletor de plantas e animais
"kingdom": ["Plantae", "Animalia"]

// Coletor sem coletas ou kingdom indefinido
"kingdom": []
```

**⚠️ MUDANÇA IMPORTANTE:**
- **ANTES:** `"kingdoms": {"Plantae": 2800, "Animalia": 1400}`
- **AGORA:** `"kingdom": ["Plantae", "Animalia"]`

### `tipo_coletor` (string)
Classificação do tipo de entidade.

**Valores possíveis:**
- `"pessoa"` - Pessoa física
- `"conjunto_pessoas"` - Múltiplas pessoas (ex: "Silva & Santos")
- `"grupo_pessoas"` - Equipe/grupo (ex: "Silva et al.")
- `"empresa_instituicao"` - Empresa ou instituição
- `"ausencia_coletor"` - Casos especiais (ex: "?", "sem coletor")

### `confianca_tipo_coletor` (float)
Nível de confiança na classificação do tipo (0.0 a 1.0).

### `total_registros` (integer)
Soma das frequências de todas as variações.

### `confianca_canonicalizacao` (float)
Nível de confiança no processo de canonicalização (0.0 a 1.0).

### `indices_busca` (objeto)
Índices fonéticos para busca por similaridade.

```json
{
  "soundex": "S412",      // Código Soundex
  "metaphone": "SLF"      // Código Metaphone
}
```

### `metadados` (objeto)
Informações sobre o processamento.

```json
{
  "data_criacao": float,           // Timestamp de criação
  "ultima_atualizacao": float,     // Timestamp da última atualização
  "algoritmo_versao": "1.0",       // Versão do algoritmo
  "revisar_manualmente": boolean   // Se precisa revisão manual
}
```

## Formatos de Timestamp

**⚠️ Importante:** Todos os campos de data/hora são armazenados como **float** (timestamp Unix) para compatibilidade com MongoDB.

**Exemplo:** `1758378801.620274` = 2025-09-20 11:40:01.620274

## Índices MongoDB

A coleção possui os seguintes índices para performance:

```javascript
// Índice principal para deduplicação
{ "sobrenome_normalizado": 1 }

// Índices para busca fonética
{ "indices_busca.soundex": 1 }
{ "indices_busca.metaphone": 1 }

// Índice para classificação
{ "tipo_coletor": 1 }

// Índice para kingdoms
{ "kingdom": 1 }
```

## Exemplos Completos

### Pessoa Física com Múltiplos Kingdoms
```json
{
  "_id": "ObjectId(507f1f77bcf86cd799439011)",
  "coletor_canonico": "Damasceno-Junior, G.A.",
  "sobrenome_normalizado": "damascenojunior",
  "iniciais": ["G", "A"],
  "variacoes": [
    {
      "forma_original": "G.A. Damasceno-Junior",
      "frequencia": 45,
      "primeira_ocorrencia": 1758378601.123,
      "ultima_ocorrencia": 1758378801.456
    },
    {
      "forma_original": "Damasceno-Junior, G.",
      "frequencia": 23,
      "primeira_ocorrencia": 1758378701.789,
      "ultima_ocorrencia": 1758378801.234
    }
  ],
  "total_registros": 68,
  "confianca_canonicalizacao": 0.92,
  "kingdom": ["Plantae", "Animalia"],
  "tipo_coletor": "pessoa",
  "confianca_tipo_coletor": 0.89,
  "indices_busca": {
    "soundex": "D525",
    "metaphone": "TMSKNKNR"
  },
  "metadados": {
    "data_criacao": 1758378601.123,
    "ultima_atualizacao": 1758378801.456,
    "algoritmo_versao": "1.0",
    "revisar_manualmente": false
  }
}
```

### Instituição
```json
{
  "_id": "ObjectId(507f1f77bcf86cd799439012)",
  "coletor_canonico": "UFPI",
  "sobrenome_normalizado": "ufpi",
  "iniciais": [],
  "variacoes": [
    {
      "forma_original": "UFPI",
      "frequencia": 156,
      "primeira_ocorrencia": 1758378501.111,
      "ultima_ocorrencia": 1758378901.999
    },
    {
      "forma_original": "Universidade Federal do Piauí",
      "frequencia": 23,
      "primeira_ocorrencia": 1758378601.222,
      "ultima_ocorrencia": 1758378801.888
    }
  ],
  "total_registros": 179,
  "confianca_canonicalizacao": 0.98,
  "kingdom": ["Plantae"],
  "tipo_coletor": "empresa_instituicao",
  "confianca_tipo_coletor": 0.95,
  "indices_busca": {
    "soundex": "U120",
    "metaphone": "UFP"
  },
  "metadados": {
    "data_criacao": 1758378501.111,
    "ultima_atualizacao": 1758378901.999,
    "algoritmo_versao": "1.0",
    "revisar_manualmente": false
  }
}
```

## Migração da Estrutura Kingdom

Para migrar dados existentes da estrutura antiga para a nova:

```javascript
// MongoDB script para migração
db.coletores.find({kingdoms: {$exists: true}}).forEach(function(doc) {
    if (doc.kingdoms && typeof doc.kingdoms === 'object') {
        // Converte {Plantae: 100, Animalia: 50} para ["Plantae", "Animalia"]
        doc.kingdom = Object.keys(doc.kingdoms);
        delete doc.kingdoms;
        db.coletores.save(doc);
    }
});
```

## Considerações de Performance

1. **Deduplicação:** Busca por `sobrenome_normalizado` é O(1) com índice
2. **Similaridade:** Busca fonética por `soundex` e `metaphone` é otimizada
3. **Kingdoms:** Consultas por kingdom são indexadas para performance
4. **Timestamps:** Formato float evita problemas de compatibilidade MongoDB

## Validação de Dados

### Campos Obrigatórios
- `coletor_canonico`
- `sobrenome_normalizado`
- `variacoes` (pelo menos 1 item)
- `total_registros` > 0
- `kingdom` (array, pode estar vazio)

### Regras de Validação
- `total_registros` = soma das frequências das variações
- `kingdom` deve ser array de strings
- Timestamps devem ser números positivos
- `confianca_*` devem estar entre 0.0 e 1.0