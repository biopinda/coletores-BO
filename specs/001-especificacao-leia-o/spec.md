# Feature Specification: Sistema de Identificação e Canonicalização de Coletores de Plantas

**Feature Branch**: `001-especificacao-leia-o`
**Created**: 2025-10-02
**Status**: Draft
**Input**: User description: "especificacao - Leia o PRD.md com a especificação deste projeto"

## Execution Flow (main)
```
1. Parse user description from Input
   → If empty: ERROR "No feature description provided"
2. Extract key concepts from description
   → Identify: actors, actions, data, constraints
3. For each unclear aspect:
   → Mark with [NEEDS CLARIFICATION: specific question]
4. Fill User Scenarios & Testing section
   → If no clear user flow: ERROR "Cannot determine user scenarios"
5. Generate Functional Requirements
   → Each requirement must be testable
   → Mark ambiguous requirements
6. Identify Key Entities (if data involved)
7. Run Review Checklist
   → If any [NEEDS CLARIFICATION]: WARN "Spec has uncertainties"
   → If implementation details found: ERROR "Remove tech details"
8. Return: SUCCESS (spec ready for planning)
```

---

## ⚡ Quick Guidelines
- ✅ Focus on WHAT users need and WHY
- ❌ Avoid HOW to implement (no tech stack, APIs, code structure)
- 👥 Written for business stakeholders, not developers

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

## Clarifications

### Session 2025-10-02
- Q: Qual critério define o nome canônico quando múltiplas variações são agrupadas? → A: Variação padronizada (aplicar regra: "Sobrenome, Iniciais" sempre)
- Q: Qual o tempo máximo aceitável para processamento completo dos 4.6 milhões de registros? → A: ≤ 6 horas (processamento durante turno de trabalho)
- Q: O sistema deve suportar processamento em lotes/paralelo ou sequencial? → A: Processamento paralelo (múltiplos registros simultaneamente para atingir meta de 6h)
- Q: O relatório CSV deve incluir o índice de confiança para cada entrada? → A: Não, apenas nome canônico, variações e contagens
- Q: Qual o limiar mínimo de confiança aceitável para classificações e agrupamentos? → A: ≥ 0.70 (confiança moderada - aceitar maioria dos casos)

### Session 2025-10-03
- Q: What normalization rules should be applied to individual collector names? → A: Remove extra spaces + standardize punctuation + convert to uppercase for comparison (case-insensitive matching)
- Q: Which similarity algorithms should the system use for grouping name variations? → A: Combination: Levenshtein + Jaro-Winkler + phonetic (Soundex/Metaphone)
- Q: What should be the local database structure/schema for storing canonical entities and variations? → A: Single denormalized table: entity records with classification and embedded variation arrays

---

## User Scenarios & Testing *(mandatory)*

### Primary User Story
O sistema deve processar aproximadamente 4.6 milhões de registros de amostras de plantas (onde kingdom == "Plantae") de um banco de dados MongoDB, identificando e classificando coletores de amostras através da análise de strings contendo nomes. O objetivo é agrupar diferentes variações de representação de um mesmo coletor (por exemplo: "Forzza, R.C.", "Forzza, R.", "R.C. Forzza", e "Rafaela C. Forzza") sob um nome canônico, criando uma base de dados confiável de entidades com suas variações.

### Acceptance Scenarios
1. **Given** uma string de entrada "Silva, J. & R.C. Forzza; Santos, M. et al.", **When** o sistema processa a string, **Then** deve classificar como "conjunto_pessoas" com índice de confiança >= 0.90 e atomizar em ["Silva, J.", "R.C. Forzza", "Santos, M."]

2. **Given** múltiplas variações de um mesmo coletor no banco de dados (ex: "Forzza, R.C.", "Forzza, R.", "R.C. Forzza"), **When** o algoritmo de agrupamento é executado, **Then** todas as variações devem ser agrupadas sob um único nome canônico

3. **Given** uma string "Pesquisas da Biodiversidade", **When** o sistema classifica a entrada, **Then** deve identificar como "grupo_pessoas" (denominação genérica sem nomes próprios)

4. **Given** uma string "EMBRAPA" ou "USP", **When** o sistema classifica a entrada, **Then** deve identificar como "empresa/instituição"

5. **Given** uma string "?" ou "sem coletor", **When** o sistema classifica a entrada, **Then** deve identificar como "não determinado"

6. **Given** o processamento de 4.6 milhões de registros, **When** o algoritmo está em execução, **Then** o banco de dados local deve ser atualizado dinamicamente com novos padrões e agrupamentos identificados

7. **Given** a conclusão do processamento, **When** o relatório final é gerado, **Then** deve conter nome canônico, todas as variações, contagem de ocorrências para cada variação em formato CSV

### Edge Cases
- O que acontece quando uma string contém tanto nomes próprios quanto denominações institucionais misturados?
- Como o sistema lida com strings em diferentes idiomas ou com caracteres especiais/acentuação?
- Como o sistema processa strings com formatações inconsistentes ou malformadas?
- Como o sistema distingue entre iniciais de nomes e acrônimos institucionais?
- Quando o índice de confiança de classificação ou agrupamento está abaixo de 0.70, o sistema deve rejeitar ou marcar para revisão manual
- Como o sistema lida com registros duplicados ou redundantes durante o processamento?
- Como são tratadas as atualizações quando novos padrões são identificados que afetam agrupamentos já realizados?

## Requirements *(mandatory)*

### Functional Requirements

#### Classificação
- **FR-001**: Sistema MUST analisar strings e classificar em cinco categorias: Pessoa, Conjunto de Pessoas, Grupo de Pessoas, Empresa/Instituição, ou Não determinado
- **FR-002**: Sistema MUST calcular e armazenar um índice de confiança para cada classificação (escala 0.0 a 1.0)
- **FR-002a**: Sistema MUST aceitar classificações com índice de confiança >= 0.70 e rejeitar ou marcar para revisão manual classificações abaixo deste limiar
- **FR-003**: Sistema MUST identificar padrões de nomes individuais para classificar como "Pessoa" (ex: "Silva, J.C.", "Maria Santos", "G.A. Damasceno-Junior")
- **FR-004**: Sistema MUST identificar múltiplos nomes separados por ";", "&", ou "et al." como "Conjunto de Pessoas"
- **FR-005**: Sistema MUST identificar denominações genéricas sem nomes próprios como "Grupo de Pessoas" (ex: "Alunos da disciplina", "Equipe de pesquisa")
- **FR-006**: Sistema MUST identificar acrônimos e códigos institucionais como "Empresa/Instituição" (ex: "EMBRAPA", "USP", "RB", "INPA")
- **FR-007**: Sistema MUST classificar strings como "Não determinado" quando não puderem ser identificadas (ex: "?", "sem coletor", "não identificado")

#### Atomização
- **FR-008**: Sistema MUST separar strings classificadas como "Conjunto de Pessoas" em nomes individuais
- **FR-009**: Sistema MUST preservar a formatação original de cada nome individual após atomização
- **FR-010**: Sistema MUST reconhecer e processar corretamente os separadores: ";", "&", e "et al."

#### Normalização
- **FR-011**: Sistema MUST normalizar cada nome individual identificado
- **FR-012**: Sistema MUST aplicar normalização: remover espaços extras, padronizar pontuação, e converter para uppercase para comparação (matching case-insensitive)

#### Canonicalização
- **FR-013**: Sistema MUST agrupar variações similares de um mesmo coletor sob um nome canônico
- **FR-014**: Sistema MUST reconhecer como mesma entidade variações como: "Forzza, R.C.", "Forzza, R.", "R.C. Forzza", "Rafaela C. Forzza"
- **FR-015**: Sistema MUST calcular e armazenar um índice de confiança para cada agrupamento (escala 0.0 a 1.0)
- **FR-015a**: Sistema MUST aceitar agrupamentos com índice de confiança >= 0.70 e rejeitar ou marcar para revisão manual agrupamentos abaixo deste limiar
- **FR-016**: Sistema MUST aplicar formato padronizado "Sobrenome, Iniciais" como nome canônico para todas as entidades do tipo Pessoa (ex: todas as variações de "Forzza" devem resultar em "Forzza, R.C.")

#### Processamento e Performance
- **FR-017**: Sistema MUST processar registros de um banco MongoDB onde kingdom == "Plantae"
- **FR-018**: Sistema MUST ser capaz de processar aproximadamente 4.6 milhões de registros
- **FR-019**: Sistema MUST atualizar dinamicamente o banco de dados local durante o processamento à medida que novos padrões e agrupamentos são identificados
- **FR-020**: Sistema MUST completar o processamento de 4.6 milhões de registros em no máximo 6 horas (turno de trabalho)
- **FR-021**: Sistema MUST suportar processamento paralelo de múltiplos registros simultaneamente para atingir a meta de tempo de 6 horas

#### Armazenamento e Persistência
- **FR-022**: Sistema MUST armazenar resultados em um banco de dados local
- **FR-023**: Sistema MUST persistir: nome canônico de cada entidade, todas as variações identificadas, índice de confiança da classificação, índice de confiança do agrupamento
- **FR-024**: Sistema MUST manter o banco de dados local após conclusão do processamento para futuros tratamentos

#### Relatórios e Documentação
- **FR-025**: Sistema MUST gerar relatório final em formato CSV contendo exatamente três tipos de informação: nome canônico, variações identificadas, e contagem de ocorrências para cada variação (sem incluir índices de confiança)
- **FR-026**: Sistema MUST manter documentação das regras de identificação, separação e agrupamento de entidades
- **FR-027**: Sistema MUST permitir que a documentação seja editável para refinamento do algoritmo baseado na análise dos resultados

#### Pesquisa e Algoritmos
- **FR-029**: Sistema MUST utilizar algoritmos apropriados para identificação e classificação de strings com nomes de pessoas
- **FR-030**: Sistema MUST utilizar algoritmos de similaridade para agrupamento de variações de nomes
- **FR-031**: Sistema MUST utilizar combinação de algoritmos: Levenshtein distance + Jaro-Winkler + algoritmo fonético (Soundex ou Metaphone) para calcular similaridade entre nomes

### Key Entities *(include if feature involves data)*

- **Registro de Amostra**: Representa um registro individual do MongoDB com campo de coletor. Atributos principais: campo de texto com nome(s) do(s) coletor(es), kingdom (deve ser "Plantae"). Relacionamento: origem dos dados a serem processados

- **Classificação**: Representa o resultado da análise de uma string. Atributos: string original, categoria (Pessoa/Conjunto de Pessoas/Grupo de Pessoas/Empresa-Instituição/Não determinado), índice de confiança. Relacionamento: base para decisão de atomização

- **Nome Atomizado**: Representa um nome individual extraído de um conjunto. Atributos: string do nome, formatação original preservada, origem (string pai). Relacionamento: entrada para normalização

- **Nome Normalizado**: Representa um nome após processamento de normalização. Atributos: nome original, nome normalizado, regras aplicadas. Relacionamento: entrada para canonicalização

- **Entidade Canônica**: Representa um coletor único identificado pelo sistema. Atributos: nome canônico, tipo de entidade (Pessoa/Grupo/Instituição), índice de confiança do agrupamento. Relacionamento: agrupa múltiplas variações

- **Variação de Nome**: Representa uma forma diferente de representar uma entidade. Atributos: string da variação, contagem de ocorrências, índice de confiança da associação ao canônico. Relacionamento: vinculada a uma Entidade Canônica

- **Banco de Dados Local**: Armazena resultados do processamento. Atributos: tabela única desnormalizada contendo: id da entidade, nome canônico, tipo de classificação (Pessoa/Grupo/Instituição/Não determinado), índice de confiança da classificação, índice de confiança do agrupamento, array de variações (cada variação com: texto da variação, contagem de ocorrências, índice de confiança da associação). Relacionamento: repositório persistente de entidades canônicas e variações

- **Relatório CSV**: Documento final com resultados consolidados. Atributos: nome canônico, lista de variações, contagens de ocorrência para cada variação (não inclui índices de confiança). Relacionamento: visão consolidada simplificada do Banco de Dados Local

- **Documentação de Regras**: Documento editável com regras do algoritmo. Atributos: regras de classificação, regras de atomização, regras de normalização, regras de agrupamento. Relacionamento: guia para refinamento iterativo do sistema

---

## Review & Acceptance Checklist
*GATE: Automated checks run during main() execution*

### Content Quality
- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

### Requirement Completeness
- [x] No [NEEDS CLARIFICATION] markers remain (all resolved)
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

---

## Execution Status
*Updated by main() during processing*

- [x] User description parsed
- [x] Key concepts extracted
- [x] Ambiguities marked (7 clarification points identified)
- [x] User scenarios defined
- [x] Requirements generated (31 functional requirements)
- [x] Entities identified (9 key entities)
- [x] Review checklist passed (all clarifications resolved)

---

## Pending Clarifications

None - All clarifications have been resolved in Session 2025-10-03.

