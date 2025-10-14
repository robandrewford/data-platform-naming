# Data Platform Naming Conventions

**Battle-tested AWS + Databricks resource naming automation with ACID transactions.**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Complete Workflow

### Overview

This guide shows how to use the three key parts of the system together:

- **`.dpn/*.yaml`** - Configuration files (naming values and patterns)
- **`blueprints/*.json`** - Resource definitions (what to create)
- **`schemas/*.json`** - Validation schemas (ensures correctness)

### Step 1: Initialize Configuration (.dpn/*.yaml)

Set up your project's naming configuration:

```bash
# Interactive prompts
uv run dpn config init

# Or specify values directly
uv run dpn config init --project myproject --environment dev --region us-east-1
```

This creates two configuration files in `.dpn/`:

- **`.dpn/naming-values.yaml`** - Variable values (project, environment, region, etc.)
- **`.dpn/naming-patterns.yaml`** - Name templates with placeholders

Customize if needed:

```bash
# Edit values
vim .dpn/naming-values.yaml

# Edit patterns (optional - defaults usually work)
vim .dpn/naming-patterns.yaml

# Validate your changes
uv run dpn config validate

# View current configuration
uv run dpn config show
```

### Step 2: Create Blueprint (blueprints/*.json)

Generate a blueprint that defines what resources to create:

```bash
# Creates blueprints/dev.json
uv run dpn plan init --env dev --project myproject

# Creates blueprints/prd.json
uv run dpn plan init --env prd --project myproject
```

Edit the blueprint to customize your resources:

```bash
vim blueprints/dev.json
```

The blueprint specifies:
- Environment metadata (env, project, region, team, cost center)
- AWS resources (S3 buckets, Glue databases/tables)
- Databricks resources (clusters, jobs, Unity Catalog)

### Step 3: Validate Blueprint (schemas/*.json)

Validate blueprint structure and configuration:

```bash
# Validate blueprint against schema
uv run dpn plan validate blueprints/dev.json

# Validate configuration files
uv run dpn config validate
```

Validation uses schemas in `schemas/`:
- `naming-values-schema.json` - Validates configuration values
- `naming-patterns-schema.json` - Validates naming patterns
- Blueprint schema (internal) - Validates blueprint structure

### Step 4: Preview Generated Names

See what names will be created before executing:

```bash
# Table format (default)
uv run dpn plan preview blueprints/dev.json

# JSON format for automation
uv run dpn plan preview blueprints/dev.json --format json --output preview.json

# With runtime overrides
uv run dpn plan preview blueprints/dev.json --override environment=prd
```

### Step 5: Create Resources

Deploy your infrastructure:

```bash
# Dry run first (recommended)
uv run dpn create --blueprint blueprints/dev.json --dry-run

# Execute creation
uv run dpn create --blueprint blueprints/dev.json
```

### File Relationships Diagram

```
.dpn/
├── naming-values.yaml      → Variable values (project, environment, etc.)
└── naming-patterns.yaml    → Name templates with {placeholders}
          ↓
  (combine values + patterns)
          ↓
    Generated Names
          ↓
blueprints/
└── dev.json                → Resource definitions
          ↓
  (validated against)
          ↓
schemas/
├── naming-values-schema.json
├── naming-patterns-schema.json
└── (internal blueprint schema)
          ↓
   (creates resources)
          ↓
AWS & Databricks Resources
```

### Quick Example

Complete workflow in 5 commands:

```bash
# 1. Set up configuration
uv run dpn config init --project dataplatform --environment dev

# 2. Create blueprint
uv run dpn plan init --env dev --project dataplatform

# 3. Preview names
uv run dpn plan preview blueprints/dev.json

# 4. Dry run
uv run dpn create --blueprint blueprints/dev.json --dry-run

# 5. Create resources
uv run dpn create --blueprint blueprints/dev.json
```

### Configuration Details

**Values (.dpn/naming-values.yaml):**
```yaml
defaults:
  project: dataplatform
  environment: dev
  region: us-east-1
```

**Patterns (.dpn/naming-patterns.yaml):**
```yaml
patterns:
  aws_s3_bucket:
    template: "{project}-{purpose}-{layer}-{environment}-{region_code}"
```

**Blueprint (blueprints/dev.json):**
```json
{
  "version": "1.0",
  "metadata": {"environment": "dev", "project": "dataplatform"},
  "resources": {
    "aws": {"s3_buckets": [{"purpose": "raw", "layer": "raw"}]}
  }
}
```

**Result:** S3 bucket named `dataplatform-raw-raw-dev-use1`

## Quick Start

```bash
# Install UV (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone repository
git clone https://github.com/robandrewford/data-platform-naming.git
cd data-platform-naming

# Install dependencies (creates .venv automatically)
uv sync

# Verify installation
uv run dpn --help

# Preview names
uv run dpn plan preview blueprints/prd.json

# Generate blueprint (creates blueprints/prd.json by default)
uv run dpn plan init --env prd --project platform

# Create resources (dry-run first)
uv run dpn create --blueprint blueprints/prd.json --dry-run
uv run dpn create --blueprint blueprints/prd.json
```

> **Note:** `uv sync` automatically creates a `.venv` virtual environment. You don't need to run `uv venv` manually or activate the environment - `uv run` handles everything!

### UV (Recommended)

```bash
uv sync
uv run dpn --help
```

### pip

```bash
pip install data-platform-naming
dpn --help
```

## Features

### 🎯 Automated Naming

- **AWS**: S3, Glue (databases/tables)
- **Databricks**: Clusters, Jobs, Unity Catalog (3-tier)
- **Consistent**: Environment-aware patterns
- **Validated**: Schema enforcement

### 🔄 ACID Transactions

- **Atomic**: All-or-nothing execution
- **Consistent**: Pre/post validation
- **Isolated**: File-lock WAL
- **Durable**: Crash recovery

### 📋 Blueprint Planning

- **Declarative**: JSON configuration
- **Validated**: JSON Schema compliance
- **Preview**: Dry-run mode
- **Dependencies**: Auto-resolved execution order

### 💻 CRUD Operations

- **Create**: Batch resource provisioning
- **Read**: Configuration inspection
- **Update**: In-place modifications
- **Delete**: Archive or permanent removal

## Configuration

### Quick Start with Configuration

The configuration system allows you to customize naming patterns and values without modifying code:

```bash
# 1. Initialize configuration
uv run dpn config init
# Prompts for: project, environment, region

# 2. Validate configuration
uv run dpn config validate

# 3. View configuration
uv run dpn config show
uv run dpn config show --resource-type aws_s3_bucket

# 4. Use in commands (automatic with .dpn/ configs)
uv run dpn plan preview dev.json
uv run dpn create --blueprint dev.json
```

### Configuration Files

Two YAML files control resource naming:

**`naming-values.yaml`** - Variable values with precedence hierarchy:
```yaml
defaults:
  project: dataplatform
  environment: dev
  region: us-east-1
  team: data-engineering

environments:
  prd:
    environment: prd
    team: data-platform

resource_types:
  aws_s3_bucket:
    purpose: analytics
```

**`naming-patterns.yaml`** - Template patterns with placeholders:
```yaml
patterns:
  aws_s3_bucket:
    template: "{project}-{purpose}-{layer}-{environment}-{region_code}"
    required_variables: ["project", "purpose", "layer", "environment", "region_code"]
  
  dbx_cluster:
    template: "{project}-{workload}-{cluster_type}-{environment}"
    required_variables: ["project", "workload", "cluster_type", "environment"]

transformations:
  region_mapping:
    us-east-1: "use1"
    us-west-2: "usw2"

validation:
  max_length:
    aws_s3_bucket: 63
    dbx_cluster: 100
```

### Configuration Locations

**Default location:** `.dpn/` (project directory)
- `.dpn/naming-values.yaml`
- `.dpn/naming-patterns.yaml`

**Custom paths:** Use flags with any command
```bash
uv run dpn plan preview dev.json \
  --values-config custom-values.yaml \
  --patterns-config custom-patterns.yaml
```

### Runtime Overrides

Override any value at runtime without modifying config files:

```bash
# Single override
uv run dpn plan preview dev.json --override environment=prd

# Multiple overrides
uv run dpn plan preview dev.json \
  --override environment=prd \
  --override project=oncology \
  --override region=us-west-2

# Works with all commands
uv run dpn create --blueprint dev.json \
  --override environment=prd \
  --dry-run
```

### Value Precedence (highest to lowest)

1. **Runtime overrides** (`--override` flags)
2. **Blueprint metadata** (explicit values in blueprint)
3. **Resource type overrides** (in naming-values.yaml)
4. **Environment overrides** (in naming-values.yaml)
5. **Defaults** (in naming-values.yaml)

### Configuration Workflow

```bash
# Initialize (one-time setup)
uv run dpn config init --project myproject --environment dev --region us-east-1

# Customize values
vim .dpn/naming-values.yaml

# Customize patterns (optional)
vim .dpn/naming-patterns.yaml

# Validate changes
uv run dpn config validate

# View effective configuration
uv run dpn config show

# Test with preview
uv run dpn plan preview my-blueprint.json

# Create resources
uv run dpn create --blueprint my-blueprint.json
```

### Backward Compatibility

Commands work without configuration files (legacy mode):
```bash
# Without config - uses hardcoded patterns
uv run dpn plan preview dev.json
# ⚠ No configuration files found, using legacy mode
# Run 'uv run dpn config init' to create configuration files

# With config - uses customizable patterns
uv run dpn config init
uv run dpn plan preview dev.json
# ✓ Using configuration-based naming
```

### Migration Guide

For detailed migration instructions, see [Configuration Migration Guide](docs/configuration-migration-guide.md).

## Usage

### 1. Plan Mode

#### Initialize Blueprint

```bash
uv run dpn plan init --env prd --project dataplatform --output prod.json
```

#### Validate Schema

```bash
uv run dpn plan validate prod.json
```

#### Preview Names

```bash
# Table format
uv run dpn plan preview prod.json

# JSON export
uv run dpn plan preview prod.json --format json --output preview.json
```

#### Export Schema

```bash
uv run dpn plan schema --output blueprint-schema.json
```

### 2. CRUD Operations

#### Create Resources

```bash
# Dry run
uv run dpn create --blueprint prod.json --dry-run

# Execute
uv run dpn create --blueprint prod.json

# With AWS profile
uv run dpn create --blueprint prod.json --aws-profile production

# With Databricks
uv run dpn create --blueprint prod.json \
  --dbx-host https://workspace.cloud.databricks.com \
  --dbx-token dapi123...
```

#### Read Configuration

```bash
# JSON format
uv run dpn read --resource-id cluster-name --type cluster --format json

# YAML format
uv run dpn read --resource-id bucket-name --type s3 --format yaml

# Table format
uv run dpn read --resource-id db-name --type glue-db --format table
```

#### Update Resources

```bash
# Rename
uv run dpn update --resource-id old-name --rename new-name

# Update params
uv run dpn update --resource-id cluster-name --params updates.json
```

#### Delete Resources

```bash
# Permanent delete (with confirmation)
uv run dpn delete --resource-id cluster-name --type cluster

# Archive (soft delete)
uv run dpn delete --resource-id cluster-name --type cluster --archive
```

### 3. Utility Commands

#### Recover from Failures

```bash
uv run dpn recover
```

#### Check Status

```bash
uv run dpn status
```

## Blueprint Structure

```json
{
  "version": "1.0",
  "metadata": {
    "environment": "prd",
    "project": "dataplatform",
    "region": "us-east-1",
    "team": "data-engineering",
    "cost_center": "IT-1001"
  },
  "resources": {
    "aws": {
      "s3_buckets": [
        {
          "purpose": "raw",
          "layer": "raw",
          "versioning": true,
          "lifecycle_days": 90
        }
      ],
      "glue_databases": [
        {
          "domain": "finance",
          "layer": "gold",
          "description": "Finance gold layer"
        }
      ],
      "glue_tables": [
        {
          "database_ref": "finance-gold",
          "entity": "customers",
          "table_type": "dim",
          "columns": [...]
        }
      ]
    },
    "databricks": {
      "clusters": [
        {
          "workload": "etl",
          "cluster_type": "shared",
          "node_type": "i3.xlarge",
          "autoscale": {"min": 2, "max": 8}
        }
      ],
      "jobs": [
        {
          "job_type": "batch",
          "purpose": "customer-ingestion",
          "cluster_ref": "etl",
          "schedule": "daily"
        }
      ],
      "unity_catalog": {
        "catalogs": [
          {
            "catalog_type": "main",
            "schemas": [
              {
                "domain": "finance",
                "layer": "gold",
                "tables": [
                  {
                    "entity": "customers",
                    "table_type": "dim",
                    "columns": [...]
                  }
                ]
              }
            ]
          }
        ]
      }
    }
  }
}
```

## Naming Patterns

### AWS

**S3 Bucket:**

```md
{project}-{purpose}-{layer}-{env}-{region}
Example: dataplatform-raw-raw-prd-useast1
```

**Glue Database:**

```md
{project}_{domain}_{layer}_{env}
Example: dataplatform_finance_gold_prd
```

**Glue Table:**

```md
{type}_{entity}
Example: dim_customers, fact_transactions
```

### Databricks

**Cluster:**

```md
{project}-{workload}-{type}-{env}
Example: dataplatform-etl-shared-prd
```

**Job:**

```md
{project}-{type}-{purpose}-{env}-{schedule}
Example: dataplatform-batch-customer-load-prd-daily
```

**Unity Catalog (3-tier):**

```md
Catalog: {project}_{type}_{env}
Schema:  {domain}_{layer}
Table:   {type}_{entity}

Full: dataplatform_main_prd.finance_gold.dim_customers
```

## Quality Control

### UV + Ruff + Black

```bash
# Install dev dependencies
uv sync --dev

# Format
uv run black src/ tests/

# Lint
uv run ruff check src/ tests/

# Type check
uv run mypy src/
```

### MegaLinter (All Languages)

```bash
docker run --rm \
  -v $(pwd):/tmp/lint \
  oxsecurity/megalinter:v7
```

**Supported Languages:**

- Python (black, ruff, mypy)
- Bash (shellcheck, shfmt)
- SQL (sqlfluff)
- R (lintr)
- Scala (scalafmt)
- Terraform (tflint, terraform-fmt)

### Testing

```bash
# Run tests
uv run pytest

# With coverage
uv run pytest --cov

# Specific test
uv run pytest tests/test_transaction_manager.py
```

## ACID Guarantees

### Atomicity

All operations succeed or all rollback. No partial changes.

### Consistency

Pre/post-condition validation ensures valid state transitions.

### Isolation

File-based locking prevents concurrent transaction conflicts.

### Durability

Write-ahead logging (WAL) persists all state. Automatic crash recovery.

### Architecture

```md
Transaction
├── Write to WAL
├── Execute Operations
│   ├── Operation 1 → Success
│   ├── Operation 2 → Success
│   └── Operation 3 → Failed
└── Rollback (reverse order)
    ├── Revert Operation 2
    └── Revert Operation 1
```

## Progress Tracking

```bash
Creating resources... ━━━━━━━━━━━━━━ 67% [23.4s] Creating job: batch-customer-prd

✓ Cluster created: dataplatform-etl-shared-prd
✓ Job created: dataplatform-batch-customer-load-prd-daily
✗ Table failed: Invalid schema
→ Rolling back transaction...
✓ Transaction rolled back: tx-abc123
```

## Configuration

### Environment Variables

```bash
# AWS
export AWS_PROFILE=production
export AWS_REGION=us-east-1

# Databricks
export DATABRICKS_HOST=https://workspace.cloud.databricks.com
export DATABRICKS_TOKEN=dapi123...
```

### State Directory

```md
.dpn/
├── wal/              # Write-ahead log
│   ├── {tx-id}.wal
│   ├── {tx-id}.committed
│   └── {tx-id}.rolled_back
└── state/
    └── state.json    # Resource state
```

## Examples

### Multi-Environment Deployment

```bash
# Development
uv run dpn create --blueprint dev.json --aws-profile dev

# Staging
uv run dpn create --blueprint stg.json --aws-profile staging

# Production
uv run dpn create --blueprint prd.json --aws-profile production
```

### Resource Inspection

```bash
# List all S3 buckets
uv run dpn read --type s3 --resource-id "dataplatform-*"

# Cluster details
uv run dpn read --type cluster --resource-id etl-cluster --format json
```

### Disaster Recovery

```bash
# Recover failed transactions
uv run dpn recover

# Archive resources
uv run dpn delete --resource-id old-cluster --type cluster --archive

# Check system status
uv run dpn status
```

## Development

### Setup

```bash
git clone https://github.com/yourusername/data-platform-naming.git
cd data-platform-naming
uv sync --dev
```

### Run Tests

```bash
uv run pytest
uv run pytest --cov
```

### Lint

```bash
uv run ruff check src/ tests/
uv run black src/ tests/
uv run mypy src/
```

### Run MegaLinter

```bash
docker run --rm -v $(pwd):/tmp/lint oxsecurity/megalinter:v7
```

## Contributing

1. Fork repository
2. Create feature branch
3. Run tests + linters
4. Submit pull request

## License

MIT License - see [LICENSE](LICENSE) file.

## Support

- **Issues**: <https://github.com/robandrewford/data-platform-naming/issues>
- **Documentation**: <https://github.com/robandrewford/data-platform-naming/docs>
- **Discussions**: <https://github.com/robandrewford/data-platform-naming/discussions>

## Roadmap

- [ ] Azure naming support
- [ ] GCP naming support
- [ ] Terraform provider
- [ ] GitHub Actions integration
- [ ] Web UI
- [ ] API server mode
