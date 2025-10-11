# Configuration-Based Naming System Migration Guide

## Overview

This guide helps you migrate from the legacy hardcoded naming patterns to the new configuration-based naming system introduced in version 0.2.0.

## Breaking Changes

### What Changed

The naming generators (`AWSNamingGenerator` and `DatabricksNamingGenerator`) now require:

1. **ConfigurationManager**: A configuration manager instance that loads naming patterns and values
2. **use_config=True flag**: Explicit opt-in to use the configuration-based system
3. **YAML configuration files**: Two configuration files that define your naming patterns and values

### Why This Change?

The configuration-based approach provides:

- **Flexibility**: Change naming patterns without code changes
- **Consistency**: Centralized naming rules across all environments
- **Customization**: Override patterns per environment or resource type
- **Validation**: Schema validation ensures correct configuration
- **Transparency**: See all naming rules in one place

## Migration Steps

### Step 1: Create Configuration Files

Create two YAML files to define your naming patterns and values.

#### naming-values.yaml

This file defines the values used in naming patterns.

```yaml
version: "1.0"

# Default values used across all environments
defaults:
  project: "dataplatform"
  environment: "prd"
  region: "us-east-1"
  team: "data-engineering"
  cost_center: "CC-1234"

# Environment-specific overrides
environments:
  dev:
    environment: "dev"
  stg:
    environment: "stg"
  prd:
    environment: "prd"

# Resource-type specific overrides (optional)
resource_types:
  aws_s3_bucket:
    layer: "raw"
  aws_glue_database:
    layer: "bronze"
```

#### naming-patterns.yaml

This file defines the naming patterns for each resource type.

```yaml
version: "1.0"

# Naming patterns for all resource types
patterns:
  # AWS Resources (13 types)
  aws_s3_bucket: "{project}-{purpose}-{layer}-{environment}-{region_short}"
  aws_glue_database: "{project}_{domain}_{layer}_{environment}"
  aws_glue_table: "{table_type}_{entity}"
  aws_glue_crawler: "{project}-{environment}-crawler-{database}-{source}"
  aws_lambda_function: "{project}-{environment}-{domain}-{trigger}-{action}"
  aws_iam_role: "{project}-{environment}-{service}-{purpose}-role"
  aws_iam_policy: "{project}-{environment}-{service}-{purpose}-policy"
  aws_kinesis_stream: "{project}-{environment}-{domain}-{source}-stream"
  aws_kinesis_firehose: "{project}-{environment}-{domain}-to-{destination}"
  aws_dynamodb_table: "{project}-{environment}-{entity}-{purpose}"
  aws_sns_topic: "{project}-{environment}-{event_type}-{purpose}"
  aws_sqs_queue: "{project}-{environment}-{purpose}-{queue_type}"
  aws_step_function: "{project}-{environment}-{workflow}-{purpose}"
  
  # Databricks Resources (14 types)
  dbx_workspace: "dbx-{project}-{purpose}-{environment}-{region_short}"
  dbx_cluster: "{project}-{workload}-{cluster_type}-{environment}"
  dbx_job: "{project}-{job_type}-{purpose}-{schedule}-{environment}"
  dbx_notebook_path: "/{project}/{domain}/{purpose}/{environment}/{notebook_name}"
  dbx_repo: "{project}-{repo_purpose}-{environment}"
  dbx_pipeline: "{project}-{pipeline_type}-{source}-{target}-{environment}"
  dbx_sql_warehouse: "{project}-sql-{purpose}-{size}-{environment}"
  dbx_catalog: "{project}_{catalog_type}_{environment}"
  dbx_schema: "{domain}_{layer}"
  dbx_table: "{table_type}_{entity}"
  dbx_volume: "{data_type}_{purpose}"
  dbx_secret_scope: "{project}-{purpose}-{environment}"
  dbx_instance_pool: "{project}-pool-{node_type}-{purpose}-{environment}"
  dbx_policy: "{project}-{target}-{policy_type}-{environment}"

# Transformations applied to values
transformations:
  # Map AWS regions to short codes
  region_mapping:
    us-east-1: "use1"
    us-east-2: "use2"
    us-west-1: "usw1"
    us-west-2: "usw2"
    eu-west-1: "euw1"
    eu-west-2: "euw2"
    eu-central-1: "euc1"
    ap-southeast-1: "aps1"
    ap-southeast-2: "aps2"
    ap-northeast-1: "apne1"
  
  # Hash generation for unique identifiers
  hash_generation:
    algorithm: "md5"
    length: 8
    prefix: ""
    separator: "-"

# Validation rules
validation:
  max_lengths:
    aws_s3_bucket: 63
    aws_glue_database: 255
    aws_glue_table: 255
    aws_glue_crawler: 255
    aws_lambda_function: 64
    aws_iam_role: 64
    aws_iam_policy: 128
    aws_kinesis_stream: 128
    aws_kinesis_firehose: 64
    aws_dynamodb_table: 255
    aws_sns_topic: 256
    aws_sqs_queue: 80
    aws_step_function: 80
    dbx_workspace: 255
    dbx_cluster: 255
    dbx_job: 255
    dbx_notebook_path: 1000
    dbx_repo: 255
    dbx_pipeline: 255
    dbx_sql_warehouse: 255
    dbx_catalog: 255
    dbx_schema: 255
    dbx_table: 255
    dbx_volume: 255
    dbx_secret_scope: 128
    dbx_instance_pool: 255
    dbx_policy: 255
```

### Step 2: Update Your Code

#### Before (Legacy Mode - No Longer Supported)

```python
from data_platform_naming.aws_naming import AWSNamingGenerator, AWSNamingConfig

# Old way - NO LONGER WORKS
config = AWSNamingConfig(
    environment="prd",
    project="dataplatform",
    region="us-east-1"
)

generator = AWSNamingGenerator(config)
bucket_name = generator.generate_s3_bucket_name("raw", "raw")
# This will raise NotImplementedError!
```

#### After (Configuration-Based)

```python
from pathlib import Path
from data_platform_naming.aws_naming import AWSNamingGenerator, AWSNamingConfig
from data_platform_naming.config.configuration_manager import ConfigurationManager

# Load configuration files
config_manager = ConfigurationManager()
config_manager.load_configs(
    values_path=Path("naming-values.yaml"),
    patterns_path=Path("naming-patterns.yaml")
)

# Create generator with configuration
aws_config = AWSNamingConfig(
    environment="prd",
    project="dataplatform",
    region="us-east-1"
)

generator = AWSNamingGenerator(
    config=aws_config,
    configuration_manager=config_manager,
    use_config=True  # Required!
)

# Generate names - now uses patterns from YAML
bucket_name = generator.generate_s3_bucket_name(
    purpose="raw",
    layer="raw"
)
# Result: "dataplatform-raw-raw-prd-use1"
```

#### Alternative: Pre-loaded Loaders

```python
from data_platform_naming.config.naming_values_loader import NamingValuesLoader
from data_platform_naming.config.naming_patterns_loader import NamingPatternsLoader
from data_platform_naming.config.configuration_manager import ConfigurationManager

# Load configurations
values_loader = NamingValuesLoader()
values_loader.load_from_file(Path("naming-values.yaml"))

patterns_loader = NamingPatternsLoader()
patterns_loader.load_from_file(Path("naming-patterns.yaml"))

# Create ConfigurationManager with pre-loaded loaders
config_manager = ConfigurationManager(
    values_loader=values_loader,
    patterns_loader=patterns_loader
)

# Use as before...
```

### Step 3: Store Configuration Files

You have two options for storing configuration files:

#### Option 1: Default Location (Recommended)

Store files in `~/.dpn/` directory:

```bash
mkdir -p ~/.dpn
cp naming-values.yaml ~/.dpn/
cp naming-patterns.yaml ~/.dpn/
```

Then load with:

```python
config_manager = ConfigurationManager()
config_manager.load_from_default_locations()
```

#### Option 2: Custom Location

Store files anywhere and provide explicit paths:

```python
config_manager = ConfigurationManager()
config_manager.load_configs(
    values_path=Path("/path/to/naming-values.yaml"),
    patterns_path=Path("/path/to/naming-patterns.yaml")
)
```

## Advanced Features

### Metadata Overrides

Override values at runtime using the `metadata` parameter:

```python
# Override environment for a specific resource
bucket_name = generator.generate_s3_bucket_name(
    purpose="raw",
    layer="raw",
    metadata={"environment": "dev"}  # Override from prd to dev
)
# Result: "dataplatform-raw-raw-dev-use1"
```

### Value Precedence

Values are applied in this order (highest precedence last):

1. **defaults** in naming-values.yaml
2. **environments[env]** overrides
3. **resource_types[type]** overrides
4. **blueprint metadata** (from JSON blueprints)
5. **method metadata parameter** (runtime overrides)

### Pattern Customization

Customize patterns per environment:

```yaml
# naming-values.yaml
environments:
  dev:
    environment: "dev"
  prd:
    environment: "prd"

resource_types:
  aws_s3_bucket:
    dev:
      layer: "sandbox"  # Different default for dev
    prd:
      layer: "production"  # Different default for prd
```

## Troubleshooting

### Error: "use_config=True requires configuration_manager parameter"

**Cause**: You set `use_config=True` but didn't provide a ConfigurationManager.

**Solution**: Create and pass a ConfigurationManager:

```python
config_manager = ConfigurationManager()
config_manager.load_configs(...)

generator = AWSNamingGenerator(
    config=aws_config,
    configuration_manager=config_manager,
    use_config=True
)
```

### Error: "Pattern validation failed: Missing patterns"

**Cause**: Your naming-patterns.yaml doesn't include patterns for all resource types.

**Solution**: Ensure all 27 resource types have patterns defined (13 AWS + 14 Databricks).

### Error: "Naming values configuration not loaded"

**Cause**: ConfigurationManager doesn't have values loaded.

**Solution**: Call `load_configs()` or `load_from_default_locations()` before using the manager.

### Error: "Generator requires use_config=True"

**Cause**: You're trying to use the generator in legacy mode (no longer supported).

**Solution**: Set `use_config=True` and provide a ConfigurationManager.

## Migration Checklist

- [ ] Create `naming-values.yaml` with your project's values
- [ ] Create `naming-patterns.yaml` with your naming patterns
- [ ] Validate configuration files with schema validation
- [ ] Update code to use ConfigurationManager
- [ ] Set `use_config=True` when creating generators
- [ ] Test name generation with your patterns
- [ ] Store configuration files in `~/.dpn/` or custom location
- [ ] Update CI/CD pipelines to include configuration files
- [ ] Update documentation with new usage patterns

## Benefits After Migration

✅ **Flexibility**: Change patterns without code deployment
✅ **Consistency**: Single source of truth for naming
✅ **Validation**: Schema validation prevents errors
✅ **Customization**: Environment-specific overrides
✅ **Transparency**: All naming rules visible in YAML
✅ **Testability**: Test different patterns without code changes

## Resources

- [Configuration System Documentation](schemas/README.md)
- [Example Configuration Files](examples/configs/)
- [JSON Schema Reference](schemas/naming-patterns-schema.json)
- [Integration Tests](tests/test_integration_e2e.py)

## Support

If you encounter issues during migration:

1. Review the [troubleshooting section](#troubleshooting) above
2. Check example configuration files in `examples/configs/`
3. Run integration tests: `uv run pytest tests/test_integration_e2e.py`
4. Report bugs using `/reportbug` command in Cline chat
