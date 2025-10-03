
# Implementation Plan: Sistema de Identificação e Canonicalização de Coletores de Plantas

**Branch**: `001-especificacao-leia-o` | **Date**: 2025-10-03 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `H:\git\coletoresBO\specs\001-especificacao-leia-o\spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → If not found: ERROR "No feature spec at {path}"
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → Detect Project Type from file system structure or context (web=frontend+backend, mobile=app+api)
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
Sistema de processamento NLP para identificar, classificar e canonicalizar nomes de coletores de plantas em 4.6 milhões de registros MongoDB. O pipeline processa strings através de classificação (5 categorias), atomização (separação de nomes), normalização (padronização) e canonicalização (agrupamento por similaridade usando Levenshtein + Jaro-Winkler + algoritmo fonético). Saída: banco de dados local com entidades canônicas e variações, relatório CSV, e documentação editável de regras.

## Technical Context
**Language/Version**: Python 3.11+
**Primary Dependencies**: pymongo (MongoDB client), pandas (CSV/data processing), NLP libraries (nltk, jellyfish for phonetic algorithms), similarity algorithms (python-Levenshtein, jellyfish for Jaro-Winkler)
**Storage**: MongoDB (source - 4.6M records), SQLite ou DuckDB (local denormalized table with embedded JSON arrays for variations)
**Testing**: pytest (unit/integration), pytest-benchmark (performance validation)
**Target Platform**: Linux/Windows server (CLI application)
**Project Type**: single (data processing pipeline)
**Performance Goals**: Process 4.6M records in ≤6 hours (~213 records/second), parallel processing support
**Constraints**: Confidence threshold ≥0.70 for classifications/groupings, case-insensitive matching with normalization
**Scale/Scope**: 4.6M MongoDB records (kingdom=="Plantae"), estimated 100K-500K unique canonical entities

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Code Quality Standards
- ✅ Static Analysis: Will enforce zero linting/type errors with mypy strict mode
- ✅ Documentation: Public APIs will have complete docstrings (Google/NumPy style)
- ✅ Complexity: Pipeline stages are naturally modular (<50 lines each)
- ✅ Duplication: Algorithm stages are distinct (classify→atomize→normalize→canonicalize)

### Test-First Development (TDD)
- ✅ Tests written before implementation for each pipeline stage
- ✅ Target: 80% coverage minimum, 100% for business logic (similarity algorithms, classification rules)
- ✅ Contract tests: Data schemas (input strings, output entities)
- ✅ Integration tests: End-to-end pipeline scenarios from spec acceptance criteria

### User Experience Consistency
- ⚠️ N/A: CLI application (no GUI), but will provide clear progress indicators for 6-hour processing
- ✅ Error Handling: User-friendly messages for DB connection failures, low-confidence results

### Performance Requirements
- ✅ Quantifiable targets: ≤6 hours for 4.6M records (~213 rec/sec)
- ✅ Performance tests: pytest-benchmark for similarity algorithms
- ✅ Resource constraints: Parallel processing design, streaming MongoDB cursors (memory efficient)

### Violations/Justifications
None - All constitutional principles applicable and achievable for this data processing pipeline.

## Project Structure

### Documentation (this feature)
```
specs/[###-feature]/
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->
```
src/
├── pipeline/
│   ├── __init__.py
│   ├── classifier.py       # Stage 1: Classification
│   ├── atomizer.py          # Stage 2: Atomization
│   ├── normalizer.py        # Stage 3: Normalization
│   └── canonicalizer.py     # Stage 4: Canonicalization
├── algorithms/
│   ├── __init__.py
│   ├── similarity.py        # Levenshtein, Jaro-Winkler
│   └── phonetic.py          # Soundex/Metaphone
├── models/
│   ├── __init__.py
│   ├── entities.py          # Data models (Pydantic/dataclasses)
│   └── schemas.py           # Input/output schemas
├── storage/
│   ├── __init__.py
│   ├── mongodb_client.py    # Source MongoDB connection
│   └── local_db.py          # SQLite/DuckDB client
├── cli.py                   # Main CLI entry point
└── config.py                # Configuration management

tests/
├── contract/
│   ├── test_classification_schema.py
│   ├── test_entity_schema.py
│   └── test_output_schema.py
├── integration/
│   ├── test_pipeline_e2e.py
│   └── test_scenarios.py    # From acceptance criteria
└── unit/
    ├── test_classifier.py
    ├── test_atomizer.py
    ├── test_normalizer.py
    ├── test_canonicalizer.py
    └── test_algorithms.py

docs/
└── rules.md                 # Editable algorithm rules documentation
```

**Structure Decision**: Single project structure (data processing pipeline). This is a CLI-based Python application with clear separation of concerns: pipeline stages (classify→atomize→normalize→canonicalize), algorithms (similarity/phonetic), data models, storage adapters (MongoDB source, local DB), and comprehensive testing.

## Phase 0: Outline & Research
1. **Extract unknowns from Technical Context** above:
   - For each NEEDS CLARIFICATION → research task
   - For each dependency → best practices task
   - For each integration → patterns task

2. **Generate and dispatch research agents**:
   ```
   For each unknown in Technical Context:
     Task: "Research {unknown} for {feature context}"
   For each technology choice:
     Task: "Find best practices for {tech} in {domain}"
   ```

3. **Consolidate findings** in `research.md` using format:
   - Decision: [what was chosen]
   - Rationale: [why chosen]
   - Alternatives considered: [what else evaluated]

**Output**: research.md with all NEEDS CLARIFICATION resolved

## Phase 1: Design & Contracts
*Prerequisites: research.md complete*

1. **Extract entities from feature spec** → `data-model.md`:
   - Entity name, fields, relationships
   - Validation rules from requirements
   - State transitions if applicable

2. **Generate API contracts** from functional requirements:
   - For each user action → endpoint
   - Use standard REST/GraphQL patterns
   - Output OpenAPI/GraphQL schema to `/contracts/`

3. **Generate contract tests** from contracts:
   - One test file per endpoint
   - Assert request/response schemas
   - Tests must fail (no implementation yet)

4. **Extract test scenarios** from user stories:
   - Each story → integration test scenario
   - Quickstart test = story validation steps

5. **Update agent file incrementally** (O(1) operation):
   - Run `.specify/scripts/powershell/update-agent-context.ps1 -AgentType claude`
     **IMPORTANT**: Execute it exactly as specified above. Do not add or remove any arguments.
   - If exists: Add only NEW tech from current plan
   - Preserve manual additions between markers
   - Update recent changes (keep last 3)
   - Keep under 150 lines for token efficiency
   - Output to repository root

**Output**: data-model.md, /contracts/*, failing tests, quickstart.md, agent-specific file

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:
1. **Setup Tasks** (Infrastructure):
   - Create project structure (src/, tests/, docs/)
   - Setup Python 3.11+ environment with requirements.txt
   - Configure DuckDB/SQLite schema
   - Setup MongoDB test connection

2. **Contract Test Tasks** (TDD Phase 1 - from pipeline_contracts.py):
   - Test classification schema contract [P]
   - Test atomization schema contract [P]
   - Test normalization schema contract [P]
   - Test canonicalization schema contract [P]
   - Test entity/variation schema contract [P]
   - Test CSV export schema contract [P]

3. **Data Model Tasks** (from data-model.md):
   - Implement Pydantic models (entities.py, schemas.py) [P]
   - Create database schema (local_db.py)
   - Implement MongoDB client (mongodb_client.py) [P]

4. **Algorithm Tasks** (from research.md):
   - Implement similarity algorithms (Levenshtein + Jaro-Winkler + Phonetic) [P]
   - Write unit tests for similarity scoring
   - Benchmark performance (<1ms per comparison)

5. **Pipeline Stage Tasks** (TDD Phase 2):
   - Write integration tests for Scenario 1-7 (from quickstart.md)
   - Implement Classifier (classifier.py) → make Scenario 1,3,4,5 tests pass
   - Implement Atomizer (atomizer.py) → make Scenario 1 atomization pass
   - Implement Normalizer (normalizer.py) → make Scenario 2 normalization pass
   - Implement Canonicalizer (canonicalizer.py) → make Scenario 2 grouping pass

6. **Integration Tasks**:
   - Implement CLI orchestrator (cli.py)
   - Add parallel processing (multiprocessing)
   - Implement progress tracking (tqdm)
   - Test Scenario 6 (dynamic DB updates)
   - Test Scenario 7 (CSV export)

7. **Performance Validation**:
   - Benchmark 100K records → validate ≥213 rec/sec
   - Tune worker count and batch size if needed

8. **Documentation**:
   - Generate rules.md (editable algorithm rules)
   - Add README with usage instructions

**Ordering Strategy**:
- TDD strict: All tests before implementation
- Dependency order: Models → Algorithms → Pipeline stages → Integration
- Parallel opportunities: Contract tests [P], Model creation [P], Algorithm implementation [P]

**Estimated Output**: 30-35 numbered tasks with clear dependencies

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)  
**Phase 4**: Implementation (execute tasks.md following constitutional principles)  
**Phase 5**: Validation (run tests, execute quickstart.md, performance validation)

## Complexity Tracking
*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |


## Progress Tracking
*This checklist is updated during execution flow*

**Phase Status**:
- [x] Phase 0: Research complete (/plan command) - research.md created
- [x] Phase 1: Design complete (/plan command) - data-model.md, contracts/, quickstart.md, CLAUDE.md created
- [x] Phase 2: Task planning complete (/plan command - approach described above)
- [x] Phase 3: Tasks generated (/tasks command) - tasks.md created with 40 numbered tasks
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS - No violations
- [x] Post-Design Constitution Check: PASS - Design follows all constitutional principles
- [x] All NEEDS CLARIFICATION resolved - 3 clarifications answered in Session 2025-10-03
- [x] Complexity deviations documented - None (no violations)

---
*Based on Constitution v2.1.1 - See `/memory/constitution.md`*
