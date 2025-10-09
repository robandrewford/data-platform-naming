# Data Platform Naming Conventions

**Battle-tested AWS + Databricks resource naming automation with ACID transactions.**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

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

# Generate blueprint (creates blueprints/prd.json by default)
uv run dpn plan init --env prd --project platform

# Preview names
uv run dpn plan preview blueprints/prd.json

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

## Usage

### 1. Plan Mode

#### Initialize Blueprint

dpn plan init --env prd --project dataplatform --output prod.json

#### Validate Schema

```bash
dpn plan validate prod.json
```

#### Preview Names

```bash
# Table format
dpn plan preview prod.json

# JSON export
dpn plan preview prod.json --format json --output preview.json
```

#### Export Schema

```bash
dpn plan schema --output blueprint-schema.json
```

### 2. CRUD Operations

#### Create Resources

```bash
# Dry run
dpn create --blueprint prod.json --dry-run

# Execute
dpn create --blueprint prod.json

# With AWS profile
dpn create --blueprint prod.json --aws-profile production

# With Databricks
dpn create --blueprint prod.json \
  --dbx-host https://workspace.cloud.databricks.com \
  --dbx-token dapi123...
```

#### Read Configuration

```bash
# JSON format
dpn read --resource-id cluster-name --type cluster --format json

# YAML format
dpn read --resource-id bucket-name --type s3 --format yaml

# Table format
dpn read --resource-id db-name --type glue-db --format table
```

#### Update Resources

```bash
# Rename
dpn update --resource-id old-name --rename new-name

# Update params
dpn update --resource-id cluster-name --params updates.json
```

#### Delete Resources

```bash
# Permanent delete (with confirmation)
dpn delete --resource-id cluster-name --type cluster

# Archive (soft delete)
dpn delete --resource-id cluster-name --type cluster --archive
```

### 3. Utility Commands

#### Recover from Failures

```bash
dpn recover
```

#### Check Status

```bash
dpn status
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
~/.dpn/
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
dpn create --blueprint dev.json --aws-profile dev

# Staging
dpn create --blueprint stg.json --aws-profile staging

# Production
dpn create --blueprint prd.json --aws-profile production
```

### Resource Inspection

```bash
# List all S3 buckets
dpn read --type s3 --resource-id "dataplatform-*"

# Cluster details
dpn read --type cluster --resource-id etl-cluster --format json
```

### Disaster Recovery

```bash
# Recover failed transactions
dpn recover

# Archive resources
dpn delete --resource-id old-cluster --type cluster --archive

# Check system status
dpn status
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
