#!/usr/bin/env python3
"""
Tests for ConfigurationManager class.
"""

import tempfile
from pathlib import Path

import pytest

from data_platform_naming.constants import Environment
from data_platform_naming.config.configuration_manager import (
    ConfigurationManager,
    GeneratedName,
)
from data_platform_naming.config.naming_patterns_loader import (
    PatternError,
)
from data_platform_naming.config.naming_values_loader import (
    ConfigurationError,
)


class TestGeneratedName:
    """Test GeneratedName dataclass"""

    def test_is_valid_no_errors(self):
        """Test is_valid when no validation errors"""
        name = GeneratedName(
            name="test-name",
            resource_type="aws_s3_bucket",
            pattern_used="{project}-{environment}",
            values_used={"project": "test", "environment": "dev"},
            validation_errors=[]
        )
        assert name.is_valid is True

    def test_is_valid_with_errors(self):
        """Test is_valid when validation errors present"""
        name = GeneratedName(
            name="test-name",
            resource_type="aws_s3_bucket",
            pattern_used="{project}-{environment}",
            values_used={"project": "test", "environment": "dev"},
            validation_errors=["Name too long"]
        )
        assert name.is_valid is False


class TestConfigurationManager:
    """Test ConfigurationManager class"""

    @pytest.fixture
    def values_config(self):
        """Valid values configuration"""
        return {
            "version": "1.0",
            "defaults": {
                "project": "testproject",
                "region": "us-east-1",
                "region_short": "use1"
            },
            "environments": {
                "dev": {
                    "environment": Environment.DEV.value
                },
                "prd": {
                    "environment": Environment.PRD.value
                }
            },
            "resource_types": {
                "aws_s3_bucket": {
                    "purpose": "raw",
                    "layer": "raw"
                }
            }
        }

    @pytest.fixture
    def patterns_config(self):
        """Valid patterns configuration with all 27 resource types"""
        return {
            "version": "1.0",
            "patterns": {
                # AWS (13)
                "aws_s3_bucket": "{project}-{purpose}-{layer}-{environment}-{region_short}",
                "aws_glue_database": "{project}_{environment}",
                "aws_glue_table": "{entity}",
                "aws_glue_crawler": "{project}-{environment}-crawler",
                "aws_lambda_function": "{project}-{environment}-{domain}",
                "aws_iam_role": "{project}-{environment}-role",
                "aws_iam_policy": "{project}-{environment}-policy",
                "aws_kinesis_stream": "{project}-{environment}-stream",
                "aws_kinesis_firehose": "{project}-{environment}-firehose",
                "aws_dynamodb_table": "{project}-{environment}-{entity}",
                "aws_sns_topic": "{project}-{environment}-topic",
                "aws_sqs_queue": "{project}-{environment}-queue",
                "aws_step_function": "{project}-{environment}-workflow",
                # Databricks (14)
                "dbx_workspace": "dbx-{project}-{environment}",
                "dbx_cluster": "{project}-{environment}",
                "dbx_job": "{project}-{environment}",
                "dbx_notebook_path": "/{project}/{environment}",
                "dbx_repo": "{project}-{environment}",
                "dbx_pipeline": "{project}-{environment}",
                "dbx_sql_warehouse": "{project}-{environment}",
                "dbx_catalog": "{project}_{environment}",
                "dbx_schema": "{domain}",
                "dbx_table": "{entity}",
                "dbx_volume": "{purpose}",
                "dbx_secret_scope": "{project}-{environment}",
                "dbx_instance_pool": "{project}-{environment}",
                "dbx_policy": "{project}-{environment}"
            },
            "transformations": {
                "region_mapping": {
                    "us-east-1": "use1"
                },
                "lowercase": ["project", "environment"]
            },
            "validation": {
                "max_length": {
                    "aws_s3_bucket": 63
                },
                "allowed_chars": {
                    "aws_s3_bucket": "^[a-z0-9-]+$"
                },
                "required_variables": {
                    "aws_s3_bucket": ["project", "purpose", "environment", "region_short"]
                }
            }
        }

    def test_init_default(self):
        """Test initialization with default loaders"""
        manager = ConfigurationManager()
        assert manager.values_loader is not None
        assert manager.patterns_loader is not None
        assert manager.is_loaded is False

    def test_init_with_custom_loaders(self):
        """Test initialization with custom loaders"""
        from data_platform_naming.config import NamingPatternsLoader, NamingValuesLoader

        values_loader = NamingValuesLoader()
        patterns_loader = NamingPatternsLoader()
        manager = ConfigurationManager(
            values_loader=values_loader,
            patterns_loader=patterns_loader
        )

        assert manager.values_loader is values_loader
        assert manager.patterns_loader is patterns_loader

    def test_load_configs_from_dicts(self, values_config, patterns_config):
        """Test loading configs from dictionaries"""
        manager = ConfigurationManager()
        manager.load_configs(
            values_dict=values_config,
            patterns_dict=patterns_config
        )

        assert manager.is_loaded is True
        assert manager._values_loaded is True
        assert manager._patterns_loaded is True

    def test_load_configs_missing_values(self, patterns_config):
        """Test loading without values config raises error"""
        manager = ConfigurationManager()

        with pytest.raises(ConfigurationError, match="values_path or values_dict"):
            manager.load_configs(patterns_dict=patterns_config)

    def test_load_configs_missing_patterns(self, values_config):
        """Test loading without patterns config raises error"""
        manager = ConfigurationManager()

        with pytest.raises(ConfigurationError, match="patterns_path or patterns_dict"):
            manager.load_configs(values_dict=values_config)

    def test_load_from_default_locations_not_exist(self):
        """Test loading from default locations when files don't exist"""
        manager = ConfigurationManager()

        # Use a temp dir that definitely doesn't have the files
        with tempfile.TemporaryDirectory() as tmpdir:
            result = manager.load_from_default_locations(Path(tmpdir))
            assert result is False
            assert manager.is_loaded is False

    def test_generate_name_simple(self, values_config, patterns_config):
        """Test generating a simple name"""
        manager = ConfigurationManager()
        manager.load_configs(
            values_dict=values_config,
            patterns_dict=patterns_config
        )

        result = manager.generate_name(
            resource_type="aws_s3_bucket",
            environment=Environment.PRD.value
        )

        assert result.is_valid
        assert result.name == "testproject-raw-raw-prd-use1"
        assert result.resource_type == "aws_s3_bucket"
        assert result.pattern_used == "{project}-{purpose}-{layer}-{environment}-{region_short}"

    def test_generate_name_with_overrides(self, values_config, patterns_config):
        """Test generating name with value overrides"""
        manager = ConfigurationManager()
        manager.load_configs(
            values_dict=values_config,
            patterns_dict=patterns_config
        )

        result = manager.generate_name(
            resource_type="aws_s3_bucket",
            environment=Environment.PRD.value,
            value_overrides={"purpose": "processed"}
        )

        assert result.is_valid
        assert result.name == "testproject-processed-raw-prd-use1"

    def test_generate_name_with_blueprint_metadata(self, values_config, patterns_config):
        """Test generating name with blueprint metadata"""
        manager = ConfigurationManager()
        manager.load_configs(
            values_dict=values_config,
            patterns_dict=patterns_config
        )

        result = manager.generate_name(
            resource_type="aws_s3_bucket",
            environment=Environment.PRD.value,
            blueprint_metadata={"layer": "gold"}
        )

        assert result.is_valid
        assert result.name == "testproject-raw-gold-prd-use1"

    def test_generate_name_not_loaded(self):
        """Test generating name before loading configs"""
        manager = ConfigurationManager()

        with pytest.raises(ConfigurationError, match="not loaded"):
            manager.generate_name("aws_s3_bucket")

    def test_generate_name_invalid_resource_type(self, values_config, patterns_config):
        """Test generating name for non-existent resource type"""
        manager = ConfigurationManager()
        manager.load_configs(
            values_dict=values_config,
            patterns_dict=patterns_config
        )

        with pytest.raises(PatternError, match="No pattern defined"):
            manager.generate_name("nonexistent_type")

    def test_generate_names_for_blueprint(self, values_config, patterns_config):
        """Test generating names for multiple resources"""
        manager = ConfigurationManager()
        manager.load_configs(
            values_dict=values_config,
            patterns_dict=patterns_config
        )

        resources = [
            {
                "id": "bucket1",
                "type": "aws_s3_bucket"
            },
            {
                "id": "bucket2",
                "type": "aws_s3_bucket",
                "metadata": {"purpose": "processed"}
            }
        ]

        results = manager.generate_names_for_blueprint(
            resources=resources,
            environment=Environment.PRD.value
        )

        assert len(results) == 2
        assert "bucket1" in results
        assert "bucket2" in results
        assert results["bucket1"].is_valid
        assert results["bucket2"].is_valid
        assert "raw" in results["bucket1"].name
        assert "processed" in results["bucket2"].name

    def test_generate_names_for_blueprint_with_errors(self, values_config, patterns_config):
        """Test generating names when some resources have errors"""
        manager = ConfigurationManager()
        manager.load_configs(
            values_dict=values_config,
            patterns_dict=patterns_config
        )

        resources = [
            {"id": "valid", "type": "aws_s3_bucket"},
            {"id": "invalid", "type": "nonexistent_type"}
        ]

        results = manager.generate_names_for_blueprint(
            resources=resources,
            environment=Environment.PRD.value
        )

        assert len(results) == 2
        assert results["valid"].is_valid
        assert not results["invalid"].is_valid
        assert len(results["invalid"].validation_errors) > 0

    def test_validate_configuration_valid(self, values_config, patterns_config):
        """Test configuration validation when valid"""
        manager = ConfigurationManager()
        manager.load_configs(
            values_dict=values_config,
            patterns_dict=patterns_config
        )

        warnings = manager.validate_configuration()
        # May have warnings about other resource types missing variables
        assert isinstance(warnings, list)

    def test_validate_configuration_missing_variables(self):
        """Test configuration validation with missing variables"""
        values_config = {
            "version": "1.0",
            "defaults": {
                "project": "test"
                # Missing other variables
            }
        }

        patterns_config = {
            "version": "1.0",
            "patterns": {
                # AWS (13)
                "aws_s3_bucket": "{project}-{missing_var}",
                "aws_glue_database": "{project}",
                "aws_glue_table": "{entity}",
                "aws_glue_crawler": "{project}",
                "aws_lambda_function": "{project}",
                "aws_iam_role": "{project}",
                "aws_iam_policy": "{project}",
                "aws_kinesis_stream": "{project}",
                "aws_kinesis_firehose": "{project}",
                "aws_dynamodb_table": "{project}",
                "aws_sns_topic": "{project}",
                "aws_sqs_queue": "{project}",
                "aws_step_function": "{project}",
                # Databricks (14)
                "dbx_workspace": "{project}",
                "dbx_cluster": "{project}",
                "dbx_job": "{project}",
                "dbx_notebook_path": "/{project}",
                "dbx_repo": "{project}",
                "dbx_pipeline": "{project}",
                "dbx_sql_warehouse": "{project}",
                "dbx_catalog": "{project}",
                "dbx_schema": "{domain}",
                "dbx_table": "{entity}",
                "dbx_volume": "{project}",
                "dbx_secret_scope": "{project}",
                "dbx_instance_pool": "{project}",
                "dbx_policy": "{project}"
            },
            "validation": {
                "required_variables": {
                    "aws_s3_bucket": ["project", "missing_var"]
                }
            }
        }

        manager = ConfigurationManager()
        manager.load_configs(
            values_dict=values_config,
            patterns_dict=patterns_config
        )

        warnings = manager.validate_configuration()
        assert len(warnings) > 0
        assert any("missing_var" in w for w in warnings)

    def test_get_available_resource_types(self, values_config, patterns_config):
        """Test getting available resource types"""
        manager = ConfigurationManager()
        manager.load_configs(
            values_dict=values_config,
            patterns_dict=patterns_config
        )

        types = manager.get_available_resource_types()
        assert "aws_s3_bucket" in types
        assert len(types) == 27

    def test_get_available_environments(self, values_config, patterns_config):
        """Test getting available environments"""
        manager = ConfigurationManager()
        manager.load_configs(
            values_dict=values_config,
            patterns_dict=patterns_config
        )

        environments = manager.get_available_environments()
        assert Environment.DEV.value in environments
        assert Environment.PRD.value in environments
        assert len(environments) == 2

    def test_preview_name(self, patterns_config):
        """Test previewing a name with custom values"""
        manager = ConfigurationManager()
        # Only load patterns for preview
        manager.load_configs(
            values_dict={"version": "1.0", "defaults": {}},
            patterns_dict=patterns_config
        )

        result = manager.preview_name(
            resource_type="aws_s3_bucket",
            values={
                "project": "myproject",
                "purpose": "raw",
                "layer": "bronze",
                "environment": Environment.DEV.value,
                "region": "us-east-1"
            }
        )

        assert result.is_valid
        assert result.name == "myproject-raw-bronze-dev-use1"

    def test_preview_name_patterns_not_loaded(self):
        """Test preview when patterns not loaded"""
        manager = ConfigurationManager()

        with pytest.raises(ConfigurationError, match="Patterns configuration not loaded"):
            manager.preview_name("aws_s3_bucket", {})

    def test_repr_not_loaded(self):
        """Test string representation when not loaded"""
        manager = ConfigurationManager()
        assert repr(manager) == "ConfigurationManager(not loaded)"

    def test_repr_loaded(self, values_config, patterns_config):
        """Test string representation when loaded"""
        manager = ConfigurationManager()
        manager.load_configs(
            values_dict=values_config,
            patterns_dict=patterns_config
        )

        repr_str = repr(manager)
        assert "ConfigurationManager" in repr_str
        assert "values_version=1.0" in repr_str
        assert "patterns_version=1.0" in repr_str
        assert "resource_types=27" in repr_str
        assert "environments=2" in repr_str

    def test_check_loaded_values_not_loaded(self, patterns_config):
        """Test _check_loaded when values not loaded"""
        manager = ConfigurationManager()
        manager.patterns_loader.load_from_dict(patterns_config)
        manager._patterns_loaded = True

        with pytest.raises(ConfigurationError, match="values.*not loaded"):
            manager._check_loaded()

    def test_check_loaded_patterns_not_loaded(self, values_config):
        """Test _check_loaded when patterns not loaded"""
        manager = ConfigurationManager()
        manager.values_loader.load_from_dict(values_config)
        manager._values_loaded = True

        with pytest.raises(ConfigurationError, match="patterns.*not loaded"):
            manager._check_loaded()

    def test_integration_with_transformations(self, values_config, patterns_config):
        """Test full integration with transformations applied"""
        # Use valid lowercase values that will be transformed
        values_config["defaults"]["project"] = "data-platform"
        values_config["defaults"]["environment"] = Environment.PRD.value

        manager = ConfigurationManager()
        manager.load_configs(
            values_dict=values_config,
            patterns_dict=patterns_config
        )

        # Test with value overrides that need transformation
        result = manager.generate_name(
            resource_type="aws_s3_bucket",
            environment=Environment.PRD.value
        )

        # Transformations applied correctly
        assert result.is_valid
        assert result.name.startswith("data-platform")
        assert Environment.PRD.value in result.name

    def test_validation_errors_in_generated_name(self):
        """Test that validation errors are captured in GeneratedName"""
        values_config = {
            "version": "1.0",
            "defaults": {
                "project": "a" * 100,  # Way too long
                "purpose": "raw",
                "layer": "raw",
                "environment": Environment.PRD.value,
                "region": "us-east-1",
                "region_short": "use1"
            }
        }

        patterns_config = {
            "version": "1.0",
            "patterns": {
                # AWS (13)
                "aws_s3_bucket": "{project}-{purpose}-{layer}-{environment}-{region_short}",
                "aws_glue_database": "{project}",
                "aws_glue_table": "{entity}",
                "aws_glue_crawler": "{project}",
                "aws_lambda_function": "{project}",
                "aws_iam_role": "{project}",
                "aws_iam_policy": "{project}",
                "aws_kinesis_stream": "{project}",
                "aws_kinesis_firehose": "{project}",
                "aws_dynamodb_table": "{project}",
                "aws_sns_topic": "{project}",
                "aws_sqs_queue": "{project}",
                "aws_step_function": "{project}",
                # Databricks (14)
                "dbx_workspace": "{project}",
                "dbx_cluster": "{project}",
                "dbx_job": "{project}",
                "dbx_notebook_path": "/{project}",
                "dbx_repo": "{project}",
                "dbx_pipeline": "{project}",
                "dbx_sql_warehouse": "{project}",
                "dbx_catalog": "{project}",
                "dbx_schema": "{domain}",
                "dbx_table": "{entity}",
                "dbx_volume": "{project}",
                "dbx_secret_scope": "{project}",
                "dbx_instance_pool": "{project}",
                "dbx_policy": "{project}"
            },
            "validation": {
                "max_length": {
                    "aws_s3_bucket": 63
                }
            }
        }

        manager = ConfigurationManager()
        manager.load_configs(
            values_dict=values_config,
            patterns_dict=patterns_config
        )

        result = manager.generate_name("aws_s3_bucket")

        assert not result.is_valid
        assert len(result.validation_errors) > 0
        assert "exceeds maximum length" in result.validation_errors[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
