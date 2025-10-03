# Algorithm Rules Documentation

**Last Updated**: 2025-10-03
**Purpose**: Document all classification, normalization, and canonicalization rules for the collector name pipeline

---

## Classification Patterns

### Pattern Hierarchy (checked in order):

#### 1. Não Determinado (Confidence: 1.0)
**Exact matches**:
- `?`
- `sem coletor`
- `não identificado`
- `desconhecido`

**Pattern**: Exact string match (case-insensitive)

---

#### 2. Empresa/Instituição (Confidence: 0.85-0.90)
**All-caps acronyms** (Confidence: 0.90):
- Pattern: `^[A-Z]{2,}$`
- Examples: `EMBRAPA`, `USP`, `UNICAMP`

**Institution keywords** (Confidence: 0.85):
- `embrapa`, `usp`, `unicamp`, `ufrj`, `ufmg`, `inpa`, `jbrj`
- `herbário`, `herbario`
- `jardim botânico`, `jardim botanico`
- `instituto`, `universidade`, `faculdade`

---

#### 3. Conjunto de Pessoas (Confidence: 0.90-0.95)
**Separators detected**:
- `;` (semicolon)
- `&` (ampersand)
- `et al.` (et al pattern)

**Confidence boost to 0.95** if name patterns also detected:
- "Surname, Initials" format: `[A-Z][a-z]+(?:-[A-Z][a-z]+)?,\s*[A-Z]\.(?:[A-Z]\.)*`
- Initials pattern: `\b[A-Z]\.[A-Z]\.?\b`

**Examples**:
- `Silva, J. & R.C. Forzza` ’ ConjuntoPessoas (0.95)
- `Santos, M.; Oliveira, P.` ’ ConjuntoPessoas (0.95)

---

#### 4. Pessoa (Confidence: 0.85-0.90)
**Single name patterns**:
- "Surname, Initials" format (Confidence: 0.90)
- Initials detected (Confidence: 0.85)

**Examples**:
- `Forzza, R.C.` ’ Pessoa (0.90)
- `J. Silva` ’ Pessoa (0.85)

---

#### 5. Grupo de Pessoas (Confidence: 0.75)
**Generic group terms**:
- `pesquisas`, `equipe`, `grupo`, `projeto`
- `expedição`, `expedicao`
- `levantamento`

**No proper name patterns** (otherwise would be Pessoa or ConjuntoPessoas)

**Example**:
- `Pesquisas da Biodiversidade` ’ GrupoPessoas (0.75)

---

## Atomization Separators

Only applied when category is **ConjuntoPessoas**.

### Separator Priority:
1. `et al.` (et al pattern) ’ `SeparatorType.ET_AL`
2. `;` (semicolon) ’ `SeparatorType.SEMICOLON`
3. `&` (ampersand) ’ `SeparatorType.AMPERSAND`

### Processing Rules:
- Preserve original formatting
- Assign position (0-indexed)
- Track which separator was used
- First name has `SeparatorType.NONE`

**Example**:
```
Input: "Silva, J. & R.C. Forzza; Santos, M."
Output:
  [0] "Silva, J." (separator: NONE)
  [1] "R.C. Forzza" (separator: AMPERSAND)
  [2] "Santos, M." (separator: SEMICOLON)
```

---

## Normalization Rules

Applied to **all names** for case-insensitive matching.

### Rule 1: Remove Extra Whitespace
- Collapse multiple spaces to single space
- Trim leading/trailing spaces
- Implementation: `' '.join(text.split())`

### Rule 2: Standardize Punctuation Spacing
- Ensure punctuation marks (`,`, `;`, `.`, `&`) are followed by a space
- Regex: `r'\s*([,;.&])\s*'` ’ `r'\1 '`

### Rule 3: Uppercase Conversion
- Convert all text to uppercase for comparison
- Implementation: `text.upper()`

**Examples**:
```
"  Silva,J.C. " ’ "SILVA, J.C."
"R.C.  Forzza" ’ "R.C. FORZZA"
"silva, j." ’ "SILVA, J."
```

---

## Canonicalization Format

### For Pessoa entities:
- **Format**: "Sobrenome, Iniciais"
- If already in that format, use as-is
- Otherwise, use normalized name

### For other entity types:
- Use normalized name as canonical name

---

## Similarity Algorithm Weights

Used for grouping name variations under canonical entities.

### Combined Score Formula:
```
similarity_score = (Levenshtein × 0.4) + (Jaro-Winkler × 0.4) + (Phonetic × 0.2)
```

### Component Algorithms:
1. **Levenshtein Distance** (Weight: 0.4)
   - Measures edit distance between strings
   - Normalized: `1 - (distance / max_length)`

2. **Jaro-Winkler** (Weight: 0.4)
   - Optimized for short strings
   - Gives higher weight to prefix matches (important for surnames)

3. **Phonetic (Metaphone)** (Weight: 0.2)
   - Binary score: 1.0 if phonetic codes match, 0.0 otherwise
   - Catches phonetically similar names (e.g., "Silva" vs "Sylva")

### Grouping Threshold:
- **Minimum similarity**: 0.70
- Names with similarity e 0.70 are grouped under the same canonical entity
- Confidence scores below 0.70 are rejected

---

## Configuration Parameters

**Editable in `config.yaml`**:

```yaml
processing:
  confidence_threshold: 0.70  # Minimum confidence for all stages

algorithms:
  similarity_weights:
    levenshtein: 0.4    # Edit distance weight
    jaro_winkler: 0.4   # Jaro-Winkler weight
    phonetic: 0.2       # Phonetic matching weight
```

---

## Performance Targets

- **Processing rate**: e 213 records/second
- **Target time**: d 6 hours for 4.6M records
- **Algorithm performance**: Similarity calculations < 1ms per comparison

---

## Notes for Algorithm Refinement

This document is **editable** and should be updated when:
- New classification patterns are identified
- Similarity weights need tuning for better grouping
- Normalization rules require adjustments
- New entity types or separators are added

All changes should be tested against the quickstart.md acceptance scenarios before deployment.
