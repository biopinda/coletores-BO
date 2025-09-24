# Implementation Plan: Sistema de Canonicalização de Coletores Biológicos

**Branch**: `main` | **Date**: 2025-09-24 | **Spec**: [001-este-projeto-centrado](../001-este-projeto-centrado/spec.md) + [002-outra-categoria-a](../002-outra-categoria-a/spec.md)
**Input**: Feature specification from `/specs/001-este-projeto-centrado/spec.md` and `/specs/002-outra-categoria-a/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → If not found: ERROR "No feature spec at {path}"
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → Detect Project Type from context (web=frontend+backend, mobile=app+api)
   → Set Structure Decision based on project type
3. Fill the Constitution Check section based on the content of the constitution document.
4. Evaluate Constitution Check section below
   → If violations exist: Document in Complexity Tracking
   → If no justification possible: ERROR "Simplify approach first"
   → Update Progress Tracking: Initial Constitution Check
5. Execute Phase 0 → research.md
   → If NEEDS CLARIFICATION remain: ERROR "Resolve unknowns"
6. Execute Phase 1 → contracts, data-model.md, quickstart.md, agent-specific template file (e.g., `CLAUDE.md` for Claude Code, `.github/copilot-instructions.md` for GitHub Copilot, `GEMINI.md` for Gemini CLI, `QWEN.md` for Qwen Code or `AGENTS.md` for opencode).
7. Re-evaluate Constitution Check section
   → If new violations: Refactor design, return to Phase 1
   → Update Progress Tracking: Post-Design Constitution Check
8. Plan Phase 2 → Describe task generation approach (DO NOT create tasks.md)
9. STOP - Ready for /tasks command
```

**IMPORTANT**: The /plan command STOPS at step 7. Phases 2-4 are executed by other commands:
- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary
Sistema de canonicalização de coletores biológicos para processar 11M registros de espécimes em MongoDB, classificando e agrupando variações de nomes de coletores em identidades canônicas. Inclui 6 tipos de classificação: pessoa, conjunto_pessoas, grupo_pessoas, empresa_instituicao, coletor_indeterminado, e representação_insuficiente. Utiliza algoritmos de similaridade baseados em sobrenome, iniciais e análise fonética para criar agrupamentos canônicos com scores de confiança.

**IMPORTANTE**: A estrutura de execução segue ordem específica baseada nos scripts existentes: (1) análise exploratória para descobrir padrões, (2) processamento principal usando padrões descobertos, (3) geração de relatórios com insights, (4) validação de qualidade.

## Technical Context
**Language/Version**: Python 3.11
**Primary Dependencies**: pymongo, pandas, phonetic algorithms (metaphone/soundex), scikit-learn
**Storage**: MongoDB (coleção coletores, atributo recordedBy)
**Testing**: pytest
**Target Platform**: Linux server
**Project Type**: single - CLI-based data processing pipeline
**Performance Goals**: Process 11M records in batches, handle 3M+3M stratified sampling
**Constraints**: Memory efficient batch processing, checkpoint recovery, <0.5 confidence threshold for manual review
**Scale/Scope**: 11M MongoDB records, 6 classification types, similarity scoring pipeline

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution template not yet configured - proceeding with standard software engineering practices:
- Library-first approach with standalone modules
- CLI interface with text I/O protocols
- Test-driven development mandatory
- Clear API contracts and data models
- Observability through structured logging

## Project Structure

### Documentation (this feature)
```
specs/main/
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)
```
# Option 1: Single project (DEFAULT)
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/
```

**Structure Decision**: Option 1 (single project) - CLI-based data processing pipeline for MongoDB canonicalization

## Execution Structure (Based on Existing Scripts)

### Existing Scripts in src/
1. **analise_coletores.py** - Análise exploratória e descoberta de padrões
2. **processar_coletores.py** - Processamento principal de canonicalização
3. **gerar_relatorios.py** - Geração de relatórios de qualidade
4. **validar_canonicalizacao.py** - Validação dos resultados
5. **canonicalizador_coletores.py** - Classes core do sistema

### Mandatory Execution Order
```
1. ANÁLISE EXPLORATÓRIA (analise_coletores.py)
   → Descoberta de padrões, distribuições, anomalias
   → Configuração dinâmica de thresholds
   → Baseline estatístico para validação

2. PROCESSAMENTO PRINCIPAL (processar_coletores.py)
   → Canonicalização usando padrões descobertos
   → Aplicação de configurações otimizadas
   → Checkpoint recovery com contexto de análise

3. GERAÇÃO DE RELATÓRIOS (gerar_relatorios.py)
   → Relatórios enriquecidos com insights da análise
   → Métricas de qualidade baseadas no baseline
   → Comparação com expectativas descobertas

4. VALIDAÇÃO DE QUALIDADE (validar_canonicalizacao.py)
   → Validação baseada em padrões esperados
   → Detecção de desvios das distribuições normais
   → Confirmação da qualidade dos agrupamentos
```

### Integration Requirements
- **Pattern Discovery**: Análise deve exportar padrões descobertos para uso posterior
- **Dynamic Configuration**: Processamento deve consumir configurações otimizadas da análise
- **Context Preservation**: Cada etapa deve preservar contexto da análise inicial
- **Quality Baseline**: Validação deve comparar com métricas estabelecidas na análise

## Phase 0: Outline & Research
1. **Extract unknowns from Technical Context** above:
   - MongoDB connection and query optimization patterns
   - Phonetic algorithm library selection (metaphone vs soundex vs double metaphone)
   - Batch processing strategies for 11M records
   - Similarity scoring algorithm implementation
   - Classification confidence scoring methods

2. **Generate and dispatch research agents**:
   ```
   Task: "Research MongoDB batch processing patterns for large datasets"
   Task: "Find best practices for phonetic similarity algorithms in Python"
   Task: "Research text similarity scoring approaches for name canonicalization"
   Task: "Find checkpoint recovery patterns for long-running data processing"
   Task: "Research memory-efficient processing of large pandas DataFrames"
   ```

3. **Consolidate findings** in `research.md` using format:
   - Decision: [what was chosen]
   - Rationale: [why chosen]
   - Alternatives considered: [what else evaluated]

**Output**: research.md with all technical decisions documented

## Phase 1: Design & Contracts
*Prerequisites: research.md complete*

1. **Extract entities from feature spec** → `data-model.md`:
   - CollectorRecord (recordedBy, kingdom, occurrence metadata)
   - CanonicalCollector (canonical form, confidence, variations, statistics)
   - CollectorVariation (original text, frequency, occurrence dates, metrics)
   - ClassificationResult (entity type, confidence, reasoning)
   - SimilarityScore (surname match, initial compatibility, phonetic similarity)
   - KingdomStatistics (kingdom breakdown, collection frequencies)

2. **Generate API contracts** from functional requirements:
   - CLI commands for batch processing (considerando ordem: análise → processamento → relatórios → validação)
   - Configuration interfaces for similarity thresholds
   - Report generation endpoints
   - Checkpoint recovery interfaces
   - Output schemas for TXT reports

3. **Generate contract tests** from contracts:
   - Classification accuracy tests
   - Similarity scoring validation tests
   - Batch processing pipeline tests (incluindo teste de ordem de execução)
   - Report format validation tests

4. **Extract test scenarios** from user stories:
   - Multi-person collector string atomization
   - Single person name canonicalization
   - Institution name processing
   - Variation grouping validation
   - Large dataset processing scenarios
   - **NOVO**: Análise exploratória de padrões antes do processamento

5. **Update agent file incrementally**:
   - Run `.specify/scripts/powershell/update-agent-context.ps1 -AgentType claude`
   - Add collector canonicalization context
   - Include MongoDB and similarity algorithm specifics
   - **NOVO**: Include execution order requirements

**Output**: data-model.md, /contracts/*, failing tests, quickstart.md, CLAUDE.md

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:
- Load `.specify/templates/tasks-template.md` as base
- Generate tasks from Phase 1 design docs (contracts, data model, quickstart)
- Each entity model → creation task [P]
- Each classification type → algorithm implementation task
- Each similarity scoring component → implementation task [P]
- MongoDB connection and batch processing tasks
- CLI interface and configuration tasks
- Report generation and output formatting tasks
- Integration test tasks for each user scenario

**Ordering Strategy**:
- TDD order: Contract tests before implementation
- Dependency order: Models before services before CLI
- Core algorithms before batch processing pipeline
- Mark [P] for parallel execution (independent modules)

**Estimated Output**: 30-35 numbered, ordered tasks in tasks.md

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)
**Phase 4**: Implementation (execute tasks.md following constitutional principles)
**Phase 5**: Validation (run tests, execute quickstart.md, performance validation)

## Complexity Tracking
*Fill ONLY if Constitution Check has violations that must be justified*

No constitutional violations identified.

## Progress Tracking
*This checklist is updated during execution flow*

**Phase Status**:
- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)
- [x] Phase 2: Task planning complete (/plan command - describe approach only)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved
- [x] Complexity deviations documented

---
*Based on Constitution v2.1.1 - See `/memory/constitution.md`*