#!/usr/bin/env python3
"""
Tests for NamingPatternsLoader class.
"""

import pytest
import yaml
import tempfile
from pathlib import Path
from data_platform_naming.config.naming_patterns_loader import (
    NamingPatternsLoader,
    NamingPattern,
    PatternError,
)
from data_platform_naming.config.naming_values_loader import (
    ConfigurationError,
    SchemaValidationError,
    FileLoadError,
)


class TestNamingPattern:
    """Test NamingPattern dataclass"""
    
    def test_get_variables(self):
        """Test extracting variables from pattern"""
        pattern = NamingPattern(
            pattern="{project}-{environment}-{region}",
            resource_type="test",
            required_variables=[]
        )
        variables = pattern.get_variables()
        assert "project" in variables
        assert "environment" in variables
        assert "region" in variables
        assert len(variables) == 3
    
    def test_validate_variables_all_present(self):
        """Test variable validation when all variables are present"""
        pattern = NamingPattern(
            pattern="{project}-{environment}",
            resource_type="test",
            required_variables=[]
        )
        available = {"project": "test", "environment": "dev", "extra": "value"}
        missing = pattern.validate_variables(available)
        assert missing == []
    
    def test_validate_variables_missing(self):
        """Test variable validation when variables are missing"""
        pattern = NamingPattern(
            pattern="{project}-{environment}-{region}",
            resource_type="test",
            required_variables=[]
        )
        available = {"project": "test"}
        missing = pattern.validate_variables(available)
        assert "environment" in missing
        assert "region" in missing
        assert len(missing) == 2
    
    def test_format_success(self):
        """Test successful pattern formatting"""
        pattern = NamingPattern(
            pattern="{project}-{environment}",
            resource_type="test",
            required_variables=[]
        )
        values = {"project": "myproject", "environment": "prd"}
        result = pattern.format(values)
        assert result == "myproject-prd"
    
    def test_format_missing_variables(self):
        """Test formatting with missing variables raises error"""
        pattern = NamingPattern(
            pattern="{project}-{environment}",
            resource_type="test",
            required_variables=[]
        )
        values = {"project": "myproject"}  # Missing environment
        
        with pytest.raises(PatternError, match="Missing required variables"):
            pattern.format(values)


class TestNamingPatternsLoader:
    """Test NamingPatternsLoader class"""
    
    @pytest.fixture
    def valid_config(self):
        """Valid configuration dict"""
        return {
            "version": "1.0",
            "patterns": {
                "aws_s3_bucket": "{project}-{purpose}-{environment}",
                "aws_glue_database": "{project}_{domain}_{environment}",
                "aws_glue_table": "{table_type}_{entity}",
                "dbx_cluster": "{project}-{workload}-{environment}",
                "dbx_job": "{project}-{job_type}-{environment}",
                "dbx_catalog": "{project}_{catalog_type}_{environment}",
                "dbx_schema": "{domain}_{layer}",
                "dbx_table": "{table_type}_{entity}"
            },
            "transformations": {
                "region_mapping": {
                    "us-east-1": "use1",
                    "us-west-2": "usw2"
                },
                "lowercase": ["project", "environment"],
                "uppercase": ["cost_center"],
                "replace_hyphens": {
                    "project": "_"
                }
            },
            "validation": {
                "max_length": {
                    "aws_s3_bucket": 63,
                    "dbx_cluster": 100
                },
                "allowed_chars": {
                    "aws_s3_bucket": "^[a-z0-9-]+$",
                    "aws_glue_database": "^[a-z0-9_]+$"
                },
                "required_variables": {
                    "aws_s3_bucket": ["project", "purpose", "environment"],
                    "dbx_cluster": ["project", "workload", "environment"]
                }
            }
        }
    
    @pytest.fixture
    def temp_yaml_file(self, valid_config):
        """Create temporary YAML file"""
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.yaml',
            delete=False
        ) as f:
            yaml.dump(valid_config, f)
            temp_path = Path(f.name)
        
        yield temp_path
        
        # Cleanup
        if temp_path.exists():
            temp_path.unlink()
    
    def test_init_with_default_schema(self):
        """Test initialization with default schema"""
        loader = NamingPatternsLoader()
        assert loader.config is None
        assert loader.schema is not None
        assert loader.config_path is None
    
    def test_init_with_custom_schema(self):
        """Test initialization with custom schema path"""
        schema_path = Path(__file__).parent.parent / "schemas" / "naming-patterns-schema.json"
        loader = NamingPatternsLoader(schema_path=schema_path)
        assert loader.schema is not None
    
    def test_load_from_dict_valid(self, valid_config):
        """Test loading valid configuration from dict"""
        loader = NamingPatternsLoader()
        loader.load_from_dict(valid_config)
        
        assert loader.config == valid_config
        assert loader.config_path is None
    
    def test_load_from_dict_invalid_version(self):
        """Test loading invalid configuration (bad version)"""
        invalid_config = {
            "version": "2.0",  # Invalid
            "patterns": {
                "aws_s3_bucket": "{project}",
                "aws_glue_database": "{project}",
                "aws_glue_table": "{entity}",
                "dbx_cluster": "{project}",
                "dbx_job": "{project}",
                "dbx_catalog": "{project}",
                "dbx_schema": "{domain}",
                "dbx_table": "{entity}"
            }
        }
        
        loader = NamingPatternsLoader()
        with pytest.raises(SchemaValidationError):
            loader.load_from_dict(invalid_config)
    
    def test_load_from_dict_missing_required_patterns(self):
        """Test loading configuration missing required patterns"""
        invalid_config = {
            "version": "1.0",
            "patterns": {
                "aws_s3_bucket": "{project}"
                # Missing other required patterns
            }
        }
        
        loader = NamingPatternsLoader()
        with pytest.raises(SchemaValidationError):
            loader.load_from_dict(invalid_config)
    
    def test_load_from_file_valid(self, temp_yaml_file):
        """Test loading valid configuration from file"""
        loader = NamingPatternsLoader()
        loader.load_from_file(temp_yaml_file)
        
        assert loader.config is not None
        assert loader.config_path == temp_yaml_file
    
    def test_load_from_file_not_found(self):
        """Test loading from non-existent file"""
        loader = NamingPatternsLoader()
        
        with pytest.raises(FileLoadError, match="not found"):
            loader.load_from_file(Path("/nonexistent/file.yaml"))
    
    def test_load_from_file_invalid_yaml(self):
        """Test loading invalid YAML file"""
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.yaml',
            delete=False
        ) as f:
            f.write("invalid: yaml: content: [")
            temp_path = Path(f.name)
        
        try:
            loader = NamingPatternsLoader()
            with pytest.raises(FileLoadError, match="Invalid YAML"):
                loader.load_from_file(temp_path)
        finally:
            if temp_path.exists():
                temp_path.unlink()
    
    def test_get_pattern_success(self, valid_config):
        """Test getting a pattern successfully"""
        loader = NamingPatternsLoader()
        loader.load_from_dict(valid_config)
        
        pattern = loader.get_pattern("aws_s3_bucket")
        assert pattern.pattern == "{project}-{purpose}-{environment}"
        assert pattern.resource_type == "aws_s3_bucket"
        assert "project" in pattern.required_variables
    
    def test_get_pattern_not_found(self, valid_config):
        """Test getting a pattern that doesn't exist"""
        loader = NamingPatternsLoader()
        loader.load_from_dict(valid_config)
        
        with pytest.raises(PatternError, match="No pattern defined"):
            loader.get_pattern("nonexistent_resource")
    
    def test_get_pattern_no_config_loaded(self):
        """Test getting pattern before loading config"""
        loader = NamingPatternsLoader()
        
        with pytest.raises(ConfigurationError, match="No configuration loaded"):
            loader.get_pattern("aws_s3_bucket")
    
    def test_get_all_patterns(self, valid_config):
        """Test getting all patterns"""
        loader = NamingPatternsLoader()
        loader.load_from_dict(valid_config)
        
        patterns = loader.get_all_patterns()
        assert len(patterns) == 8
        assert "aws_s3_bucket" in patterns
        assert "dbx_cluster" in patterns
        assert all(isinstance(p, NamingPattern) for p in patterns.values())
    
    def test_apply_transformations_region_mapping(self, valid_config):
        """Test region mapping transformation"""
        loader = NamingPatternsLoader()
        loader.load_from_dict(valid_config)
        
        values = {"region": "us-east-1", "other": "value"}
        transformed = loader.apply_transformations(values)
        
        assert transformed["region"] == "us-east-1"  # Original preserved
        assert transformed["region_short"] == "use1"  # Mapped value added
    
    def test_apply_transformations_lowercase(self, valid_config):
        """Test lowercase transformation"""
        loader = NamingPatternsLoader()
        loader.load_from_dict(valid_config)
        
        values = {"project": "MyProject", "environment": "PRD"}
        transformed = loader.apply_transformations(values)
        
        assert transformed["project"] == "myproject"
        assert transformed["environment"] == "prd"
    
    def test_apply_transformations_uppercase(self, valid_config):
        """Test uppercase transformation"""
        loader = NamingPatternsLoader()
        loader.load_from_dict(valid_config)
        
        values = {"cost_center": "cc-123"}
        transformed = loader.apply_transformations(values)
        
        assert transformed["cost_center"] == "CC-123"
    
    def test_apply_transformations_replace_hyphens(self, valid_config):
        """Test hyphen replacement transformation"""
        loader = NamingPatternsLoader()
        loader.load_from_dict(valid_config)
        
        values = {"project": "data-platform"}
        transformed = loader.apply_transformations(values)
        
        assert transformed["project"] == "data_platform"
    
    def test_apply_transformations_combined(self, valid_config):
        """Test multiple transformations applied together"""
        loader = NamingPatternsLoader()
        loader.load_from_dict(valid_config)
        
        values = {
            "project": "Data-Platform",  # Will be lowercased and hyphens replaced
            "environment": "PRD",  # Will be lowercased
            "region": "us-west-2",  # Will be mapped
            "cost_center": "cc-123"  # Will be uppercased
        }
        transformed = loader.apply_transformations(values)
        
        assert transformed["project"] == "data_platform"
        assert transformed["environment"] == "prd"
        assert transformed["region_short"] == "usw2"
        assert transformed["cost_center"] == "CC-123"
    
    def test_get_max_length(self, valid_config):
        """Test getting max length constraint"""
        loader = NamingPatternsLoader()
        loader.load_from_dict(valid_config)
        
        assert loader.get_max_length("aws_s3_bucket") == 63
        assert loader.get_max_length("dbx_cluster") == 100
        assert loader.get_max_length("unknown_type") is None
    
    def test_get_allowed_chars_pattern(self, valid_config):
        """Test getting allowed characters pattern"""
        loader = NamingPatternsLoader()
        loader.load_from_dict(valid_config)
        
        assert loader.get_allowed_chars_pattern("aws_s3_bucket") == "^[a-z0-9-]+$"
        assert loader.get_allowed_chars_pattern("aws_glue_database") == "^[a-z0-9_]+$"
        assert loader.get_allowed_chars_pattern("unknown_type") is None
    
    def test_get_required_variables(self, valid_config):
        """Test getting required variables"""
        loader = NamingPatternsLoader()
        loader.load_from_dict(valid_config)
        
        s3_vars = loader.get_required_variables("aws_s3_bucket")
        assert "project" in s3_vars
        assert "purpose" in s3_vars
        assert "environment" in s3_vars
        
        # Unknown type returns empty list
        assert loader.get_required_variables("unknown_type") == []
    
    def test_validate_name_valid(self, valid_config):
        """Test name validation for valid name"""
        loader = NamingPatternsLoader()
        loader.load_from_dict(valid_config)
        
        errors = loader.validate_name("aws_s3_bucket", "myproject-raw-prd")
        assert errors == []
    
    def test_validate_name_too_long(self, valid_config):
        """Test name validation for name exceeding max length"""
        loader = NamingPatternsLoader()
        loader.load_from_dict(valid_config)
        
        long_name = "a" * 100  # Exceeds 63 character limit for S3
        errors = loader.validate_name("aws_s3_bucket", long_name)
        assert len(errors) > 0
        assert "exceeds maximum length" in errors[0]
    
    def test_validate_name_invalid_chars(self, valid_config):
        """Test name validation for invalid characters"""
        loader = NamingPatternsLoader()
        loader.load_from_dict(valid_config)
        
        invalid_name = "MyProject_RAW"  # Uppercase and underscore not allowed for S3
        errors = loader.validate_name("aws_s3_bucket", invalid_name)
        assert len(errors) > 0
        assert "invalid characters" in errors[0]
    
    def test_list_resource_types(self, valid_config):
        """Test listing resource types"""
        loader = NamingPatternsLoader()
        loader.load_from_dict(valid_config)
        
        types = loader.list_resource_types()
        assert "aws_s3_bucket" in types
        assert "dbx_cluster" in types
        assert len(types) == 8
    
    def test_get_version(self, valid_config):
        """Test getting configuration version"""
        loader = NamingPatternsLoader()
        loader.load_from_dict(valid_config)
        
        assert loader.get_version() == "1.0"
    
    def test_repr_no_config(self):
        """Test string representation with no config"""
        loader = NamingPatternsLoader()
        assert repr(loader) == "NamingPatternsLoader(no config loaded)"
    
    def test_repr_with_config_from_dict(self, valid_config):
        """Test string representation with config from dict"""
        loader = NamingPatternsLoader()
        loader.load_from_dict(valid_config)
        
        repr_str = repr(loader)
        assert "version=1.0" in repr_str
        assert "patterns=8" in repr_str
        assert "transformations=True" in repr_str
        assert "validation=True" in repr_str
        assert "path=" not in repr_str  # No path when loaded from dict
    
    def test_repr_with_config_from_file(self, temp_yaml_file):
        """Test string representation with config from file"""
        loader = NamingPatternsLoader()
        loader.load_from_file(temp_yaml_file)
        
        repr_str = repr(loader)
        assert "version=1.0" in repr_str
        assert "patterns=8" in repr_str
        assert "path=" in repr_str
        assert str(temp_yaml_file) in repr_str
    
    def test_minimal_valid_config(self):
        """Test with minimal valid configuration (no transformations/validation)"""
        minimal_config = {
            "version": "1.0",
            "patterns": {
                "aws_s3_bucket": "{project}",
                "aws_glue_database": "{project}",
                "aws_glue_table": "{entity}",
                "dbx_cluster": "{project}",
                "dbx_job": "{project}",
                "dbx_catalog": "{project}",
                "dbx_schema": "{domain}",
                "dbx_table": "{entity}"
            }
        }
        
        loader = NamingPatternsLoader()
        loader.load_from_dict(minimal_config)
        
        pattern = loader.get_pattern("aws_s3_bucket")
        assert pattern.pattern == "{project}"
        
        # No transformations/validation defined
        assert loader.get_max_length("aws_s3_bucket") is None
        assert loader.get_allowed_chars_pattern("aws_s3_bucket") is None
        assert loader.get_required_variables("aws_s3_bucket") == []
    
    def test_pattern_with_no_placeholder_rejected(self):
        """Test that pattern without placeholder is rejected by schema"""
        invalid_config = {
            "version": "1.0",
            "patterns": {
                "aws_s3_bucket": "static-name",  # No placeholder
                "aws_glue_database": "{project}",
                "aws_glue_table": "{entity}",
                "dbx_cluster": "{project}",
                "dbx_job": "{project}",
                "dbx_catalog": "{project}",
                "dbx_schema": "{domain}",
                "dbx_table": "{entity}"
            }
        }
        
        loader = NamingPatternsLoader()
        with pytest.raises(SchemaValidationError):
            loader.load_from_dict(invalid_config)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
