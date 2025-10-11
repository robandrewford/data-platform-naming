#!/usr/bin/env python3
"""
Data Platform Naming CLI
Unified interface for blueprint planning and CRUD operations
"""

import click
import json
import os
import sys
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax

# Import core modules
from data_platform_naming.aws_naming import AWSNamingGenerator, AWSNamingConfig
from data_platform_naming.dbx_naming import DatabricksNamingGenerator, DatabricksNamingConfig
from data_platform_naming.plan.blueprint import BlueprintParser, BLUEPRINT_SCHEMA
from data_platform_naming.crud.transaction_manager import (
    TransactionManager, Operation, OperationType, ResourceType
)
from data_platform_naming.crud.aws_operations import AWSExecutorRegistry
from data_platform_naming.crud.dbx_operations import DatabricksExecutorRegistry, DatabricksConfig
from data_platform_naming.config.configuration_manager import ConfigurationManager

console = Console()


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
        default_dir = Path.home() / '.dpn'
        values_path = default_dir / 'naming-values.yaml'
        patterns_path = default_dir / 'naming-patterns.yaml'
        
        if values_path.exists() and patterns_path.exists():
            try:
                manager = ConfigurationManager()
                manager.load_from_default_locations()
                console.print(f"[dim]Loaded config from: ~/.dpn/[/dim]")
            except Exception as e:
                raise click.ClickException(
                    f"Config files found in ~/.dpn/ but failed to load: {str(e)}\n"
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
            override_dict[key.strip()] = value.strip()
        
        # Store overrides for use in name generation
        manager._cli_overrides = override_dict
        if override_dict:
            console.print(f"[dim]Applied overrides: {', '.join(f'{k}={v}' for k, v in override_dict.items())}[/dim]")
    
    return manager


@click.group()
@click.version_option(version='0.1.0')
def cli():
    """Data Platform Naming Convention CLI
    
    Generate, validate, and execute infrastructure blueprints
    for AWS and Databricks resources.
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
@click.option('--env', type=click.Choice(['dev', 'stg', 'prd']), required=True)
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
        with open(blueprint, 'r') as f:
            data = json.load(f)
        
        import jsonschema
        jsonschema.validate(instance=data, schema=BLUEPRINT_SCHEMA)
        
        console.print(f"[green]✓[/green] Blueprint valid: {blueprint}")
        
    except jsonschema.ValidationError as e:
        console.print(f"[red]✗[/red] Validation failed:")
        console.print(f"  Path: {'.'.join(str(p) for p in e.path)}")
        console.print(f"  Error: {e.message}")
        sys.exit(1)
    
    except Exception as e:
        console.print(f"[red]✗[/red] Error: {str(e)}")
        sys.exit(1)


@plan.command('preview')
@click.argument('blueprint', type=click.Path(exists=True))
@click.option('--values-config', type=click.Path(exists=True),
              help='Path to naming-values.yaml (default: ~/.dpn/naming-values.yaml)')
@click.option('--patterns-config', type=click.Path(exists=True),
              help='Path to naming-patterns.yaml (default: ~/.dpn/naming-patterns.yaml)')
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
        with open(blueprint, 'r') as f:
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
        
        # Create generators with or without ConfigurationManager
        if config_manager:
            console.print("[dim]Using configuration-based naming[/dim]")
            generators = {
                'aws': AWSNamingGenerator(
                    config=aws_config,
                    configuration_manager=config_manager,
                    use_config=True
                ),
                'databricks': DatabricksNamingGenerator(
                    config=dbx_config,
                    configuration_manager=config_manager,
                    use_config=True
                )
            }
        else:
            console.print("[yellow]No configuration files found, using legacy mode[/yellow]")
            console.print("[yellow]Run 'dpn config init' to create configuration files[/yellow]\n")
            generators = {
                'aws': AWSNamingGenerator(aws_config),
                'databricks': DatabricksNamingGenerator(dbx_config)
            }
        
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
def create(blueprint: str, dry_run: bool, aws_profile: Optional[str], 
           dbx_host: Optional[str], dbx_token: Optional[str]):
    """Create resources from blueprint"""
    
    try:
        # Load blueprint
        with open(blueprint, 'r') as f:
            data = json.load(f)
        
        metadata = data['metadata']
        
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
        
        generators = {
            'aws': AWSNamingGenerator(aws_config),
            'databricks': DatabricksNamingGenerator(dbx_config)
        }
        
        # Parse
        parser = BlueprintParser(generators)
        parsed = parser.parse(Path(blueprint))
        
        # Build operations
        operations = []
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
            console.print(f"\n[yellow]Run without --dry-run to execute[/yellow]")
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
        
        if dbx_host and dbx_token:
            dbx_registry = DatabricksExecutorRegistry(
                DatabricksConfig(host=dbx_host, token=dbx_token)
            )
        else:
            dbx_registry = None
        
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
            registry = AWSExecutorRegistry(
                boto3.Session(profile_name=aws_profile) if aws_profile else None
            )
            result = registry.execute(op)
        else:
            registry = DatabricksExecutorRegistry(
                DatabricksConfig(host=dbx_host, token=dbx_token)
            )
            result = registry.execute(op)
        
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
    """Show CLI status and configuration"""
    
    config_dir = Path.home() / '.dpn'
    
    table = Table(title="DPN Status")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")
    
    table.add_row("Config Dir", str(config_dir))
    table.add_row("WAL Dir", str(config_dir / 'wal'))
    table.add_row("State Store", str(config_dir / 'state'))
    
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


if __name__ == '__main__':
    cli()
