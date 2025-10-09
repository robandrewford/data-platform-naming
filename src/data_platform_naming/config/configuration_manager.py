#!/usr/bin/env python3
"""
ConfigurationManager - Orchestrate naming values and patterns.

This module provides a unified interface for managing naming configurations
by coordinating between NamingValuesLoader and NamingPatternsLoader.
"""

from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from .naming_values_loader import (
    NamingValuesLoader,
    NamingValues,
    ConfigurationError,
)
from .naming_patterns_loader import (
    NamingPatternsLoader,
    NamingPattern,
    PatternError,
)


@dataclass
class GeneratedName:
    """Container for a generated resource name with metadata"""
    name: str
    resource_type: str
    pattern_used: str
    values_used: Dict[str, Any]
    validation_errors: List[str]
    
    @property
    def is_valid(self) -> bool:
        """Check if name is valid (no validation errors)"""
        return len(self.validation_errors) == 0


class ConfigurationManager:
    """
    Unified interface for managing naming configurations.
    
    Orchestrates NamingValuesLoader and NamingPatternsLoader to:
    - Load both configurations from files or dicts
    - Generate resource names by combining values and patterns
    - Apply transformations
    - Validate generated names
    
    Example:
        >>> manager = ConfigurationManager()
        >>> manager.load_configs(
        ...     values_path="naming-values.yaml",
        ...     patterns_path="naming-patterns.yaml"
        ... )
        >>> result = manager.generate_name(
        ...     resource_type="aws_s3_bucket",
        ...     environment="prd"
        ... )
        >>> print(result.name)
        'dataplatform-raw-raw-prd-use1'
    """
    
    def __init__(
        self,
        values_loader: Optional[NamingValuesLoader] = None,
        patterns_loader: Optional[NamingPatternsLoader] = None
    ):
        """
        Initialize ConfigurationManager.
        
        Args:
            values_loader: Optional pre-configured NamingValuesLoader
            patterns_loader: Optional pre-configured NamingPatternsLoader
        """
        self.values_loader = values_loader or NamingValuesLoader()
        self.patterns_loader = patterns_loader or NamingPatternsLoader()
        self._values_loaded = False
        self._patterns_loaded = False
    
    def load_configs(
        self,
        values_path: Optional[Path] = None,
        patterns_path: Optional[Path] = None,
        values_dict: Optional[Dict[str, Any]] = None,
        patterns_dict: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Load both naming values and patterns configurations.
        
        Args:
            values_path: Path to naming values YAML file
            patterns_path: Path to naming patterns YAML file
            values_dict: Dictionary with naming values config (alternative to file)
            patterns_dict: Dictionary with naming patterns config (alternative to file)
            
        Raises:
            ConfigurationError: If neither paths nor dicts are provided
            FileLoadError: If files cannot be loaded
            SchemaValidationError: If configurations don't validate
        """
        # Load values
        if values_path:
            self.values_loader.load_from_file(values_path)
            self._values_loaded = True
        elif values_dict:
            self.values_loader.load_from_dict(values_dict)
            self._values_loaded = True
        else:
            raise ConfigurationError(
                "Must provide either values_path or values_dict"
            )
        
        # Load patterns
        if patterns_path:
            self.patterns_loader.load_from_file(patterns_path)
            self._patterns_loaded = True
        elif patterns_dict:
            self.patterns_loader.load_from_dict(patterns_dict)
            self._patterns_loaded = True
        else:
            raise ConfigurationError(
                "Must provide either patterns_path or patterns_dict"
            )
    
    def load_from_default_locations(self, base_dir: Optional[Path] = None) -> bool:
        """
        Load configurations from default locations.
        
        Default locations:
        - ~/.dpn/naming-values.yaml
        - ~/.dpn/naming-patterns.yaml
        
        Args:
            base_dir: Optional base directory (defaults to ~/.dpn/)
            
        Returns:
            True if configs were loaded, False if default files don't exist
            
        Raises:
            SchemaValidationError: If configurations don't validate
        """
        if base_dir is None:
            base_dir = Path.home() / ".dpn"
        
        values_path = base_dir / "naming-values.yaml"
        patterns_path = base_dir / "naming-patterns.yaml"
        
        if not (values_path.exists() and patterns_path.exists()):
            return False
        
        self.load_configs(
            values_path=values_path,
            patterns_path=patterns_path
        )
        return True
    
    def generate_name(
        self,
        resource_type: str,
        environment: Optional[str] = None,
        blueprint_metadata: Optional[Dict[str, Any]] = None,
        value_overrides: Optional[Dict[str, Any]] = None
    ) -> GeneratedName:
        """
        Generate a resource name by combining values and patterns.
        
        Process:
        1. Get values for resource type and environment
        2. Apply any value overrides
        3. Apply transformations
        4. Get pattern for resource type
        5. Format pattern with transformed values
        6. Validate generated name
        
        Args:
            resource_type: Resource type (e.g., 'aws_s3_bucket')
            environment: Optional environment code ('dev', 'stg', 'prd')
            blueprint_metadata: Optional blueprint metadata (highest precedence)
            value_overrides: Optional value overrides to apply
            
        Returns:
            GeneratedName object with name and metadata
            
        Raises:
            ConfigurationError: If configs not loaded
            PatternError: If pattern not found or variables missing
        """
        self._check_loaded()
        
        # Get merged values
        values = self.values_loader.get_values_for_resource(
            resource_type=resource_type,
            environment=environment,
            blueprint_metadata=blueprint_metadata
        )
        
        # Apply any additional overrides
        merged_values = dict(values.values)
        if value_overrides:
            merged_values.update(value_overrides)
        
        # Apply transformations
        transformed_values = self.patterns_loader.apply_transformations(
            merged_values
        )
        
        # Get pattern
        pattern = self.patterns_loader.get_pattern(resource_type)
        
        # Format pattern with values
        name = pattern.format(transformed_values)
        
        # Validate name
        validation_errors = self.patterns_loader.validate_name(
            resource_type, name
        )
        
        return GeneratedName(
            name=name,
            resource_type=resource_type,
            pattern_used=pattern.pattern,
            values_used=transformed_values,
            validation_errors=validation_errors
        )
    
    def generate_names_for_blueprint(
        self,
        resources: List[Dict[str, Any]],
        environment: Optional[str] = None,
        blueprint_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, GeneratedName]:
        """
        Generate names for all resources in a blueprint.
        
        Args:
            resources: List of resource definitions with 'type' field
            environment: Optional environment code
            blueprint_metadata: Optional blueprint-level metadata
            
        Returns:
            Dictionary mapping resource IDs to GeneratedName objects
            
        Raises:
            ConfigurationError: If configs not loaded
        """
        self._check_loaded()
        
        results = {}
        for resource in resources:
            resource_id = resource.get("id", resource.get("type"))
            resource_type = resource["type"]
            
            # Merge blueprint metadata with resource metadata
            resource_metadata = dict(blueprint_metadata or {})
            if "metadata" in resource:
                resource_metadata.update(resource["metadata"])
            
            try:
                result = self.generate_name(
                    resource_type=resource_type,
                    environment=environment,
                    blueprint_metadata=resource_metadata if resource_metadata else None
                )
                results[resource_id] = result
            except (PatternError, ConfigurationError) as e:
                # Store error as validation error
                results[resource_id] = GeneratedName(
                    name="",
                    resource_type=resource_type,
                    pattern_used="",
                    values_used={},
                    validation_errors=[str(e)]
                )
        
        return results
    
    def validate_configuration(self) -> List[str]:
        """
        Validate the loaded configuration.
        
        Checks:
        - All pattern variables have corresponding values
        - Required variables are defined
        - Patterns are valid
        
        Returns:
            List of validation warnings/errors (empty if valid)
        """
        self._check_loaded()
        
        warnings = []
        
        # Get all patterns
        patterns = self.patterns_loader.get_all_patterns()
        
        # Get default values to check against
        defaults = self.values_loader.get_defaults()
        
        # Check each pattern
        for resource_type, pattern in patterns.items():
            pattern_vars = pattern.get_variables()
            required_vars = set(pattern.required_variables)
            
            # Check if pattern variables are available in defaults
            # (environment and resource-type specific values may add more)
            missing_required = required_vars - set(defaults.keys())
            if missing_required:
                warnings.append(
                    f"{resource_type}: Required variables not in defaults: "
                    f"{', '.join(sorted(missing_required))}"
                )
            
            # Check for variables in pattern but not marked as required
            unmarked_vars = pattern_vars - required_vars
            if unmarked_vars and not defaults.keys() >= unmarked_vars:
                missing = unmarked_vars - set(defaults.keys())
                if missing:
                    warnings.append(
                        f"{resource_type}: Pattern uses variables not in defaults "
                        f"or required list: {', '.join(sorted(missing))}"
                    )
        
        return warnings
    
    def get_available_resource_types(self) -> List[str]:
        """
        Get list of resource types that have both values and patterns defined.
        
        Returns:
            List of resource type names
        """
        self._check_loaded()
        return self.patterns_loader.list_resource_types()
    
    def get_available_environments(self) -> List[str]:
        """
        Get list of configured environments.
        
        Returns:
            List of environment codes
        """
        self._check_loaded()
        return self.values_loader.list_environments()
    
    def preview_name(
        self,
        resource_type: str,
        values: Dict[str, Any]
    ) -> GeneratedName:
        """
        Preview a name with specific values (bypass value loading).
        
        Useful for testing or demonstrating naming without full config.
        
        Args:
            resource_type: Resource type
            values: Dictionary of values to use
            
        Returns:
            GeneratedName object
        """
        if not self._patterns_loaded:
            raise ConfigurationError("Patterns configuration not loaded")
        
        # Apply transformations
        transformed = self.patterns_loader.apply_transformations(values)
        
        # Get pattern
        pattern = self.patterns_loader.get_pattern(resource_type)
        
        # Format
        name = pattern.format(transformed)
        
        # Validate
        errors = self.patterns_loader.validate_name(resource_type, name)
        
        return GeneratedName(
            name=name,
            resource_type=resource_type,
            pattern_used=pattern.pattern,
            values_used=transformed,
            validation_errors=errors
        )
    
    def _check_loaded(self) -> None:
        """Check that both configurations are loaded"""
        if not self._values_loaded:
            raise ConfigurationError("Naming values configuration not loaded")
        if not self._patterns_loaded:
            raise ConfigurationError("Naming patterns configuration not loaded")
    
    @property
    def is_loaded(self) -> bool:
        """Check if both configurations are loaded"""
        return self._values_loaded and self._patterns_loaded
    
    def __repr__(self) -> str:
        """String representation of manager"""
        if not self.is_loaded:
            return "ConfigurationManager(not loaded)"
        
        values_version = self.values_loader.get_version()
        patterns_version = self.patterns_loader.get_version()
        resource_type_count = len(self.get_available_resource_types())
        environment_count = len(self.get_available_environments())
        
        return (
            f"ConfigurationManager("
            f"values_version={values_version}, "
            f"patterns_version={patterns_version}, "
            f"resource_types={resource_type_count}, "
            f"environments={environment_count})"
        )


# Example usage
if __name__ == "__main__":
    # Initialize manager
    manager = ConfigurationManager()
    
    # Load configurations
    manager.load_configs(
        values_path=Path("examples/configs/naming-values.yaml"),
        patterns_path=Path("examples/configs/naming-patterns.yaml")
    )
    
    print(f"Loaded: {manager}")
    print(f"Resource types: {manager.get_available_resource_types()}")
    print(f"Environments: {manager.get_available_environments()}")
    
    # Generate a name
    result = manager.generate_name(
        resource_type="aws_s3_bucket",
        environment="prd"
    )
    
    print(f"\nGenerated name: {result.name}")
    print(f"Pattern used: {result.pattern_used}")
    print(f"Valid: {result.is_valid}")
    
    if not result.is_valid:
        print(f"Validation errors: {result.validation_errors}")
    
    # Validate configuration
    warnings = manager.validate_configuration()
    if warnings:
        print(f"\nConfiguration warnings:")
        for warning in warnings:
            print(f"  - {warning}")
    else:
        print("\nConfiguration is valid!")
