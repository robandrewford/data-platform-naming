#!/usr/bin/env python3
"""
Databricks CLI Resource Naming Module
Automated naming convention generator for Databricks resources
Integrates with existing AWS naming conventions
"""

import re
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


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
    
    def __init__(self, config: DatabricksNamingConfig):
        self.config = config
        self._validate_config()
    
    def _validate_config(self):
        """Validate configuration parameters"""
        if self.config.environment not in ['dev', 'stg', 'prd']:
            raise ValueError(f"Invalid environment: {self.config.environment}")
        
        if not re.match(r'^[a-z0-9-]+$', self.config.project):
            raise ValueError(f"Invalid project name: {self.config.project}")
    
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
    
    def generate_workspace_name(self, purpose: str = "data") -> str:
        """Generate workspace name"""
        parts = [
            "dbx",
            self.config.project,
            purpose,
            self.config.environment,
            self.config.region.replace('-', '')
        ]
        name = '-'.join(parts)
        return self._truncate_name(
            self._sanitize_name(name, DatabricksResourceType.WORKSPACE),
            DatabricksResourceType.WORKSPACE
        )
    
    def generate_cluster_name(self, 
                            workload: str,
                            cluster_type: str = "shared",
                            version: Optional[str] = None) -> str:
        """Generate cluster name
        
        Args:
            workload: Workload identifier (etl, ml, analytics, etc.)
            cluster_type: shared, dedicated, or job
            version: Optional version suffix
        """
        parts = [
            self.config.project,
            workload,
            cluster_type,
            self.config.environment
        ]
        if version:
            parts.append(f"v{version}")
        
        name = '-'.join(parts)
        return self._truncate_name(
            self._sanitize_name(name, DatabricksResourceType.CLUSTER),
            DatabricksResourceType.CLUSTER
        )
    
    def generate_job_name(self,
                         job_type: str,
                         purpose: str,
                         schedule: Optional[str] = None) -> str:
        """Generate job name
        
        Args:
            job_type: batch, streaming, ml, etc.
            purpose: Business purpose or data domain
            schedule: Optional schedule indicator (daily, hourly, etc.)
        """
        parts = [
            self.config.project,
            job_type,
            purpose,
            self.config.environment
        ]
        if schedule:
            parts.append(schedule)
        
        name = '-'.join(parts)
        return self._truncate_name(
            self._sanitize_name(name, DatabricksResourceType.JOB),
            DatabricksResourceType.JOB
        )
    
    def generate_notebook_path(self,
                              domain: str,
                              purpose: str,
                              notebook_name: str) -> str:
        """Generate notebook path
        
        Args:
            domain: Data domain (finance, marketing, etc.)
            purpose: etl, analysis, ml, etc.
            notebook_name: Descriptive notebook name
        """
        parts = [
            self.config.project,
            domain,
            purpose,
            self.config.environment,
            notebook_name
        ]
        path = '/'.join(parts)
        return f"/{path}"
    
    def generate_repo_name(self, repo_purpose: str) -> str:
        """Generate Git repo integration name"""
        parts = [
            self.config.project,
            repo_purpose,
            self.config.environment
        ]
        name = '-'.join(parts)
        return self._truncate_name(
            self._sanitize_name(name, DatabricksResourceType.REPO),
            DatabricksResourceType.REPO
        )
    
    def generate_pipeline_name(self,
                              source: str,
                              target: str,
                              pipeline_type: str = "dlt") -> str:
        """Generate Delta Live Tables pipeline name
        
        Args:
            source: Source system or data domain
            target: Target table/dataset
            pipeline_type: dlt (Delta Live Tables) or other
        """
        parts = [
            self.config.project,
            pipeline_type,
            source,
            target,
            self.config.environment
        ]
        name = '-'.join(parts)
        return self._truncate_name(
            self._sanitize_name(name, DatabricksResourceType.PIPELINE),
            DatabricksResourceType.PIPELINE
        )
    
    def generate_sql_warehouse_name(self,
                                   size: str = "medium",
                                   purpose: str = "analytics") -> str:
        """Generate SQL warehouse name
        
        Args:
            size: small, medium, large, xlarge
            purpose: analytics, reporting, adhoc
        """
        parts = [
            self.config.project,
            "sql",
            purpose,
            size,
            self.config.environment
        ]
        name = '-'.join(parts)
        return self._truncate_name(
            self._sanitize_name(name, DatabricksResourceType.SQL_WAREHOUSE),
            DatabricksResourceType.SQL_WAREHOUSE
        )
    
    def generate_catalog_name(self, catalog_type: str = "main") -> str:
        """Generate Unity Catalog catalog name
        
        Args:
            catalog_type: main, dev, test, sandbox
        """
        parts = [
            self.config.project,
            catalog_type,
            self.config.environment
        ]
        name = '_'.join(parts)
        return self._truncate_name(
            self._sanitize_name(name, DatabricksResourceType.CATALOG),
            DatabricksResourceType.CATALOG
        )
    
    def generate_schema_name(self,
                           domain: str,
                           layer: str = "bronze") -> str:
        """Generate Unity Catalog schema name
        
        Args:
            domain: Data domain (finance, marketing, etc.)
            layer: bronze, silver, gold (medallion architecture)
        """
        parts = [domain, layer]
        name = '_'.join(parts)
        return self._truncate_name(
            self._sanitize_name(name, DatabricksResourceType.SCHEMA),
            DatabricksResourceType.SCHEMA
        )
    
    def generate_table_name(self,
                          entity: str,
                          table_type: str = "fact") -> str:
        """Generate Unity Catalog table name
        
        Args:
            entity: Business entity (customers, orders, etc.)
            table_type: fact, dim, bridge, etc.
        """
        if table_type == "fact":
            name = f"fact_{entity}"
        elif table_type == "dim":
            name = f"dim_{entity}"
        else:
            name = f"{table_type}_{entity}"
        
        return self._truncate_name(
            self._sanitize_name(name, DatabricksResourceType.TABLE),
            DatabricksResourceType.TABLE
        )
    
    def generate_volume_name(self,
                           purpose: str,
                           data_type: str = "raw") -> str:
        """Generate Unity Catalog volume name
        
        Args:
            purpose: Business purpose
            data_type: raw, processed, archive
        """
        parts = [data_type, purpose]
        name = '_'.join(parts)
        return self._truncate_name(
            self._sanitize_name(name, DatabricksResourceType.VOLUME),
            DatabricksResourceType.VOLUME
        )
    
    def generate_secret_scope_name(self, purpose: str = "general") -> str:
        """Generate secret scope name"""
        parts = [
            self.config.project,
            purpose,
            self.config.environment
        ]
        name = '-'.join(parts)
        return self._truncate_name(
            self._sanitize_name(name, DatabricksResourceType.SECRET_SCOPE),
            DatabricksResourceType.SECRET_SCOPE
        )
    
    def generate_instance_pool_name(self,
                                   node_type: str,
                                   purpose: str = "general") -> str:
        """Generate instance pool name
        
        Args:
            node_type: Node type identifier (compute, memory, etc.)
            purpose: general, ml, etl
        """
        parts = [
            self.config.project,
            "pool",
            node_type,
            purpose,
            self.config.environment
        ]
        name = '-'.join(parts)
        return self._truncate_name(
            self._sanitize_name(name, DatabricksResourceType.INSTANCE_POOL),
            DatabricksResourceType.INSTANCE_POOL
        )
    
    def generate_policy_name(self,
                           policy_type: str,
                           target: str = "cluster") -> str:
        """Generate policy name
        
        Args:
            policy_type: security, cost, performance
            target: cluster, sql, job
        """
        parts = [
            self.config.project,
            target,
            policy_type,
            self.config.environment
        ]
        name = '-'.join(parts)
        return self._truncate_name(
            self._sanitize_name(name, DatabricksResourceType.POLICY),
            DatabricksResourceType.POLICY
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
                                     table_type: str = "fact") -> str:
        """Generate fully qualified table name"""
        catalog = self.generate_catalog_name(catalog_type)
        schema = self.generate_schema_name(domain, layer)
        table = self.generate_table_name(entity, table_type)
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
