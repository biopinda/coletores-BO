# Feature Specification: Estrutura de Execução Baseada em Scripts Existentes

**Feature Branch**: `main`
**Created**: 2025-09-24
**Status**: Integrated into [main spec](spec.md)
**Input**: "a estrutura de execução de ve considerar os scripts existentes em @src\ e a ordem de execução destes scripts. Fundamentar ter um script que inicialmente analisa (analise_coletores.py) para encontrar os padrões e aprender com estes padrões."

## User Scenarios & Testing

### Primary User Story
Pesquisadores e administradores de banco de dados precisam executar o sistema de canonicalização de coletores seguindo uma ordem específica que considera os scripts existentes, começando com uma análise exploratória para descobrir padrões nos dados antes de iniciar o processamento principal.

### Acceptance Scenarios
1. **Given** o sistema possui scripts existentes em src/, **When** o usuário executa o workflow de canonicalização, **Then** o sistema deve executar analise_coletores.py primeiro para descobrir padrões
2. **Given** a análise exploratória foi concluída, **When** o sistema procede para o processamento, **Then** deve usar os padrões descobertos para otimizar a canonicalização
3. **Given** o processamento principal foi executado, **When** o sistema gera relatórios, **Then** deve incluir insights da análise inicial
4. **Given** os relatórios foram gerados, **When** o sistema executa validação, **Then** deve comparar resultados com padrões esperados da análise
5. **Given** todo o pipeline foi executado, **When** o usuário consulta os resultados, **Then** deve ter acesso a métricas de qualidade baseadas na análise inicial

### Edge Cases
- Como o sistema lida quando analise_coletores.py encontra padrões inesperados ou anômalos?
- O que acontece se a análise inicial falha mas existem checkpoints de processamentos anteriores?
- Como o sistema se comporta quando os padrões descobertos diferem significativamente dos padrões esperados?

## Requirements

### Functional Requirements
- **FR-001**: Sistema DEVE executar analise_coletores.py como primeiro passo obrigatório do pipeline de canonicalização
- **FR-002**: Script analise_coletores.py DEVE processar TODOS os registros da coleção "ocorrencias" que possuem o atributo "recordedBy" (sem limitação de quantidade)
- **FR-003**: Sistema DEVE descobrir padrões de separadores, grupos e instituições através da análise exploratória completa do dataset
- **FR-004**: Sistema DEVE aplicar padrões descobertos na análise para configurar dinamicamente os algoritmos de processamento
- **FR-005**: Sistema DEVE seguir ordem específica de execução: análise → processamento → relatórios → validação
- **FR-006**: Sistema DEVE preservar resultados da análise exploratória para uso em etapas subsequentes
- **FR-007**: Sistema DEVE permitir reexecução de etapas individuais usando resultados de análises anteriores
- **FR-008**: Sistema DEVE integrar descobertas da análise nos relatórios de qualidade e validação
- **FR-009**: Sistema DEVE otimizar configurações de similaridade baseando-se na distribuição completa de dados descoberta
- **FR-010**: Sistema DEVE detectar automaticamente quando nova análise é necessária (mudanças significativas nos dados)
- **FR-011**: Sistema DEVE manter histórico de análises para comparação de evolução dos padrões de dados

### Key Entities
- **Script de Análise**: analise_coletores.py responsável por descoberta de padrões e análise exploratória
- **Script Principal**: processar_coletores.py que executa canonicalização baseada nos padrões descobertos
- **Script de Relatórios**: gerar_relatorios.py que inclui insights da análise inicial
- **Script de Validação**: validar_canonicalizacao.py que compara resultados com expectativas da análise
- **Ordem de Execução**: Sequência obrigatória que garante que análise precede processamento
- **Padrões Descobertos**: Estruturas de dados que capturam regularidades encontradas na análise exploratória

---

## Estrutura de Execução Atual (Scripts Existentes)

### Scripts Identificados no src/
1. **analise_coletores.py** - Análise exploratória e descoberta de padrões
2. **processar_coletores.py** - Processamento principal de canonicalização
3. **gerar_relatorios.py** - Geração de relatórios de qualidade
4. **validar_canonicalizacao.py** - Validação dos resultados
5. **canonicalizador_coletores.py** - Classes core do sistema

### Ordem de Execução Proposta
```
1. ANÁLISE EXPLORATÓRIA (analise_coletores.py)
   ↓ Descoberta de padrões, distribuições, anomalias

2. PROCESSAMENTO PRINCIPAL (processar_coletores.py)
   ↓ Canonicalização usando padrões descobertos

3. GERAÇÃO DE RELATÓRIOS (gerar_relatorios.py)
   ↓ Relatórios enriquecidos com insights da análise

4. VALIDAÇÃO DE QUALIDADE (validar_canonicalizacao.py)
   ↓ Validação baseada em expectativas da análise inicial
```

### Justificativa para Análise Primeiro

**Descoberta de Padrões Reais**: A análise exploratória de TODOS os registros com recordedBy revela padrões específicos do dataset completo, permitindo configuração dinâmica dos algoritmos ao invés de usar configurações estáticas baseadas em amostras.

**Otimização de Similaridade**: Análise da distribuição completa de nomes permite ajustar thresholds de similaridade para todo o dataset específico, garantindo máxima precisão.

**Detecção de Anomalias**: Identificação prévia de casos edge em todo o conjunto de dados permite tratamento especializado durante o processamento.

**Métricas de Qualidade**: Estabelece baseline estatístico abrangente para validação posterior da qualidade dos resultados baseado na totalidade dos dados.

**Configuração Adaptativa**: Permite que o sistema se adapte automaticamente a diferentes tipos de dados de biodiversidade usando o conhecimento completo do dataset.

**Cobertura Completa**: Análise de todos os 11M+ registros garante que nenhum padrão importante seja perdido por amostragem limitada.

## Review & Acceptance Checklist

### Content Quality
- [x] Focused on execution workflow and script integration
- [x] Based on existing codebase structure
- [x] Written for technical stakeholders
- [x] All mandatory sections completed

### Requirement Completeness
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Scope is clearly bounded
- [x] Dependencies on existing scripts identified

---

## Implementation Impact

Esta especificação requer atualizações em:

1. **specs/main/plan.md** - Adicionar fase de análise exploratória antes do processamento
2. **specs/main/tasks.md** - Reorganizar tarefas para priorizar análise e descoberta de padrões
3. **Pipeline de Execução** - Implementar orquestração que garante ordem correta
4. **Integração de Dados** - Mecanismo para passar padrões descobertos entre scripts