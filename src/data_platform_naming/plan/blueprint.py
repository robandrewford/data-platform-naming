#!/usr/bin/env python3
"""
Blueprint Parser - JSON Schema Validation & Name Generation
Transforms declarative blueprints into executable operations
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import jsonschema

from ..constants import Environment

# JSON Schema Definition
BLUEPRINT_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["version", "metadata", "resources"],
    "properties": {
        "version": {
            "type": "string",
            "pattern": "^1\\.0$"
        },
        "metadata": {
            "type": "object",
            "required": ["environment", "project", "region"],
            "properties": {
                "environment": {
                    "type": "string",
                    "enum": [e.value for e in Environment]
                },
                "project": {
                    "type": "string",
                    "pattern": "^[a-z0-9-]+$"
                },
                "region": {
                    "type": "string",
                    "pattern": "^[a-z]+-[a-z]+-[0-9]$"
                },
                "team": {"type": "string"},
                "cost_center": {"type": "string"},
                "data_classification": {
                    "type": "string",
                    "enum": ["public", "internal", "confidential", "restricted"]
                }
            }
        },
        "resources": {
            "type": "object",
            "properties": {
                "aws": {
                    "type": "object",
                    "properties": {
                        "s3_buckets": {
                            "type": "array",
                            "items": {"$ref": "#/definitions/s3_bucket"}
                        },
                        "glue_databases": {
                            "type": "array",
                            "items": {"$ref": "#/definitions/glue_database"}
                        },
                        "glue_tables": {
                            "type": "array",
                            "items": {"$ref": "#/definitions/glue_table"}
                        }
                    }
                },
                "databricks": {
                    "type": "object",
                    "properties": {
                        "clusters": {
                            "type": "array",
                            "items": {"$ref": "#/definitions/dbx_cluster"}
                        },
                        "jobs": {
                            "type": "array",
                            "items": {"$ref": "#/definitions/dbx_job"}
                        },
                        "unity_catalog": {
                            "type": "object",
                            "properties": {
                                "catalogs": {
                                    "type": "array",
                                    "items": {"$ref": "#/definitions/uc_catalog"}
                                }
                            }
                        }
                    }
                }
            }
        },
        "scope": {
            "type": "object",
            "required": ["mode", "patterns"],
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": ["include", "exclude"],
                    "description": "Filter mode: 'include' processes only matching types, 'exclude' processes all except matching types"
                },
                "patterns": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "minLength": 1
                    },
                    "minItems": 1,
                    "description": "Wildcard patterns for resource types (e.g., 'aws_*', 'dbx_cluster', '*_bucket')"
                }
            },
            "additionalProperties": False
        }
    },
    "definitions": {
        "s3_bucket": {
            "type": "object",
            "required": ["purpose", "layer"],
            "properties": {
                "purpose": {"type": "string"},
                "layer": {"type": "string", "enum": ["raw", "processed", "curated"]},
                "versioning": {"type": "boolean"},
                "lifecycle_days": {"type": "integer"}
            }
        },
        "glue_database": {
            "type": "object",
            "required": ["domain", "layer"],
            "properties": {
                "domain": {"type": "string"},
                "layer": {"type": "string", "enum": ["bronze", "silver", "gold"]},
                "description": {"type": "string"}
            }
        },
        "glue_table": {
            "type": "object",
            "required": ["database_ref", "entity", "columns"],
            "properties": {
                "database_ref": {"type": "string"},
                "entity": {"type": "string"},
                "table_type": {"type": "string", "enum": ["fact", "dim", "bridge"]},
                "columns": {"type": "array"},
                "partition_keys": {"type": "array"}
            }
        },
        "dbx_cluster": {
            "type": "object",
            "required": ["workload", "cluster_type", "node_type"],
            "properties": {
                "workload": {"type": "string"},
                "cluster_type": {"type": "string", "enum": ["shared", "dedicated", "job"]},
                "node_type": {"type": "string"},
                "spark_version": {"type": "string"},
                "autoscale": {
                    "type": "object",
                    "properties": {
                        "min": {"type": "integer"},
                        "max": {"type": "integer"}
                    }
                }
            }
        },
        "dbx_job": {
            "type": "object",
            "required": ["job_type", "purpose", "cluster_ref"],
            "properties": {
                "job_type": {"type": "string"},
                "purpose": {"type": "string"},
                "schedule": {"type": "string"},
                "cluster_ref": {"type": "string"},
                "tasks": {"type": "array"}
            }
        },
        "uc_catalog": {
            "type": "object",
            "required": ["catalog_type", "schemas"],
            "properties": {
                "catalog_type": {"type": "string"},
                "storage_root": {"type": "string"},
                "schemas": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/uc_schema"}
                }
            }
        },
        "uc_schema": {
            "type": "object",
            "required": ["domain", "layer"],
            "properties": {
                "domain": {"type": "string"},
                "layer": {"type": "string", "enum": ["bronze", "silver", "gold"]},
                "tables": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/uc_table"}
                }
            }
        },
        "uc_table": {
            "type": "object",
            "required": ["entity"],
            "properties": {
                "entity": {"type": "string"},
                "table_type": {"type": "string", "enum": ["fact", "dim", "bridge"]},
                "columns": {"type": "array"}
            }
        }
    }
}


@dataclass
class ParsedResource:
    """Single parsed resource with generated names"""
    resource_type: str
    resource_id: str
    display_name: str
    params: dict[str, Any]
    dependencies: list[str] = field(default_factory=list)


@dataclass
class ParsedBlueprint:
    """Complete parsed blueprint"""
    metadata: dict[str, Any]
    resources: list[ParsedResource]
    dependency_graph: dict[str, list[str]]
    scope_config: Optional[dict[str, Any]] = None

    def get_execution_order(self) -> list[ParsedResource]:
        """Topological sort for dependency resolution"""
        visited = set()
        result = []

        def dfs(resource_id: str):
            if resource_id in visited:
                return
            visited.add(resource_id)

            for dep in self.dependency_graph.get(resource_id, []):
                dfs(dep)

            # Find resource by ID
            for resource in self.resources:
                if resource.resource_id == resource_id:
                    result.append(resource)
                    break

        for resource in self.resources:
            dfs(resource.resource_id)

        return result


class BlueprintParser:
    """Parse and validate blueprints"""

    def __init__(
        self,
        naming_generators: dict[str, Any],
        configuration_manager: Optional[Any] = None
    ):
        """
        Args:
            naming_generators: {'aws': AWSNamingGenerator, 'databricks': DatabricksNamingGenerator}
            configuration_manager: Optional ConfigurationManager for config-based naming
        """
        self.naming_generators = naming_generators
        self.configuration_manager = configuration_manager
        self.schema = BLUEPRINT_SCHEMA

    def parse(self, blueprint_path: Path) -> ParsedBlueprint:
        """Parse blueprint file"""
        # Load
        with open(blueprint_path) as f:
            blueprint = json.load(f)

        # Validate
        self._validate(blueprint)

        # Parse
        metadata = blueprint['metadata']
        resources = []
        dependency_graph = {}

        # AWS Resources
        if 'aws' in blueprint['resources']:
            aws_resources = self._parse_aws(
                blueprint['resources']['aws'],
                metadata
            )
            resources.extend(aws_resources)

        # Databricks Resources
        if 'databricks' in blueprint['resources']:
            dbx_resources = self._parse_databricks(
                blueprint['resources']['databricks'],
                metadata
            )
            resources.extend(dbx_resources)

        # Apply scope filter if configured
        scope_config = blueprint.get('scope')
        if scope_config:
            resources = self._apply_scope_filter(resources, scope_config)

        # Build dependency graph
        for resource in resources:
            dependency_graph[resource.resource_id] = resource.dependencies

        return ParsedBlueprint(
            metadata=metadata,
            resources=resources,
            dependency_graph=dependency_graph,
            scope_config=scope_config
        )

    def _validate(self, blueprint: dict) -> None:
        """Validate against schema"""
        try:
            jsonschema.validate(instance=blueprint, schema=self.schema)
        except jsonschema.ValidationError as e:
            raise ValueError(f"Blueprint validation failed: {e.message}") from e

    def _apply_scope_filter(
        self,
        resources: list[ParsedResource],
        scope_config: dict[str, Any]
    ) -> list[ParsedResource]:
        """
        Apply scope filtering to resources based on configuration.

        Args:
            resources: List of parsed resources
            scope_config: Scope configuration with 'mode' and 'patterns'

        Returns:
            Filtered list of resources
        """
        # Import here to avoid circular dependency
        from ..config.scope_filter import FilterMode, ScopeFilter

        # Create filter
        mode = FilterMode.INCLUDE if scope_config['mode'] == 'include' else FilterMode.EXCLUDE
        scope_filter = ScopeFilter(mode=mode, patterns=scope_config['patterns'])

        # Filter resources
        filtered_resources = [
            resource for resource in resources
            if scope_filter.should_process(resource.resource_type)
        ]

        return filtered_resources

    def _parse_aws(self, aws_config: dict, metadata: dict) -> list[ParsedResource]:
        """Parse AWS resources"""
        resources = []
        aws_gen = self.naming_generators['aws']

        # S3 Buckets
        for bucket_spec in aws_config.get('s3_buckets', []):
            bucket_name = aws_gen.generate_s3_bucket_name(
                purpose=bucket_spec['purpose'],
                layer=bucket_spec['layer'],
                metadata=metadata
            )

            resources.append(ParsedResource(
                resource_type='aws_s3_bucket',
                resource_id=bucket_name,
                display_name=f"S3: {bucket_name}",
                params={
                    'region': metadata['region'],
                    'versioning': bucket_spec.get('versioning', True),
                    'lifecycle_rules': self._build_lifecycle_rules(
                        bucket_spec.get('lifecycle_days', 90)
                    ),
                    'tags': self._build_tags(metadata)
                }
            ))

        # Glue Databases
        db_refs = {}
        for db_spec in aws_config.get('glue_databases', []):
            db_name = aws_gen.generate_glue_database_name(
                domain=db_spec['domain'],
                layer=db_spec['layer'],
                metadata=metadata
            )

            db_ref = f"{db_spec['domain']}-{db_spec['layer']}"
            db_refs[db_ref] = db_name

            resources.append(ParsedResource(
                resource_type='aws_glue_database',
                resource_id=db_name,
                display_name=f"Glue DB: {db_name}",
                params={
                    'description': db_spec.get('description', '')
                }
            ))

        # Glue Tables
        for table_spec in aws_config.get('glue_tables', []):
            db_name = db_refs.get(table_spec['database_ref'])
            if not db_name:
                raise ValueError(f"Database ref not found: {table_spec['database_ref']}")

            table_name = aws_gen.generate_glue_table_name(
                entity=table_spec['entity'],
                table_type=table_spec.get('table_type', 'fact'),
                metadata=metadata
            )

            resources.append(ParsedResource(
                resource_type='aws_glue_table',
                resource_id=table_name,
                display_name=f"Glue Table: {db_name}.{table_name}",
                params={
                    'database_name': db_name,
                    'columns': table_spec['columns'],
                    'partition_keys': table_spec.get('partition_keys', [])
                },
                dependencies=[db_name]
            ))

        return resources

    def _parse_databricks(self, dbx_config: dict, metadata: dict) -> list[ParsedResource]:
        """Parse Databricks resources"""
        resources = []
        dbx_gen = self.naming_generators['databricks']

        # Clusters
        cluster_refs = {}
        for cluster_spec in dbx_config.get('clusters', []):
            cluster_name = dbx_gen.generate_cluster_name(
                workload=cluster_spec['workload'],
                cluster_type=cluster_spec['cluster_type'],
                metadata=metadata
            )

            cluster_refs[cluster_spec['workload']] = cluster_name

            resources.append(ParsedResource(
                resource_type='dbx_cluster',
                resource_id=cluster_name,
                display_name=f"Cluster: {cluster_name}",
                params={
                    'spark_version': cluster_spec.get('spark_version', '13.3.x-scala2.12'),
                    'node_type': cluster_spec['node_type'],
                    'autoscale': cluster_spec.get('autoscale', {'min': 2, 'max': 8}),
                    'tags': self._build_tags(metadata)
                }
            ))

        # Jobs
        for job_spec in dbx_config.get('jobs', []):
            job_name = dbx_gen.generate_job_name(
                job_type=job_spec['job_type'],
                purpose=job_spec['purpose'],
                schedule=job_spec.get('schedule'),
                metadata=metadata
            )

            cluster_ref = job_spec.get('cluster_ref')
            dependencies = []
            if cluster_ref and cluster_ref in cluster_refs:
                dependencies.append(cluster_refs[cluster_ref])

            resources.append(ParsedResource(
                resource_type='dbx_job',
                resource_id=job_name,
                display_name=f"Job: {job_name}",
                params={
                    'tasks': job_spec.get('tasks', []),
                    'schedule': job_spec.get('schedule'),
                    'tags': self._build_tags(metadata)
                },
                dependencies=dependencies
            ))

        # Unity Catalog
        if 'unity_catalog' in dbx_config:
            uc_resources = self._parse_unity_catalog(
                dbx_config['unity_catalog'],
                metadata
            )
            resources.extend(uc_resources)

        return resources

    def _parse_unity_catalog(self, uc_config: dict, metadata: dict) -> list[ParsedResource]:
        """Parse Unity Catalog hierarchy"""
        resources = []
        dbx_gen = self.naming_generators['databricks']

        for catalog_spec in uc_config.get('catalogs', []):
            # Catalog
            catalog_name = dbx_gen.generate_catalog_name(
                catalog_type=catalog_spec['catalog_type'],
                metadata=metadata
            )

            resources.append(ParsedResource(
                resource_type='dbx_catalog',
                resource_id=catalog_name,
                display_name=f"Catalog: {catalog_name}",
                params={
                    'storage_root': catalog_spec.get('storage_root')
                }
            ))

            # Schemas
            for schema_spec in catalog_spec.get('schemas', []):
                schema_name = dbx_gen.generate_schema_name(
                    domain=schema_spec['domain'],
                    layer=schema_spec['layer'],
                    metadata=metadata
                )

                full_schema_name = f"{catalog_name}.{schema_name}"

                resources.append(ParsedResource(
                    resource_type='dbx_schema',
                    resource_id=schema_name,
                    display_name=f"Schema: {full_schema_name}",
                    params={
                        'catalog_name': catalog_name
                    },
                    dependencies=[catalog_name]
                ))

                # Tables
                for table_spec in schema_spec.get('tables', []):
                    table_name = dbx_gen.generate_table_name(
                        entity=table_spec['entity'],
                        table_type=table_spec.get('table_type', 'fact'),
                        metadata=metadata
                    )

                    full_table_name = f"{catalog_name}.{schema_name}.{table_name}"

                    resources.append(ParsedResource(
                        resource_type='dbx_table',
                        resource_id=table_name,
                        display_name=f"Table: {full_table_name}",
                        params={
                            'catalog_name': catalog_name,
                            'schema_name': schema_name,
                            'columns': table_spec.get('columns', [])
                        },
                        dependencies=[full_schema_name]
                    ))

        return resources

    def _build_tags(self, metadata: dict) -> dict[str, str]:
        """Build standard tags"""
        tags = {
            'Environment': metadata['environment'],
            'Project': metadata['project'],
            'ManagedBy': 'dpn-cli'
        }

        if 'team' in metadata:
            tags['Team'] = metadata['team']

        if 'cost_center' in metadata:
            tags['CostCenter'] = metadata['cost_center']

        return tags

    def _build_lifecycle_rules(self, transition_days: int) -> list[dict]:
        """Build S3 lifecycle rules"""
        return [{
            'Status': 'Enabled',
            'Transitions': [
                {
                    'Days': transition_days,
                    'StorageClass': 'INTELLIGENT_TIERING'
                }
            ]
        }]

    def export_preview(self, parsed: ParsedBlueprint, output_path: Path) -> None:
        """Export resource names preview"""
        preview = {
            'metadata': parsed.metadata,
            'resources': {
                'total_count': len(parsed.resources),
                'by_type': {},
                'execution_order': []
            }
        }

        # Count by type
        for resource in parsed.resources:
            resource_type = resource.resource_type
            if resource_type not in preview['resources']['by_type']:
                preview['resources']['by_type'][resource_type] = []

            preview['resources']['by_type'][resource_type].append({
                'resource_id': resource.resource_id,
                'display_name': resource.display_name,
                'dependencies': resource.dependencies
            })

        # Execution order
        for resource in parsed.get_execution_order():
            preview['resources']['execution_order'].append({
                'resource_id': resource.resource_id,
                'resource_type': resource.resource_type
            })

        with open(output_path, 'w') as f:
            json.dump(preview, f, indent=2)


# Example usage
if __name__ == "__main__":
    from ..aws_naming import AWSNamingConfig, AWSNamingGenerator
    from ..config.configuration_manager import ConfigurationManager
    from ..dbx_naming import DatabricksNamingConfig, DatabricksNamingGenerator

    # Setup generators
    aws_config = AWSNamingConfig(
        environment=Environment.PRD.value,
        project='dataplatform',
        region='us-east-1'
    )

    dbx_config = DatabricksNamingConfig(
        environment=Environment.PRD.value,
        project='dataplatform',
        region='us-east-1'
    )

    # Load configuration manager
    config_mgr = ConfigurationManager()
    config_mgr.load_configs(
        values_path=Path('examples/configs/naming-values.yaml'),
        patterns_path=Path('examples/configs/naming-patterns.yaml')
    )

    generators = {
        'aws': AWSNamingGenerator(aws_config, config_mgr),
        'databricks': DatabricksNamingGenerator(dbx_config, config_mgr)
    }

    # Parse blueprint
    parser = BlueprintParser(generators)
    parsed = parser.parse(Path('blueprint.json'))

    # Export preview
    parser.export_preview(parsed, Path('preview.json'))

    print(f"Parsed {len(parsed.resources)} resources")
    print(f"Execution order: {len(parsed.get_execution_order())} steps")
