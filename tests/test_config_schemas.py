#!/usr/bin/env python3
"""
Tests for configuration schemas (naming-values and naming-patterns)
Validates JSON Schema definitions and example configurations
"""

import json
import pytest
import yaml
from pathlib import Path
from jsonschema import validate, ValidationError, Draft7Validator


# Get project root directory
PROJECT_ROOT = Path(__file__).parent.parent


class TestNamingValuesSchema:
    """Test naming-values-schema.json"""
    
    @pytest.fixture
    def schema(self):
        """Load naming-values schema"""
        schema_path = PROJECT_ROOT / "schemas" / "naming-values-schema.json"
        with open(schema_path) as f:
            return json.load(f)
    
    @pytest.fixture
    def example_config(self):
        """Load example naming-values.yaml"""
        config_path = PROJECT_ROOT / "examples" / "configs" / "naming-values.yaml"
        with open(config_path) as f:
            return yaml.safe_load(f)
    
    def test_schema_is_valid_json_schema(self, schema):
        """Verify the schema itself is valid JSON Schema Draft 7"""
        Draft7Validator.check_schema(schema)
    
    def test_schema_has_required_properties(self, schema):
        """Verify schema has all required top-level properties"""
        assert "$schema" in schema
        assert schema["$schema"] == "http://json-schema.org/draft-07/schema#"
        assert "title" in schema
        assert "description" in schema
        assert "type" in schema
        assert schema["type"] == "object"
        assert "required" in schema
        assert "version" in schema["required"]
        assert "defaults" in schema["required"]
    
    def test_example_config_validates(self, schema, example_config):
        """Verify example naming-values.yaml validates against schema"""
        validate(instance=example_config, schema=schema)
    
    def test_valid_minimal_config(self, schema):
        """Test minimal valid configuration"""
        config = {
            "version": "1.0",
            "defaults": {
                "project": "testproject",
                "environment": "dev"
            }
        }
        validate(instance=config, schema=schema)
    
    def test_valid_full_config(self, schema):
        """Test full configuration with all sections"""
        config = {
            "version": "1.0",
            "defaults": {
                "project": "dataplatform",
                "environment": "prd",
                "region": "us-east-1",
                "region_short": "use1",
                "team": "data-team",
                "cost_center": "CC-12345"
            },
            "environments": {
                "dev": {
                    "environment": "dev",
                    "data_classification": "internal"
                },
                "stg": {
                    "environment": "stg"
                },
                "prd": {
                    "environment": "prd",
                    "data_classification": "confidential"
                }
            },
            "resource_types": {
                "aws_s3_bucket": {
                    "purpose": "raw",
                    "layer": "raw"
                },
                "dbx_cluster": {
                    "workload": "etl"
                }
            }
        }
        validate(instance=config, schema=schema)
    
    def test_invalid_version(self, schema):
        """Test that invalid version is rejected"""
        config = {
            "version": "2.0",  # Invalid version
            "defaults": {"project": "test"}
        }
        with pytest.raises(ValidationError):
            validate(instance=config, schema=schema)
    
    def test_missing_required_version(self, schema):
        """Test that missing version is rejected"""
        config = {
            "defaults": {"project": "test"}
        }
        with pytest.raises(ValidationError):
            validate(instance=config, schema=schema)
    
    def test_missing_required_defaults(self, schema):
        """Test that missing defaults is rejected"""
        config = {
            "version": "1.0"
        }
        with pytest.raises(ValidationError):
            validate(instance=config, schema=schema)
    
    def test_invalid_environment_name(self, schema):
        """Test that invalid environment name is rejected"""
        config = {
            "version": "1.0",
            "defaults": {"project": "test"},
            "environments": {
                "production": {"environment": "production"}  # Invalid, should be 'prd'
            }
        }
        with pytest.raises(ValidationError):
            validate(instance=config, schema=schema)
    
    def test_invalid_project_format(self, schema):
        """Test that invalid project format is rejected"""
        config = {
            "version": "1.0",
            "defaults": {
                "project": "Data_Platform"  # Invalid: uppercase and underscore
            }
        }
        with pytest.raises(ValidationError):
            validate(instance=config, schema=schema)
    
    def test_valid_project_formats(self, schema):
        """Test various valid project name formats"""
        valid_projects = [
            "dataplatform",
            "data-platform",
            "platform123",
            "123platform",
            "data-platform-v2"
        ]
        for project in valid_projects:
            config = {
                "version": "1.0",
                "defaults": {"project": project}
            }
            validate(instance=config, schema=schema)
    
    def test_invalid_region_format(self, schema):
        """Test that invalid region format is rejected"""
        config = {
            "version": "1.0",
            "defaults": {
                "project": "test",
                "region": "us_east_1"  # Invalid: underscores instead of hyphens
            }
        }
        with pytest.raises(ValidationError):
            validate(instance=config, schema=schema)
    
    def test_valid_region_formats(self, schema):
        """Test various valid region formats"""
        valid_regions = [
            "us-east-1",
            "us-west-2",
            "eu-west-1",
            "ap-southeast-1"
        ]
        for region in valid_regions:
            config = {
                "version": "1.0",
                "defaults": {
                    "project": "test",
                    "region": region
                }
            }
            validate(instance=config, schema=schema)
    
    def test_custom_variables(self, schema):
        """Test that custom variables are allowed"""
        config = {
            "version": "1.0",
            "defaults": {
                "project": "test",
                "custom_field1": "value1",
                "custom_field2": "value2",
                "business_unit": "analytics"
            }
        }
        validate(instance=config, schema=schema)
    
    def test_valid_data_classification_values(self, schema):
        """Test all valid data classification values"""
        classifications = ["public", "internal", "confidential", "restricted"]
        for classification in classifications:
            config = {
                "version": "1.0",
                "defaults": {
                    "project": "test",
                    "data_classification": classification
                }
            }
            validate(instance=config, schema=schema)
    
    def test_invalid_data_classification(self, schema):
        """Test that invalid data classification is rejected"""
        config = {
            "version": "1.0",
            "defaults": {
                "project": "test",
                "data_classification": "secret"  # Invalid
            }
        }
        with pytest.raises(ValidationError):
            validate(instance=config, schema=schema)


class TestNamingPatternsSchema:
    """Test naming-patterns-schema.json"""
    
    @pytest.fixture
    def schema(self):
        """Load naming-patterns schema"""
        schema_path = PROJECT_ROOT / "schemas" / "naming-patterns-schema.json"
        with open(schema_path) as f:
            return json.load(f)
    
    @pytest.fixture
    def example_config(self):
        """Load example naming-patterns.yaml"""
        config_path = PROJECT_ROOT / "examples" / "configs" / "naming-patterns.yaml"
        with open(config_path) as f:
            return yaml.safe_load(f)
    
    def test_schema_is_valid_json_schema(self, schema):
        """Verify the schema itself is valid JSON Schema Draft 7"""
        Draft7Validator.check_schema(schema)
    
    def test_schema_has_required_properties(self, schema):
        """Verify schema has all required top-level properties"""
        assert "$schema" in schema
        assert schema["$schema"] == "http://json-schema.org/draft-07/schema#"
        assert "title" in schema
        assert "description" in schema
        assert "type" in schema
        assert schema["type"] == "object"
        assert "required" in schema
        assert "version" in schema["required"]
        assert "patterns" in schema["required"]
    
    def test_example_config_validates(self, schema, example_config):
        """Verify example naming-patterns.yaml validates against schema"""
        validate(instance=example_config, schema=schema)
    
    def test_valid_minimal_config(self, schema):
        """Test minimal valid configuration with all required patterns"""
        config = {
            "version": "1.0",
            "patterns": {
                "aws_s3_bucket": "{project}-{environment}",
                "aws_glue_database": "{project}_{environment}",
                "aws_glue_table": "{entity}",
                "dbx_cluster": "{project}-{environment}",
                "dbx_job": "{project}-{environment}",
                "dbx_catalog": "{project}_{environment}",
                "dbx_schema": "{domain}",
                "dbx_table": "{entity}"
            }
        }
        validate(instance=config, schema=schema)
    
    def test_missing_required_pattern(self, schema):
        """Test that missing required pattern is rejected"""
        config = {
            "version": "1.0",
            "patterns": {
                "aws_s3_bucket": "{project}-{environment}",
                # Missing other required patterns
            }
        }
        with pytest.raises(ValidationError):
            validate(instance=config, schema=schema)
    
    def test_invalid_pattern_no_placeholder(self, schema):
        """Test that pattern without placeholder is rejected"""
        config = {
            "version": "1.0",
            "patterns": {
                "aws_s3_bucket": "static-name",  # Invalid: no placeholder
                "aws_glue_database": "{project}_{environment}",
                "aws_glue_table": "{entity}",
                "dbx_cluster": "{project}-{environment}",
                "dbx_job": "{project}-{environment}",
                "dbx_catalog": "{project}_{environment}",
                "dbx_schema": "{domain}",
                "dbx_table": "{entity}"
            }
        }
        with pytest.raises(ValidationError):
            validate(instance=config, schema=schema)
    
    def test_valid_pattern_formats(self, schema):
        """Test various valid pattern formats"""
        valid_patterns = [
            "{project}-{environment}",
            "{project}_{domain}_{layer}",
            "{table_type}_{entity}",
            "{project}-{workload}-{cluster_type}-{environment}",
            "prefix-{project}-{environment}-suffix"
        ]
        for pattern in valid_patterns:
            config = {
                "version": "1.0",
                "patterns": {
                    "aws_s3_bucket": pattern,
                    "aws_glue_database": "{project}_{environment}",
                    "aws_glue_table": "{entity}",
                    "dbx_cluster": "{project}-{environment}",
                    "dbx_job": "{project}-{environment}",
                    "dbx_catalog": "{project}_{environment}",
                    "dbx_schema": "{domain}",
                    "dbx_table": "{entity}"
                }
            }
            validate(instance=config, schema=schema)
    
    def test_valid_transformations_section(self, schema):
        """Test valid transformations configuration"""
        config = {
            "version": "1.0",
            "patterns": {
                "aws_s3_bucket": "{project}-{environment}",
                "aws_glue_database": "{project}_{environment}",
                "aws_glue_table": "{entity}",
                "dbx_cluster": "{project}-{environment}",
                "dbx_job": "{project}-{environment}",
                "dbx_catalog": "{project}_{environment}",
                "dbx_schema": "{domain}",
                "dbx_table": "{entity}"
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
            }
        }
        validate(instance=config, schema=schema)
    
    def test_invalid_region_mapping_format(self, schema):
        """Test that invalid region mapping format is rejected"""
        config = {
            "version": "1.0",
            "patterns": {
                "aws_s3_bucket": "{project}-{environment}",
                "aws_glue_database": "{project}_{environment}",
                "aws_glue_table": "{entity}",
                "dbx_cluster": "{project}-{environment}",
                "dbx_job": "{project}-{environment}",
                "dbx_catalog": "{project}_{environment}",
                "dbx_schema": "{domain}",
                "dbx_table": "{entity}"
            },
            "transformations": {
                "region_mapping": {
                    "us_east_1": "use1"  # Invalid: underscores instead of hyphens
                }
            }
        }
        with pytest.raises(ValidationError):
            validate(instance=config, schema=schema)
    
    def test_valid_validation_section(self, schema):
        """Test valid validation rules configuration"""
        config = {
            "version": "1.0",
            "patterns": {
                "aws_s3_bucket": "{project}-{environment}",
                "aws_glue_database": "{project}_{environment}",
                "aws_glue_table": "{entity}",
                "dbx_cluster": "{project}-{environment}",
                "dbx_job": "{project}-{environment}",
                "dbx_catalog": "{project}_{environment}",
                "dbx_schema": "{domain}",
                "dbx_table": "{entity}"
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
                    "aws_s3_bucket": ["project", "environment"],
                    "dbx_cluster": ["project", "workload"]
                }
            }
        }
        validate(instance=config, schema=schema)
    
    def test_invalid_max_length_zero(self, schema):
        """Test that zero max_length is rejected"""
        config = {
            "version": "1.0",
            "patterns": {
                "aws_s3_bucket": "{project}-{environment}",
                "aws_glue_database": "{project}_{environment}",
                "aws_glue_table": "{entity}",
                "dbx_cluster": "{project}-{environment}",
                "dbx_job": "{project}-{environment}",
                "dbx_catalog": "{project}_{environment}",
                "dbx_schema": "{domain}",
                "dbx_table": "{entity}"
            },
            "validation": {
                "max_length": {
                    "aws_s3_bucket": 0  # Invalid: must be >= 1
                }
            }
        }
        with pytest.raises(ValidationError):
            validate(instance=config, schema=schema)
    
    def test_additional_pattern_not_allowed(self, schema):
        """Test that additional (unlisted) patterns are rejected"""
        config = {
            "version": "1.0",
            "patterns": {
                "aws_s3_bucket": "{project}-{environment}",
                "aws_glue_database": "{project}_{environment}",
                "aws_glue_table": "{entity}",
                "dbx_cluster": "{project}-{environment}",
                "dbx_job": "{project}-{environment}",
                "dbx_catalog": "{project}_{environment}",
                "dbx_schema": "{domain}",
                "dbx_table": "{entity}",
                "custom_resource": "{project}"  # Invalid: not allowed
            }
        }
        with pytest.raises(ValidationError):
            validate(instance=config, schema=schema)


class TestSchemaIntegration:
    """Integration tests for both schemas together"""
    
    def test_example_files_exist(self):
        """Verify all example files exist"""
        assert (PROJECT_ROOT / "schemas" / "naming-values-schema.json").exists()
        assert (PROJECT_ROOT / "schemas" / "naming-patterns-schema.json").exists()
        assert (PROJECT_ROOT / "examples" / "configs" / "naming-values.yaml").exists()
        assert (PROJECT_ROOT / "examples" / "configs" / "naming-patterns.yaml").exists()
    
    def test_schemas_directory_structure(self):
        """Verify schemas directory has expected structure"""
        schemas_dir = PROJECT_ROOT / "schemas"
        assert schemas_dir.exists()
        assert (schemas_dir / "README.md").exists()
        assert (schemas_dir / "naming-values-schema.json").exists()
        assert (schemas_dir / "naming-patterns-schema.json").exists()
    
    def test_examples_directory_structure(self):
        """Verify examples directory has expected structure"""
        examples_dir = PROJECT_ROOT / "examples" / "configs"
        assert examples_dir.exists()
        assert (examples_dir / "naming-values.yaml").exists()
        assert (examples_dir / "naming-patterns.yaml").exists()
    
    def test_both_examples_validate(self):
        """Verify both example files validate against their schemas"""
        # Load schemas
        with open(PROJECT_ROOT / "schemas" / "naming-values-schema.json") as f:
            values_schema = json.load(f)
        
        with open(PROJECT_ROOT / "schemas" / "naming-patterns-schema.json") as f:
            patterns_schema = json.load(f)
        
        # Load examples
        with open(PROJECT_ROOT / "examples" / "configs" / "naming-values.yaml") as f:
            values_config = yaml.safe_load(f)
        
        with open(PROJECT_ROOT / "examples" / "configs" / "naming-patterns.yaml") as f:
            patterns_config = yaml.safe_load(f)
        
        # Validate
        validate(instance=values_config, schema=values_schema)
        validate(instance=patterns_config, schema=patterns_schema)
    
    def test_schema_version_consistency(self):
        """Verify both schemas use same JSON Schema version"""
        with open(PROJECT_ROOT / "schemas" / "naming-values-schema.json") as f:
            values_schema = json.load(f)
        
        with open(PROJECT_ROOT / "schemas" / "naming-patterns-schema.json") as f:
            patterns_schema = json.load(f)
        
        assert values_schema["$schema"] == patterns_schema["$schema"]
        assert values_schema["$schema"] == "http://json-schema.org/draft-07/schema#"
    
    def test_example_version_consistency(self):
        """Verify both example files use same version"""
        with open(PROJECT_ROOT / "examples" / "configs" / "naming-values.yaml") as f:
            values_config = yaml.safe_load(f)
        
        with open(PROJECT_ROOT / "examples" / "configs" / "naming-patterns.yaml") as f:
            patterns_config = yaml.safe_load(f)
        
        assert values_config["version"] == patterns_config["version"]
        assert values_config["version"] == "1.0"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
