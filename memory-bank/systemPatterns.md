# System Patterns

## Recent Architectural Evolution

### Sprint 1: Simplification & Type Safety (Oct 2025)

**Problem Identified**: Dual-mode complexity (use_config flag), 61 type errors, no input validation

**Solutions**:

1. **Removed Legacy Mode** (-162 lines)
   - Made ConfigurationManager required
   - Eliminated 27 try/except fallback blocks
   - Learning: Single path > flexibility

2. **Fixed Type Safety** (61 → 0 errors)
   - TYPE_CHECKING guards, Optional handling, cast() ops
   - Learning: Strong typing prevents error classes

3. **Input Validation** (Whitelist approach)
   - ALLOWED_OVERRIDE_KEYS, enum validation, regex
   - Learning: Fail-fast improves UX

**Impact**: Single code path, 100% mypy compliance, all CLI inputs validated

### Sprint 2: Consistency & Error Context (In Progress - Oct 2025)

**Status**: 53% Complete | **Started**: Oct 22, 2025

**Strategy**:

1. **Type-safe Enums** (Issue #4) - 50% complete
   - Replace 50+ magic strings with enums
   - Removed duplicate ResourceType enum
   - Learning: Enum consolidation requires careful dependency tracking

2. **Modern Type Hints** (Issue #5) - 0% complete
   - Add `from __future__ import annotations` to 17 files
   - Replace Dict/List with dict/list syntax
   - Learning: Deferred to focus on exception hierarchy first

3. **Exception Hierarchy** (Issue #7) - 65% complete
   - 8 custom exception classes with rich context
   - 59 replacements completed across 5 files
   - 13 replacements remaining across 3 files
   - Learning: Enhanced debugging worth the refactoring effort

**Key Insights**:

- **Tool Selection**: write_to_file more reliable than replace_in_file for large files (>1000 lines)
- **Batch Operations**: Multiple SEARCH/REPLACE blocks in single call more efficient
- **Import Ripple Effects**: Removing exports breaks consumers - must update in lockstep
- **Pre-existing Design**: Well-designed exception hierarchy accelerated implementation
- **Test Impact**: Exception changes require careful test assertion updates

---

## System Architecture

### High-Level Components

```
CLI Layer
    ↓
Blueprint Layer (parsing, validation, name generation)
    ↓
Transaction Manager (ACID, WAL, rollback)
    ↓
CRUD Operations (AWS & Databricks)
```

### Data Flow

1. **Blueprint → Validation**: Schema enforcement, reference resolution
2. **Validation → Planning**: Dependency graph, execution order
3. **Planning → Transaction**: WAL creation, file locking
4. **Transaction → Execution**: Sequential operations, progress tracking
5. **Execution → Completion**: Commit WAL or rollback

---

## Key Technical Decisions

### 1. File-Based Transaction Management

**Decision**: WAL instead of database

**Rationale**: Simple, portable, sufficient for CLI tool

**Trade-offs**: Not for high-concurrency, manual cleanup required

### 2. Declarative Blueprint Format

**Decision**: JSON with JSON Schema

**Rationale**: Strong validation, wide tooling support, version control

**Trade-offs**: More verbose than YAML

### 3. Separate Platform Operations

**Decision**: Distinct AWS & Databricks modules

**Rationale**: Different APIs, independent error handling, clear separation

**Trade-offs**: Some code duplication

### 4. Sequential Execution

**Decision**: Execute operations sequentially with rollback

**Rationale**: Simpler error handling, clear rollback order, predictable

**Trade-offs**: Slower than parallel (acceptable for <100 resources)

### 5. CLI-First Interface

**Decision**: CLI tool, not web service

**Rationale**: IaC workflows, CI/CD integration, no server infrastructure

**Future**: API server mode can wrap CLI

---

## Configuration System Architecture

### High-Level

```m
Configuration Files (YAML)
    ↓
ConfigurationManager (orchestrator)
    ↓ (NamingValuesLoader, NamingPatternsLoader, ScopeFilter)
    ↓
Name Generators (AWS & Databricks)
    ↓
Generated Names
```

### Value Precedence

```m
defaults → environment → resource_type → blueprint metadata
```

---

## Design Patterns in Use

### 1. Command Pattern (CLI)

Each CLI command encapsulated (`create`, `read`, `update`, `delete`)

### 2. Strategy Pattern (Platform Operations)

Different strategies for AWS vs Databricks with common interface

### 3. Template Method Pattern (Transaction Flow)

TransactionManager defines skeleton, operations fill in details

### 4. Builder Pattern (Blueprint Construction)

Fluent interface for building blueprints

### 5. Repository Pattern (State Management)

Abstract state storage and retrieval

### 6. Strategy Pattern (Configuration)

Configurable naming strategies based on YAML files

### 7. Composite Pattern (Configuration Hierarchy)

Merge configurations with clear precedence

### 8. Filter Pattern (Scope Filtering)

Filter resources by type with wildcard support

---

## Critical Implementation Paths

### Path 1: Create Resources (Happy Path)

1. Parse blueprint (validate schema, resolve references)
2. Generate names (apply patterns, validate)
3. Plan execution (build dependency graph)
4. Execute transaction (WAL, lock, operations, commit)
5. Update state (persist metadata, timestamps)

### Path 2: Rollback on Failure

1. Operation fails (capture exception, mark failed)
2. Initiate rollback (reverse operation list)
3. Complete rollback (mark WAL, release lock, update state)

### Path 3: Recovery from Crash

1. Detect incomplete transaction (scan WAL)
2. Analyze state (determine completed ops)
3. Execute recovery (rollback partial ops, cleanup)

### Path 4: Preview Mode

1. Parse blueprint (same as create)
2. Generate names (same as create)
3. Simulate execution (**skip API calls**)
4. Display results (table/JSON format)

---

## Error Handling Strategy

### Validation Errors (Fail Fast)

- Caught during blueprint parsing
- Clear line-numbered messages
- No API calls made

### API Errors (Retry with Backoff)

- Transient: exponential backoff
- Permanent: fail and rollback
- Rate limiting: respect retry-after headers

### System Errors (Crash Recovery)

- File lock prevents concurrent transactions
- WAL enables recovery after crash
- Idempotent operations allow safe retry

---

## Performance Considerations

### Batch Operations

- Single API call per resource type when possible
- Minimize round trips

### Caching

- Cache AWS region data
- Cache Databricks cluster types
- Invalidate on error or refresh

### Progress Feedback

- Real-time rich progress bars
- Estimated completion time
- Clear error messages

---

## Component Relationships

### Blueprint → Generators

```m
Blueprint (JSON)
    ↓ (BlueprintParser)
GeneratedNames (validated)
    ↓ (Transaction)
PlatformOperations
```

### Transaction → Operations

```m
TransactionManager
    ↓ (creates)
Transaction (with WAL)
    ↓ (executes)
Operations (AWS/DBX)
    ↓ (updates)
State Repository
```

### CLI → All Layers

```m
CLI Command
    ↓ (loads)
Blueprint
    ↓ (validates)
Schema + Validators
    ↓ (initiates)
Transaction
    ↓ (executes)
Platform Operations
```

---

## Naming Conventions

```python
AWS S3: {project}-{purpose}-{layer}-{env}-{region}
AWS Glue: {project}_{domain}_{layer}_{env}
Databricks Cluster: {project}-{workload}-{type}-{env}
Unity Catalog: {project}_{type}_{env}.{domain}_{layer}.{type}_{entity}
```

---

## Testing Strategy

### Unit Tests

- Name generators with various inputs
- Validators with edge cases
- Transaction manager with mock operations

### Integration Tests

- Full blueprint processing
- Transaction commit and rollback
- State persistence and recovery

### End-to-End Tests (Manual)

- Real AWS/DBX accounts (test environments)
- Multi-environment deployments
- Disaster recovery scenarios
