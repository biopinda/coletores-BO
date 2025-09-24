# Feature Specification: Sistema de Canonicalização de Coletores Biológicos

**Feature Branch**: `001-este-projeto-centrado`
**Created**: 2025-09-24
**Status**: Draft
**Input**: User description: "Este projeto é centrado no desenvolvimento e implementação de um algoritmo que irá acessar uma base de dados (MongoDB), em uma coleção específica (coletores) e um atributo específico (recordedBy), que contem uma string com nomes de coletores."

## Execution Flow (main)
```
1. Parse user description from Input
   • If empty: ERROR "No feature description provided"
2. Extract key concepts from description
   • Identify: actors, actions, data, constraints
3. For each unclear aspect:
   • Mark with [NEEDS CLARIFICATION: specific question]
4. Fill User Scenarios & Testing section
   • If no clear user flow: ERROR "Cannot determine user scenarios"
5. Generate Functional Requirements
   • Each requirement must be testable
   • Mark ambiguous requirements
6. Identify Key Entities (if data involved)
7. Run Review Checklist
   • If any [NEEDS CLARIFICATION]: WARN "Spec has uncertainties"
   • If implementation details found: ERROR "Remove tech details"
8. Return: SUCCESS (spec ready for planning)
```

---

## 📋 Quick Guidelines
-  Focus on WHAT users need and WHY
- Avoid HOW to implement (no tech stack, APIs, code structure)
- Written for business stakeholders, not developers

### Section Requirements
- **Mandatory sections**: Must be completed for every feature
- **Optional sections**: Include only when relevant to the feature
- When a section doesn't apply, remove it entirely (don't leave as "N/A")

### For AI Generation
When creating this spec from a user prompt:
1. **Mark all ambiguities**: Use [NEEDS CLARIFICATION: specific question] for any assumption you'd need to make
2. **Don't guess**: If the prompt doesn't specify something (e.g., "login system" without auth method), mark it
3. **Think like a tester**: Every vague requirement should fail the "testable and unambiguous" checklist item
4. **Common underspecified areas**:
   - User types and permissions
   - Data retention/deletion policies
   - Performance targets and scale
   - Error handling behaviors
   - Integration requirements
   - Security/compliance needs

---

## User Scenarios & Testing

### Primary User Story
Researchers and database administrators need to identify and harmonize collector names from biological specimen records in MongoDB databases. The system processes raw collector strings (e.g., "Silva, J. & R.C. Forzza; Santos, M. et al.") through a multi-stage pipeline to create canonical collector identities, resolving variations like "FORZZA", "Forzza, R.", "R.C. Forzza" into a single canonical form.

### Acceptance Scenarios
1. **Given** a collector string containing multiple people, **When** the system processes it, **Then** it classifies as "conjunto_pessoas" and atomizes into individual names
2. **Given** a collector string with a single person name, **When** the system processes it, **Then** it classifies as "pessoa" and creates a canonical form
3. **Given** a collector string with institutional name, **When** the system processes it, **Then** it classifies as "empresa_instituicao" and creates institutional canonical form
4. **Given** multiple variations of the same collector across records, **When** the system canonicalizes, **Then** all variations are grouped under the same canonical identifier
5. **Given** processing of 11M specimen records, **When** the system completes canonicalization, **Then** a comprehensive collector database with variations, frequencies, and kingdom statistics is created

### Edge Cases
- What happens when collector strings contain ambiguous separators or unclear patterns?
- How does system handle collector names with special characters or non-Latin scripts?
- What occurs when collector confidence scores are below manual review thresholds?
- How does system process collector strings that could be either person names or institutional codes?

## Requirements

### Functional Requirements
- **FR-001**: System MUST classify collector strings into four distinct entity types: pessoa, conjunto_pessoas, grupo_pessoas, empresa_instituicao
- **FR-002**: System MUST assign confidence scores (0.0-1.0) for each entity type classification
- **FR-003**: System MUST atomize conjunto_pessoas entries into individual collector names using configurable separator patterns
- **FR-004**: System MUST normalize individual collector names by extracting surnames, initials, and generating phonetic keys
- **FR-005**: System MUST canonicalize collector variations by calculating similarity scores using surname (50%), initial compatibility (30%), and phonetic similarity (20%)
- **FR-006**: System MUST group collector variations above similarity threshold (0.85) into canonical entries
- **FR-007**: System MUST track collector statistics by biological kingdom (Plantae/Animalia) for specialization analysis
- **FR-008**: System MUST maintain collector variation frequencies and occurrence dates for each canonical entry
- **FR-009**: System MUST flag entries requiring manual review when confidence scores fall below threshold (0.5)
- **FR-010**: System MUST process specimen records in configurable batches with checkpoint recovery capability
- **FR-011**: System MUST generate comprehensive reports on canonicalization quality, top collectors, and validation metrics
- **FR-012**: System MUST support stratified sampling for exploratory analysis (3M Plantae + 3M Animalia records)

### Key Entities
- **Collector Record**: Source specimen record containing recordedBy field, kingdom classification, and occurrence metadata
- **Canonical Collector**: Normalized collector identity with chosen canonical form, confidence score, grouped variations, kingdom statistics, and entity type classification
- **Collector Variation**: Individual form of collector name with original text, frequency count, first/last occurrence dates, and similarity metrics
- **Classification Result**: Entity type determination with confidence score and reasoning for pessoa/conjunto_pessoas/grupo_pessoas/empresa_instituicao categories
- **Similarity Score**: Calculated metric combining surname matching, initial compatibility, and phonetic similarity for collector canonicalization
- **Kingdom Statistics**: Collector activity breakdown by biological kingdom showing specialization patterns and collection frequencies

---

## Review & Acceptance Checklist

### Content Quality
- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

### Requirement Completeness
- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

---

## Execution Status

- [x] User description parsed
- [x] Key concepts extracted
- [x] Ambiguities marked
- [x] User scenarios defined
- [x] Requirements generated
- [x] Entities identified
- [x] Review checklist passed

---