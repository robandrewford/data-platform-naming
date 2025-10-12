# Configuration Schemas

This directory contains JSON Schema definitions for the configuration-based naming system.

## Overview

The configuration-based naming system enables users to:
- Centrally manage naming values (project, environment, etc.) without modifying code
- Customize naming pattern templates for resource name generation
- Override values at different precedence levels (defaults → environments → resource types → blueprint metadata)
- Filter resources by type (include/exclude with wildcards)

## Schema Files

### 1. naming-values-schema.json

**Purpose**: Defines the structure for naming value substitutions.

**Key Features**:
- Hierarchical precedence: `defaults` → `environments` → `resource_types`
- Standard variables: project, environment, region, team, cost_center, etc.
- Custom variables: Add any additional key-value pairs needed

**Structure**:
```json
{
  "version": "1.0",
  "defaults": { ... },           // Lowest precedence
  "environments": {
    "dev": { ... },
    "stg": { ... },
    "prd": { ... }
  },                             // Medium precedence
  "resource_types": {
    "aws_s3_bucket": { ... },
    "dbx_cluster": { ... }
  }                              // High precedence
}
```

**Example**: See `examples/configs/naming-values.yaml`

### 2. naming-patterns-schema.json

**Purpose**: Defines the structure for naming pattern templates with placeholder variables.

**Key Features**:
- Pattern templates with `{variable}` placeholders for each resource type
- Optional transformations (region mapping, case conversion, character replacement)
- Validation rules (max length, allowed characters, required variables)

**Structure**:
```json
{
  "version": "1.0",
  "patterns": {
    "aws_s3_bucket": "{project}-{purpose}-{layer}-{environment}-{region_short}",
    "dbx_cluster": "{project}-{workload}-{cluster_type}-{environment}",
    ...
  },
  "transformations": {
    "region_mapping": { ... },
    "lowercase": [ ... ],
    "replace_hyphens": { ... }
  },
  "validation": {
    "max_length": { ... },
    "allowed_chars": { ... },
    "required_variables": { ... }
  }
}
```

**Example**: See `examples/configs/naming-patterns.yaml`

## Supported Resource Types

| Resource Type | Description | Example Pattern |
|--------------|-------------|-----------------|
| `aws_s3_bucket` | AWS S3 bucket | `{project}-{purpose}-{layer}-{environment}-{region_short}` |
| `aws_glue_database` | AWS Glue database | `{project}_{domain}_{layer}_{environment}` |
| `aws_glue_table` | AWS Glue table | `{table_type}_{entity}` |
| `dbx_cluster` | Databricks cluster | `{project}-{workload}-{cluster_type}-{environment}` |
| `dbx_job` | Databricks job | `{project}-{job_type}-{purpose}-{schedule}-{environment}` |
| `dbx_catalog` | Unity Catalog catalog | `{project}_{catalog_type}_{environment}` |
| `dbx_schema` | Unity Catalog schema | `{domain}_{layer}` |
| `dbx_table` | Unity Catalog table | `{table_type}_{entity}` |

## Common Pattern Variables

| Variable | Description | Example Values |
|----------|-------------|----------------|
| `project` | Project name | `dataplatform`, `oncology`, `finance` |
| `environment` | Environment code | `dev`, `stg`, `prd` |
| `region` | AWS region (full) | `us-east-1`, `eu-west-1` |
| `region_short` | AWS region (abbreviated) | `use1`, `euw1` |
| `purpose` | Resource purpose | `raw`, `processed`, `curated`, `backup` |
| `layer` | Data layer (medallion) | `raw`, `bronze`, `silver`, `gold` |
| `domain` | Business domain | `finance`, `sales`, `marketing` |
| `workload` | Compute workload type | `etl`, `analytics`, `ml-training` |
| `cluster_type` | Cluster type | `shared`, `dedicated`, `job` |
| `job_type` | Job type | `batch`, `streaming`, `adhoc` |
| `table_type` | Table type | `fact`, `dim`, `bridge` |
| `entity` | Entity name | `customers`, `sales`, `transactions` |
| `catalog_type` | Catalog type | `main`, `dev`, `sandbox` |
| `schedule` | Job schedule | `hourly`, `daily`, `weekly` |

## Value Precedence

Values are merged with the following precedence (lowest to highest):

1. **defaults** - Global defaults applied to all resources
2. **environments.{env}** - Environment-specific overrides (dev/stg/prd)
3. **resource_types.{type}** - Resource-type-specific overrides
4. **blueprint.metadata** - Values from blueprint file (highest precedence)

Example:
```yaml
# naming-values.yaml
defaults:
  project: dataplatform
  region: us-east-1

environments:
  prd:
    environment: prd
    data_classification: confidential

resource_types:
  aws_s3_bucket:
    purpose: raw
    layer: raw

# Result for aws_s3_bucket in prd:
# {
#   project: "dataplatform",         # from defaults
#   region: "us-east-1",             # from defaults
#   environment: "prd",              # from environments.prd
#   data_classification: "confidential",  # from environments.prd
#   purpose: "raw",                  # from resource_types.aws_s3_bucket
#   layer: "raw"                     # from resource_types.aws_s3_bucket
# }
```

## Transformations

### Region Mapping

Automatically converts full AWS region names to abbreviated codes:

```yaml
transformations:
  region_mapping:
    us-east-1: use1
    us-west-2: usw2
    eu-west-1: euw1
```

### Case Conversion

Convert specific variables to lowercase or uppercase:

```yaml
transformations:
  lowercase:
    - project
    - environment
    - domain
  uppercase:
    - cost_center
```

### Character Replacement

Replace characters in specific variables:

```yaml
transformations:
  replace_hyphens:
    project: "_"  # Converts "data-platform" → "data_platform"
```

## Validation Rules

### Maximum Length

Enforce maximum length constraints per resource type:

```yaml
validation:
  max_length:
    aws_s3_bucket: 63
    dbx_cluster: 100
```

### Allowed Characters

Define regex patterns for allowed characters:

```yaml
validation:
  allowed_chars:
    aws_s3_bucket: "^[a-z0-9-]+$"
    aws_glue_database: "^[a-z0-9_]+$"
```

### Required Variables

Specify which variables must be present for each resource type:

```yaml
validation:
  required_variables:
    aws_s3_bucket:
      - project
      - purpose
      - environment
      - region_short
```

## Usage Examples

### 1. Create resources with configuration files

```bash
dpn create \
  --blueprint my-blueprint.json \
  --values-config naming-values.yaml \
  --patterns-config naming-patterns.yaml
```

### 2. Override values inline

```bash
dpn create \
  --blueprint my-blueprint.json \
  --values-config naming-values.yaml \
  --patterns-config naming-patterns.yaml \
  --override project=oncology \
  --override environment=prd
```

### 3. Use default config locations

Place config files in `~/.dpn/`:
- `~/.dpn/naming-values.yaml`
- `~/.dpn/naming-patterns.yaml`

Then run without explicit paths:
```bash
dpn create --blueprint my-blueprint.json
```

### 4. Validate configuration files

```bash
dpn config validate \
  --values naming-values.yaml \
  --patterns naming-patterns.yaml
```

### 5. Initialize default configs

```bash
dpn config init --output ~/.dpn/
```

## Migration Example

Migrating from `dataplatform` to `oncology` project:

**Before** (hardcoded in code):
- S3 bucket: `dataplatform-raw-raw-prd-use1`
- Glue DB: `dataplatform_finance_gold_prd`
- Cluster: `dataplatform-etl-shared-prd`

**After** (using naming-values.yaml with `project: oncology`):
- S3 bucket: `oncology-raw-raw-prd-use1`
- Glue DB: `oncology_finance_gold_prd`
- Cluster: `oncology-etl-shared-prd`

Simply change one value in the config file!

## Best Practices

1. **Version Control**: Store config files in Git alongside blueprints
2. **Environment Separation**: Use separate values configs for dev/stg/prd
3. **Validation First**: Always validate configs before using in production
4. **Custom Variables**: Add organization-specific variables as needed
5. **Documentation**: Document any custom variables and their purpose
6. **Testing**: Test pattern changes in dev environment first

## Schema Validation

Both schemas follow JSON Schema Draft 7 specification and can be used with any JSON Schema validator:

```python
import json
import jsonschema
import yaml

# Load schema
with open('schemas/naming-values-schema.json') as f:
    schema = json.load(f)

# Load config
with open('naming-values.yaml') as f:
    config = yaml.safe_load(f)

# Validate
jsonschema.validate(instance=config, schema=schema)
```

## Related Documentation

- [Blueprint Schema](../src/data_platform_naming/plan/blueprint.py) - Blueprint JSON structure
- [AWS Naming Guide](../docs/aws-naming-guide.md) - AWS naming conventions
- [Databricks Naming Guide](../docs/dbx-naming-guide.md) - Databricks naming conventions
- [Example Configs](../examples/configs/) - Working configuration examples

## Support

For issues or questions about schemas:
1. Check example configs in `examples/configs/`
2. Review schema documentation above
3. Open an issue on GitHub with schema validation errors
