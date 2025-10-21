# Sprint 2 Implementation Plan: Code Quality & Consistency

**Sprint Goal**: Improve codebase maintainability through consistency, eliminate magic strings, and enhance error handling

**Duration**: Week 2 (5 days)

**Prerequisites**: Sprint 1 Complete ✅
- Legacy mode removed
- All type hints fixed (0 mypy errors)
- 94/94 core tests passing

---

## Overview

Sprint 2 addresses three code review findings:

1. **Issue #4**: Consolidate magic strings into constants
2. **Issue #5**: Standardize type hints (modern Python 3.9+ syntax)
3. **Issue #7**: Enhanced error context with exception hierarchy

**Success Metrics**:
- Zero magic strings in critical paths
- Consistent type hint style throughout
- Structured error messages with context
- All tests passing (94+ tests)
- Mypy passes with 0 errors

---

## Day 1-2: Consolidate Magic Strings (Issue #4)

**Goal**: Replace 50+ magic string occurrences with type-safe enums

**Estimated Time**: 8 hours

### Current Problems

Magic strings repeated throughout codebase:

```python
# Environment strings (10+ occurrences)
'dev', 'stg', 'prd'

# Resource types (50+ occurrences)
'aws_s3_bucket', 'aws_glue_database', 'dbx_cluster', etc.

# Data layers (20+ occurrences)
# AWS: 'raw', 'processed', 'curated'
# Databricks: 'bronze', 'silver', 'gold'
```

**Issues**:
- No type safety (typos like 'prod' vs 'prd' possible)
- No IDE autocomplete
- Hard to extend (add new environment)
- Easy to introduce bugs

### Implementation Steps

#### Step 1: Expand constants.py with Enums (2 hours)

Add to `src/data_platform_naming/constants.py`:

```python
from enum import Enum

class Environment(str, Enum):
    """Environment codes for deployments"""
    DEV = "dev"
    STG = "stg"
    PRD = "prd"

class AWSResourceType(str, Enum):
    """AWS resource type identifiers"""
    S3_BUCKET = "aws_s3_bucket"
    GLUE_DATABASE = "aws_glue_database"
    GLUE_TABLE = "aws_glue_table"
    GLUE_CRAWLER = "aws_glue_crawler"
    LAMBDA_FUNCTION = "aws_lambda_function"
    IAM_ROLE = "aws_iam_role"
    IAM_POLICY = "aws_iam_policy"
    KINESIS_STREAM = "aws_kinesis_stream"
    KINESIS_FIREHOSE = "aws_kinesis_firehose"
    DYNAMODB_TABLE = "aws_dynamodb_table"
    SNS_TOPIC = "aws_sns_topic"
    SQS_QUEUE = "aws_sqs_queue"
    STEP_FUNCTION = "aws_step_function"

class DatabricksResourceType(str, Enum):
    """Databricks resource type identifiers"""
    WORKSPACE = "dbx_workspace"
    CLUSTER = "dbx_cluster"
    JOB = "dbx_job"
    NOTEBOOK = "dbx_notebook"
    REPO = "dbx_repo"
    PIPELINE = "dbx_pipeline"
    SQL_WAREHOUSE = "dbx_sql_warehouse"
    CATALOG = "dbx_catalog"
    SCHEMA = "dbx_schema"
    TABLE = "dbx_table"
    VOLUME = "dbx_volume"
    SECRET_SCOPE = "dbx_secret_scope"
    INSTANCE_POOL = "dbx_instance_pool"
    POLICY = "dbx_policy"

class AWSDataLayer(str, Enum):
    """AWS S3 data layer names"""
    RAW = "raw"
    PROCESSED = "processed"
    CURATED = "curated"
    ARCHIVE = "archive"
    LOGS = "logs"

class DatabricksDataLayer(str, Enum):
    """Databricks medallion architecture layers"""
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
```

**Why `str, Enum`?**
- Enums work as strings in all contexts
- JSON serialization automatic
- Type safety + IDE autocomplete
- Backward compatible with string comparisons

#### Step 2: Update All Modules (4 hours)

**Priority files** (most occurrences → least):

1. `src/data_platform_naming/config/configuration_manager.py`
2. `src/data_platform_naming/aws_naming.py`
3. `src/data_platform_naming/dbx_naming.py`
4. `src/data_platform_naming/plan/blueprint.py`
5. `src/data_platform_naming/cli.py`
6. `src/data_platform_naming/config/naming_values_loader.py`
7. `src/data_platform_naming/config/naming_patterns_loader.py`

**Transformation pattern**:

```python
# BEFORE
if environment not in ['dev', 'stg', 'prd']:
    raise ValueError(f"Invalid environment: {environment}")

# AFTER
from constants import Environment

if environment not in [e.value for e in Environment]:
    raise ValueError(
        f"Invalid environment: {environment}. "
        f"Valid options: {', '.join(e.value for e in Environment)}"
    )

# OR with type hints (preferred)
def generate_name(environment: Environment, ...) -> str:
    # Type checker ensures only valid environments
    pass
```

**Search and replace patterns**:

```bash
# Find all magic strings
grep -r "'dev'" src/
grep -r "'stg'" src/
grep -r "'prd'" src/
grep -r "'aws_s3_bucket'" src/
grep -r "'dbx_cluster'" src/
grep -r "'bronze'" src/
grep -r "'silver'" src/
grep -r "'gold'" src/
```

#### Step 3: Update Tests (2 hours)

Update ~30 tests across:
- `tests/test_aws_naming.py`
- `tests/test_dbx_naming.py`
- `tests/test_configuration_manager.py`
- `tests/test_cli_integration.py`

**Example transformation**:

```python
# BEFORE
def test_s3_bucket_name():
    name = generator.generate_s3_bucket_name(
        purpose="raw",
        layer="raw",
        metadata={"environment": "dev"}
    )

# AFTER
from constants import AWSDataLayer, Environment

def test_s3_bucket_name():
    name = generator.generate_s3_bucket_name(
        purpose="raw",
        layer=AWSDataLayer.RAW.value,
        metadata={"environment": Environment.DEV.value}
    )
```

#### Step 4: Verification (30 minutes)

```bash
# Search for remaining magic strings
grep -r "'dev'" src/ tests/
grep -r "'aws_s3_bucket'" src/ tests/
grep -r "'bronze'" src/ tests/

# Run full test suite
uv run pytest --cov

# Type check
uv run mypy src/

# Expected results:
# - <10 magic string occurrences (only in comments/docs)
# - All tests passing (94+)
# - 0 mypy errors
```

### Day 1-2 Success Criteria

- ✅ Enums added to constants.py (5 new enums)
- ✅ Zero magic strings in critical paths
- ✅ All 7 priority files updated
- ✅ ~30 tests updated and passing
- ✅ Mypy passes (0 errors)
- ✅ Code reduction: ~50 lines removed

---

## Day 3: Standardize Type Hints (Issue #5)

**Goal**: Consistent modern Python 3.9+ type hint syntax throughout codebase

**Estimated Time**: 6 hours

### Current Problems

Mixed type hint styles:

```python
# Modern syntax (Python 3.9+)
def method(values: dict[str, Any]) -> list[str]:
    pass

# Old syntax (Python 3.8 compat)
from typing import Dict, List
def method(values: Dict[str, Any]) -> List[str]:
    pass

# Overuse of Any
def method(config: Any) -> Any:
    pass
```

### Implementation Steps

#### Step 1: Add Future Annotations Import (30 minutes)

Add to ALL Python files in `src/`:

```python
from __future__ import annotations
```

**Benefits**:
- Forward references without quotes
- Postponed evaluation of annotations
- Better performance
- Required for some type features

**Files to update** (~17 files):
```bash
# Find all Python files
find src/ -name "*.py" -type f

# Add import to each file (first import line)
```

#### Step 2: Replace Old-Style Type Hints (2 hours)

**Conversion rules**:

```python
# Collections
Dict[K, V] → dict[K, V]
List[T] → list[T]
Set[T] → set[T]
Tuple[T, ...] → tuple[T, ...]

# Keep Optional (Python 3.9, not 3.10+)
Optional[T] → Optional[T]  # Don't change to T | None yet
```

**Files to update**:
- `src/data_platform_naming/`
- `src/data_platform_naming/config/`
- `src/data_platform_naming/crud/`
- `src/data_platform_naming/plan/`

**Search patterns**:

```bash
grep -r "Dict\[" src/
grep -r "List\[" src/
grep -r "Set\[" src/
grep -r "Tuple\[" src/
```

#### Step 3: Replace Any with Specific Types (2 hours)

**Target areas with Any**:

1. **Configuration Manager**:

```python
# BEFORE
def get_values_for_resource(
    self, 
    resource_type: Any
) -> dict[str, Any]:
    pass

# AFTER
def get_values_for_resource(
    self, 
    resource_type: str | AWSResourceType | DatabricksResourceType
) -> dict[str, str | int | bool]:
    pass
```

2. **Name Generators**:

```python
# BEFORE
def generate_name(
    self,
    params: Any
) -> Any:
    pass

# AFTER  
def generate_name(
    self,
    params: dict[str, str]
) -> GeneratedName:
    pass
```

3. **Blueprint Parser**:

```python
# BEFORE
def parse_blueprint(
    self,
    blueprint: Any
) -> Any:
    pass

# AFTER
def parse_blueprint(
    self,
    blueprint: dict[str, Any]
) -> list[Operation]:
    pass
```

#### Step 4: Run Mypy Verification (30 minutes)

```bash
# Clean check with strict mode
uv run mypy src/ --strict

# Fix any new errors introduced
# Target: 0 errors

# Common fixes needed:
# - Add return type annotations
# - Fix Optional handling
# - Add None checks before attribute access
```

#### Step 5: Update Test Type Hints (1 hour)

Apply same standards to test files:

```python
# Modern syntax
def test_function() -> None:
    values: dict[str, str] = {"key": "value"}
    result: list[str] = process_values(values)
    assert result == expected
```

### Day 3 Success Criteria

- ✅ All files use `from __future__ import annotations`
- ✅ Zero old-style type hints (Dict, List, etc.)
- ✅ <10 uses of `Any` in src/ (only where truly needed)
- ✅ Mypy passes with --strict flag
- ✅ All tests passing (94+)

---

## Day 4-5: Enhanced Error Context (Issue #7)

**Goal**: Structured exception hierarchy with rich context for debugging

**Estimated Time**: 11 hours

### Current Problems

```python
# Generic exceptions
raise ValueError(f"Blueprint validation failed: {e.message}")
raise Exception("Something went wrong")

# Issues:
# - No context about what was being processed
# - No links to documentation
# - Hard to debug in production
# - Unclear recovery steps
```

### Implementation Steps

#### Step 1: Create Exception Hierarchy (2 hours)

Create `src/data_platform_naming/exceptions.py`:

```python
from __future__ import annotations
from typing import Any

class DataPlatformNamingError(Exception):
    """Base exception for all DPN errors"""
    
    def __init__(
        self, 
        message: str, 
        context: dict[str, Any] | None = None,
        doc_link: str | None = None
    ):
        super().__init__(message)
        self.context = context or {}
        self.doc_link = doc_link
    
    def __str__(self) -> str:
        parts = [super().__str__()]
        
        if self.context:
            parts.append("\nContext:")
            for key, value in self.context.items():
                parts.append(f"  {key}: {value}")
        
        if self.doc_link:
            parts.append(f"\nDocumentation: {self.doc_link}")
        
        return "".join(parts)


class ConfigurationError(DataPlatformNamingError):
    """Error in configuration files"""
    pass


class ValidationError(DataPlatformNamingError):
    """Error during validation"""
    pass


class NamingGenerationError(DataPlatformNamingError):
    """Error during name generation"""
    
    def __init__(
        self,
        message: str,
        resource_type: str,
        context: dict[str, Any] | None = None,
        doc_link: str | None = None
    ):
        super().__init__(message, context, doc_link)
        self.resource_type = resource_type


class OperationError(DataPlatformNamingError):
    """Error during CRUD operations"""
    
    def __init__(
        self,
        message: str,
        operation: str,
        platform: str,
        context: dict[str, Any] | None = None,
        doc_link: str | None = None
    ):
        super().__init__(message, context, doc_link)
        self.operation = operation
        self.platform = platform


class TransactionError(DataPlatformNamingError):
    """Error during transaction management"""
    pass


class BlueprintError(DataPlatformNamingError):
    """Error during blueprint processing"""
    pass
```

**Key Features**:
- Rich context dictionary
- Documentation links
- Structured error information
- Easy to extend

#### Step 2: Update Error Handling in Code (4 hours)

**2.1 Configuration Manager** (1 hour):

```python
# BEFORE
raise ValueError("Pattern not found")

# AFTER
from exceptions import ConfigurationError

raise ConfigurationError(
    f"Pattern not found for resource type: {resource_type}",
    context={
        "resource_type": resource_type,
        "available_patterns": list(self.patterns.keys())
    },
    doc_link="https://docs.example.com/configuration#patterns"
)
```

**2.2 Name Generators** (1 hour):

```python
# BEFORE
raise ValueError(f"Failed to generate name")

# AFTER
from exceptions import NamingGenerationError

raise NamingGenerationError(
    f"Failed to generate S3 bucket name: purpose '{purpose}' not found",
    resource_type="aws_s3_bucket",
    context={
        "purpose": purpose,
        "layer": layer,
        "environment": metadata.get("environment"),
        "pattern": pattern.pattern
    },
    doc_link="https://docs.example.com/troubleshooting#s3-naming"
)
```

**2.3 CRUD Operations** (1 hour):

```python
# BEFORE
raise Exception("API call failed")

# AFTER
from exceptions import OperationError

raise OperationError(
    f"Failed to create S3 bucket: {api_error}",
    operation="create",
    platform="aws",
    context={
        "bucket_name": bucket_name,
        "region": region,
        "error_code": api_error.code,
        "request_id": api_error.request_id
    },
    doc_link="https://docs.example.com/troubleshooting#aws-errors"
)
```

**2.4 Blueprint Parser** (1 hour):

```python
# BEFORE
raise ValueError("Invalid blueprint")

# AFTER
from exceptions import BlueprintError

raise BlueprintError(
    f"Invalid blueprint structure: missing required field '{field}'",
    context={
        "blueprint_file": blueprint_path,
        "field": field,
        "section": section
    },
    doc_link="https://docs.example.com/blueprint-format"
)
```

#### Step 3: Add Documentation Links (2 hours)

Create `docs/error-codes.md`:

```markdown
# Error Codes Reference

## ConfigurationError

### Pattern Not Found
**Symptom:** `Pattern not found for resource type: aws_s3_bucket`

**Cause:** The requested resource type has no defined pattern in naming-patterns.yaml

**Solution:**
1. Open `~/.dpn/naming-patterns.yaml`
2. Add pattern for resource type:
   ```yaml
   patterns:
     aws_s3_bucket: "{project}-{purpose}-{layer}-{environment}-{region}"
   ```
3. Validate: `dpn config validate`

**Link:** https://docs.example.com/configuration#patterns

---

## NamingGenerationError

### Required Variable Missing
**Symptom:** `Required variable 'purpose' not found in values`

**Cause:** Pattern requires variable not provided in configuration or metadata

**Solution:**
1. Check pattern in naming-patterns.yaml
2. Ensure variable exists in naming-values.yaml defaults or environment section
3. Or provide in blueprint metadata

**Link:** https://docs.example.com/troubleshooting#missing-variables

---

[... more error codes ...]
```

**Error codes to document**:
- Top 10 most common errors
- All configuration errors
- All validation errors
- Common operation errors

#### Step 4: Update Tests (2 hours)

Update ~20 tests to expect new exception types:

```python
# BEFORE
with pytest.raises(ValueError):
    generator.generate_name(...)

# AFTER
from exceptions import NamingGenerationError

with pytest.raises(NamingGenerationError) as exc_info:
    generator.generate_name(...)

# Verify context is present
assert exc_info.value.resource_type == "aws_s3_bucket"
assert "purpose" in exc_info.value.context
assert exc_info.value.doc_link is not None
```

**Test files to update**:
- `tests/test_aws_naming.py`
- `tests/test_dbx_naming.py`
- `tests/test_configuration_manager.py`
- `tests/test_blueprint_scope.py`

#### Step 5: Update CLI Error Display (1 hour)

Update `cli.py` to display rich error context:

```python
from exceptions import DataPlatformNamingError

try:
    # ... operation ...
except DataPlatformNamingError as e:
    # Display error with rich formatting
    console.print(f"[red]Error:[/red] {e}")
    
    # Show context
    if e.context:
        console.print("\n[yellow]Context:[/yellow]")
        for key, value in e.context.items():
            console.print(f"  {key}: {value}")
    
    # Show documentation link
    if e.doc_link:
        console.print(f"\n[blue]Documentation:[/blue] {e.doc_link}")
    
    raise click.ClickException(str(e))
except Exception as e:
    # Handle unexpected errors
    console.print(f"[red]Unexpected error:[/red] {e}")
    raise
```

### Day 4-5 Success Criteria

- ✅ Exception hierarchy complete (7 exception classes)
- ✅ All critical paths use custom exceptions
- ✅ Context included in all exceptions
- ✅ Documentation links for top 10 error types
- ✅ Tests verify exception context
- ✅ CLI displays rich error information
- ✅ All tests passing (94+)

---

## Sprint 2 Summary

### Total Effort

- Day 1-2: Magic strings (8 hours)
- Day 3: Type hints (6 hours)
- Day 4-5: Error context (11 hours)
- **Total: 25 hours (~3 days actual work)**

### Files to Create

1. `src/data_platform_naming/exceptions.py` (~200 lines)
2. `docs/error-codes.md` (~400 lines)

### Files to Modify

1. `src/data_platform_naming/constants.py` (~100 lines added)
2. All 17 source files in `src/` (type hints + enums + exceptions)
3. ~30 test files (updated assertions)

### Key Benefits

1. **Code Quality**:
   - Single source of truth for constants
   - Type-safe development
   - Better error messages

2. **Developer Experience**:
   - IDE autocomplete for all constants
   - Clear error context for debugging
   - Modern Python idioms

3. **Maintainability**:
   - Easy to extend (add new environments, resource types)
   - Clear error handling patterns
   - Documented error recovery paths

### Breaking Changes

**NONE** - All changes are internal refactoring. Public API unchanged.

### Testing Strategy

After each day:

```bash
# Run full test suite
uv run pytest --cov

# Type checking
uv run mypy src/

# Verify coverage maintained
# Target: >89% coverage (currently 89%)

# Expected results after Sprint 2:
# - All tests passing (94+)
# - 0 mypy errors
# - Coverage: 89-92%
# - Code quality: Improved
```

---

## Implementation Order

**Recommended sequence**:

1. **Day 1**: Enums in constants.py + update 3 core files
2. **Day 2**: Complete enum migration + update tests
3. **Day 3**: Type hint standardization (all files in one day)
4. **Day 4**: Exception hierarchy + update 2 modules
5. **Day 5**: Complete exception migration + documentation

**Why this order?**

- Enums provide foundation for type hints
- Type hints provide foundation for exceptions
- Each day's work is independently testable
- Can stop and deploy at end of any day

---

## Risk Mitigation

### Potential Issues

1. **Test failures during enum migration**
   - Mitigation: Update tests incrementally with each module
   - Recovery: Git revert individual files

2. **Mypy errors during type hint updates**
   - Mitigation: Fix one file at a time, test after each
   - Recovery: Use type: ignore comments temporarily

3. **Breaking changes in exception handling**
   - Mitigation: Keep old exceptions as fallback
   - Recovery: Catch both old and new exception types

### Rollback Plan

Each day's work is in separate commit:

```bash
# If Day 3 breaks something
git revert HEAD~1

# If need to rollback multiple days
git revert HEAD~3..HEAD
```

---

## Post-Sprint Actions

After Sprint 2 complete:

1. **Update CHANGELOG.md**:
   ```markdown
   ## [0.2.0] - 2025-XX-XX
   
   ### Changed
   - Consolidated magic strings into type-safe enums
   - Standardized type hints to modern Python 3.9+ syntax
   - Enhanced error context with exception hierarchy
   
   ### Improved
   - Better error messages with context and documentation links
   - IDE autocomplete for all constants
   - Type safety throughout codebase
   ```

2. **Update documentation**:
   - Add error-codes.md to docs TOC
   - Update troubleshooting.md with new error format
   - Add developer guide section on using enums

3. **Create release**:
   ```bash
   git tag v0.2.0
   git push origin v0.2.0
   ```

4. **Update Memory Bank**:
   - Mark Sprint 2 complete in progress.md
   - Document lessons learned in activeContext.md
   - Plan Sprint 3 (if applicable)

---

## Sprint 2 Checklist

Use this checklist to track progress:

### Day 1-2: Magic Strings
- [ ] Create enums in constants.py
- [ ] Update configuration_manager.py
- [ ] Update aws_naming.py
- [ ] Update dbx_naming.py
- [ ] Update blueprint.py
- [ ] Update cli.py
- [ ] Update remaining modules
- [ ] Update ~30 tests
- [ ] Verify: grep for magic strings
- [ ] Verify: pytest passes
- [ ] Verify: mypy passes

### Day 3: Type Hints
- [ ] Add `from __future__ import annotations` to all files
- [ ] Replace Dict → dict in all files
- [ ] Replace List → list in all files
- [ ] Replace Any with specific types (ConfigurationManager)
- [ ] Replace Any with specific types (generators)
- [ ] Replace Any with specific types (other modules)
- [ ] Update test type hints
- [ ] Verify: mypy --strict passes
- [ ] Verify: pytest passes

### Day 4-5: Error Context
- [ ] Create exceptions.py with hierarchy
- [ ] Update ConfigurationManager exceptions
- [ ] Update generator exceptions
- [ ] Update CRUD operation exceptions
- [ ] Update blueprint parser exceptions
- [ ] Create error-codes.md documentation
- [ ] Update ~20 tests
- [ ] Update CLI error display
- [ ] Verify: pytest passes
- [ ] Verify: Error messages include context
- [ ] Verify: Documentation links work

### Final Verification
- [ ] All 94+ tests passing
- [ ] Mypy: 0 errors
- [ ] Coverage: >89%
- [ ] No magic strings in critical paths
- [ ] Consistent type hints throughout
- [ ] Rich error context everywhere
- [ ] Update CHANGELOG.md
- [ ] Update Memory Bank
- [ ] Git tag v0.2.0

---

**Ready to implement Sprint 2!**
