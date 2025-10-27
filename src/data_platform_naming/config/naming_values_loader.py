#!/usr/bin/env python3
"""
NamingValuesLoader - Load and manage naming value configurations.

This module provides functionality to load naming values from YAML files,
validate them against JSON Schema, and merge values according to precedence rules.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, cast

import jsonschema
import yaml
from jsonschema import ValidationError as JsonSchemaValidationError


class ConfigurationError(Exception):
    """Base exception for configuration errors"""
    pass


class SchemaValidationError(ConfigurationError):
    """Raised when configuration doesn't validate against schema"""
    pass


class FileLoadError(ConfigurationError):
    """Raised when configuration file cannot be loaded"""
    pass


class ValueResolutionError(ConfigurationError):
    """Raised when value resolution fails"""
    pass


@dataclass
class NamingValues:
    """Container for resolved naming values"""
    values: dict[str, Any]
    source: str  # Describes where values came from

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value by key with optional default"""
        return self.values.get(key, default)

    def __getitem__(self, key: str) -> Any:
        """Get a value by key, raises KeyError if not found"""
        return self.values[key]

    def __contains__(self, key: str) -> bool:
        """Check if key exists in values"""
        return key in self.values

    def keys(self) -> list[str]:
        """Return list of all keys"""
        return list(self.values.keys())


class NamingValuesLoader:
    """
    Load and manage naming value configurations with hierarchical precedence.
    
    Precedence (lowest to highest):
    1. defaults - Global defaults applied to all resources
    2. environments.{env} - Environment-specific overrides
    3. resource_types.{type} - Resource-type-specific overrides
    4. blueprint metadata - Values from blueprint (handled externally)
    
    Example:
        >>> loader = NamingValuesLoader()
        >>> loader.load_from_file("naming-values.yaml")
        >>> values = loader.get_values_for_resource(
        ...     resource_type="aws_s3_bucket",
        ...     environment="prd"
        ... )
        >>> print(values["project"])
        'dataplatform'
    """

    def __init__(self, schema_path: Path | None = None):
        """
        Initialize the NamingValuesLoader.
        
        Args:
            schema_path: Optional path to JSON schema file.
                        If not provided, uses bundled schema.
        """
        self.config: dict[str, Any] | None = None
        self.schema: dict[str, Any] = self._load_schema(schema_path)
        self.config_path: Path | None = None

    def _load_schema(self, schema_path: Path | None = None) -> dict[str, Any]:
        """Load the JSON schema for validation"""
        if schema_path is None:
            # Use bundled schema
            module_dir = Path(__file__).parent.parent.parent.parent
            schema_path = module_dir / "schemas" / "naming-values-schema.json"

        try:
            with open(schema_path) as f:
                return cast(dict[str, Any], json.load(f))
        except FileNotFoundError:
            raise ConfigurationError(
                f"Schema file not found: {schema_path}"
            )
        except json.JSONDecodeError as e:
            raise ConfigurationError(
                f"Invalid JSON in schema file: {e}"
            )

    def load_from_file(self, config_path: Path) -> None:
        """
        Load configuration from a YAML file.
        
        Args:
            config_path: Path to YAML configuration file
            
        Raises:
            FileLoadError: If file cannot be read
            SchemaValidationError: If configuration doesn't validate
        """
        config_path = Path(config_path)

        if not config_path.exists():
            raise FileLoadError(
                f"Configuration file not found: {config_path}"
            )

        try:
            with open(config_path) as f:
                self.config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise FileLoadError(
                f"Invalid YAML in configuration file: {e}"
            )
        except Exception as e:
            raise FileLoadError(
                f"Failed to read configuration file: {e}"
            )

        self.config_path = config_path
        self._validate_config()

    def load_from_dict(self, config: dict[str, Any]) -> None:
        """
        Load configuration from a dictionary.

        Args:
            config: Configuration dictionary

        Raises:
            SchemaValidationError: If configuration doesn't validate
        """
        self.config = config
        self.config_path = None
        self._validate_config()

    def _validate_config(self) -> None:
        """
        Validate configuration against JSON schema.
        
        Raises:
            SchemaValidationError: If validation fails
        """
        if self.config is None:
            raise ConfigurationError("No configuration loaded")

        try:
            jsonschema.validate(instance=self.config, schema=self.schema)
        except JsonSchemaValidationError as e:
            # Provide helpful error message
            error_path = " -> ".join(str(p) for p in e.path) if e.path else "root"
            raise SchemaValidationError(
                f"Configuration validation failed at {error_path}: {e.message}"
            )

    def get_values_for_resource(
        self,
        resource_type: str,
        environment: str | None = None,
        blueprint_metadata: dict[str, Any] | None = None
    ) -> NamingValues:
        """
        Get merged values for a specific resource type and environment.

        Values are merged according to precedence:
        defaults → environments.{env} → resource_types.{type} → blueprint_metadata

        Args:
            resource_type: Resource type (e.g., 'aws_s3_bucket')
            environment: Optional environment code ('dev', 'stg', 'prd')
            blueprint_metadata: Optional blueprint metadata to merge (highest precedence)

        Returns:
            NamingValues object with merged values

        Raises:
            ValueResolutionError: If value resolution fails
        """
        if self.config is None:
            raise ConfigurationError("No configuration loaded")

        # Start with defaults
        values = dict(self.config.get("defaults", {}))
        sources = ["defaults"]

        # Merge environment-specific values
        if environment:
            env_values = self.config.get("environments", {}).get(environment, {})
            if env_values:
                values.update(env_values)
                sources.append(f"environments.{environment}")

        # Merge resource-type-specific values
        resource_values = self.config.get("resource_types", {}).get(resource_type, {})
        if resource_values:
            values.update(resource_values)
            sources.append(f"resource_types.{resource_type}")

        # Merge blueprint metadata (highest precedence)
        if blueprint_metadata:
            values.update(blueprint_metadata)
            sources.append("blueprint_metadata")

        source_description = " < ".join(sources)

        return NamingValues(
            values=values,
            source=source_description
        )

    def get_defaults(self) -> dict[str, Any]:
        """
        Get default values without any overrides.

        Returns:
            Dictionary of default values
        """
        if self.config is None:
            raise ConfigurationError("No configuration loaded")

        return dict(self.config.get("defaults", {}))

    def get_environment_values(self, environment: str) -> dict[str, Any]:
        """
        Get environment-specific values.

        Args:
            environment: Environment code ('dev', 'stg', 'prd')

        Returns:
            Dictionary of environment-specific values
        """
        if self.config is None:
            raise ConfigurationError("No configuration loaded")

        return dict(
            self.config.get("environments", {}).get(environment, {})
        )

    def get_resource_type_values(self, resource_type: str) -> dict[str, Any]:
        """
        Get resource-type-specific values.

        Args:
            resource_type: Resource type (e.g., 'aws_s3_bucket')

        Returns:
            Dictionary of resource-type-specific values
        """
        if self.config is None:
            raise ConfigurationError("No configuration loaded")

        return dict(
            self.config.get("resource_types", {}).get(resource_type, {})
        )

    def list_environments(self) -> list[str]:
        """
        List all configured environments.

        Returns:
            List of environment codes
        """
        if self.config is None:
            raise ConfigurationError("No configuration loaded")

        return list(self.config.get("environments", {}).keys())

    def list_resource_types(self) -> list[str]:
        """
        List all configured resource types.

        Returns:
            List of resource type names
        """
        if self.config is None:
            raise ConfigurationError("No configuration loaded")

        return list(self.config.get("resource_types", {}).keys())

    def get_version(self) -> str:
        """
        Get configuration version.
        
        Returns:
            Version string (e.g., '1.0')
        """
        if self.config is None:
            raise ConfigurationError("No configuration loaded")

        return cast(str, self.config.get("version", "unknown"))

    def __repr__(self) -> str:
        """String representation of loader"""
        if self.config is None:
            return "NamingValuesLoader(no config loaded)"

        version = self.get_version()
        env_count = len(self.list_environments())
        rt_count = len(self.list_resource_types())

        if self.config_path:
            return (
                f"NamingValuesLoader(version={version}, "
                f"environments={env_count}, resource_types={rt_count}, "
                f"path={self.config_path})"
            )
        else:
            return (
                f"NamingValuesLoader(version={version}, "
                f"environments={env_count}, resource_types={rt_count})"
            )


# Example usage
if __name__ == "__main__":
    # Load configuration
    loader = NamingValuesLoader()
    loader.load_from_file(Path("examples/configs/naming-values.yaml"))

    print(f"Loaded: {loader}")
    print(f"Environments: {loader.list_environments()}")
    print(f"Resource types: {loader.list_resource_types()}")

    # Get values for a specific resource
    values = loader.get_values_for_resource(
        resource_type="aws_s3_bucket",
        environment="prd"
    )

    print("\nValues for aws_s3_bucket in prd:")
    print(f"  Source: {values.source}")
    print(f"  Project: {values.get('project')}")
    print(f"  Environment: {values.get('environment')}")
    print(f"  Purpose: {values.get('purpose')}")
    print(f"  Layer: {values.get('layer')}")
