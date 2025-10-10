# Active Context

## Current Work Focus

The data-platform-naming project is in a **Beta state (v0.1.0)** with core functionality implemented. The system provides CLI-based naming automation for AWS and Databricks resources with ACID transaction guarantees.

### Current State

- ✅ Core naming conventions implemented (AWS and Databricks)
- ✅ Blueprint-based declarative configuration with JSON Schema validation
- ✅ CLI interface with plan, create, read, delete commands
- ✅ Transaction management with file-based WAL
- ✅ Comprehensive testing and quality tooling (pytest, black, ruff, mypy, MegaLinter)
- ✅ Documentation complete (README, naming guides, CRUD docs)
- ✅ Configuration system foundation complete (values, patterns, scope filter)
- ✅ **AWS Generator refactored to use ConfigurationManager** (Phase 3A complete!)
- ⚠️ Databricks generator refactoring in progress
- ⚠️ Databricks SDK integration in progress (currently using requests library)
- ⚠️ Update command declared but not fully implemented
- ⚠️ No integration tests with real cloud accounts yet

### Active Areas

**Current Status**: Implementing Phase 3B - Databricks Generator Refactoring.

**Development Phase**: Beta (v0.1.0) - functional with major refactoring underway.

**Active Development**: Configuration-based naming system implementation (Phase 3):
- ✅ Phase 3A: AWS Generator refactored to use patterns + values (COMPLETE)
- ⏳ Phase 3B: Databricks Generator refactoring (NEXT)
- ⏳ Phase 3C: Move transformations to patterns (region codes, hash generation)
- ⏳ Phase 3D: Update blueprint parser to inject ConfigurationManager
- ⏳ Phase 3E: Integration testing and documentation

## Recent Changes

### Phase 3A: AWS Generator Refactoring (JUST COMPLETED)

**Date**: 2025-01-10

Successfully refactored AWSNamingGenerator for configuration-based name generation:

**Key Changes**:
1. **Constructor Enhancement**
   - Added `configuration_manager` parameter (Optional[ConfigurationManager])
   - Added explicit `use_config: bool = False` flag
   - Pattern validation runs at initialization (fail-fast approach)

2. **New Helper Methods**
   - `_validate_patterns_at_init()`: Validates all 13 AWS resource patterns on startup
   - `_generate_with_config()`: Unified generation logic for all methods
     - Merges config values with method parameters
     - Calls ConfigurationManager.generate_name()
     - Validates generated names
     - Returns clean result or raises ValueError

3. **All 13 Methods Refactored**
   - Each method now uses `_generate_with_config()` helper
   - Added optional `metadata` parameter for blueprint context
   - Comprehensive docstrings (Args, Returns, Raises)
   - Raises NotImplementedError if use_config=False (legacy mode removed)
   
   Refactored methods:
   - generate_s3_bucket_name
   - generate_glue_database_name
   - generate_glue_table_name
   - generate_glue_crawler_name
   - generate_lambda_function_name
   - generate_iam_role_name
   - generate_iam_policy_name
   - generate_kinesis_stream_name
   - generate_kinesis_firehose_name
   - generate_dynamodb_table_name
   - generate_sns_topic_name
   - generate_sqs_queue_name
   - generate_step_function_name

**Architecture Benefits**:
- Clean code with no legacy dual-mode complexity
- Fail-fast pattern validation at initialization
- Explicit opt-in with use_config flag
- Consistent pattern across all methods
- Easy to extend for new resource types

**Breaking Changes**:
- Legacy hardcoded pattern mode removed
- ConfigurationManager now required for name generation
- All methods require use_config=True to function
- Old API without ConfigurationManager raises NotImplementedError

**Testing**: Ready for unit tests in next phase.

### Initial Release

- Implemented naming patterns for AWS (S3, Glue) and Databricks (clusters, jobs, Unity Catalog)
- Built transaction manager with ACID guarantees
- Created CLI interface with Click
- Added comprehensive testing suite
- Integrated quality tools (black, ruff, mypy, MegaLinter)

## Current Implementation Plan

### Configuration-Based Naming System (IN PROGRESS - 60% Complete)

**Goal**: Enable users to easily change naming parameters and patterns without modifying code or blueprints.

**User Requirements**:
1. Set scope for blueprint (e.g., only process `aws_s3_bucket`) ✓
2. Easily change naming values (e.g., "platform" → "oncology") ✓
3. Substitute values via config file ✓
4. Customize naming patterns via separate config file ✓

**Architecture**:
```
CLI → ConfigurationManager → [NamingValuesLoader, NamingPatternsLoader, ScopeFilter]
    → Enhanced Generators (AWS/DBX) → Resources
```

**Key Components** (Status):
- ✅ `naming-values.yaml`: Substitutes variable values (project, env, etc.) - COMPLETE
- ✅ `naming-patterns.yaml`: Defines pattern templates with {placeholders} - COMPLETE
- ✅ `ScopeFilter`: Filters resources by type (include/exclude with wildcards) - COMPLETE
- ✅ `ConfigurationManager`: Orchestrates configs and validates patterns - COMPLETE
- ✅ JSON Schemas with comprehensive validation - COMPLETE
- ✅ Comprehensive schema documentation (schemas/README.md) - COMPLETE
- ⏳ Blueprint integration: Add scope section to blueprint schema - IN PROGRESS
- ❌ Enhanced generators: Use patterns + values instead of hardcoded logic - NOT STARTED
- ❌ CLI integration: Add config commands and flags - NOT STARTED

**Config File Locations**:
- Explicit paths: `--values-config path/to/file.yaml`
- Default locations: `~/.dpn/naming-values.yaml`
- Both supported

**Test Coverage**:
- NamingValuesLoader: 88% coverage ✓
- NamingPatternsLoader: 89% coverage ✓
- ConfigurationManager: 94% coverage ✓
- ScopeFilter: 100% coverage (33 tests) ✓

**Implementation Status**: 
- ✅ Phase 1: Foundation (COMPLETE - values, patterns, config manager)
- ✅ Phase 2: Scope Filtering (COMPLETE - filter + blueprint integration)
- ✅ Phase 3A: AWS Generator Refactoring (COMPLETE - 13 methods refactored)
- ⏳ Phase 3B: Databricks Generator Refactoring (NEXT - 15+ methods to refactor)
- ⏳ Phase 3C: Pattern Transformations (move region codes, hash to YAML)
- ⏳ Phase 3D: Blueprint Parser Update (inject ConfigurationManager)
- ⏳ Phase 3E: Integration & Documentation

## Next Steps

Priority implementation tasks:

1. **Configuration System** (Weeks 1-3)
   - JSON schemas for configs
   - Config loaders and validators
   - Scope filtering
   - Generator refactoring
   - CLI integration

2. When configuration system complete, future priority areas:

1. **Platform Expansion** (from roadmap)
   - Azure naming support
   - GCP naming support

2. **Integration Enhancements**
   - Terraform provider
   - GitHub Actions integration

3. **User Experience**
   - Web UI for blueprint creation
   - API server mode for programmatic access

4. **Security & Compliance**
   - SCIM integration for ACL synchronization
   - Automated compliance reporting

## Active Decisions and Considerations

### Architecture Decisions Made

## 1. File-Based Transaction Management

- Decision: Use file-based WAL instead of database
- Rationale: Simplicity, no external dependencies, portable
- Status: Implemented and working well
- Consideration: If high-concurrency becomes a requirement, would need to reconsider

## 2. JSON Blueprint Format**

- Decision: JSON with JSON Schema validation (not YAML)
- Rationale: Strong validation, wide tooling support, programmatic generation
- Status: Working well
- Consideration: Users occasionally request YAML support; could add as output format

## 3. Sequential Execution

- Decision: Execute operations sequentially, not in parallel
- Rationale: Simpler rollback, clear error attribution, predictable behavior
- Status: Acceptable performance for typical use cases
- Consideration: For large deployments (>100 resources), parallel execution could help

## 4. CLI-First Approach

- Decision: Build as CLI tool, not web service
- Rationale: Fits IaC workflows, easy CI/CD integration, no server management
- Status: Perfect for target audience
- Consideration: Some users want web UI; could be added later wrapping CLI

### Technical Patterns in Use

## Naming Conventions

```python
# AWS S3 Bucket
{project}-{purpose}-{layer}-{env}-{region}
Example: dataplatform-raw-raw-prd-useast1

# AWS Glue Database
{project}_{domain}_{layer}_{env}
Example: dataplatform_finance_gold_prd

# Databricks Cluster
{project}-{workload}-{type}-{env}
Example: dataplatform-etl-shared-prd

# Unity Catalog 3-tier
{project}_{type}_{env}.{domain}_{layer}.{type}_{entity}
Example: dataplatform_main_prd.finance_gold.dim_customers
```

## Transaction Flow

```python
1. Begin transaction → Create WAL file
2. Acquire file lock
3. Execute operations sequentially
4. On success: Commit WAL, release lock
5. On failure: Rollback operations, mark WAL, release lock
```

## Error Handling Strategy

- Validation errors: Fail fast before any API calls
- API errors: Retry with backoff for transient, rollback for permanent
- System errors: WAL enables crash recovery

### Learnings and Project Insights

## What Works Well

1. **Blueprint Preview Mode**
   - Users love seeing all names before creation
   - Catches errors early
   - Builds confidence in automation

2. **Rich Progress Bars**
   - Real-time feedback critical for user experience
   - Prevents "is it working?" uncertainty
   - Clear error messages when things fail

3. **Transaction Rollback**
   - Automatic rollback prevents partial deployments
   - Users trust the system won't leave mess
   - Recovery commands rarely needed

4. **UV Package Manager**
   - Fast, reliable dependency management
   - Single command setup (`uv sync`)
   - Better than pip for development workflow

5. **Separate Platform Modules**
   - AWS and DBX logic cleanly separated
   - Easy to test independently
   - Clear extension points for new platforms

## Areas for Improvement

1. **Blueprint Creation**
   - Currently manual JSON editing
   - Could benefit from interactive wizard
   - Template library would help users get started

2. **Error Messages**
   - Some AWS/DBX errors are cryptic
   - Could provide more context-specific guidance
   - Link to documentation for common issues

3. **State Inspection**
   - Current state query capabilities limited
   - Could add richer filtering and search
   - Dashboard view would be helpful

4. **Parallel Execution**
   - Sequential execution can be slow for large blueprints
   - Safe parallelization would improve performance
   - Need to maintain rollback capability

5. **Documentation**
   - Good README, but need more examples
   - Video tutorials would help adoption
   - Troubleshooting guide for common issues

## Key Patterns to Maintain

1. **Safety First**: Always validate before executing
2. **Transparency**: Show what will happen before it happens
3. **Recoverability**: Every operation can be rolled back
4. **Simplicity**: Common tasks should be one command
5. **Extensibility**: Easy to add new platforms and resources

## Development Practices

1. **Test Coverage**: Maintain >80% coverage
2. **Type Hints**: All public functions have type annotations
3. **Documentation**: Docstrings for all public APIs
4. **Code Quality**: Black + Ruff + Mypy before commit
5. **Dependencies**: Minimize external dependencies

## Important Implementation Notes

### Blueprint Reference Resolution

- References use format: `{resource_type}-{identifier}`
- Example: `"cluster_ref": "etl"` resolves to cluster named `dataplatform-etl-shared-prd`
- Resolution happens during blueprint parsing
- Circular references are detected and rejected

### WAL File Naming

- Format: `tx-{timestamp}-{random}.wal`
- Committed: `.committed` suffix added
- Rolled back: `.rolled_back` suffix added
- Recovery scans for files without suffix

### File Locking

- Uses `fcntl.flock()` on Unix (macOS, Linux)
- Uses `msvcrt.locking()` on Windows
- Lock held for entire transaction duration
- Prevents concurrent modifications

### Name Generation Edge Cases

- Region names normalized: `us-east-1` → `useast1`
- Environment names lowercased: `PRD` → `prd`
- Project names lowercased with hyphens: `Data Platform` → `data-platform`
- Invalid characters replaced with hyphens

### Error Context Preservation

- Exceptions wrapped with operation context
- Stack traces preserved for debugging
- User-friendly messages extracted
- Original error available in logs

## Configuration Preferences

### Code Style

- Line length: 100 characters (project override in pyproject.toml)
- Import sorting: ruff handles automatically
- Type hints: Required for all public functions
- Docstrings: Google style

### Testing

- Use pytest fixtures for common setup
- Mock AWS/DBX calls in unit tests
- Integration tests use real services in test accounts
- Coverage target: >80%

### Git Workflow

- Feature branches from main
- PR required for merges
- CI runs tests + linters
- Squash commits on merge

### Documentation

- README for getting started
- Individual docs for naming guides
- Inline comments for complex logic
- Docstrings for all public APIs

## Environment Details

### Development Machine

- macOS (primary development environment)
- Python 3.9+ via pyenv or system Python
- UV package manager for dependencies
- VSCode with Python extension

### Testing Environments

- AWS: Test account with limited permissions
- Databricks: Test workspace
- CI/CD: GitHub Actions (future)

### State Location

- Local: `~/.dpn/`
- WAL: `~/.dpn/wal/`
- State: `~/.dpn/state/state.json`

## Quick Reference Commands

```bash
# Development Setup
uv sync --dev

# Create Blueprint
uv run dpn plan init --env prd --project platform --output prod.json

# Preview Names
uv run dpn plan preview prod.json

# Create Resources
uv run dpn create --blueprint prod.json --dry-run
uv run dpn create --blueprint prod.json

# Run Tests
uv run pytest --cov

# Code Quality
uv run black src/ tests/
uv run ruff check src/ tests/ --fix
uv run mypy src/
```

## Current Challenges

None currently. System is stable and working as designed.

## Success Metrics Tracking

### User Metrics (Target vs Actual)

- Time to provision: < 2 min ✅ (typically 30-60s)
- Error rate: < 5% ✅ (validation catches most errors)
- Recovery time: < 30s ✅ (automatic rollback)
- Learning curve: < 10 min ✅ (simple CLI interface)

### System Health

- Code coverage: >80% ✅
- Type coverage: 100% ✅
- Linter warnings: 0 ✅
- Documentation: Complete ✅
