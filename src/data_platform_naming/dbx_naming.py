#!/usr/bin/env python3
"""
Databricks CLI Resource Naming Module
Automated naming convention generator for Databricks resources
Integrates with existing AWS naming conventions
"""

import re
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

# Import ConfigurationManager for config-based name generation
try:
    from .config.configuration_manager import ConfigurationManager
except ImportError:
    ConfigurationManager = None  # Make optional for backwards compatibility


class DatabricksResourceType(Enum):
    """Databricks resource types with naming patterns"""
    WORKSPACE = "workspace"
    CLUSTER = "cluster"
    JOB = "job"
    NOTEBOOK = "notebook"
    REPO = "repo"
    PIPELINE = "pipeline"
    SQL_WAREHOUSE = "sql_warehouse"
    CATALOG = "catalog"
    SCHEMA = "schema"
    TABLE = "table"
    VOLUME = "volume"
    SECRET_SCOPE = "secret_scope"
    INSTANCE_POOL = "instance_pool"
    POLICY = "policy"
    TOKEN = "token"


@dataclass
class DatabricksNamingConfig:
    """Configuration for Databricks naming conventions"""
    environment: str  # dev, stg, prd
    project: str
    region: str  # us-east-1, eu-west-1, etc.
    team: Optional[str] = None
    cost_center: Optional[str] = None
    data_classification: Optional[str] = None  # public, internal, confidential, restricted


class DatabricksNamingGenerator:
    """Generate standardized names for Databricks resources"""
    
    # Maximum lengths for different resource types
    MAX_LENGTHS = {
        DatabricksResourceType.WORKSPACE: 64,
        DatabricksResourceType.CLUSTER: 100,
        DatabricksResourceType.JOB: 100,
        DatabricksResourceType.NOTEBOOK: 256,
        DatabricksResourceType.REPO: 100,
        DatabricksResourceType.PIPELINE: 100,
        DatabricksResourceType.SQL_WAREHOUSE: 64,
        DatabricksResourceType.CATALOG: 255,
        DatabricksResourceType.SCHEMA: 255,
        DatabricksResourceType.TABLE: 255,
        DatabricksResourceType.VOLUME: 255,
        DatabricksResourceType.SECRET_SCOPE: 128,
        DatabricksResourceType.INSTANCE_POOL: 100,
        DatabricksResourceType.POLICY: 100,
        DatabricksResourceType.TOKEN: 100,
    }
    
    # Allowed characters per resource type
    ALLOWED_CHARS = {
        DatabricksResourceType.CATALOG: r'^[a-zA-Z0-9_]+$',
        DatabricksResourceType.SCHEMA: r'^[a-zA-Z0-9_]+$',
        DatabricksResourceType.TABLE: r'^[a-zA-Z0-9_]+$',
        DatabricksResourceType.VOLUME: r'^[a-zA-Z0-9_]+$',
    }
    
    def __init__(self, 
                 config: DatabricksNamingConfig,
                 configuration_manager: Optional['ConfigurationManager'] = None,
                 use_config: bool = False):
        """
        Initialize Databricks naming generator.
        
        Args:
            config: Databricks naming configuration
            configuration_manager: Optional configuration manager for pattern-based generation
            use_config: If True, use ConfigurationManager for name generation
        
        Raises:
            ValueError: If use_config=True but configuration_manager not provided
            ValueError: If required patterns missing from configuration
        """
        self.config = config
        self.configuration_manager = configuration_manager
        self.use_config = use_config
        
        self._validate_config()
        
        if use_config:
            if not configuration_manager:
                raise ValueError("configuration_manager required when use_config=True")
    
    def _validate_config(self):
        """Validate configuration parameters"""
        if self.config.environment not in ['dev', 'stg', 'prd']:
            raise ValueError(f"Invalid environment: {self.config.environment}")
        
        if not re.match(r'^[a-z0-9-]+$', self.config.project):
            raise ValueError(f"Invalid project name: {self.config.project}")
    
    
    def _generate_with_config(self,
                             resource_type: str,
                             method_params: Dict[str, Any],
                             metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate resource name using ConfigurationManager.
        
        Args:
            resource_type: Databricks resource type (e.g., 'databricks_cluster')
            method_params: Parameters from the calling method
            metadata: Optional blueprint metadata for value precedence
        
        Returns:
            Generated resource name
        
        Raises:
            ValueError: If name generation fails
            NotImplementedError: If use_config=False
        """
        if not self.use_config:
            raise NotImplementedError(
                "Config-based generation required. Set use_config=True and provide "
                "ConfigurationManager with pattern definitions."
            )
        
        # Merge config values with method params
        values = {
            'environment': self.config.environment,
            'project': self.config.project,
            'region': self.config.region,
        }
        
        if self.config.team:
            values['team'] = self.config.team
        if self.config.cost_center:
            values['cost_center'] = self.config.cost_center
        if self.config.data_classification:
            values['data_classification'] = self.config.data_classification
        
        # Add method-specific parameters
        values.update(method_params)
        
        # Add metadata if provided (highest precedence)
        if metadata:
            values.update(metadata)
        
        # Generate name using ConfigurationManager
        result = self.configuration_manager.generate_name(
            resource_type=resource_type,
            environment=self.config.environment,
            blueprint_metadata=metadata,
            value_overrides=values
        )
        
        if not result.is_valid:
            raise ValueError(f"Generated invalid name: {', '.join(result.validation_errors)}")
        
        return result.name
    
    def _sanitize_name(self, name: str, resource_type: DatabricksResourceType) -> str:
        """Sanitize name based on resource type constraints"""
        if resource_type in self.ALLOWED_CHARS:
            # Unity Catalog objects: only alphanumeric and underscore
            name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        else:
            # Other resources: alphanumeric, dash, underscore
            name = re.sub(r'[^a-zA-Z0-9_-]', '-', name)
        
        # Remove consecutive special characters
        name = re.sub(r'[-_]+', lambda m: m.group()[0], name)
        
        # Ensure doesn't start/end with special characters
        name = name.strip('-_')
        
        return name
    
    def _truncate_name(self, name: str, resource_type: DatabricksResourceType) -> str:
        """Truncate name to maximum allowed length"""
        max_length = self.MAX_LENGTHS[resource_type]
        if len(name) <= max_length:
            return name
        
        # Truncate intelligently, preserving suffix
        suffix_parts = name.split('-')[-2:]  # Keep last 2 segments
        suffix = '-'.join(suffix_parts)
        prefix_length = max_length - len(suffix) - 1
        
        if prefix_length < 10:
            return name[:max_length]
        
        prefix = name[:prefix_length]
        return f"{prefix}-{suffix}"
    
    def generate_workspace_name(self, 
                               purpose: str = "data",
                               metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate Databricks workspace name.
        
        Args:
            purpose: Workspace purpose (data, analytics, ml, etc.)
            metadata: Optional blueprint metadata for value precedence
        
        Returns:
            Generated workspace name
        
        Raises:
            ValueError: If name generation fails
            NotImplementedError: If use_config=False
        
        Example:
            >>> gen = DatabricksNamingGenerator(config, config_mgr, use_config=True)
            >>> name = gen.generate_workspace_name('analytics')
            >>> print(name)
            'dbx-dataplatform-analytics-prd-useast1'
        """
        params = {'purpose': purpose}
        return self._generate_with_config(
            resource_type='dbx_workspace',
            method_params=params,
            metadata=metadata
        )
    
    def generate_cluster_name(self, 
                            workload: str,
                            cluster_type: str = "shared",
                            version: Optional[str] = None,
                            metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate Databricks cluster name.
        
        Args:
            workload: Workload identifier (etl, ml, analytics, etc.)
            cluster_type: shared, dedicated, or job
            version: Optional version suffix
            metadata: Optional blueprint metadata for value precedence
        
        Returns:
            Generated cluster name
        
        Raises:
            ValueError: If name generation fails
            NotImplementedError: If use_config=False
        
        Example:
            >>> gen = DatabricksNamingGenerator(config, config_mgr, use_config=True)
            >>> name = gen.generate_cluster_name('etl', 'shared')
            >>> print(name)
            'dataplatform-etl-shared-prd'
        """
        params = {
            'workload': workload,
            'cluster_type': cluster_type,
        }
        if version:
            params['version'] = version
        
        return self._generate_with_config(
            resource_type='dbx_cluster',
            method_params=params,
            metadata=metadata
        )
    
    def generate_job_name(self,
                         job_type: str,
                         purpose: str,
                         schedule: Optional[str] = None,
                         metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate Databricks job name.
        
        Args:
            job_type: batch, streaming, ml, etc.
            purpose: Business purpose or data domain
            schedule: Optional schedule indicator (daily, hourly, etc.)
            metadata: Optional blueprint metadata for value precedence
        
        Returns:
            Generated job name
        
        Raises:
            ValueError: If name generation fails
            NotImplementedError: If use_config=False
        
        Example:
            >>> gen = DatabricksNamingGenerator(config, config_mgr, use_config=True)
            >>> name = gen.generate_job_name('batch', 'customer-load', 'daily')
            >>> print(name)
            'dataplatform-batch-customer-load-prd-daily'
        """
        params = {
            'job_type': job_type,
            'purpose': purpose,
        }
        if schedule:
            params['schedule'] = schedule
        
        return self._generate_with_config(
            resource_type='dbx_job',
            method_params=params,
            metadata=metadata
        )
    
    def generate_notebook_path(self,
                              domain: str,
                              purpose: str,
                              notebook_name: str,
                              metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate Databricks notebook path.
        
        Args:
            domain: Data domain (finance, marketing, etc.)
            purpose: etl, analysis, ml, etc.
            notebook_name: Descriptive notebook name
            metadata: Optional blueprint metadata for value precedence
        
        Returns:
            Generated notebook path (starts with /)
        
        Raises:
            ValueError: If name generation fails
            NotImplementedError: If use_config=False
        
        Example:
            >>> gen = DatabricksNamingGenerator(config, config_mgr, use_config=True)
            >>> path = gen.generate_notebook_path('finance', 'etl', 'customer-load')
            >>> print(path)
            '/dataplatform/finance/etl/prd/customer-load'
        """
        params = {
            'domain': domain,
            'purpose': purpose,
            'notebook_name': notebook_name,
        }
        return self._generate_with_config(
            resource_type='dbx_notebook_path',
            method_params=params,
            metadata=metadata
        )
    
    def generate_repo_name(self, 
                          repo_purpose: str,
                          metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate Git repo integration name.
        
        Args:
            repo_purpose: Repository purpose (code, notebooks, pipelines, etc.)
            metadata: Optional blueprint metadata for value precedence
        
        Returns:
            Generated repo name
        
        Raises:
            ValueError: If name generation fails
            NotImplementedError: If use_config=False
        
        Example:
            >>> gen = DatabricksNamingGenerator(config, config_mgr, use_config=True)
            >>> name = gen.generate_repo_name('etl')
            >>> print(name)
            'dataplatform-etl-prd'
        """
        params = {'repo_purpose': repo_purpose}
        return self._generate_with_config(
            resource_type='dbx_repo',
            method_params=params,
            metadata=metadata
        )
    
    def generate_pipeline_name(self,
                              source: str,
                              target: str,
                              pipeline_type: str = "dlt",
                              metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate Delta Live Tables pipeline name.
        
        Args:
            source: Source system or data domain
            target: Target table/dataset
            pipeline_type: dlt (Delta Live Tables) or other
            metadata: Optional blueprint metadata for value precedence
        
        Returns:
            Generated pipeline name
        
        Raises:
            ValueError: If name generation fails
            NotImplementedError: If use_config=False
        
        Example:
            >>> gen = DatabricksNamingGenerator(config, config_mgr, use_config=True)
            >>> name = gen.generate_pipeline_name('kafka', 'events', 'dlt')
            >>> print(name)
            'dataplatform-dlt-kafka-events-prd'
        """
        params = {
            'source': source,
            'target': target,
            'pipeline_type': pipeline_type,
        }
        return self._generate_with_config(
            resource_type='dbx_pipeline',
            method_params=params,
            metadata=metadata
        )
    
    def generate_sql_warehouse_name(self,
                                   size: str = "medium",
                                   purpose: str = "analytics",
                                   metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate SQL warehouse name.
        
        Args:
            size: small, medium, large, xlarge
            purpose: analytics, reporting, adhoc
            metadata: Optional blueprint metadata for value precedence
        
        Returns:
            Generated SQL warehouse name
        
        Raises:
            ValueError: If name generation fails
            NotImplementedError: If use_config=False
        
        Example:
            >>> gen = DatabricksNamingGenerator(config, config_mgr, use_config=True)
            >>> name = gen.generate_sql_warehouse_name('medium', 'analytics')
            >>> print(name)
            'dataplatform-sql-analytics-medium-prd'
        """
        params = {
            'size': size,
            'purpose': purpose,
        }
        return self._generate_with_config(
            resource_type='dbx_sql_warehouse',
            method_params=params,
            metadata=metadata
        )
    
    def generate_catalog_name(self, 
                             catalog_type: str = "main",
                             metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate Unity Catalog catalog name.
        
        Args:
            catalog_type: main, dev, test, sandbox
            metadata: Optional blueprint metadata for value precedence
        
        Returns:
            Generated catalog name (uses underscores)
        
        Raises:
            ValueError: If name generation fails
            NotImplementedError: If use_config=False
        
        Example:
            >>> gen = DatabricksNamingGenerator(config, config_mgr, use_config=True)
            >>> name = gen.generate_catalog_name('main')
            >>> print(name)
            'dataplatform_main_prd'
        """
        params = {'catalog_type': catalog_type}
        return self._generate_with_config(
            resource_type='dbx_catalog',
            method_params=params,
            metadata=metadata
        )
    
    def generate_schema_name(self,
                           domain: str,
                           layer: str = "bronze",
                           metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate Unity Catalog schema name.
        
        Args:
            domain: Data domain (finance, marketing, etc.)
            layer: bronze, silver, gold (medallion architecture)
            metadata: Optional blueprint metadata for value precedence
        
        Returns:
            Generated schema name (uses underscores)
        
        Raises:
            ValueError: If name generation fails
            NotImplementedError: If use_config=False
        
        Example:
            >>> gen = DatabricksNamingGenerator(config, config_mgr, use_config=True)
            >>> name = gen.generate_schema_name('finance', 'gold')
            >>> print(name)
            'finance_gold'
        """
        params = {
            'domain': domain,
            'layer': layer,
        }
        return self._generate_with_config(
            resource_type='dbx_schema',
            method_params=params,
            metadata=metadata
        )
    
    def generate_table_name(self,
                          entity: str,
                          table_type: str = "fact",
                          metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate Unity Catalog table name.
        
        Args:
            entity: Business entity (customers, orders, etc.)
            table_type: fact, dim, bridge, etc.
            metadata: Optional blueprint metadata for value precedence
        
        Returns:
            Generated table name (uses underscores with type prefix)
        
        Raises:
            ValueError: If name generation fails
            NotImplementedError: If use_config=False
        
        Example:
            >>> gen = DatabricksNamingGenerator(config, config_mgr, use_config=True)
            >>> name = gen.generate_table_name('customers', 'dim')
            >>> print(name)
            'dim_customers'
        """
        params = {
            'entity': entity,
            'table_type': table_type,
        }
        return self._generate_with_config(
            resource_type='dbx_table',
            method_params=params,
            metadata=metadata
        )
    
    def generate_volume_name(self,
                           purpose: str,
                           data_type: str = "raw",
                           metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate Unity Catalog volume name.
        
        Args:
            purpose: Business purpose
            data_type: raw, processed, archive
            metadata: Optional blueprint metadata for value precedence
        
        Returns:
            Generated volume name (uses underscores)
        
        Raises:
            ValueError: If name generation fails
            NotImplementedError: If use_config=False
        
        Example:
            >>> gen = DatabricksNamingGenerator(config, config_mgr, use_config=True)
            >>> name = gen.generate_volume_name('landing', 'raw')
            >>> print(name)
            'raw_landing'
        """
        params = {
            'purpose': purpose,
            'data_type': data_type,
        }
        return self._generate_with_config(
            resource_type='dbx_volume',
            method_params=params,
            metadata=metadata
        )
    
    def generate_secret_scope_name(self, 
                                  purpose: str = "general",
                                  metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate secret scope name.
        
        Args:
            purpose: Secret scope purpose (general, aws, azure, etc.)
            metadata: Optional blueprint metadata for value precedence
        
        Returns:
            Generated secret scope name
        
        Raises:
            ValueError: If name generation fails
            NotImplementedError: If use_config=False
        
        Example:
            >>> gen = DatabricksNamingGenerator(config, config_mgr, use_config=True)
            >>> name = gen.generate_secret_scope_name('aws')
            >>> print(name)
            'dataplatform-aws-prd'
        """
        params = {'purpose': purpose}
        return self._generate_with_config(
            resource_type='dbx_secret_scope',
            method_params=params,
            metadata=metadata
        )
    
    def generate_instance_pool_name(self,
                                   node_type: str,
                                   purpose: str = "general",
                                   metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate instance pool name.
        
        Args:
            node_type: Node type identifier (compute, memory, etc.)
            purpose: general, ml, etl
            metadata: Optional blueprint metadata for value precedence
        
        Returns:
            Generated instance pool name
        
        Raises:
            ValueError: If name generation fails
            NotImplementedError: If use_config=False
        
        Example:
            >>> gen = DatabricksNamingGenerator(config, config_mgr, use_config=True)
            >>> name = gen.generate_instance_pool_name('compute', 'etl')
            >>> print(name)
            'dataplatform-pool-compute-etl-prd'
        """
        params = {
            'node_type': node_type,
            'purpose': purpose,
        }
        return self._generate_with_config(
            resource_type='dbx_instance_pool',
            method_params=params,
            metadata=metadata
        )
    
    def generate_policy_name(self,
                           policy_type: str,
                           target: str = "cluster",
                           metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate policy name.
        
        Args:
            policy_type: security, cost, performance
            target: cluster, sql, job
            metadata: Optional blueprint metadata for value precedence
        
        Returns:
            Generated policy name
        
        Raises:
            ValueError: If name generation fails
            NotImplementedError: If use_config=False
        
        Example:
            >>> gen = DatabricksNamingGenerator(config, config_mgr, use_config=True)
            >>> name = gen.generate_policy_name('security', 'cluster')
            >>> print(name)
            'dataplatform-cluster-security-prd'
        """
        params = {
            'policy_type': policy_type,
            'target': target,
        }
        return self._generate_with_config(
            resource_type='dbx_policy',
            method_params=params,
            metadata=metadata
        )
    
    def generate_standard_tags(self, 
                              resource_type: DatabricksResourceType,
                              additional_tags: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Generate standard tags for Databricks resources"""
        tags = {
            "Environment": self.config.environment,
            "Project": self.config.project,
            "ManagedBy": "terraform",
            "ResourceType": resource_type.value,
        }
        
        if self.config.team:
            tags["Team"] = self.config.team
        
        if self.config.cost_center:
            tags["CostCenter"] = self.config.cost_center
        
        if self.config.data_classification:
            tags["DataClassification"] = self.config.data_classification
        
        if additional_tags:
            tags.update(additional_tags)
        
        return tags
    
    def generate_full_table_reference(self,
                                     catalog_type: str,
                                     domain: str,
                                     layer: str,
                                     entity: str,
                                     table_type: str = "fact",
                                     metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate fully qualified Unity Catalog table reference.
        
        Args:
            catalog_type: main, dev, test, sandbox
            domain: Data domain (finance, marketing, etc.)
            layer: bronze, silver, gold (medallion architecture)
            entity: Business entity (customers, orders, etc.)
            table_type: fact, dim, bridge, etc.
            metadata: Optional blueprint metadata for value precedence
        
        Returns:
            Fully qualified table name (catalog.schema.table)
        
        Raises:
            ValueError: If name generation fails
            NotImplementedError: If use_config=False
        
        Example:
            >>> gen = DatabricksNamingGenerator(config, config_mgr, use_config=True)
            >>> ref = gen.generate_full_table_reference('main', 'finance', 'gold', 'customers', 'dim')
            >>> print(ref)
            'dataplatform_main_prd.finance_gold.dim_customers'
        """
        catalog = self.generate_catalog_name(catalog_type, metadata)
        schema = self.generate_schema_name(domain, layer, metadata)
        table = self.generate_table_name(entity, table_type, metadata)
        return f"{catalog}.{schema}.{table}"


class DatabricksNamingCLI:
    """CLI interface for Databricks naming generator"""
    
    def __init__(self):
        self.generator = None
    
    def configure(self,
                 environment: str,
                 project: str,
                 region: str,
                 team: Optional[str] = None,
                 cost_center: Optional[str] = None) -> None:
        """Configure the naming generator"""
        config = DatabricksNamingConfig(
            environment=environment,
            project=project,
            region=region,
            team=team,
            cost_center=cost_center
        )
        self.generator = DatabricksNamingGenerator(config)
        print(f"✓ Configured naming generator for {project} in {environment}")
    
    def generate_workspace(self, purpose: str = "data") -> str:
        """Generate workspace name"""
        if not self.generator:
            raise ValueError("Generator not configured. Run configure() first.")
        return self.generator.generate_workspace_name(purpose)
    
    def generate_cluster(self,
                        workload: str,
                        cluster_type: str = "shared") -> str:
        """Generate cluster name"""
        if not self.generator:
            raise ValueError("Generator not configured. Run configure() first.")
        return self.generator.generate_cluster_name(workload, cluster_type)
    
    def generate_job(self,
                    job_type: str,
                    purpose: str,
                    schedule: Optional[str] = None) -> str:
        """Generate job name"""
        if not self.generator:
            raise ValueError("Generator not configured. Run configure() first.")
        return self.generator.generate_job_name(job_type, purpose, schedule)
    
    def generate_unity_catalog_stack(self,
                                    catalog_type: str,
                                    domain: str,
                                    layer: str,
                                    entity: str) -> Dict[str, str]:
        """Generate complete Unity Catalog naming stack"""
        if not self.generator:
            raise ValueError("Generator not configured. Run configure() first.")
        
        return {
            "catalog": self.generator.generate_catalog_name(catalog_type),
            "schema": self.generator.generate_schema_name(domain, layer),
            "table": self.generator.generate_table_name(entity),
            "full_reference": self.generator.generate_full_table_reference(
                catalog_type, domain, layer, entity
            )
        }
    
    def export_naming_reference(self, output_file: str = "dbx_naming.json") -> None:
        """Export naming examples as JSON reference"""
        if not self.generator:
            raise ValueError("Generator not configured. Run configure() first.")
        
        reference = {
            "configuration": {
                "environment": self.generator.config.environment,
                "project": self.generator.config.project,
                "region": self.generator.config.region,
            },
            "examples": {
                "workspace": self.generator.generate_workspace_name(),
                "cluster_etl": self.generator.generate_cluster_name("etl", "shared"),
                "cluster_ml": self.generator.generate_cluster_name("ml", "dedicated"),
                "job_batch": self.generator.generate_job_name("batch", "customer-load", "daily"),
                "sql_warehouse": self.generator.generate_sql_warehouse_name("medium", "analytics"),
                "catalog": self.generator.generate_catalog_name(),
                "schema": self.generator.generate_schema_name("finance", "gold"),
                "table": self.generator.generate_table_name("customers", "dim"),
                "full_table": self.generator.generate_full_table_reference(
                    "main", "finance", "gold", "customers", "dim"
                ),
                "secret_scope": self.generator.generate_secret_scope_name("aws"),
                "instance_pool": self.generator.generate_instance_pool_name("compute", "etl"),
            }
        }
        
        with open(output_file, 'w') as f:
            json.dump(reference, f, indent=2)
        
        print(f"✓ Exported naming reference to {output_file}")


# Example usage
if __name__ == "__main__":
    # Initialize CLI
    cli = DatabricksNamingCLI()
    
    # Configure for production environment
    cli.configure(
        environment="prd",
        project="dataplatform",
        region="us-east-1",
        team="data-engineering",
        cost_center="IT-1001"
    )
    
    # Generate workspace name
    print("\n=== Workspace ===")
    workspace = cli.generate_workspace("analytics")
    print(f"Workspace: {workspace}")
    
    # Generate cluster names
    print("\n=== Clusters ===")
    etl_cluster = cli.generate_cluster("etl", "shared")
    ml_cluster = cli.generate_cluster("ml", "dedicated")
    print(f"ETL Cluster: {etl_cluster}")
    print(f"ML Cluster: {ml_cluster}")
    
    # Generate job names
    print("\n=== Jobs ===")
    batch_job = cli.generate_job("batch", "customer-ingestion", "daily")
    streaming_job = cli.generate_job("streaming", "events-processing")
    print(f"Batch Job: {batch_job}")
    print(f"Streaming Job: {streaming_job}")
    
    # Generate Unity Catalog stack
    print("\n=== Unity Catalog ===")
    uc_stack = cli.generate_unity_catalog_stack(
        catalog_type="main",
        domain="finance",
        layer="gold",
        entity="customers"
    )
    print(f"Catalog: {uc_stack['catalog']}")
    print(f"Schema: {uc_stack['schema']}")
    print(f"Table: {uc_stack['table']}")
    print(f"Full Reference: {uc_stack['full_reference']}")
    
    # Export reference
    print("\n=== Export ===")
    cli.export_naming_reference()
