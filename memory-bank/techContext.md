# Tech Context

## Technologies Used

### Core Language & Runtime
- **Python 3.9+**: Minimum version for modern type hints and features
- **Type Hints**: Extensive use of type annotations for IDE support and mypy validation
- **Async/Await**: Reserved for future parallel operations

### Package Management
- **UV (Primary)**: Fast, reliable Python package manager
  - `uv sync`: Install all dependencies
  - `uv run`: Execute commands in virtual environment
  - `pyproject.toml`: Single source of truth for dependencies
- **pip (Alternative)**: Traditional fallback for users without UV

### CLI Framework
- **Click 8+**: Command-line interface construction
  - Decorators for commands and options
  - Automatic help generation
  - Parameter validation
  - Command groups and subcommands

### Cloud SDKs
- **boto3**: AWS SDK for Python
  - S3 bucket operations
  - Glue database and table management
  - IAM and credential handling
  - Regional service clients
- **databricks-sdk**: Official Databricks Python SDK
  - Cluster management
  - Job orchestration
  - Unity Catalog (3-tier) operations
  - Workspace API access

### Data Validation
- **JSON Schema**: Blueprint validation
  - Draft 7 specification
  - Comprehensive error messages
  - Custom validators for naming patterns
- **Pydantic (Future)**: Runtime data validation and serialization

### User Interface
- **rich**: Terminal output enhancement
  - Progress bars with ETA
  - Colored output and formatting
  - Tables and panels
  - Error highlighting
- **tabulate**: Table formatting for data display

### Testing
- **pytest**: Test framework
  - Fixtures for test setup
  - Parametrized tests
  - Coverage reporting
  - Mock and patch utilities
- **pytest-cov**: Coverage measurement
- **pytest-mock**: Simplified mocking interface

### Code Quality
- **black**: Opinionated code formatter
  - Line length: 88 characters (default)
  - Automatic formatting on save
- **ruff**: Fast Python linter
  - Replaces flake8, isort, pylint
  - Import sorting
  - Code quality checks
- **mypy**: Static type checker
  - Strict mode enabled
  - Type inference
  - Protocol validation

### Multi-Language Quality (MegaLinter)
- **Docker-based**: Runs in container
- **Languages Supported**:
  - Python (black, ruff, mypy)
  - Bash (shellcheck, shfmt)
  - SQL (sqlfluff)
  - R (lintr)
  - Scala (scalafmt)
  - Terraform (tflint, terraform-fmt)
- **Configuration**: `.mega-linter.yml`

## Development Setup

### Initial Setup

```bash
# Install UV (macOS/Linux)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone repository
git clone https://github.com/robandrewford/data-platform-naming.git
cd data-platform-naming

# Install dependencies
uv sync

# Install with dev dependencies
uv sync --dev
```

### Development Workflow

```bash
# Run CLI commands
uv run dpn --help

# Run specific command
uv run dpn plan init --env dev --project test --output test.json

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov

# Run specific test file
uv run pytest tests/test_aws_naming.py

# Run specific test
uv run pytest tests/test_aws_naming.py::test_s3_bucket_name
```

### Code Quality Checks

```bash
# Format code
uv run black src/ tests/

# Lint code
uv run ruff check src/ tests/

# Fix linting issues
uv run ruff check src/ tests/ --fix

# Type check
uv run mypy src/

# Run all quality checks
uv run black src/ tests/ && \
uv run ruff check src/ tests/ && \
uv run mypy src/ && \
uv run pytest --cov
```

### MegaLinter

```bash
# Run all linters
docker run --rm \
  -v $(pwd):/tmp/lint \
  oxsecurity/megalinter:v7

# View report
open megalinter-reports/megalinter-report.html
```

## Technical Constraints

### Python Version
- **Minimum**: Python 3.9
- **Reason**: Type hints for built-in generics (list[str], dict[str, int])
- **Compatibility**: Tested on 3.9, 3.10, 3.11, 3.12

### AWS Credentials
- **Methods Supported**:
  1. AWS CLI profiles (`--aws-profile` flag)
  2. Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
  3. IAM roles (EC2 instance profiles, ECS task roles)
  4. AWS SSO profiles
- **Required Permissions**:
  - S3: `s3:CreateBucket`, `s3:PutBucketVersioning`, `s3:PutLifecycleConfiguration`
  - Glue: `glue:CreateDatabase`, `glue:CreateTable`, `glue:GetDatabase`, `glue:GetTable`
  - IAM: `iam:GetRole`, `iam:PassRole` (for Glue service roles)

### Databricks Authentication
- **Methods Supported**:
  1. Personal Access Token (PAT) via `--dbx-token` flag
  2. Environment variable (`DATABRICKS_TOKEN`)
  3. OAuth (future)
  4. Service Principal (future)
- **Host URL Required**: `--dbx-host` or `DATABRICKS_HOST` env var
- **Required Permissions**:
  - Clusters: Create, edit, delete
  - Jobs: Create, edit, delete, run
  - Unity Catalog: CREATE CATALOG, CREATE SCHEMA, CREATE TABLE

### File System
- **State Directory**: `~/.dpn/`
  - WAL directory: `~/.dpn/wal/`
  - State file: `~/.dpn/state/state.json`
- **Permissions Required**: Read/write access to home directory
- **Concurrent Access**: File locking prevents conflicts

### Network
- **Outbound HTTPS Required**:
  - AWS regional endpoints
  - Databricks workspace URLs
- **Proxy Support**: Honors `HTTP_PROXY`, `HTTPS_PROXY` environment variables
- **Timeouts**: Configurable per operation (default: 30s)

### Blueprint Size
- **Maximum File Size**: 10 MB (practical limit)
- **Maximum Resources**: 1000 per blueprint (soft limit)
- **Validation Time**: O(n) where n = number of resources

## Dependencies

### Production Dependencies (pyproject.toml)

```toml
[project]
dependencies = [
    "click>=8.0.0",           # CLI framework
    "boto3>=1.26.0",          # AWS SDK
    "databricks-sdk>=0.18.0", # Databricks SDK
    "jsonschema>=4.0.0",      # JSON validation
    "rich>=13.0.0",           # Terminal UI
    "tabulate>=0.9.0",        # Table formatting
    "pyyaml>=6.0.0",          # YAML support
]
```

### Development Dependencies

```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",          # Test framework
    "pytest-cov>=4.0.0",      # Coverage
    "pytest-mock>=3.0.0",     # Mocking
    "black>=23.0.0",          # Formatter
    "ruff>=0.1.0",            # Linter
    "mypy>=1.0.0",            # Type checker
    "types-pyyaml",           # Type stubs for PyYAML
    "types-tabulate",         # Type stubs for tabulate
]
```

### System Dependencies
- **None required**: Pure Python implementation
- **Optional**: Docker for MegaLinter

## Tool Usage Patterns

### Click CLI Pattern

```python
import click

@click.group()
def cli():
    """Data Platform Naming CLI."""
    pass

@cli.command()
@click.option('--blueprint', required=True, help='Blueprint JSON file')
@click.option('--dry-run', is_flag=True, help='Preview without executing')
@click.option('--aws-profile', help='AWS profile name')
def create(blueprint, dry_run, aws_profile):
    """Create resources from blueprint."""
    # Implementation
    pass
```

**Conventions**:
- Use `@click.option` for named parameters
- Use `@click.argument` for positional parameters
- Use `is_flag=True` for boolean flags
- Use `type=click.Path(exists=True)` for file validation

### Rich Progress Tracking

```python
from rich.progress import Progress, SpinnerColumn, TextColumn

with Progress(
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    transient=True,
) as progress:
    task = progress.add_task("Creating resources...", total=len(operations))
    
    for op in operations:
        execute_operation(op)
        progress.advance(task)
```

**Conventions**:
- Use transient=True for temporary progress
- Update task description for current operation
- Use console.print() from rich for formatted output

### boto3 Session Management

```python
import boto3

# Use profiles
session = boto3.Session(profile_name=aws_profile)
s3_client = session.client('s3', region_name=region)

# Use default credentials
s3_client = boto3.client('s3', region_name=region)

# Resource-based API (higher level)
s3_resource = session.resource('s3')
bucket = s3_resource.Bucket('bucket-name')
```

**Conventions**:
- Create session once, reuse clients
- Use client API for fine-grained control
- Use resource API for object-oriented interface
- Always specify region explicitly

### Databricks SDK Pattern

```python
from databricks.sdk import WorkspaceClient

# Initialize client
w = WorkspaceClient(
    host=dbx_host,
    token=dbx_token
)

# Use service APIs
cluster = w.clusters.create(
    cluster_name=name,
    spark_version=spark_version,
    node_type_id=node_type,
    num_workers=num_workers
)

# Unity Catalog
catalog = w.catalogs.create(name=catalog_name)
schema = w.schemas.create(catalog_name=catalog_name, name=schema_name)
```

**Conventions**:
- One client instance per workspace
- Use service-specific APIs (clusters, jobs, catalogs)
- Handle pagination automatically
- Retry on rate limits

### JSON Schema Validation

```python
import jsonschema

# Load schema
with open('blueprint-schema.json') as f:
    schema = json.load(f)

# Validate blueprint
try:
    jsonschema.validate(instance=blueprint, schema=schema)
except jsonschema.ValidationError as e:
    # Handle validation error with path and message
    print(f"Validation error at {e.json_path}: {e.message}")
```

**Conventions**:
- Use Draft 7 JSON Schema
- Provide detailed error messages
- Validate early (before any operations)

### Pytest Fixtures

```python
import pytest

@pytest.fixture
def mock_aws_client():
    """Mock boto3 client for testing."""
    return MagicMock()

@pytest.fixture
def sample_blueprint():
    """Sample blueprint for testing."""
    return {
        "version": "1.0",
        "metadata": {"environment": "dev"},
        "resources": {}
    }

def test_create_bucket(mock_aws_client, sample_blueprint):
    """Test S3 bucket creation."""
    # Test implementation
    pass
```

**Conventions**:
- Use fixtures for common test data
- Mock external services (AWS, Databricks)
- Parametrize tests for multiple scenarios
- Use descriptive test names

## Configuration Files

### pyproject.toml
- **Purpose**: Project metadata and dependencies
- **Format**: TOML
- **Sections**: project, dependencies, optional-dependencies, build-system

### .mega-linter.yml
- **Purpose**: MegaLinter configuration
- **Format**: YAML
- **Sections**: Linters to enable/disable, file patterns, report settings

### .gitignore
- **Purpose**: Exclude files from Git
- **Patterns**: `*.pyc`, `__pycache__/`, `.pytest_cache/`, `dist/`, `build/`

## Build and Distribution

### Local Development Build
```bash
# Install in development mode
uv pip install -e .

# Build distribution
uv build
```

### Package Structure
```
data-platform-naming/
├── src/
│   └── data-platform-naming/
│       ├── __init__.py
│       ├── cli.py              # Entry point
│       ├── aws_naming.py
│       ├── dbx_naming.py
│       ├── constants_py.py
│       ├── validators_py.py
│       └── crud/
│           └── ...
├── tests/
├── pyproject.toml
└── README.md
```

### Entry Points
```toml
[project.scripts]
dpn = "data_platform_naming.cli:cli"
```

This creates the `dpn` command that maps to the Click CLI group.

## Environment Variables

### AWS Configuration
- `AWS_PROFILE`: Default AWS profile to use
- `AWS_REGION`: Default AWS region
- `AWS_ACCESS_KEY_ID`: Access key (if not using profile)
- `AWS_SECRET_ACCESS_KEY`: Secret key (if not using profile)

### Databricks Configuration
- `DATABRICKS_HOST`: Workspace URL
- `DATABRICKS_TOKEN`: Personal access token

### Tool Configuration
- `HTTP_PROXY`: HTTP proxy URL
- `HTTPS_PROXY`: HTTPS proxy URL
- `NO_COLOR`: Disable colored output (for CI/CD)

### Development
- `PYTEST_CURRENT_TEST`: Set by pytest during test runs
- `COVERAGE_FILE`: Coverage data file location
