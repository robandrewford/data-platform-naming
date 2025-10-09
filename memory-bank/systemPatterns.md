# System Patterns

## System Architecture

### High-Level Components

```md
┌─────────────────────────────────────────────────────────┐
│                        CLI Layer                         │
│  (Click-based commands: plan, create, read, update,     │
│   delete, recover, status)                              │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│                   Blueprint Layer                        │
│  • Blueprint parsing & validation (JSON Schema)          │
│  • Name generation (AWS & DBX patterns)                  │
│  • Dependency resolution                                 │
│  • Preview mode                                          │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│                Transaction Manager                       │
│  • ACID guarantees                                       │
│  • Write-Ahead Log (WAL)                                 │
│  • Rollback mechanism                                    │
│  • State management                                      │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│                  CRUD Operations                         │
│  ┌──────────────┐           ┌──────────────┐           │
│  │ AWS Ops      │           │ DBX Ops      │           │
│  │ • S3         │           │ • Clusters   │           │
│  │ • Glue DB    │           │ • Jobs       │           │
│  │ • Glue Table │           │ • UC 3-tier  │           │
│  └──────────────┘           └──────────────┘           │
└─────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Blueprint → Validation**
   - JSON Schema enforcement
   - Reference resolution
   - Naming pattern validation

2. **Validation → Planning**
   - Dependency graph construction
   - Execution order determination
   - Preview generation

3. **Planning → Transaction**
   - Transaction initialization
   - WAL entry creation
   - File lock acquisition

4. **Transaction → Execution**
   - Sequential operation execution
   - Progress tracking
   - Error capture

5. **Execution → Completion**
   - Success: Commit WAL, release lock, update state
   - Failure: Rollback operations, mark WAL, release lock

## Key Technical Decisions

### 1. File-Based Transaction Management

**Decision**: Use file-based Write-Ahead Log (WAL) instead of database

**Rationale**:
- No external dependencies (database servers)
- Simple deployment (single binary approach)
- Portable across environments
- Easy to inspect and debug (plain text files)
- Sufficient for CLI tool use case

**Trade-offs**:
- Not suitable for high-concurrency scenarios
- Manual file cleanup required
- Limited query capabilities

**Implementation**: `~/.dpn/wal/` directory with transaction files

### 2. Declarative Blueprint Format

**Decision**: Use JSON with JSON Schema validation

**Rationale**:
- Human-readable and editable
- Strong validation via JSON Schema
- Wide tooling support (editors, validators)
- Easy to version control
- Can be generated programmatically

**Trade-offs**:
- More verbose than YAML
- No native comments (use description fields)

**Implementation**: `blueprint.py` handles parsing and validation

### 3. Separate Platform Operations

**Decision**: Distinct modules for AWS and Databricks operations

**Rationale**:
- Different API patterns and authentication
- Independent error handling
- Platform-specific retry logic
- Easier to test in isolation
- Clear separation of concerns

**Implementation**:
- `aws_operations.py` - boto3-based operations
- `dbx_operations.py` - databricks-sdk operations

### 4. Progressive Execution with Rollback

**Decision**: Execute operations sequentially with automatic rollback on failure

**Rationale**:
- Simpler than distributed transactions
- Clear error attribution
- Predictable rollback order (reverse of execution)
- User-friendly error messages

**Trade-offs**:
- Slower than parallel execution
- Partial rollback may leave system in inconsistent state (mitigated by idempotent operations)

**Implementation**: `transaction_manager.py` with operation stack

### 5. CLI-First Interface

**Decision**: Build as CLI tool first, not web service

**Rationale**:
- Fits infrastructure-as-code workflows
- Easy to integrate in CI/CD pipelines
- No server infrastructure required
- Direct credential access (AWS profiles, env vars)

**Future**: API server mode can wrap CLI commands

## Design Patterns

### 1. Command Pattern (CLI)

**Usage**: Each CLI command (`create`, `read`, `update`, `delete`) is encapsulated

```python
# cli.py structure
@click.group()
def cli():
    pass

@cli.command()
def create(blueprint, dry_run, aws_profile, dbx_host, dbx_token):
    # Encapsulated create logic
    pass

@cli.command()
def read(resource_id, resource_type, format):
    # Encapsulated read logic
    pass
```

**Benefits**:
- Easy to add new commands
- Clear separation of concerns
- Testable in isolation

### 2. Strategy Pattern (Platform Operations)

**Usage**: Different strategies for AWS vs Databricks operations

```python
# Abstract interface
class PlatformOperations:
    def create_resource(self, config):
        raise NotImplementedError
    
    def delete_resource(self, resource_id):
        raise NotImplementedError

# Concrete strategies
class AWSOperations(PlatformOperations):
    def create_resource(self, config):
        # AWS-specific implementation
        pass

class DBXOperations(PlatformOperations):
    def create_resource(self, config):
        # Databricks-specific implementation
        pass
```

**Benefits**:
- Easy to add new platforms (Azure, GCP)
- Platform-specific logic isolated
- Common interface for transaction manager

### 3. Template Method Pattern (Transaction Flow)

**Usage**: Transaction manager defines skeleton, operations fill in details

```python
class TransactionManager:
    def execute_transaction(self, operations):
        self._begin()
        try:
            for op in operations:
                self._execute_operation(op)  # Hook method
            self._commit()
        except Exception:
            self._rollback()
```

**Benefits**:
- Consistent transaction handling
- Operation-specific logic in subclasses
- Clear extension points

### 4. Builder Pattern (Blueprint Construction)

**Usage**: Fluent interface for building blueprints

```python
blueprint = (
    BlueprintBuilder()
    .with_metadata(env="prd", project="platform")
    .add_s3_bucket(purpose="raw", layer="raw")
    .add_glue_database(domain="finance", layer="gold")
    .build()
)
```

**Benefits**:
- Readable blueprint creation
- Progressive disclosure
- Validation at build time

### 5. Repository Pattern (State Management)

**Usage**: Abstract state storage and retrieval

```python
class StateRepository:
    def save_resource(self, resource):
        pass
    
    def get_resource(self, resource_id):
        pass
    
    def list_resources(self, filters):
        pass
```

**Benefits**:
- Storage implementation can change
- Easy to test with mock repository
- Clear data access layer

## Component Relationships

### Blueprint → Name Generators

```
Blueprint (JSON)
    ↓ parsed by
BlueprintParser
    ↓ uses
AWSNaming / DBXNaming
    ↓ generates
Resource Names (validated)
```

**Key Points**:
- Name generators are stateless
- Validators ensure format compliance
- References resolved during parsing

### Transaction Manager → Operations

```
TransactionManager
    ↓ creates
Transaction (with WAL)
    ↓ executes
Operations (AWS/DBX)
    ↓ reports to
ProgressTracker
    ↓ updates
State Repository
```

**Key Points**:
- Transaction owns the WAL lifecycle
- Operations are atomic and reversible
- Progress tracked for user feedback
- State persisted for inspection

### CLI → All Layers

```
CLI Command
    ↓ loads
Blueprint
    ↓ validates
Schema + Validators
    ↓ initiates
Transaction
    ↓ executes
Platform Operations
    ↓ returns
Results + State
```

**Key Points**:
- CLI orchestrates but doesn't implement logic
- Each layer has clear responsibility
- Errors bubble up with context

## Critical Implementation Paths

### Path 1: Create Resources (Happy Path)

1. **Parse Blueprint**
   - Load JSON file
   - Validate against schema
   - Resolve references

2. **Generate Names**
   - Apply naming patterns
   - Validate format
   - Check for conflicts

3. **Plan Execution**
   - Build dependency graph
   - Determine execution order
   - Show preview (if requested)

4. **Execute Transaction**
   - Initialize WAL
   - Acquire file lock
   - Execute operations sequentially
   - Track progress
   - Commit WAL
   - Release lock

5. **Update State**
   - Persist resource metadata
   - Record timestamps
   - Return success status

### Path 2: Rollback on Failure

1. **Operation Fails**
   - Capture exception
   - Log error details
   - Mark current operation as failed

2. **Initiate Rollback**
   - Reverse operation list
   - Execute rollback for each completed operation
   - Track rollback progress

3. **Complete Rollback**
   - Mark WAL as rolled back
   - Release file lock
   - Update state with rollback info
   - Return error with recovery guidance

### Path 3: Recovery from Crash

1. **Detect Incomplete Transaction**
   - Scan WAL directory
   - Find uncommitted transaction files
   - Check file timestamps

2. **Analyze State**
   - Determine which operations completed
   - Identify partial operations
   - Assess system state

3. **Execute Recovery**
   - Rollback partial operations
   - Clean up temporary resources
   - Mark WAL as recovered
   - Log recovery actions

### Path 4: Preview Mode

1. **Parse Blueprint** (same as create)

2. **Generate Names** (same as create)

3. **Simulate Execution**
   - Build operation list
   - Generate preview output
   - Show naming results
   - **Skip actual API calls**

4. **Display Results**
   - Table format with all names
   - JSON export option
   - Validation warnings

## Error Handling Strategy

### Validation Errors (Fail Fast)
- Caught during blueprint parsing
- Clear error messages with line numbers
- No API calls made
- Easy to fix and retry

### API Errors (Retry with Backoff)
- Transient errors: Retry with exponential backoff
- Permanent errors: Fail and rollback
- Rate limiting: Respect retry-after headers
- Authentication: Clear error, no retry

### System Errors (Crash Recovery)
- File lock prevents concurrent transactions
- WAL enables recovery after crash
- Idempotent operations allow safe retry
- Manual recovery tools available

## Performance Considerations

### Batch Operations
- Single API call per resource type when possible
- Minimize round trips
- Use async operations where available (future)

### Caching
- Cache AWS region data
- Cache Databricks cluster types
- Invalidate on error or explicit refresh

### Progress Feedback
- Real-time updates using rich progress bars
- Estimated completion time
- Clear error messages
- Cancelable operations (future)

## Testing Strategy

### Unit Tests
- Name generators with various inputs
- Validators with edge cases
- Transaction manager with mock operations
- CLI commands with mock dependencies

### Integration Tests
- Full blueprint processing
- Transaction commit and rollback
- State persistence and recovery
- Error handling paths

### End-to-End Tests (Manual)
- Real AWS and Databricks accounts (test environments)
- Multi-environment deployments
- Disaster recovery scenarios
- Performance benchmarks
