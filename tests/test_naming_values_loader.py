#!/usr/bin/env python3
"""
Tests for NamingValuesLoader class.
"""

import pytest
import yaml
import tempfile
from pathlib import Path
from data_platform_naming.config.naming_values_loader import (
    NamingValuesLoader,
    NamingValues,
    ConfigurationError,
    SchemaValidationError,
    FileLoadError,
)


class TestNamingValues:
    """Test NamingValues dataclass"""
    
    def test_get_with_default(self):
        """Test get method with default value"""
        values = NamingValues(
            values={"project": "test"},
            source="defaults"
        )
        assert values.get("project") == "test"
        assert values.get("missing", "default") == "default"
    
    def test_getitem(self):
        """Test __getitem__ method"""
        values = NamingValues(
            values={"project": "test"},
            source="defaults"
        )
        assert values["project"] == "test"
        
        with pytest.raises(KeyError):
            _ = values["missing"]
    
    def test_contains(self):
        """Test __contains__ method"""
        values = NamingValues(
            values={"project": "test"},
            source="defaults"
        )
        assert "project" in values
        assert "missing" not in values
    
    def test_keys(self):
        """Test keys method"""
        values = NamingValues(
            values={"project": "test", "environment": "dev"},
            source="defaults"
        )
        keys = values.keys()
        assert "project" in keys
        assert "environment" in keys
        assert len(keys) == 2


class TestNamingValuesLoader:
    """Test NamingValuesLoader class"""
    
    @pytest.fixture
    def valid_config(self):
        """Valid configuration dict"""
        return {
            "version": "1.0",
            "defaults": {
                "project": "testproject",
                "region": "us-east-1",
                "region_short": "use1",
                "team": "test-team"
            },
            "environments": {
                "dev": {
                    "environment": "dev",
                    "data_classification": "internal"
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
        loader = NamingValuesLoader()
        assert loader.config is None
        assert loader.schema is not None
        assert loader.config_path is None
    
    def test_init_with_custom_schema(self):
        """Test initialization with custom schema path"""
        # Use the actual schema file
        schema_path = Path(__file__).parent.parent / "schemas" / "naming-values-schema.json"
        loader = NamingValuesLoader(schema_path=schema_path)
        assert loader.schema is not None
    
    def test_load_from_dict_valid(self, valid_config):
        """Test loading valid configuration from dict"""
        loader = NamingValuesLoader()
        loader.load_from_dict(valid_config)
        
        assert loader.config == valid_config
        assert loader.config_path is None
    
    def test_load_from_dict_invalid_version(self):
        """Test loading invalid configuration (bad version)"""
        invalid_config = {
            "version": "2.0",  # Invalid
            "defaults": {"project": "test"}
        }
        
        loader = NamingValuesLoader()
        with pytest.raises(SchemaValidationError):
            loader.load_from_dict(invalid_config)
    
    def test_load_from_dict_missing_required(self):
        """Test loading configuration missing required fields"""
        invalid_config = {
            "version": "1.0"
            # Missing defaults
        }
        
        loader = NamingValuesLoader()
        with pytest.raises(SchemaValidationError):
            loader.load_from_dict(invalid_config)
    
    def test_load_from_file_valid(self, temp_yaml_file):
        """Test loading valid configuration from file"""
        loader = NamingValuesLoader()
        loader.load_from_file(temp_yaml_file)
        
        assert loader.config is not None
        assert loader.config_path == temp_yaml_file
    
    def test_load_from_file_not_found(self):
        """Test loading from non-existent file"""
        loader = NamingValuesLoader()
        
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
            loader = NamingValuesLoader()
            with pytest.raises(FileLoadError, match="Invalid YAML"):
                loader.load_from_file(temp_path)
        finally:
            if temp_path.exists():
                temp_path.unlink()
    
    def test_get_values_for_resource_defaults_only(self, valid_config):
        """Test getting values with only defaults"""
        loader = NamingValuesLoader()
        loader.load_from_dict(valid_config)
        
        values = loader.get_values_for_resource(
            resource_type="custom_resource"
        )
        
        assert values.get("project") == "testproject"
        assert values.get("region") == "us-east-1"
        assert values.source == "defaults"
    
    def test_get_values_for_resource_with_environment(self, valid_config):
        """Test getting values with environment override"""
        loader = NamingValuesLoader()
        loader.load_from_dict(valid_config)
        
        values = loader.get_values_for_resource(
            resource_type="custom_resource",
            environment="prd"
        )
        
        assert values.get("project") == "testproject"  # from defaults
        assert values.get("environment") == "prd"  # from environment
        assert values.get("data_classification") == "confidential"  # from environment
        assert "defaults < environments.prd" in values.source
    
    def test_get_values_for_resource_with_resource_type(self, valid_config):
        """Test getting values with resource type override"""
        loader = NamingValuesLoader()
        loader.load_from_dict(valid_config)
        
        values = loader.get_values_for_resource(
            resource_type="aws_s3_bucket",
            environment="prd"
        )
        
        assert values.get("project") == "testproject"  # from defaults
        assert values.get("environment") == "prd"  # from environment
        assert values.get("purpose") == "raw"  # from resource_type
        assert values.get("layer") == "raw"  # from resource_type
        assert "defaults < environments.prd < resource_types.aws_s3_bucket" in values.source
    
    def test_get_values_for_resource_with_blueprint_metadata(self, valid_config):
        """Test getting values with blueprint metadata (highest precedence)"""
        loader = NamingValuesLoader()
        loader.load_from_dict(valid_config)
        
        blueprint_metadata = {
            "project": "override-project",  # Override default
            "custom_field": "custom-value"
        }
        
        values = loader.get_values_for_resource(
            resource_type="aws_s3_bucket",
            environment="prd",
            blueprint_metadata=blueprint_metadata
        )
        
        assert values.get("project") == "override-project"  # overridden
        assert values.get("environment") == "prd"  # from environment
        assert values.get("purpose") == "raw"  # from resource_type
        assert values.get("custom_field") == "custom-value"  # from blueprint
        assert "blueprint_metadata" in values.source
    
    def test_get_values_no_config_loaded(self):
        """Test getting values before loading config"""
        loader = NamingValuesLoader()
        
        with pytest.raises(ConfigurationError, match="No configuration loaded"):
            loader.get_values_for_resource("aws_s3_bucket")
    
    def test_get_defaults(self, valid_config):
        """Test getting default values"""
        loader = NamingValuesLoader()
        loader.load_from_dict(valid_config)
        
        defaults = loader.get_defaults()
        assert defaults["project"] == "testproject"
        assert defaults["region"] == "us-east-1"
        assert "environment" not in defaults  # not in defaults
    
    def test_get_environment_values(self, valid_config):
        """Test getting environment-specific values"""
        loader = NamingValuesLoader()
        loader.load_from_dict(valid_config)
        
        dev_values = loader.get_environment_values("dev")
        assert dev_values["environment"] == "dev"
        assert dev_values["data_classification"] == "internal"
        
        prd_values = loader.get_environment_values("prd")
        assert prd_values["environment"] == "prd"
        assert prd_values["data_classification"] == "confidential"
        
        # Non-existent environment
        missing_values = loader.get_environment_values("nonexistent")
        assert missing_values == {}
    
    def test_get_resource_type_values(self, valid_config):
        """Test getting resource-type-specific values"""
        loader = NamingValuesLoader()
        loader.load_from_dict(valid_config)
        
        s3_values = loader.get_resource_type_values("aws_s3_bucket")
        assert s3_values["purpose"] == "raw"
        assert s3_values["layer"] == "raw"
        
        cluster_values = loader.get_resource_type_values("dbx_cluster")
        assert cluster_values["workload"] == "etl"
        
        # Non-existent resource type
        missing_values = loader.get_resource_type_values("nonexistent")
        assert missing_values == {}
    
    def test_list_environments(self, valid_config):
        """Test listing environments"""
        loader = NamingValuesLoader()
        loader.load_from_dict(valid_config)
        
        environments = loader.list_environments()
        assert "dev" in environments
        assert "prd" in environments
        assert len(environments) == 2
    
    def test_list_resource_types(self, valid_config):
        """Test listing resource types"""
        loader = NamingValuesLoader()
        loader.load_from_dict(valid_config)
        
        resource_types = loader.list_resource_types()
        assert "aws_s3_bucket" in resource_types
        assert "dbx_cluster" in resource_types
        assert len(resource_types) == 2
    
    def test_get_version(self, valid_config):
        """Test getting configuration version"""
        loader = NamingValuesLoader()
        loader.load_from_dict(valid_config)
        
        assert loader.get_version() == "1.0"
    
    def test_repr_no_config(self):
        """Test string representation with no config"""
        loader = NamingValuesLoader()
        assert repr(loader) == "NamingValuesLoader(no config loaded)"
    
    def test_repr_with_config_from_dict(self, valid_config):
        """Test string representation with config from dict"""
        loader = NamingValuesLoader()
        loader.load_from_dict(valid_config)
        
        repr_str = repr(loader)
        assert "version=1.0" in repr_str
        assert "environments=2" in repr_str
        assert "resource_types=2" in repr_str
        assert "path=" not in repr_str  # No path when loaded from dict
    
    def test_repr_with_config_from_file(self, temp_yaml_file):
        """Test string representation with config from file"""
        loader = NamingValuesLoader()
        loader.load_from_file(temp_yaml_file)
        
        repr_str = repr(loader)
        assert "version=1.0" in repr_str
        assert "environments=2" in repr_str
        assert "resource_types=2" in repr_str
        assert "path=" in repr_str
        assert str(temp_yaml_file) in repr_str
    
    def test_value_precedence_order(self, valid_config):
        """Test that value precedence follows correct order"""
        # Modify config to test precedence clearly
        config = {
            "version": "1.0",
            "defaults": {
                "value": "from_defaults"
            },
            "environments": {
                "dev": {
                    "value": "from_environment"
                }
            },
            "resource_types": {
                "aws_s3_bucket": {
                    "value": "from_resource_type"
                }
            }
        }
        
        loader = NamingValuesLoader()
        loader.load_from_dict(config)
        
        # Test 1: Only defaults
        values = loader.get_values_for_resource("dbx_cluster")
        assert values["value"] == "from_defaults"
        
        # Test 2: Environment overrides defaults
        values = loader.get_values_for_resource("dbx_cluster", environment="dev")
        assert values["value"] == "from_environment"
        
        # Test 3: Resource type overrides environment
        values = loader.get_values_for_resource("aws_s3_bucket", environment="dev")
        assert values["value"] == "from_resource_type"
        
        # Test 4: Blueprint metadata overrides everything
        values = loader.get_values_for_resource(
            "aws_s3_bucket",
            environment="dev",
            blueprint_metadata={"value": "from_blueprint"}
        )
        assert values["value"] == "from_blueprint"
    
    def test_minimal_valid_config(self):
        """Test with minimal valid configuration"""
        minimal_config = {
            "version": "1.0",
            "defaults": {
                "project": "test"
            }
        }
        
        loader = NamingValuesLoader()
        loader.load_from_dict(minimal_config)
        
        values = loader.get_values_for_resource("aws_s3_bucket")
        assert values.get("project") == "test"
        assert loader.list_environments() == []
        assert loader.list_resource_types() == []
    
    def test_custom_variables(self):
        """Test that custom variables are preserved"""
        config = {
            "version": "1.0",
            "defaults": {
                "project": "test",
                "custom_field1": "value1",
                "custom_field2": "value2",
                "business_unit": "analytics"
            }
        }
        
        loader = NamingValuesLoader()
        loader.load_from_dict(config)
        
        values = loader.get_values_for_resource("aws_s3_bucket")
        assert values.get("custom_field1") == "value1"
        assert values.get("custom_field2") == "value2"
        assert values.get("business_unit") == "analytics"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
