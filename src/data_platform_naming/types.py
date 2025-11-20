#!/usr/bin/env python3
"""
Type definitions for data platform naming.

Provides TypedDict definitions for structured dictionaries
to improve type safety and IDE autocomplete.
"""

from __future__ import annotations

from typing import Any, TypedDict


class MetadataDict(TypedDict, total=False):
    """
    Blueprint metadata structure.

    All fields are optional to support partial metadata in blueprints.
    """
    environment: str
    project: str
    region: str
    team: str
    cost_center: str
    data_classification: str


class TagsDict(TypedDict, total=False):
    """
    Standard resource tags structure.

    Required fields: Environment, Project, ManagedBy, ResourceType
    Optional fields: Team, CostCenter, DataClassification
    """
    Environment: str
    Project: str
    ManagedBy: str
    ResourceType: str
    Team: str
    CostCenter: str
    DataClassification: str


class ValidationContext(TypedDict, total=False):
    """Validation context dictionary for error reporting."""
    resource_type: str
    operation: str
    field: str
    value: str
    suggestion: str


class ConfigValuesDict(TypedDict, total=False):
    """Configuration values dictionary structure."""
    project: str
    environment: str
    region: str
    region_short: str
    team: str
    cost_center: str
    data_classification: str


class PatternVariablesDict(TypedDict, total=False):
    """Pattern variable substitution dictionary."""
    project: str
    environment: str
    region: str
    region_short: str
    purpose: str
    layer: str
    domain: str
    entity: str
    table_type: str
    cluster_type: str
    workload: str
    # Many more fields can be added as needed


class SchemaDict(TypedDict, total=False):
    """JSON schema dictionary structure."""
    type: str
    properties: dict[str, Any]
    required: list[str]
    additionalProperties: bool


# Phase 4: Additional TypedDicts for configuration management


class ValueOverridesDict(TypedDict, total=False):
    """
    Value overrides for resource name generation.

    Used to override default or environment-specific values
    for a specific resource instance.
    """
    project: str
    environment: str
    region: str
    region_short: str
    purpose: str
    layer: str
    domain: str
    entity: str
    team: str
    cost_center: str
    data_classification: str
    workload: str
    cluster_type: str
    table_type: str


class TransformationRulesDict(TypedDict, total=False):
    """
    Transformation rules configuration structure.

    Defines how values should be transformed during name generation.
    """
    region_mapping: dict[str, str]
    lowercase: list[str]
    uppercase: list[str]
    replace_hyphens: dict[str, str]
    hash_generation: dict[str, Any]


class ValidationWarningsDict(TypedDict, total=False):
    """
    Validation warnings and errors structure.

    Used for configuration validation results.
    """
    resource_type: str
    warnings: list[str]
    errors: list[str]
    missing_variables: list[str]
    unused_variables: list[str]


class ResourceDefinitionDict(TypedDict, total=False):
    """
    Blueprint resource definition structure.

    Defines a resource to be created from a blueprint.
    """
    id: str
    type: str
    metadata: MetadataDict
    params: dict[str, Any]
    tags: TagsDict
    depends_on: list[str]


class BlueprintDict(TypedDict, total=False):
    """
    Complete blueprint structure.

    Top-level blueprint containing multiple resources.
    """
    version: str
    environment: str
    metadata: MetadataDict
    resources: list[ResourceDefinitionDict]
    tags: TagsDict


# Phase 6: CRUD Operation TypedDicts


class S3CreateParamsDict(TypedDict, total=False):
    """S3 bucket creation parameters."""
    region: str
    versioning: bool
    encryption: bool
    lifecycle_rules: list[dict[str, Any]]
    tags: dict[str, str]


class S3UpdateParamsDict(TypedDict, total=False):
    """S3 bucket update parameters."""
    tags: dict[str, str]
    lifecycle_rules: list[dict[str, Any]]


class GlueCreateDatabaseParamsDict(TypedDict, total=False):
    """Glue database creation parameters."""
    description: str
    location_uri: str
    parameters: dict[str, str]


class GlueCreateTableParamsDict(TypedDict, total=False):
    """Glue table creation parameters."""
    database_name: str
    columns: list[dict[str, str]]
    location: str
    partition_keys: list[dict[str, str]]
    input_format: str
    output_format: str
    serde: str
    parameters: dict[str, str]


class DatabricksClusterParamsDict(TypedDict, total=False):
    """Databricks cluster creation parameters."""
    spark_version: str
    node_type_id: str
    num_workers: int
    autoscale: dict[str, int]
    spark_conf: dict[str, str]
    aws_attributes: dict[str, Any]
    custom_tags: dict[str, str]


class DatabricksJobParamsDict(TypedDict, total=False):
    """Databricks job creation parameters."""
    notebook_path: str
    cluster_id: str
    timeout_seconds: int
    max_retries: int
    schedule: dict[str, str]
    email_notifications: dict[str, list[str]]


# Phase 7: Validator TypedDicts


class S3ConstraintsDict(TypedDict, total=False):
    """S3 bucket naming constraints."""
    min_length: int
    max_length: int
    pattern: str
    reserved_prefixes: list[str]
    allow_uppercase: bool
    allow_underscores: bool


class GlueConstraintsDict(TypedDict, total=False):
    """Glue resource naming constraints."""
    max_length: int
    pattern: str
    allow_hyphens: bool
    allow_uppercase: bool


class DatabricksConstraintsDict(TypedDict, total=False):
    """Databricks resource naming constraints."""
    max_length: int
    pattern: str
    allow_hyphens: bool
    allow_underscores: bool


# Phase 6: CRUD Transaction Manager TypedDicts


class OperationResultDict(TypedDict, total=False):
    """
    Result from executing a CRUD operation.

    Contains rollback data and resource-specific response information.
    """
    rollback_data: dict[str, Any]
    config: dict[str, Any]
    cluster: dict[str, Any]
    job: dict[str, Any]
    database: dict[str, Any]
    table: dict[str, Any]
    catalog: dict[str, Any]
    schema: dict[str, Any]


class RollbackDataDict(TypedDict, total=False):
    """
    Rollback data for CRUD operations.

    Stores information needed to reverse an operation.
    """
    # AWS resources
    bucket_name: str
    region: str
    database_name: str
    table_name: str

    # Databricks resources
    cluster_id: str
    cluster_name: str
    job_id: str
    job_name: str
    catalog_name: str
    schema_name: str


class StateDict(TypedDict):
    """
    State store dictionary for tracking resource state.

    Stores metadata about created resources.
    """
    resource_type: str
    params: dict[str, Any]
    created_at: float
