<!--
Sync Impact Report:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Version: Initial (v1.0.0)
Created: 2025-10-02

Principles Established:
  1. Code Quality Standards - Comprehensive quality gates
  2. Test-First Development - Mandatory TDD with verification
  3. User Experience Consistency - Design system and patterns
  4. Performance Requirements - Quantifiable metrics and budgets

Templates Status:
  ✅ plan-template.md - Aligned (Constitution Check section references this doc)
  ✅ spec-template.md - Aligned (Quality requirements compatible)
  ✅ tasks-template.md - Aligned (TDD workflow enforced)

Follow-up TODOs: None
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-->

# coletoresBO Project Constitution

## Core Principles

### I. Code Quality Standards

All code contributions MUST meet these non-negotiable quality gates:

- **Static Analysis**: Zero linting errors, zero type errors (strict mode enabled)
- **Code Review**: All changes require peer review before merge; reviewer must verify tests pass
- **Formatting**: Automated formatting enforced (no manual formatting debates)
- **Documentation**: Public APIs/interfaces MUST have complete docstrings/comments explaining purpose, parameters, return values, and side effects
- **Complexity**: Functions >50 lines or cyclomatic complexity >10 require refactoring or explicit justification
- **Duplication**: DRY violations (>3 similar code blocks) MUST be refactored

**Rationale**: Quality gates prevent technical debt accumulation and ensure maintainable codebase. Automated enforcement removes subjectivity and saves review time.

### II. Test-First Development (NON-NEGOTIABLE)

TDD cycle MUST be strictly enforced for all features:

1. **Write Tests First**: Tests written and reviewed BEFORE implementation begins
2. **Verify Failure**: Tests MUST fail initially (red phase) - proves test validity
3. **Implement Minimally**: Write only enough code to make tests pass (green phase)
4. **Refactor**: Clean up code while keeping tests green

**Test Coverage Requirements**:
- Minimum 80% line coverage (measured, enforced in CI)
- 100% coverage for business logic and critical paths
- Contract tests for all public APIs
- Integration tests for user-facing workflows

**Rationale**: TDD ensures testable design, prevents over-engineering, provides living documentation, and catches regressions immediately.

### III. User Experience Consistency

All user-facing features MUST maintain consistent experience:

- **Design System**: Use established component library/design tokens; custom UI requires design approval
- **Interaction Patterns**: Follow platform conventions (web: standard forms, mobile: native patterns)
- **Accessibility**: WCAG 2.1 AA compliance mandatory (keyboard nav, screen readers, color contrast)
- **Error Handling**: User-friendly error messages with recovery actions (no raw stack traces)
- **Responsive**: All interfaces MUST work across target device/viewport sizes
- **Loading States**: Show progress indicators for operations >300ms

**Rationale**: Consistent UX reduces cognitive load, improves user satisfaction, and decreases support burden. Accessibility is both ethical and often legally required.

### IV. Performance Requirements

All features MUST meet quantifiable performance targets:

**Response Times** (measured at p95):
- API endpoints: <200ms
- Page loads: <2s (initial), <500ms (navigations)
- User interactions: <100ms (perceived instant)

**Resource Budgets**:
- Bundle size: <500KB initial JS (gzipped), <200KB per lazy chunk
- Memory: <200MB heap per user session
- Database queries: <50ms, N+1 queries forbidden

**Validation**:
- Performance tests run in CI for critical paths
- Lighthouse/Web Vitals scores: Performance >90, Accessibility 100
- Load testing: System handles 1000 concurrent users at target latency

**Rationale**: Performance directly impacts user satisfaction, conversion, and operational costs. Quantifiable targets enable objective evaluation.

## Testing Standards

### Test Categories

**Contract Tests** (API boundaries):
- One test file per endpoint/interface
- Assert request/response schemas match contracts
- Mock external dependencies
- Run in <5s total

**Integration Tests** (user workflows):
- End-to-end user scenarios from feature specs
- Use test databases/sandboxed environments
- Cover happy paths and critical error cases
- Cleanup state after each test

**Unit Tests** (isolated logic):
- Pure functions, algorithms, validations
- Fast (<100ms per suite)
- No I/O (filesystem, network, DB)

### Test Quality Gates

- All tests MUST be deterministic (no flaky tests tolerated)
- Test names MUST clearly describe what is being tested
- Tests MUST be independent (any order, parallel execution safe)
- Failures MUST provide actionable error messages

## Development Workflow

### Feature Development Process

1. **Specification**: Create feature spec (what/why, no how) → `/specify` approval
2. **Planning**: Design contracts, data models, tests → Constitution check
3. **Test Writing**: Write failing tests → Peer review → Verify red state
4. **Implementation**: Make tests pass → Keep commits atomic
5. **Validation**: All tests green, performance validated, docs updated

### Code Review Requirements

**Reviewer Responsibilities**:
- Verify tests exist and pass
- Check performance impact (no regressions)
- Validate accessibility compliance
- Confirm documentation completeness
- Ensure constitutional compliance

**Merge Criteria**:
- All CI checks green (tests, linting, type checking, performance)
- At least one approval from code owner
- No unresolved review comments
- Branch up-to-date with target

### Commit Standards

- **Atomic commits**: One logical change per commit
- **Conventional format**: `type(scope): description` (e.g., `feat(auth): add password reset`)
- **Types**: feat, fix, docs, test, refactor, perf, chore
- **Description**: Imperative mood ("add" not "added"), <72 chars

## Governance

### Amendment Process

Constitution changes require:
1. Written proposal with rationale and impact analysis
2. Team discussion (synchronous or async)
3. Consensus approval (or formal vote if consensus unreachable)
4. Migration plan for existing code (if applicable)
5. Template/documentation updates

### Versioning Policy

- **MAJOR**: Principle removal or backward-incompatible rule changes
- **MINOR**: New principles or substantially expanded guidance
- **PATCH**: Clarifications, wording improvements, typo fixes

### Compliance Enforcement

- All pull requests MUST pass constitution checklist (automated where possible)
- Constitutional violations block merge unless explicitly justified in Complexity Tracking
- Retrospectives review adherence and identify improvement opportunities
- Constitution supersedes all other practices in case of conflict

### Living Document Philosophy

This constitution should evolve with project needs:
- Review quarterly or when pain points emerge
- Propose changes via pull request (this file is version controlled)
- Amendments take effect upon merge, not retroactively
- Prior versions preserved in git history

**Version**: 1.0.0 | **Ratified**: 2025-10-02 | **Last Amended**: 2025-10-02
