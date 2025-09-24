# Tasks: Sistema de Canonicalização de Coletores Biológicos

**Input**: Design documents from `/specs/main/`
**Prerequisites**: plan.md (✓), research.md (✓), data-model.md (✓), contracts/ (✓), quickstart.md (✓)

## Execution Flow (main)
```
1. Load plan.md from feature directory
   → If not found: ERROR "No implementation plan found"
   → Extract: tech stack, libraries, structure
2. Load optional design documents:
   → data-model.md: Extract entities → model tasks
   → contracts/: Each file → contract test task
   → research.md: Extract decisions → setup tasks
3. Generate tasks by category:
   → Setup: project init, dependencies, linting
   → Tests: contract tests, integration tests
   → Core: models, services, CLI commands
   → Integration: DB, middleware, logging
   → Polish: unit tests, performance, docs
4. Apply task rules:
   → Different files = mark [P] for parallel
   → Same file = sequential (no [P])
   → Tests before implementation (TDD)
5. Number tasks sequentially (T001, T002...)
6. Generate dependency graph
7. Create parallel execution examples
8. Validate task completeness:
   → All contracts have tests?
   → All entities have models?
   → All endpoints implemented?
9. Return: SUCCESS (tasks ready for execution)
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Path Conventions
- **Single project**: `src/`, `tests/` at repository root (confirmed from plan.md)
- All paths relative to repository root: `D:\git\coletoresBO\`

## Phase 3.1: Setup

- [x] T001 Create project structure with src/ and tests/ directories following single CLI pipeline architecture
- [x] T002 Initialize Python 3.11 project with requirements.txt including pymongo, pandas, jellyfish, rapidfuzz, pytest dependencies
- [x] T003 [P] Configure linting and formatting tools (black, flake8, isort) in pyproject.toml

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**

### Execution Order Tests (Based on Existing Scripts Structure)
- [x] T004 [P] Contract test for execution order: análise → processamento → relatórios → validação in tests/contract/test_execution_order.py
- [x] T005 [P] Contract test for analise_coletores.py pattern discovery in tests/contract/test_cli_analysis.py
- [x] T006 [P] Contract test for processar_coletores.py using discovered patterns in tests/contract/test_cli_process.py
- [x] T007 [P] Contract test for gerar_relatorios.py with analysis insights in tests/contract/test_cli_reports.py
- [x] T008 [P] Contract test for validar_canonicalizacao.py quality validation in tests/contract/test_cli_validation.py

### Legacy Script Integration Tests (Complete Dataset Focus)
- [x] T009 [P] Integration test for existing analise_coletores.py processing ALL records with recordedBy in tests/integration/test_analysis_script.py
- [x] T010 [P] Integration test for existing processar_coletores.py workflow using complete dataset patterns in tests/integration/test_processing_script.py
- [x] T011 [P] Integration test for existing gerar_relatorios.py output with complete dataset insights in tests/integration/test_reports_script.py
- [x] T012 [P] Integration test for existing validar_canonicalizacao.py checks against complete dataset baseline in tests/integration/test_validation_script.py
- [x] T013 [P] Integration test for complete dataset pattern discovery and application pipeline in tests/integration/test_pattern_discovery.py
- [x] T014 [P] Integration test for complete dataset analysis-first workflow (all 11M+ records) in tests/integration/test_full_analysis_workflow.py

## Phase 3.3: Core Implementation (ONLY after tests are failing)

### Data Models (Based on data-model.md entities)
- [x] T015 [P] CollectorRecord model in src/models/collector_record.py
- [x] T016 [P] ClassificationResult model in src/models/classification_result.py
- [x] T017 [P] CanonicalCollector model in src/models/canonical_collector.py
- [x] T018 [P] CollectorVariation model in src/models/collector_variation.py
- [x] T019 [P] SimilarityScore model in src/models/similarity_score.py
- [x] T020 [P] KingdomStatistics model in src/models/kingdom_statistics.py
- [x] T021 [P] CheckpointData model in src/models/checkpoint_data.py
- [x] T022 [P] ProcessingBatch model in src/models/processing_batch.py

### Legacy Script Enhancement (Priority: Complete Dataset Analysis First)
- [ ] T023 Enhance existing analise_coletores.py to process ALL records from "ocorrencias" collection with "recordedBy" attribute (no record limit) in src/analise_coletores.py
- [ ] T024 [P] Pattern discovery service for dynamic threshold configuration based on complete dataset analysis in src/services/pattern_discovery.py
- [ ] T025 [P] Analysis results persistence and loading for complete dataset insights in src/services/analysis_persistence.py
- [ ] T026 Enhance existing processar_coletores.py to consume complete analysis patterns in src/processar_coletores.py (depends on T023-T025)
- [ ] T027 Enhance existing gerar_relatorios.py with complete dataset analysis insights in src/gerar_relatorios.py (depends on T023)
- [ ] T028 Enhance existing validar_canonicalizacao.py for quality validation against complete dataset baseline in src/validar_canonicalizacao.py (depends on T023)

### Core Services (Supporting the Script Pipeline)
- [ ] T029 [P] MongoDB connection manager in src/services/mongodb_manager.py
- [ ] T030 [P] Phonetic similarity calculator in src/services/phonetic_calculator.py
- [ ] T031 [P] String similarity calculator with Jaro-Winkler in src/services/string_similarity.py
- [ ] T032 [P] Collector classifier with 6 entity types in src/services/collector_classifier.py
- [ ] T033 Collector canonicalization service in src/services/collector_canonizer.py (depends on T030-T032)
- [ ] T034 [P] Checkpoint manager with hierarchical recovery in src/services/checkpoint_manager.py
- [ ] T035 [P] Report generator for canonicalization analysis in src/services/report_generator.py
- [ ] T036 Batch processor for 11M+ record handling in src/services/batch_processor.py (depends on T033-T034)

### CLI Interface Implementation (Orchestrating Existing Scripts)
- [ ] T037 Main CLI entry point with execution order orchestration in src/cli/__main__.py
- [ ] T038 Analysis command wrapper for analise_coletores.py in src/cli/commands/analysis.py (depends on T023)
- [ ] T039 Processing command wrapper for processar_coletores.py in src/cli/commands/process.py (depends on T026)
- [ ] T040 [P] Reports command wrapper for gerar_relatorios.py in src/cli/commands/reports.py
- [ ] T041 [P] Validation command wrapper for validar_canonicalizacao.py in src/cli/commands/validation.py
- [ ] T042 [P] Full pipeline command (analysis → processing → reports → validation) in src/cli/commands/pipeline.py
- [ ] T043 CLI configuration and argument parsing in src/cli/config.py
- [ ] T044 CLI error handling and execution order validation in src/cli/error_handler.py

## Phase 3.4: Integration

- [ ] T045 Connect analysis results to processing configuration pipeline in src/services/pattern_discovery.py
- [ ] T046 Integrate existing scripts with new orchestration layer in src/cli/__main__.py
- [ ] T047 Add logging and progress tracking throughout analysis-first pipeline in src/utils/logging_config.py
- [ ] T048 Add memory monitoring for large-scale analysis operations in src/utils/memory_monitor.py
- [ ] T049 Configure pattern persistence between analysis and processing phases in src/services/analysis_persistence.py
- [ ] T050 Add comprehensive error handling and execution order validation across pipeline

## Phase 3.5: Polish

### Unit Tests for Analysis-First Logic
- [ ] T051 [P] Unit tests for pattern discovery algorithms in tests/unit/test_pattern_discovery.py
- [ ] T052 [P] Unit tests for analysis persistence and loading in tests/unit/test_analysis_persistence.py
- [ ] T053 [P] Unit tests for execution order validation in tests/unit/test_execution_order.py
- [ ] T054 [P] Unit tests for existing script enhancements in tests/unit/test_script_enhancements.py
- [ ] T055 [P] Unit tests for CLI orchestration logic in tests/unit/test_cli_orchestration.py
- [ ] T056 [P] Unit tests for data model validation in tests/unit/test_models.py

### Performance and Quality (Complete Dataset Focus)
- [ ] T057 Performance tests for complete dataset analysis phase (11M+ records pattern discovery speed) in tests/performance/test_analysis_performance.py
- [ ] T058 Memory efficiency tests for complete dataset analysis operations (all records with recordedBy) in tests/performance/test_analysis_memory.py
- [ ] T059 [P] Code quality improvements in existing scripts optimized for complete dataset processing in src/
- [ ] T060 [P] Update documentation with complete dataset analysis-first execution order in docs/execution-order.md
- [ ] T061 Execute enhanced quickstart validation tests including complete dataset analysis phase

## Dependencies

### Critical Path Dependencies (Analysis-First Structure)
- **Setup First**: T001-T003 before all others
- **Tests Before Implementation**: T004-T014 before T015-T044
- **Models Before Services**: T015-T022 before T023-T036
- **Analysis Enhancement Priority**: T023 (analise_coletores.py) before all other script enhancements
- **Pattern Discovery Before Processing**: T024-T025 before T026 (processar_coletores.py)
- **Script Enhancements Before CLI**: T023-T028 before T037-T044
- **Core Before Integration**: T015-T044 before T045-T050
- **Implementation Before Polish**: T015-T050 before T051-T061

### Specific Dependencies (Execution Order Critical)
- **T023** (enhanced analise_coletores.py) blocks T026, T027, T028 (all downstream scripts)
- **T024-T025** (pattern services) block T026 (enhanced processar_coletores.py)
- **T038** (analysis CLI) blocks T042 (full pipeline command)
- **T039** (processing CLI) blocks T042 (full pipeline command)
- **T043** (CLI config) blocks T037-T042 (all command implementations)
- **T045-T049** (integration) blocks T050 (comprehensive error handling)

### Mandatory Execution Order in Pipeline
```
T023 → T026 → T027 → T028
(Análise → Processamento → Relatórios → Validação)
```

## Parallel Execution Examples

### Phase 3.2: All Contract Tests (Launch Together)
```bash
Task: "Contract test for canonicalize command in tests/contract/test_cli_canonicalize.py"
Task: "Contract test for classify command in tests/contract/test_cli_classify.py"
Task: "Contract test for validate command in tests/contract/test_cli_validate.py"
Task: "Contract test for report command in tests/contract/test_cli_report.py"
Task: "Contract test for checkpoint management in tests/contract/test_cli_checkpoint.py"
```

### Phase 3.2: All Integration Tests (Launch Together)
```bash
Task: "Integration test for collector classification accuracy in tests/integration/test_classification_accuracy.py"
Task: "Integration test for similarity scoring and grouping in tests/integration/test_similarity_scoring.py"
Task: "Integration test for batch processing pipeline in tests/integration/test_batch_processing.py"
Task: "Integration test for checkpoint recovery in tests/integration/test_checkpoint_recovery.py"
Task: "Integration test for MongoDB connection and queries in tests/integration/test_mongodb_operations.py"
Task: "Integration test for complete canonicalization workflow in tests/integration/test_full_workflow.py"
```

### Phase 3.3: All Data Models (Launch Together)
```bash
Task: "CollectorRecord model in src/models/collector_record.py"
Task: "ClassificationResult model in src/models/classification_result.py"
Task: "CanonicalCollector model in src/models/canonical_collector.py"
Task: "CollectorVariation model in src/models/collector_variation.py"
Task: "SimilarityScore model in src/models/similarity_score.py"
Task: "KingdomStatistics model in src/models/kingdom_statistics.py"
Task: "CheckpointData model in src/models/checkpoint_data.py"
Task: "ProcessingBatch model in src/models/processing_batch.py"
```

### Phase 3.3: Independent Services (Launch Together)
```bash
Task: "MongoDB connection manager in src/services/mongodb_manager.py"
Task: "Phonetic similarity calculator in src/services/phonetic_calculator.py"
Task: "String similarity calculator with Jaro-Winkler in src/services/string_similarity.py"
Task: "Collector classifier with 6 entity types in src/services/collector_classifier.py"
Task: "Checkpoint manager with hierarchical recovery in src/services/checkpoint_manager.py"
Task: "Report generator for canonicalization analysis in src/services/report_generator.py"
```

### Phase 3.3: Independent CLI Commands (Launch Together)
```bash
Task: "Classify command implementation in src/cli/commands/classify.py"
Task: "Validate command implementation in src/cli/commands/validate.py"
Task: "Report command implementation in src/cli/commands/report.py"
Task: "Checkpoint command implementation in src/cli/commands/checkpoint.py"
```

### Phase 3.5: All Unit Tests (Launch Together)
```bash
Task: "Unit tests for phonetic similarity algorithms in tests/unit/test_phonetic_calculator.py"
Task: "Unit tests for string similarity scoring in tests/unit/test_string_similarity.py"
Task: "Unit tests for collector classification logic in tests/unit/test_collector_classifier.py"
Task: "Unit tests for similarity score calculation in tests/unit/test_similarity_score.py"
Task: "Unit tests for data model validation in tests/unit/test_models.py"
Task: "Unit tests for checkpoint serialization in tests/unit/test_checkpoint_data.py"
```

## Notes
- [P] tasks = different files, no dependencies between them
- Verify all tests fail before implementing (TDD requirement)
- Commit after completing each task
- MongoDB indexes should be created during T039 (integration)
- Performance targets: >100 records/second, <200MB memory per batch
- All paths are relative to repository root: `D:\git\coletoresBO\`

## Task Generation Rules
*Applied during main() execution*

1. **From Contracts (CLI Interface)**:
   - 5 CLI commands → 5 contract test tasks [P] (T004-T008)
   - 5 CLI commands → 5 implementation tasks (T033-T036)

2. **From Data Model**:
   - 8 entities → 8 model creation tasks [P] (T015-T022)
   - Entity relationships → service layer tasks (T023-T030)

3. **From User Stories (Quickstart)**:
   - 6 test scenarios → 6 integration tests [P] (T009-T014)
   - Validation scenarios → polish tasks (T051-T055)

4. **Ordering Applied**:
   - Setup → Tests → Models → Services → CLI → Integration → Polish
   - Dependencies prevent inappropriate parallelization

## Validation Checklist
*GATE: Checked by main() before returning*

- [x] All contracts have corresponding tests (T004-T008 for 5 CLI commands)
- [x] All entities have model tasks (T015-T022 for 8 entities)
- [x] All tests come before implementation (Phase 3.2 before 3.3)
- [x] Parallel tasks truly independent (different files, no shared state)
- [x] Each task specifies exact file path (src/models/*.py, tests/unit/*.py, etc.)
- [x] No task modifies same file as another [P] task (verified by file paths)
- [x] TDD enforced: contract/integration tests must fail before core implementation
- [x] Critical dependencies preserved: models → services → CLI → integration → polish

## Implementation Readiness

**Total Tasks**: 61 numbered tasks (T001-T061)
**Parallel Opportunities**: 38 tasks marked [P] for concurrent execution
**Sequential Dependencies**: 23 tasks with critical path dependencies
**Estimated Effort**: 9-13 weeks with parallel execution optimizations

**Analysis-First Priority**: ✅ Tasks reorganized to prioritize existing script enhancement starting with analise_coletores.py
**Execution Order Enforced**: ✅ Mandatory pipeline sequence (análise → processamento → relatórios → validação) built into task dependencies
**Legacy Integration**: ✅ All existing scripts in src/ incorporated and enhanced rather than replaced

**Ready for Execution**: ✅ All design artifacts analyzed, tasks generated following TDD principles with analysis-first execution order and existing script integration.