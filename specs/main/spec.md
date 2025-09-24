# Feature Specification: Sistema de Canonicalização de Coletores Biológicos

**Feature Branch**: `main`
**Created**: 2025-09-24
**Status**: Active
**Input**: Comprehensive collector canonicalization system for processing 11M+ MongoDB records with complete entity classification and pattern-driven analysis

## Execution Flow (main)
```
1. Parse user requirements from consolidated specifications
   • Core canonicalization system + additional entity categories
2. Extract key concepts from consolidated requirements
   • Identify: 6 entity types, similarity algorithms, pattern discovery
3. Fill execution structure based on existing scripts
   • Mandatory order: análise → processamento → relatórios → validação
4. Generate comprehensive functional requirements
   • Each requirement tested and measurable
5. Define complete entity model (6 classification types)
6. Validate execution readiness for 11M+ record processing
7. Return: SUCCESS (ready for analysis-first implementation)
```

---

## 📋 Quick Guidelines
- Focus on WHAT users need and WHY
- Analysis-first approach: discover patterns before processing
- Complete dataset processing (all records with recordedBy)
- Written for researchers and database administrators

---

## User Scenarios & Testing

### Primary User Story
Researchers and database administrators need to identify and harmonize collector names from biological specimen records in MongoDB databases. The system processes raw collector strings through a comprehensive multi-stage pipeline to create canonical collector identities, handling 6 distinct entity types including traditional collectors, groups, institutions, indeterminate cases, and insufficient representations.

### Execution Structure (Analysis-First)
```
1. ANÁLISE EXPLORATÓRIA COMPLETA (analise_coletores.py)
   → Processar TODOS os registros da coleção "ocorrencias" com "recordedBy"
   → Descoberta de padrões, distribuições, anomalias no dataset completo
   → Configuração dinâmica de thresholds baseada na totalidade dos dados

2. PROCESSAMENTO PRINCIPAL (processar_coletores.py)
   → Canonicalização usando padrões descobertos na análise completa
   → Aplicação de configurações otimizadas para o dataset específico

3. GERAÇÃO DE RELATÓRIOS (gerar_relatorios.py)
   → Relatórios enriquecidos com insights da análise completa
   → Métricas de qualidade baseadas no baseline de todos os dados

4. VALIDAÇÃO DE QUALIDADE (validar_canonicalizacao.py)
   → Validação baseada em padrões esperados da análise completa
   → Confirmação da qualidade dos agrupamentos contra baseline completo
```

### Acceptance Scenarios
1. **Given** the system starts processing, **When** executed, **Then** it MUST run analise_coletores.py first to process ALL records and discover patterns
2. **Given** a collector string containing multiple people, **When** processed, **Then** it classifies as "conjunto_pessoas" and atomizes into individual names
3. **Given** a collector string with a single person name, **When** processed, **Then** it classifies as "pessoa" and creates canonical form
4. **Given** a collector string with institutional name, **When** processed, **Then** it classifies as "empresa_instituicao"
5. **Given** unknown collector indicators ("?", "Sem coletor"), **When** processed, **Then** it classifies as "coletor_indeterminado"
6. **Given** insufficient data (only first name or initials), **When** processed, **Then** it classifies as "representacao_insuficiente"
7. **Given** multiple variations of the same collector, **When** canonicalized, **Then** all variations are grouped under same canonical identifier
8. **Given** processing of 11M+ specimen records, **When** complete, **Then** comprehensive collector database with all 6 entity types is created

### Edge Cases
- How does system handle collector strings with ambiguous separators or unclear patterns?
- What occurs when collector confidence scores are below manual review thresholds?
- How does analysis phase adapt to unexpected pattern discoveries in complete dataset?
- What happens when initials could match existing collectors but lack sufficient context?

## Requirements

### Functional Requirements

#### Core System Requirements
- **FR-001**: System MUST execute analise_coletores.py as first mandatory step, processing ALL records from "ocorrencias" collection with "recordedBy" attribute (no record limitations)
- **FR-002**: System MUST follow mandatory execution order: análise → processamento → relatórios → validação
- **FR-003**: System MUST discover patterns through complete dataset analysis and apply them dynamically to processing configuration
- **FR-004**: System MUST preserve analysis results for use in all subsequent processing phases

#### Classification Requirements (6 Entity Types)
- **FR-005**: System MUST classify collector strings into six distinct entity types: pessoa, conjunto_pessoas, grupo_pessoas, empresa_instituicao, coletor_indeterminado, representacao_insuficiente
- **FR-006**: System MUST assign confidence scores (0.0-1.0) for each entity type classification
- **FR-007**: System MUST classify entries as "coletor_indeterminado" when containing explicit unknown indicators ("?", "Sem coletor")
- **FR-008**: System MUST classify entries as "representacao_insuficiente" when containing only single first names or initials without surname
- **FR-009**: System MUST treat identical surnames with different initial patterns as distinct individuals (e.g., "T.L. Santos" vs "A. J. dos Santos")

#### Processing Requirements
- **FR-010**: System MUST atomize conjunto_pessoas entries into individual collector names using discovered separator patterns
- **FR-011**: System MUST normalize individual collector names by extracting surnames, initials, and generating phonetic keys
- **FR-012**: System MUST canonicalize collector variations using weighted similarity: surname (50%), initial compatibility (30%), phonetic similarity (20%)
- **FR-013**: System MUST group collector variations above similarity threshold (0.85) into canonical entries
- **FR-014**: System MUST exclude "coletor_indeterminado" and "representacao_insuficiente" from canonicalization grouping
- **FR-015**: System MUST track collector statistics by biological kingdom (Plantae/Animalia) for specialization analysis

#### Quality and Recovery Requirements
- **FR-016**: System MUST flag entries requiring manual review when confidence scores fall below threshold (0.5)
- **FR-017**: System MUST process specimen records in configurable batches with checkpoint recovery capability
- **FR-018**: System MUST generate comprehensive reports covering all 6 entity types with quality metrics and validation results
- **FR-019**: System MUST maintain separate statistical tracking for all entity categories with frequency counts and occurrence patterns
- **FR-020**: System MUST optimize similarity thresholds based on complete dataset distribution analysis

### Key Entities

#### Core Processing Entities
- **Collector Record**: Source specimen record containing recordedBy field, kingdom classification, and occurrence metadata from MongoDB collection
- **Canonical Collector**: Normalized collector identity with chosen canonical form, confidence score, grouped variations, kingdom statistics, and entity type classification
- **Collector Variation**: Individual form of collector name with original text, frequency count, first/last occurrence dates, and similarity metrics
- **Classification Result**: Entity type determination with confidence score across all 6 categories: pessoa, conjunto_pessoas, grupo_pessoas, empresa_instituicao, coletor_indeterminado, representacao_insuficiente

#### Analysis and Scoring Entities
- **Similarity Score**: Calculated metric combining surname matching, initial compatibility, and phonetic similarity for collector canonicalization
- **Kingdom Statistics**: Collector activity breakdown by biological kingdom showing specialization patterns and collection frequencies
- **Pattern Discovery Results**: Comprehensive analysis output from complete dataset processing including separator patterns, threshold optimizations, and distribution insights
- **Processing Configuration**: Dynamic configuration derived from pattern discovery to optimize canonicalization for specific dataset characteristics

#### Quality Control Entities
- **Coletor Indeterminado**: Collector record explicitly indicating unknown collector information through recognized null-value indicators, tracked separately with occurrence statistics
- **Representação Insuficiente**: Collector record containing insufficient identifying information, including single names or initials, maintained with frequency tracking but excluded from grouping
- **Quality Validation Result**: Comprehensive quality assessment comparing processing results against complete dataset baseline and expected patterns
- **Checkpoint Data**: Recovery state information enabling resumption of processing from interruption points with full context preservation

---

## Review & Acceptance Checklist

### Content Quality
- [x] Focused on analysis-first execution workflow
- [x] Based on complete dataset processing requirements
- [x] Written for researchers and database administrators
- [x] All mandatory sections completed
- [x] Comprehensive 6-entity classification system

### Requirement Completeness
- [x] Analysis-first execution order enforced
- [x] Complete dataset processing specified (all records with recordedBy)
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] All 6 entity types clearly defined
- [x] Integration with existing scripts specified

### Technical Readiness
- [x] Execution structure aligned with existing scripts in src/
- [x] Pattern discovery requirements for dynamic configuration
- [x] Quality validation against complete dataset baseline
- [x] Checkpoint recovery for 11M+ record processing
- [x] Memory-efficient batch processing specified

---

## Implementation Impact

This consolidated specification requires:

1. **Enhanced Script Integration**: All existing scripts in src/ enhanced rather than replaced
2. **Analysis-First Pipeline**: Mandatory execution order implemented in orchestration layer
3. **Complete Dataset Processing**: All 11M+ records with recordedBy processed in analysis phase
4. **6-Category Classification**: Extended entity recognition beyond original 4 types
5. **Pattern-Driven Configuration**: Dynamic threshold adjustment based on discovered patterns
6. **Quality Validation**: Comprehensive validation against complete dataset baseline

**Ready for Implementation**: ✅ All specifications consolidated with analysis-first execution order and complete dataset processing requirements.