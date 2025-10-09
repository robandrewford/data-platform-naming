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
dpn plan init --env prd --project myproject

# Creates blueprints/dev.json
dpn plan init --env dev --project myproject

# Custom location (if needed)
dpn plan init --env stg --project myproject --output custom/path/stg.json
```

### Validate a Blueprint

```bash
dpn plan validate blueprints/prd.json
```

### Preview Generated Names

```bash
dpn plan preview blueprints/prd.json
```

### Create Resources

```bash
# Dry run first
dpn create --blueprint blueprints/prd.json --dry-run

# Execute
dpn create --blueprint blueprints/prd.json
```

## Example Templates

For blueprint examples and templates, see `examples/blueprints/`:

- `examples/blueprints/dev.json` - Development environment example
- `examples/blueprints/stg.json` - Staging environment example  
- `examples/blueprints/prd.json` - Production environment example

## Note

Blueprint JSON files in this directory (`blueprints/*.json`) are automatically ignored by git, so your working files won't be committed. This is intentional to keep your local development clean.
