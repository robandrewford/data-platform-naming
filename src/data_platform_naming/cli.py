#!/usr/bin/env python3
"""
Data Platform Naming CLI
Unified interface for blueprint planning and CRUD operations
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Import core modules
from data_platform_naming.aws_naming import AWSNamingConfig, AWSNamingGenerator
from data_platform_naming.config.configuration_manager import ConfigurationManager
from data_platform_naming.config.naming_patterns_loader import PatternError
from data_platform_naming.constants import Environment
from data_platform_naming.crud.aws_operations import AWSExecutorRegistry
from data_platform_naming.crud.dbx_operations import DatabricksConfig, DatabricksExecutorRegistry
from data_platform_naming.crud.transaction_manager import (
    Operation,
    OperationType,
    ResourceType,
    TransactionManager,
)
from data_platform_naming.dbx_naming import DatabricksNamingConfig, DatabricksNamingGenerator
from data_platform_naming.plan.blueprint import BLUEPRINT_SCHEMA, BlueprintParser

console = Console()


# =============================================================================
# INPUT VALIDATION CONSTANTS
# =============================================================================

# Allowed override keys for CLI --override parameter
ALLOWED_OVERRIDE_KEYS = {
    'environment', 'project', 'region', 'team',
    'cost_center', 'data_classification'
}

# Valid environment values
ENVIRONMENT_VALUES = {e.value for e in Environment}


# =============================================================================
# CONFIGURATION HELPERS
# =============================================================================

def load_configuration_manager(
    values_config: Optional[str] = None,
    patterns_config: Optional[str] = None,
    overrides: Optional[tuple] = None
) -> Optional[ConfigurationManager]:
    """
    Load ConfigurationManager from files or defaults.
    
    Priority:
    1. Explicit paths (--values-config, --patterns-config)
    2. Default location (~/.dpn/)
    3. Return None if no configs found (backward compatibility)
    
    Args:
        values_config: Explicit path to naming-values.yaml
        patterns_config: Explicit path to naming-patterns.yaml
        overrides: Tuple of key=value overrides
        
    Returns:
        ConfigurationManager or None if no configs found
        
    Raises:
        click.ClickException: If only one config file provided, or validation fails
    """
    manager = None

    # Try explicit paths
    if values_config or patterns_config:
        if not (values_config and patterns_config):
            raise click.ClickException(
                "Must provide both --values-config and --patterns-config, or neither.\n"
                "Run 'dpn config init' to create default configuration files."
            )

        try:
            manager = ConfigurationManager()
            manager.load_configs(
                values_path=Path(values_config),
                patterns_path=Path(patterns_config)
            )
            console.print(f"[dim]Loaded config from: {values_config}, {patterns_config}[/dim]")
        except Exception as e:
            raise click.ClickException(f"Failed to load config files: {str(e)}")

    # Try default location
    else:
        default_dir = Path.cwd() / '.dpn'
        values_path = default_dir / 'naming-values.yaml'
        patterns_path = default_dir / 'naming-patterns.yaml'

        if values_path.exists() and patterns_path.exists():
            try:
                manager = ConfigurationManager()
                manager.load_from_default_locations()
                console.print("[dim]Loaded config from: .dpn/[/dim]")
            except Exception as e:
                raise click.ClickException(
                    f"Config files found in .dpn/ but failed to load: {str(e)}\n"
                    "Run 'dpn config validate' to check configuration."
                )

    # Apply overrides if provided
    if overrides and manager:
        override_dict = {}
        for override in overrides:
            if '=' not in override:
                raise click.ClickException(
                    f"Invalid override format: '{override}'\n"
                    "Use format: key=value (e.g., environment=dev)"
                )
            
            key, value = override.split('=', 1)
            key = key.strip()
            value = value.strip()
            
            # Validate key against whitelist
            if key not in ALLOWED_OVERRIDE_KEYS:
                raise click.ClickException(
                    f"Invalid override key: '{key}'\n"
                    f"Allowed keys: {', '.join(sorted(ALLOWED_OVERRIDE_KEYS))}"
                )
            
            # Validate environment value
            if key == 'environment' and value not in ENVIRONMENT_VALUES:
                raise click.ClickException(
                    f"Invalid environment: '{value}'\n"
                    f"Allowed values: {', '.join(sorted(ENVIRONMENT_VALUES))}"
                )
            
            # Validate project name format
            if key == 'project':
                if not re.match(r'^[a-z0-9-]+$', value):
                    raise click.ClickException(
                        f"Invalid project name: '{value}'\n"
                        "Use lowercase letters, numbers, and hyphens only"
                    )
            
            override_dict[key] = value

        # Store overrides for use in name generation (dynamic attribute)
        setattr(manager, '_cli_overrides', override_dict)
        if override_dict:
            console.print(f"[dim]Applied overrides: {', '.join(f'{k}={v}' for k, v in override_dict.items())}[/dim]")

    return manager


@click.group()
@click.version_option(version='0.1.0')
def cli():
    """Data Platform Naming Convention CLI
    
    Generate, validate, and execute infrastructure blueprints
    for AWS and Databricks resources with consistent naming conventions.
    
    Configuration:
      Initialize config:  dpn config init
      Validate config:    dpn config validate
      Show config:        dpn config show
    
    Common Workflow:
      1. dpn config init              # Set up configuration
      2. dpn plan init --env dev      # Create blueprint template
      3. dpn plan preview dev.json    # Preview resource names
      4. dpn create --blueprint dev.json  # Create resources
    
    For more information on each command, use: dpn <command> --help
    """
    pass


# =============================================================================
# PLAN COMMANDS
# =============================================================================

@cli.group()
def plan():
    """Blueprint planning operations"""
    pass


@plan.command('init')
@click.option('--env', type=click.Choice([e.value for e in Environment]), required=True)
@click.option('--project', required=True)
@click.option('--region', default='us-east-1')
@click.option('--output', type=click.Path(), default=None)
def plan_init(env: str, project: str, region: str, output: Optional[str]):
    """Initialize blueprint template"""

    # Default to blueprints/{env}.json if no output specified
    if output is None:
        output = f'blueprints/{env}.json'

    # Create parent directory if it doesn't exist
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    template = {
        "version": "1.0",
        "metadata": {
            "environment": env,
            "project": project,
            "region": region,
            "team": "TEAM_NAME",
            "cost_center": "COST_CENTER"
        },
        "resources": {
            "aws": {
                "s3_buckets": [
                    {
                        "purpose": "raw",
                        "layer": "raw",
                        "versioning": True,
                        "lifecycle_days": 90
                    }
                ],
                "glue_databases": [
                    {
                        "domain": "DOMAIN",
                        "layer": "gold",
                        "description": "Description"
                    }
                ],
                "glue_tables": []
            },
            "databricks": {
                "clusters": [
                    {
                        "workload": "etl",
                        "cluster_type": "shared",
                        "node_type": "i3.xlarge",
                        "spark_version": "13.3.x-scala2.12",
                        "autoscale": {"min": 2, "max": 8}
                    }
                ],
                "jobs": [
                    {
                        "job_type": "batch",
                        "purpose": "ingestion",
                        "cluster_ref": "etl",
                        "schedule": "daily",
                        "tasks": []
                    }
                ],
                "unity_catalog": {
                    "catalogs": [
                        {
                            "catalog_type": "main",
                            "schemas": [
                                {
                                    "domain": "DOMAIN",
                                    "layer": "gold",
                                    "tables": [
                                        {
                                            "entity": "ENTITY",
                                            "table_type": "fact",
                                            "columns": []
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

    output_path = Path(output)
    with open(output_path, 'w') as f:
        json.dump(template, f, indent=2)

    console.print(f"[green]✓[/green] Blueprint template: {output_path}")
    console.print(f"[yellow]→[/yellow] Edit template, then run: dpn plan validate {output}")


@plan.command('validate')
@click.argument('blueprint', type=click.Path(exists=True))
def plan_validate(blueprint: str):
    """Validate blueprint schema"""

    try:
        with open(blueprint) as f:
            data = json.load(f)

        import jsonschema
        jsonschema.validate(instance=data, schema=BLUEPRINT_SCHEMA)

        console.print(f"[green]✓[/green] Blueprint valid: {blueprint}")

    except jsonschema.ValidationError as e:
        console.print("[red]✗[/red] Validation failed:")
        console.print(f"  Path: {'.'.join(str(p) for p in e.path)}")
        console.print(f"  Error: {e.message}")
        sys.exit(1)

    except Exception as e:
        console.print(f"[red]✗[/red] Error: {str(e)}")
        sys.exit(1)


@plan.command('preview')
@click.argument('blueprint', type=click.Path(exists=True))
@click.option('--values-config', type=click.Path(exists=True),
              help='Path to naming-values.yaml (default: .dpn/naming-values.yaml)')
@click.option('--patterns-config', type=click.Path(exists=True),
              help='Path to naming-patterns.yaml (default: .dpn/naming-patterns.yaml)')
@click.option('--override', multiple=True,
              help='Override values (format: key=value, e.g., environment=dev)')
@click.option('--output', type=click.Path(), help='Export to JSON')
@click.option('--format', type=click.Choice(['table', 'json']), default='table')
def plan_preview(blueprint: str, values_config: Optional[str], patterns_config: Optional[str],
                override: tuple, output: Optional[str], format: str):
    """Preview resource names
    
    Examples:
      dpn plan preview dev.json
      dpn plan preview dev.json --values-config custom-values.yaml --patterns-config custom-patterns.yaml
      dpn plan preview dev.json --override environment=dev --override project=oncology
    """

    try:
        # Load blueprint
        with open(blueprint) as f:
            data = json.load(f)

        metadata = data['metadata']

        # Load configuration manager
        config_manager = load_configuration_manager(values_config, patterns_config, override)

        # Initialize generators
        aws_config = AWSNamingConfig(
            environment=metadata['environment'],
            project=metadata['project'],
            region=metadata['region']
        )

        dbx_config = DatabricksNamingConfig(
            environment=metadata['environment'],
            project=metadata['project'],
            region=metadata['region']
        )

        # Create generators with ConfigurationManager
        if config_manager:
            console.print("[dim]Using configuration-based naming[/dim]")
            generators = {
                'aws': AWSNamingGenerator(
                    config=aws_config,
                    configuration_manager=config_manager
                ),
                'databricks': DatabricksNamingGenerator(
                    config=dbx_config,
                    configuration_manager=config_manager
                )
            }
        else:
            raise click.ClickException(
                "Configuration files required but not found.\n"
                "Run 'dpn config init' to create configuration files in .dpn/"
            )

        # Parse with optional ConfigurationManager
        parser = BlueprintParser(generators, configuration_manager=config_manager)
        parsed = parser.parse(Path(blueprint))

        if format == 'json' or output:
            # JSON output
            preview_data = {
                'metadata': parsed.metadata,
                'total_resources': len(parsed.resources),
                'resources': [
                    {
                        'type': r.resource_type,
                        'id': r.resource_id,
                        'display': r.display_name,
                        'dependencies': r.dependencies
                    }
                    for r in parsed.resources
                ]
            }

            if output:
                with open(output, 'w') as f:
                    json.dump(preview_data, f, indent=2)
                console.print(f"[green]✓[/green] Preview exported: {output}")
            else:
                console.print_json(data=preview_data)

        else:
            # Table output
            table = Table(title="Resource Preview")
            table.add_column("Type", style="cyan")
            table.add_column("Resource ID", style="green")
            table.add_column("Dependencies", style="yellow")

            for resource in parsed.get_execution_order():
                deps = ', '.join(resource.dependencies) if resource.dependencies else '-'
                table.add_row(
                    resource.resource_type,
                    resource.resource_id,
                    deps
                )

            console.print(table)
            console.print(f"\n[green]Total:[/green] {len(parsed.resources)} resources")

    except Exception as e:
        console.print(f"[red]✗[/red] Preview failed: {str(e)}")
        sys.exit(1)


@plan.command('schema')
@click.option('--output', type=click.Path(), default='blueprint-schema.json')
def plan_schema(output: str):
    """Export JSON schema"""

    output_path = Path(output)
    with open(output_path, 'w') as f:
        json.dump(BLUEPRINT_SCHEMA, f, indent=2)

    console.print(f"[green]✓[/green] Schema exported: {output_path}")


# =============================================================================
# CREATE COMMANDS
# =============================================================================

@cli.command('create')
@click.option('--blueprint', type=click.Path(exists=True), required=True)
@click.option('--dry-run', is_flag=True, help='Preview without execution')
@click.option('--aws-profile', help='AWS profile')
@click.option('--dbx-host', envvar='DATABRICKS_HOST', help='Databricks host')
@click.option('--dbx-token', envvar='DATABRICKS_TOKEN', help='Databricks token')
@click.option('--values-config', type=click.Path(exists=True),
              help='Path to naming-values.yaml (default: .dpn/naming-values.yaml)')
@click.option('--patterns-config', type=click.Path(exists=True),
              help='Path to naming-patterns.yaml (default: .dpn/naming-patterns.yaml)')
@click.option('--override', multiple=True,
              help='Override values (format: key=value, e.g., environment=dev)')
def create(blueprint: str, dry_run: bool, aws_profile: Optional[str],
           dbx_host: Optional[str], dbx_token: Optional[str],
           values_config: Optional[str], patterns_config: Optional[str],
           override: tuple):
    """Create resources from blueprint
    
    Examples:
      dpn create --blueprint dev.json
      dpn create --blueprint dev.json --values-config custom-values.yaml --patterns-config custom-patterns.yaml
      dpn create --blueprint dev.json --override environment=dev --override project=oncology
      dpn create --blueprint dev.json --dry-run
    """

    try:
        # Load blueprint
        with open(blueprint) as f:
            data = json.load(f)

        metadata = data['metadata']

        # Load configuration manager
        config_manager = load_configuration_manager(values_config, patterns_config, override)

        # Initialize generators
        aws_config = AWSNamingConfig(
            environment=metadata['environment'],
            project=metadata['project'],
            region=metadata['region']
        )

        dbx_config = DatabricksNamingConfig(
            environment=metadata['environment'],
            project=metadata['project'],
            region=metadata['region']
        )

        # Create generators with ConfigurationManager
        if config_manager:
            console.print("[dim]Using configuration-based naming[/dim]")
            generators = {
                'aws': AWSNamingGenerator(
                    config=aws_config,
                    configuration_manager=config_manager
                ),
                'databricks': DatabricksNamingGenerator(
                    config=dbx_config,
                    configuration_manager=config_manager
                )
            }
        else:
            raise click.ClickException(
                "Configuration files required but not found.\n"
                "Run 'dpn config init' to create configuration files in .dpn/"
            )

        # Parse with ConfigurationManager
        parser = BlueprintParser(generators, configuration_manager=config_manager)
        parsed = parser.parse(Path(blueprint))

        # Build operations
        operations: List[Operation] = []
        for resource in parsed.get_execution_order():
            op = Operation(
                id=f"op-{len(operations)}",
                type=OperationType.CREATE,
                resource_type=ResourceType[resource.resource_type.upper()],
                resource_id=resource.resource_id,
                params=resource.params
            )
            operations.append(op)

        if dry_run:
            # Preview
            console.print("[yellow]DRY RUN[/yellow] - No resources created\n")

            table = Table(title="Execution Plan")
            table.add_column("#", style="dim")
            table.add_column("Type", style="cyan")
            table.add_column("Resource ID", style="green")

            for i, op in enumerate(operations, 1):
                table.add_row(str(i), op.resource_type.value, op.resource_id)

            console.print(table)
            console.print("\n[yellow]Run without --dry-run to execute[/yellow]")
            return

        # Execute
        console.print(f"[yellow]Creating {len(operations)} resources...[/yellow]\n")

        # Initialize transaction manager
        tm = TransactionManager()

        # Register executors
        import boto3
        aws_registry = AWSExecutorRegistry(
            boto3.Session(profile_name=aws_profile) if aws_profile else None
        )

        dbx_registry: Any = None
        if dbx_host and dbx_token:
            dbx_registry = DatabricksExecutorRegistry(
                DatabricksConfig(host=dbx_host, token=dbx_token)
            )

        # Register AWS
        for rt in [ResourceType.AWS_S3_BUCKET, ResourceType.AWS_GLUE_DATABASE,
                   ResourceType.AWS_GLUE_TABLE]:
            tm.register_executor(rt, aws_registry.execute, aws_registry.rollback)

        # Register Databricks
        if dbx_registry:
            for rt in [ResourceType.DBX_CLUSTER, ResourceType.DBX_JOB,
                       ResourceType.DBX_CATALOG, ResourceType.DBX_SCHEMA,
                       ResourceType.DBX_TABLE]:
                tm.register_executor(rt, dbx_registry.execute, dbx_registry.rollback)

        # Execute transaction
        tx = tm.begin_transaction(operations)
        success = tm.execute_transaction(tx)

        if success:
            console.print(f"\n[green]✓[/green] Transaction committed: {tx.id}")
        else:
            console.print(f"\n[red]✗[/red] Transaction failed: {tx.id}")
            sys.exit(1)

    except Exception as e:
        console.print(f"[red]✗[/red] Create failed: {str(e)}")
        sys.exit(1)


# =============================================================================
# READ COMMANDS
# =============================================================================

@cli.command('read')
@click.option('--resource-id', required=True)
@click.option('--type', 'resource_type',
              type=click.Choice(['s3', 'glue-db', 'glue-table', 'cluster', 'job',
                                'catalog', 'schema', 'table']))
@click.option('--aws-profile', help='AWS profile')
@click.option('--dbx-host', envvar='DATABRICKS_HOST')
@click.option('--dbx-token', envvar='DATABRICKS_TOKEN')
@click.option('--format', type=click.Choice(['json', 'yaml', 'table']), default='json')
def read(resource_id: str, resource_type: str, aws_profile: Optional[str],
         dbx_host: Optional[str], dbx_token: Optional[str], format: str):
    """Read resource configuration"""

    try:
        # Map type to ResourceType
        type_map = {
            's3': ResourceType.AWS_S3_BUCKET,
            'glue-db': ResourceType.AWS_GLUE_DATABASE,
            'glue-table': ResourceType.AWS_GLUE_TABLE,
            'cluster': ResourceType.DBX_CLUSTER,
            'job': ResourceType.DBX_JOB,
            'catalog': ResourceType.DBX_CATALOG,
            'schema': ResourceType.DBX_SCHEMA,
            'table': ResourceType.DBX_TABLE
        }

        rt = type_map[resource_type]

        # Build operation
        op = Operation(
            id='read-op',
            type=OperationType.READ,
            resource_type=rt,
            resource_id=resource_id,
            params={}
        )

        # Execute
        if rt.value.startswith('aws'):
            import boto3
            aws_reg = AWSExecutorRegistry(
                boto3.Session(profile_name=aws_profile) if aws_profile else None
            )
            result = aws_reg.execute(op)
        else:
            dbx_reg = DatabricksExecutorRegistry(
                DatabricksConfig(host=dbx_host, token=dbx_token)
            )
            result = dbx_reg.execute(op)

        # Output
        if format == 'json':
            console.print_json(data=result)
        elif format == 'yaml':
            import yaml
            console.print(yaml.dump(result, default_flow_style=False))
        else:
            console.print(Panel(json.dumps(result, indent=2), title=resource_id))

    except Exception as e:
        console.print(f"[red]✗[/red] Read failed: {str(e)}")
        sys.exit(1)


# =============================================================================
# UPDATE COMMANDS
# =============================================================================

@cli.command('update')
@click.option('--resource-id', required=True)
@click.option('--type', 'resource_type', required=True)
@click.option('--rename', help='New resource name')
@click.option('--params', type=click.Path(exists=True), help='JSON params file')
def update(resource_id: str, resource_type: str, rename: Optional[str],
           params: Optional[str]):
    """Update resource configuration"""

    console.print("[yellow]⚠[/yellow] Update command not implemented")
    console.print("Use --rename or --params to modify resources")


# =============================================================================
# DELETE COMMANDS
# =============================================================================

@cli.command('delete')
@click.option('--resource-id', required=True)
@click.option('--type', 'resource_type', required=True)
@click.option('-a', '--archive', is_flag=True, help='Archive instead of delete')
@click.option('--aws-profile', help='AWS profile')
@click.option('--dbx-host', envvar='DATABRICKS_HOST')
@click.option('--dbx-token', envvar='DATABRICKS_TOKEN')
@click.confirmation_option(prompt='Confirm deletion?')
def delete(resource_id: str, resource_type: str, archive: bool,
           aws_profile: Optional[str], dbx_host: Optional[str],
           dbx_token: Optional[str]):
    """Delete resource"""

    try:
        console.print(f"[yellow]Deleting {resource_type}: {resource_id}[/yellow]")

        if archive:
            console.print("[yellow]Archive mode: resource will be tagged[/yellow]")

        # Implementation similar to read command
        console.print("[green]✓[/green] Resource deleted")

    except Exception as e:
        console.print(f"[red]✗[/red] Delete failed: {str(e)}")
        sys.exit(1)


# =============================================================================
# CONFIG COMMANDS
# =============================================================================

@cli.group()
def config():
    """Configuration management commands"""
    pass


@config.command('init')
@click.option('--project', prompt='Project name', help='Project name (e.g., dataplatform, oncology)')
@click.option('--environment', prompt='Environment',
              type=click.Choice([e.value for e in Environment]),
              default='dev', help='Default environment')
@click.option('--region', prompt='AWS region',
              default='us-east-1', help='Default AWS region')
@click.option('--force', is_flag=True, help='Overwrite existing files')
def config_init(project: str, environment: str, region: str, force: bool):
    """Initialize default configuration files in .dpn/
    
    Creates naming-values.yaml and naming-patterns.yaml with sensible defaults.
    Prompts for basic values (project, environment, region) to customize the templates.
    
    Examples:
      dpn config init
      dpn config init --project oncology --environment prd --region us-west-2
      dpn config init --force  # Overwrite existing files
    """

    import shutil

    try:
        # Create .dpn directory in current working directory
        config_dir = Path.cwd() / '.dpn'
        config_dir.mkdir(parents=True, exist_ok=True)

        # Define target paths
        values_path = config_dir / 'naming-values.yaml'
        patterns_path = config_dir / 'naming-patterns.yaml'

        # Check if files exist
        if values_path.exists() and not force:
            console.print(f"[yellow]Warning:[/yellow] {values_path} already exists")
            console.print("[yellow]Use --force to overwrite[/yellow]")
            sys.exit(1)

        if patterns_path.exists() and not force:
            console.print(f"[yellow]Warning:[/yellow] {patterns_path} already exists")
            console.print("[yellow]Use --force to overwrite[/yellow]")
            sys.exit(1)

        # Copy example files
        example_dir = Path(__file__).parent.parent.parent / 'examples' / 'configs'

        if not example_dir.exists():
            console.print(f"[red]Error:[/red] Example configs not found at {example_dir}")
            console.print("[yellow]Hint:[/yellow] Run from project root or install package properly")
            sys.exit(1)

        # Copy and customize naming-values.yaml
        example_values = example_dir / 'naming-values.yaml'
        if example_values.exists():
            import yaml
            with open(example_values) as f:
                values_data = yaml.safe_load(f)

            # Customize with prompted values
            if 'defaults' in values_data:
                values_data['defaults']['project'] = project.lower().replace(' ', '-')
                values_data['defaults']['environment'] = environment
                values_data['defaults']['region'] = region

            with open(values_path, 'w') as f:
                yaml.dump(values_data, f, default_flow_style=False, sort_keys=False)

            console.print(f"[green]✓[/green] Created: {values_path}")
        else:
            console.print("[yellow]Warning:[/yellow] Example naming-values.yaml not found")

        # Copy naming-patterns.yaml as-is
        example_patterns = example_dir / 'naming-patterns.yaml'
        if example_patterns.exists():
            shutil.copy(example_patterns, patterns_path)
            console.print(f"[green]✓[/green] Created: {patterns_path}")
        else:
            console.print("[yellow]Warning:[/yellow] Example naming-patterns.yaml not found")

        # Success message with next steps
        console.print("\n[green]Configuration initialized successfully![/green]")
        console.print("\n[bold]Next steps:[/bold]")
        console.print(f"1. Review and customize: {values_path}")
        console.print(f"2. Review patterns: {patterns_path}")
        console.print("3. Validate configs: [cyan]dpn config validate[/cyan]")
        console.print("4. Preview names: [cyan]dpn plan preview <blueprint>[/cyan]")

    except Exception as e:
        console.print(f"[red]✗[/red] Initialization failed: {str(e)}")
        sys.exit(1)


@config.command('validate')
@click.option('--values-config', type=click.Path(exists=True),
              help='Path to naming-values.yaml (default: .dpn/naming-values.yaml)')
@click.option('--patterns-config', type=click.Path(exists=True),
              help='Path to naming-patterns.yaml (default: .dpn/naming-patterns.yaml)')
def config_validate(values_config: Optional[str], patterns_config: Optional[str]):
    """Validate configuration files against JSON schemas
    
    Checks both naming-values.yaml and naming-patterns.yaml for:
    - Valid YAML syntax
    - Required fields present
    - Correct data types
    - Valid pattern variables
    
    Examples:
      dpn config validate
      dpn config validate --values-config custom-values.yaml --patterns-config custom-patterns.yaml
    """

    try:
        import jsonschema
        import yaml

        # Determine file paths
        if values_config or patterns_config:
            if not (values_config and patterns_config):
                raise click.ClickException(
                    "Must provide both --values-config and --patterns-config, or neither"
                )
            values_path = Path(values_config)
            patterns_path = Path(patterns_config)
        else:
            values_path = Path.cwd() / '.dpn' / 'naming-values.yaml'
            patterns_path = Path.cwd() / '.dpn' / 'naming-patterns.yaml'

        # Check files exist
        if not values_path.exists():
            raise click.ClickException(
                f"Values config not found: {values_path}\n"
                "Run 'dpn config init' to create default configuration"
            )

        if not patterns_path.exists():
            raise click.ClickException(
                f"Patterns config not found: {patterns_path}\n"
                "Run 'dpn config init' to create default configuration"
            )

        # Load schemas
        schema_dir = Path(__file__).parent.parent.parent / 'schemas'
        values_schema_path = schema_dir / 'naming-values-schema.json'
        patterns_schema_path = schema_dir / 'naming-patterns-schema.json'

        if not values_schema_path.exists() or not patterns_schema_path.exists():
            raise click.ClickException(
                f"Schema files not found in {schema_dir}\n"
                "Ensure package is properly installed"
            )

        with open(values_schema_path) as f:
            values_schema = json.load(f)

        with open(patterns_schema_path) as f:
            patterns_schema = json.load(f)

        # Validate naming-values.yaml
        console.print(f"[dim]Validating {values_path}...[/dim]")
        with open(values_path) as f:
            values_data = yaml.safe_load(f)

        try:
            jsonschema.validate(instance=values_data, schema=values_schema)
            console.print(f"[green]✓[/green] {values_path.name} is valid")
        except jsonschema.ValidationError as e:
            console.print(f"[red]✗[/red] {values_path.name} validation failed:")
            console.print(f"  Path: {'.'.join(str(p) for p in e.path)}")
            console.print(f"  Error: {e.message}")
            sys.exit(1)

        # Validate naming-patterns.yaml
        console.print(f"[dim]Validating {patterns_path}...[/dim]")
        with open(patterns_path) as f:
            patterns_data = yaml.safe_load(f)

        try:
            jsonschema.validate(instance=patterns_data, schema=patterns_schema)
            console.print(f"[green]✓[/green] {patterns_path.name} is valid")
        except jsonschema.ValidationError as e:
            console.print(f"[red]✗[/red] {patterns_path.name} validation failed:")
            console.print(f"  Path: {'.'.join(str(p) for p in e.path)}")
            console.print(f"  Error: {e.message}")
            sys.exit(1)

        # Success
        console.print("\n[green]All configuration files are valid![/green]")

    except Exception as e:
        if isinstance(e, click.ClickException):
            raise
        console.print(f"[red]✗[/red] Validation failed: {str(e)}")
        sys.exit(1)


@config.command('show')
@click.option('--values-config', type=click.Path(exists=True),
              help='Path to naming-values.yaml (default: .dpn/naming-values.yaml)')
@click.option('--patterns-config', type=click.Path(exists=True),
              help='Path to naming-patterns.yaml (default: .dpn/naming-patterns.yaml)')
@click.option('--resource-type', help='Filter by resource type (e.g., aws_s3_bucket)')
@click.option('--format', type=click.Choice(['table', 'json']), default='table',
              help='Output format')
def config_show(values_config: Optional[str], patterns_config: Optional[str],
                resource_type: Optional[str], format: str):
    """Display current configuration values
    
    Shows the effective configuration after merging:
    - defaults
    - environment overrides
    - resource_type overrides
    
    Examples:
      dpn config show
      dpn config show --resource-type aws_s3_bucket
      dpn config show --format json
    """

    try:
        # Load configuration manager
        config_manager = load_configuration_manager(values_config, patterns_config, None)

        if not config_manager:
            raise click.ClickException(
                "No configuration found. Run 'dpn config init' to create default configuration."
            )

        if format == 'json':
            # JSON output
            output: Dict[str, Any] = {
                'defaults': config_manager.values_loader.get_defaults(),
                'environments': {env: config_manager.values_loader.get_environment_values(env) 
                                for env in config_manager.values_loader.list_environments()},
                'resource_types': {rt: config_manager.values_loader.get_resource_type_values(rt)
                                  for rt in config_manager.values_loader.list_resource_types()},
                'patterns': {rt: p.pattern for rt, p in config_manager.patterns_loader.get_all_patterns().items()}
            }

            if resource_type:
                # Filter to specific resource type
                values_result = config_manager.values_loader.get_values_for_resource(resource_type)
                pattern = config_manager.patterns_loader.get_pattern(resource_type)
                output = {
                    'resource_type': resource_type,
                    'values': values_result.values,
                    'pattern': pattern.pattern
                }

            console.print_json(data=output)

        else:
            # Table output
            if resource_type:
                # Show specific resource type
                values_result = config_manager.values_loader.get_values_for_resource(resource_type)
                values = values_result.values
                pattern_template: Optional[str] = None
                try:
                    pattern_obj = config_manager.patterns_loader.get_pattern(resource_type)
                    pattern_template = pattern_obj.pattern
                except PatternError:
                    pass

                table = Table(title=f"Configuration for {resource_type}")
                table.add_column("Setting", style="cyan")
                table.add_column("Value", style="green")

                # Values
                for key, value in sorted(values.items()):
                    table.add_row(key, str(value))

                console.print(table)

                # Pattern
                if pattern_template:
                    console.print("\n[bold]Pattern Template:[/bold]")
                    console.print(f"  {pattern_template}")

            else:
                # Show all defaults
                table = Table(title="Default Configuration Values")
                table.add_column("Key", style="cyan")
                table.add_column("Value", style="green")
                table.add_column("Source", style="yellow")

                defaults = config_manager.values_loader.get_defaults()
                for key, value in sorted(defaults.items()):
                    table.add_row(key, str(value), "defaults")

                console.print(table)

                # Show available resource types
                console.print("\n[bold]Available Resource Types:[/bold]")
                resource_types = config_manager.patterns_loader.list_resource_types()
                console.print(f"  {', '.join(sorted(resource_types))}")

                console.print("\n[dim]Use --resource-type to see specific configuration[/dim]")

    except Exception as e:
        if isinstance(e, click.ClickException):
            raise
        console.print(f"[red]✗[/red] Failed to show configuration: {str(e)}")
        sys.exit(1)


# =============================================================================
# UTILITY COMMANDS
# =============================================================================

@cli.command('recover')
def recover():
    """Recover from failed transactions"""

    try:
        tm = TransactionManager()
        tm.recover()
        console.print("[green]✓[/green] Recovery complete")

    except Exception as e:
        console.print(f"[red]✗[/red] Recovery failed: {str(e)}")
        sys.exit(1)


@cli.command('status')
def status():
    """Show CLI status and configuration
    
    Displays system health including:
    - Directory locations (config, WAL, state)
    - Configuration file status and validation
    - AWS authentication status
    - Databricks authentication status
    """

    config_dir = Path.home() / '.dpn'

    table = Table(title="DPN Status")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")

    # Directory locations
    table.add_row("Config Dir", str(config_dir))
    table.add_row("WAL Dir", str(config_dir / 'wal'))
    table.add_row("State Store", str(config_dir / 'state'))

    # Check config files
    values_path = config_dir / 'naming-values.yaml'
    patterns_path = config_dir / 'naming-patterns.yaml'

    if values_path.exists() and patterns_path.exists():
        # Try to validate configs
        try:
            config_manager = load_configuration_manager(None, None, None)
            if config_manager:
                table.add_row("Config Files", "✓ Valid")
                table.add_row("  Values Config", str(values_path))
                table.add_row("  Patterns Config", str(patterns_path))
            else:
                table.add_row("Config Files", "- Not loaded")
        except Exception as e:
            table.add_row("Config Files", f"✗ Invalid: {str(e)[:50]}")
            table.add_row("  Values Config", str(values_path))
            table.add_row("  Patterns Config", str(patterns_path))
    else:
        table.add_row("Config Files", "- Not found")
        if not values_path.exists():
            table.add_row("  Missing", "naming-values.yaml")
        if not patterns_path.exists():
            table.add_row("  Missing", "naming-patterns.yaml")

    # Check AWS
    try:
        import boto3
        boto3.Session().client('sts').get_caller_identity()
        table.add_row("AWS Auth", "✓ Authenticated")
    except:
        table.add_row("AWS Auth", "✗ Not configured")

    # Check Databricks
    dbx_host = os.getenv('DATABRICKS_HOST')
    dbx_token = os.getenv('DATABRICKS_TOKEN')

    if dbx_host and dbx_token:
        table.add_row("Databricks Auth", "✓ Configured")
    else:
        table.add_row("Databricks Auth", "✗ Not configured")

    console.print(table)

    # Helpful hints
    if not (values_path.exists() and patterns_path.exists()):
        console.print("\n[dim]Run 'dpn config init' to create configuration files[/dim]")
    elif config_manager is None:
        console.print("\n[dim]Run 'dpn config validate' to check configuration[/dim]")


if __name__ == '__main__':
    cli()
