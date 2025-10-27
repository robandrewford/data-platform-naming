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
