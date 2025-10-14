#!/usr/bin/env python3
"""
NamingPatternsLoader - Load and manage naming pattern configurations.

This module provides functionality to load naming patterns from YAML files,
validate them against JSON Schema, and apply transformations to pattern variables.
"""

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import jsonschema
import yaml
from jsonschema import ValidationError as JsonSchemaValidationError

# Import exceptions from naming_values_loader for consistency
from .naming_values_loader import (
    ConfigurationError,
    FileLoadError,
    SchemaValidationError,
)


class PatternError(ConfigurationError):
    """Raised when pattern is invalid or cannot be resolved"""
    pass


@dataclass
class NamingPattern:
    """Container for a naming pattern with metadata"""
    pattern: str
    resource_type: str
    required_variables: List[str]

    def get_variables(self) -> Set[str]:
        """Extract all {variable} placeholders from pattern"""
        return set(re.findall(r'\{([a-z_]+)\}', self.pattern))

    def validate_variables(self, available_variables: Dict[str, Any]) -> List[str]:
        """
        Validate that all required variables are available.
        
        Args:
            available_variables: Dictionary of available variable values
            
        Returns:
            List of missing variable names (empty if all present)
        """
        pattern_vars = self.get_variables()
        available_keys = set(available_variables.keys())
        missing = pattern_vars - available_keys
        return sorted(list(missing))

    def format(self, values: Dict[str, Any]) -> str:
        """
        Format pattern with provided values.
        
        Args:
            values: Dictionary of variable values
            
        Returns:
            Formatted string with variables substituted
            
        Raises:
            PatternError: If required variables are missing
        """
        missing = self.validate_variables(values)
        if missing:
            raise PatternError(
                f"Missing required variables for pattern '{self.pattern}': {', '.join(missing)}"
            )

        try:
            return self.pattern.format(**values)
        except KeyError as e:
            raise PatternError(f"Variable substitution failed: {e}")


class NamingPatternsLoader:
    """
    Load and manage naming pattern configurations with transformations.
    
    Handles:
    - Loading patterns from YAML files
    - JSON Schema validation
    - Variable transformations (region mapping, case conversion, character replacement)
    - Pattern validation rules (max length, allowed characters)
    
    Example:
        >>> loader = NamingPatternsLoader()
        >>> loader.load_from_file("naming-patterns.yaml")
        >>> pattern = loader.get_pattern("aws_s3_bucket")
        >>> print(pattern.pattern)
        '{project}-{purpose}-{layer}-{environment}-{region_short}'
    """

    def __init__(self, schema_path: Optional[Path] = None):
        """
        Initialize the NamingPatternsLoader.
        
        Args:
            schema_path: Optional path to JSON schema file.
                        If not provided, uses bundled schema.
        """
        self.config: Optional[Dict[str, Any]] = None
        self.schema: Dict[str, Any] = self._load_schema(schema_path)
        self.config_path: Optional[Path] = None

    def _load_schema(self, schema_path: Optional[Path] = None) -> Dict[str, Any]:
        """Load the JSON schema for validation"""
        if schema_path is None:
            # Use bundled schema
            module_dir = Path(__file__).parent.parent.parent.parent
            schema_path = module_dir / "schemas" / "naming-patterns-schema.json"

        try:
            with open(schema_path) as f:
                return json.load(f)
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

    def load_from_dict(self, config: Dict[str, Any]) -> None:
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

    def get_pattern(self, resource_type: str) -> NamingPattern:
        """
        Get naming pattern for a specific resource type.
        
        Args:
            resource_type: Resource type (e.g., 'aws_s3_bucket')
            
        Returns:
            NamingPattern object
            
        Raises:
            PatternError: If pattern not found or invalid
        """
        if self.config is None:
            raise ConfigurationError("No configuration loaded")

        patterns = self.config.get("patterns", {})
        if resource_type not in patterns:
            raise PatternError(
                f"No pattern defined for resource type: {resource_type}"
            )

        pattern_str = patterns[resource_type]
        required_vars = self.get_required_variables(resource_type)

        return NamingPattern(
            pattern=pattern_str,
            resource_type=resource_type,
            required_variables=required_vars
        )

    def get_all_patterns(self) -> Dict[str, NamingPattern]:
        """
        Get all naming patterns.
        
        Returns:
            Dictionary mapping resource types to NamingPattern objects
        """
        if self.config is None:
            raise ConfigurationError("No configuration loaded")

        patterns = {}
        for resource_type in self.config.get("patterns", {}).keys():
            patterns[resource_type] = self.get_pattern(resource_type)

        return patterns

    def generate_hash(self, input_string: str) -> str:
        """
        Generate hash suffix for uniqueness.
        
        Uses configuration from transformations.hash_generation section.
        Defaults: md5, 8 characters, no prefix, '-' separator
        
        Args:
            input_string: String to hash (typically the base name)
            
        Returns:
            Hash string formatted according to config
            
        Example:
            >>> loader.generate_hash("dataplatform-raw-prd")
            'a1b2c3d4'
        """
        if self.config is None:
            raise ConfigurationError("No configuration loaded")

        transformations = self.config.get("transformations", {})
        hash_config = transformations.get("hash_generation", {})

        # Get configuration with defaults
        algorithm = hash_config.get("algorithm", "md5")
        length = hash_config.get("length", 8)
        prefix = hash_config.get("prefix", "")

        # Generate hash
        if algorithm == "sha256":
            hash_obj = hashlib.sha256(input_string.encode())
        else:  # default to md5
            hash_obj = hashlib.md5(input_string.encode())

        hash_str = hash_obj.hexdigest()[:length]

        # Add prefix if configured
        if prefix:
            return f"{prefix}{hash_str}"

        return hash_str

    def apply_transformations(self, values: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply configured transformations to values.
        
        Transformations include:
        - Region mapping (us-east-1 → use1)
        - Case conversion (lowercase/uppercase)
        - Character replacement (hyphens to underscores)
        
        Args:
            values: Dictionary of variable values
            
        Returns:
            Dictionary with transformations applied
        """
        if self.config is None:
            raise ConfigurationError("No configuration loaded")

        # Make a copy to avoid modifying original
        transformed = dict(values)
        transformations = self.config.get("transformations", {})

        # Apply region mapping
        region_mapping = transformations.get("region_mapping", {})
        if "region" in transformed and transformed["region"] in region_mapping:
            transformed["region_short"] = region_mapping[transformed["region"]]

        # Apply lowercase transformation
        lowercase_vars = transformations.get("lowercase", [])
        for var in lowercase_vars:
            if var in transformed and isinstance(transformed[var], str):
                transformed[var] = transformed[var].lower()

        # Apply uppercase transformation
        uppercase_vars = transformations.get("uppercase", [])
        for var in uppercase_vars:
            if var in transformed and isinstance(transformed[var], str):
                transformed[var] = transformed[var].upper()

        # Apply character replacement
        replace_hyphens = transformations.get("replace_hyphens", {})
        for var, replacement in replace_hyphens.items():
            if var in transformed and isinstance(transformed[var], str):
                transformed[var] = transformed[var].replace("-", replacement)

        return transformed

    def get_max_length(self, resource_type: str) -> Optional[int]:
        """
        Get maximum length constraint for resource type.
        
        Args:
            resource_type: Resource type (e.g., 'aws_s3_bucket')
            
        Returns:
            Maximum length or None if not specified
        """
        if self.config is None:
            raise ConfigurationError("No configuration loaded")

        validation = self.config.get("validation", {})
        max_lengths = validation.get("max_length", {})
        return max_lengths.get(resource_type)

    def get_allowed_chars_pattern(self, resource_type: str) -> Optional[str]:
        """
        Get allowed characters regex pattern for resource type.
        
        Args:
            resource_type: Resource type (e.g., 'aws_s3_bucket')
            
        Returns:
            Regex pattern or None if not specified
        """
        if self.config is None:
            raise ConfigurationError("No configuration loaded")

        validation = self.config.get("validation", {})
        allowed_chars = validation.get("allowed_chars", {})
        return allowed_chars.get(resource_type)

    def get_required_variables(self, resource_type: str) -> List[str]:
        """
        Get list of required variables for resource type.
        
        Args:
            resource_type: Resource type (e.g., 'aws_s3_bucket')
            
        Returns:
            List of required variable names
        """
        if self.config is None:
            raise ConfigurationError("No configuration loaded")

        validation = self.config.get("validation", {})
        required_vars = validation.get("required_variables", {})
        return required_vars.get(resource_type, [])

    def validate_name(self, resource_type: str, name: str) -> List[str]:
        """
        Validate a generated name against constraints.
        
        Args:
            resource_type: Resource type (e.g., 'aws_s3_bucket')
            name: Generated name to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Check max length
        max_length = self.get_max_length(resource_type)
        if max_length and len(name) > max_length:
            errors.append(
                f"Name exceeds maximum length of {max_length}: {len(name)} characters"
            )

        # Check allowed characters
        allowed_pattern = self.get_allowed_chars_pattern(resource_type)
        if allowed_pattern and not re.match(allowed_pattern, name):
            errors.append(
                f"Name contains invalid characters (pattern: {allowed_pattern})"
            )

        return errors

    def list_resource_types(self) -> List[str]:
        """
        List all resource types with defined patterns.
        
        Returns:
            List of resource type names
        """
        if self.config is None:
            raise ConfigurationError("No configuration loaded")

        return list(self.config.get("patterns", {}).keys())

    def get_version(self) -> str:
        """
        Get configuration version.
        
        Returns:
            Version string (e.g., '1.0')
        """
        if self.config is None:
            raise ConfigurationError("No configuration loaded")

        return self.config.get("version", "unknown")

    def __repr__(self) -> str:
        """String representation of loader"""
        if self.config is None:
            return "NamingPatternsLoader(no config loaded)"

        version = self.get_version()
        pattern_count = len(self.list_resource_types())
        has_transformations = bool(self.config.get("transformations"))
        has_validation = bool(self.config.get("validation"))

        if self.config_path:
            return (
                f"NamingPatternsLoader(version={version}, "
                f"patterns={pattern_count}, "
                f"transformations={has_transformations}, "
                f"validation={has_validation}, "
                f"path={self.config_path})"
            )
        else:
            return (
                f"NamingPatternsLoader(version={version}, "
                f"patterns={pattern_count}, "
                f"transformations={has_transformations}, "
                f"validation={has_validation})"
            )


# Example usage
if __name__ == "__main__":
    # Load configuration
    loader = NamingPatternsLoader()
    loader.load_from_file("examples/configs/naming-patterns.yaml")

    print(f"Loaded: {loader}")
    print(f"Resource types: {loader.list_resource_types()}")

    # Get pattern for S3 bucket
    pattern = loader.get_pattern("aws_s3_bucket")
    print(f"\nS3 Bucket Pattern: {pattern.pattern}")
    print(f"Required variables: {pattern.required_variables}")

    # Apply transformations
    values = {
        "project": "Data-Platform",
        "purpose": "raw",
        "layer": "RAW",
        "environment": "PRD",
        "region": "us-east-1"
    }

    transformed = loader.apply_transformations(values)
    print(f"\nOriginal values: {values}")
    print(f"Transformed values: {transformed}")

    # Format pattern
    name = pattern.format(transformed)
    print(f"\nGenerated name: {name}")

    # Validate name
    errors = loader.validate_name("aws_s3_bucket", name)
    if errors:
        print(f"Validation errors: {errors}")
    else:
        print("Name is valid!")
