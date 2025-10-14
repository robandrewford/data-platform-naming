# Blueprints Directory

This directory contains user-generated blueprint files for data platform resource provisioning.

## Purpose

Blueprint files define the infrastructure resources you want to create in AWS and Databricks. They are JSON files that specify:

- Environment metadata (environment, project, region, team, cost center)
- AWS resources (S3 buckets, Glue databases, Glue tables)
- Databricks resources (clusters, jobs, Unity Catalog)

## Usage

### Create a Blueprint

The CLI automatically saves blueprints here by default:

```bash
# Creates blueprints/prd.json
uv run dpn plan init --env prd --project myproject

# Creates blueprints/dev.json
uv run dpn plan init --env dev --project myproject

# Custom location (if needed)
uv run dpn plan init --env stg --project myproject --output custom/path/stg.json
```

### Validate a Blueprint

```bash
uv run dpn plan validate blueprints/prd.json
```

### Preview Generated Names

```bash
uv run dpn plan preview blueprints/prd.json
```

### Create Resources

```bash
# Dry run first
uv run dpn create --blueprint blueprints/prd.json --dry-run

# Execute
uv run dpn create --blueprint blueprints/prd.json
```

## Scope Filtering

Blueprints support optional scope filtering to selectively process specific resource types. This is useful when you want to:

- Deploy only AWS resources while keeping Databricks definitions for reference
- Process specific resource types (e.g., only S3 buckets and Glue databases)
- Exclude certain resources temporarily (e.g., skip clusters during testing)

### Scope Configuration

Add a `scope` section to your blueprint with two properties:

- `mode`: Either `"include"` (process only matching types) or `"exclude"` (process all except matching types)
- `patterns`: Array of wildcard patterns for resource type matching

**Supported Resource Types:**
- AWS: `aws_s3_bucket`, `aws_glue_database`, `aws_glue_table`
- Databricks: `dbx_cluster`, `dbx_job`, `dbx_catalog`, `dbx_schema`, `dbx_table`

**Wildcard Patterns:**
- `*` matches any characters: `aws_*` matches all AWS resources
- `?` matches single character: `aws_s3_?` matches `aws_s3_1`
- Exact match: `aws_s3_bucket` matches only S3 buckets
- Prefix: `aws_*` matches `aws_s3_bucket`, `aws_glue_database`, etc.
- Suffix: `*_bucket` matches `aws_s3_bucket`

### Examples

**Include only AWS resources:**
```json
{
  "version": "1.0",
  "metadata": {...},
  "scope": {
    "mode": "include",
    "patterns": ["aws_*"]
  },
  "resources": {...}
}
```

**Exclude Databricks clusters and jobs:**
```json
{
  "scope": {
    "mode": "exclude",
    "patterns": ["dbx_cluster", "dbx_job"]
  }
}
```

**Process only S3 buckets and Glue databases:**
```json
{
  "scope": {
    "mode": "include",
    "patterns": ["aws_s3_bucket", "aws_glue_database"]
  }
}
```

**Multiple patterns with wildcards:**
```json
{
  "scope": {
    "mode": "include",
    "patterns": ["aws_s3_*", "aws_glue_*", "dbx_catalog"]
  }
}
```

### Scope Examples

See working examples with scope filtering:

- `examples/blueprints/dev-aws-only.json` - Includes only AWS resources
- `examples/blueprints/dev-no-clusters.json` - Excludes Databricks clusters and jobs

### Notes on Scope Filtering

- Scope is **optional** - blueprints without scope process all resources
- Backward compatible - existing blueprints work without changes
- Filtering happens after parsing - all resources are validated regardless of scope
- Dependencies are preserved - filtered resources maintain their dependency relationships

## Example Templates

For blueprint examples and templates, see `examples/blueprints/`:

- `examples/blueprints/dev.json` - Development environment example
- `examples/blueprints/stg.json` - Staging environment example  
- `examples/blueprints/prd.json` - Production environment example
- `examples/blueprints/dev-aws-only.json` - AWS resources only (scope filtering)
- `examples/blueprints/dev-no-clusters.json` - Exclude clusters/jobs (scope filtering)

## Note

Blueprint JSON files in this directory (`blueprints/*.json`) are automatically ignored by git, so your working files won't be committed. This is intentional to keep your local development clean.
