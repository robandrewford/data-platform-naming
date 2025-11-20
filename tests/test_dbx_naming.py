#!/usr/bin/env python3
"""
Tests for DatabricksNamingGenerator class.
Mirrors structure of test_aws_naming.py for consistency.
"""


import pytest

from data_platform_naming.config.configuration_manager import (
    ConfigurationManager,
)
from data_platform_naming.constants import Environment
from data_platform_naming.dbx_naming import (
    DatabricksNamingConfig,
    DatabricksNamingGenerator,
    DatabricksResourceType,
)
from data_platform_naming.exceptions import ValidationError

# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def dbx_config():
    """Standard Databricks naming config for tests"""
    return DatabricksNamingConfig(
        environment=Environment.PRD.value,
        project="testproject",
        region="us-east-1",
        team="data-engineering",
        cost_center="eng-001"
    )


@pytest.fixture
def dbx_config_minimal():
    """Minimal Databricks naming config without optional fields"""
    return DatabricksNamingConfig(
        environment=Environment.DEV.value,
        project="testproject",
        region="us-west-2"
    )


@pytest.fixture
def values_config():
    """Values configuration for tests"""
    return {
        "version": "1.0",
        "defaults": {
            "project": "testproject",
            "region": "us-east-1",
            "region_short": "use1"
        },
        "environments": {
            "dev": {
                "environment": "dev"
            },
            "prd": {
                "environment": "prd"
            }
        },
        "resource_types": {
            "dbx_workspace": {
                "purpose": "analytics"
            },
            "dbx_cluster": {
                "workload": "etl",
                "cluster_type": "shared"
            },
            "dbx_job": {
                "job_type": "batch",
                "purpose": "transformation",
                "schedule": "daily"
            },
            "dbx_notebook_path": {
                "domain": "finance",
                "purpose": "etl",
                "notebook_name": "customer-load"
            },
            "dbx_repo": {
                "repo_purpose": "etl"
            },
            "dbx_pipeline": {
                "pipeline_type": "dlt",
                "source": "kafka",
                "target": "events"
            },
            "dbx_sql_warehouse": {
                "size": "medium",
                "purpose": "analytics"
            },
            "dbx_catalog": {
                "catalog_type": "main"
            },
            "dbx_schema": {
                "domain": "finance",
                "layer": "gold"
            },
            "dbx_table": {
                "entity": "customers",
                "table_type": "dim"
            },
            "dbx_volume": {
                "data_type": "raw",
                "purpose": "landing"
            },
            "dbx_secret_scope": {
                "purpose": "aws"
            },
            "dbx_instance_pool": {
                "node_type": "compute",
                "purpose": "etl"
            },
            "dbx_policy": {
                "policy_type": "security",
                "target": "cluster"
            }
        }
    }


@pytest.fixture
def patterns_config():
    """Patterns configuration with all Databricks patterns"""
    return {
        "version": "1.0",
        "patterns": {
            # AWS patterns (required for schema validation)
            "aws_s3_bucket": "{project}-{purpose}-{layer}-{environment}-{region_short}",
            "aws_glue_database": "{project}_{domain}_{layer}_{environment}",
            "aws_glue_table": "{table_type}_{entity}",
            "aws_glue_crawler": "{project}-{environment}-crawler-{database}-{source}",
            "aws_lambda_function": "{project}-{environment}-{domain}-{trigger}-{action}",
            "aws_iam_role": "{project}-{environment}-{service}-{purpose}-role",
            "aws_iam_policy": "{project}-{environment}-{service}-{purpose}-policy",
            "aws_kinesis_stream": "{project}-{environment}-{domain}-{source}-stream",
            "aws_kinesis_firehose": "{project}-{environment}-{domain}-to-{destination}",
            "aws_dynamodb_table": "{project}-{environment}-{entity}-{purpose}",
            "aws_sns_topic": "{project}-{environment}-{event_type}-{purpose}",
            "aws_sqs_queue": "{project}-{environment}-{purpose}-{queue_type}",
            "aws_step_function": "{project}-{environment}-{workflow}-{purpose}",
            # Databricks patterns
            "dbx_workspace": "dbx-{project}-{purpose}-{environment}-{region_short}",
            "dbx_cluster": "{project}-{workload}-{cluster_type}-{environment}",
            "dbx_job": "{project}-{job_type}-{purpose}-{schedule}-{environment}",
            "dbx_notebook_path": "/{project}/{domain}/{purpose}/{environment}/{notebook_name}",
            "dbx_repo": "{project}-{repo_purpose}-{environment}",
            "dbx_pipeline": "{project}-{pipeline_type}-{source}-{target}-{environment}",
            "dbx_sql_warehouse": "{project}-sql-{purpose}-{size}-{environment}",
            "dbx_catalog": "{project}_{catalog_type}_{environment}",
            "dbx_schema": "{domain}_{layer}",
            "dbx_table": "{table_type}_{entity}",
            "dbx_volume": "{data_type}_{purpose}",
            "dbx_secret_scope": "{project}-{purpose}-{environment}",
            "dbx_instance_pool": "{project}-pool-{node_type}-{purpose}-{environment}",
            "dbx_policy": "{project}-{target}-{policy_type}-{environment}"
        },
        "transformations": {
            "region_mapping": {
                "us-east-1": "use1",
                "us-west-2": "usw2"
            },
            "lowercase": ["project", "environment"]
        },
        "validation": {
            "max_length": {
                "dbx_cluster": 100
            },
            "allowed_chars": {
                "dbx_cluster": "^[a-zA-Z0-9-_]+$"
            },
            "required_variables": {
                "dbx_cluster": ["project", "workload", "cluster_type", "environment"]
            }
        }
    }


@pytest.fixture
def config_manager(values_config, patterns_config):
    """ConfigurationManager loaded with test configs"""
    from data_platform_naming.config.naming_patterns_loader import NamingPatternsLoader
    from data_platform_naming.config.naming_values_loader import NamingValuesLoader

    # Pre-load loaders with dict data
    values_loader = NamingValuesLoader()
    values_loader.load_from_dict(values_config)

    patterns_loader = NamingPatternsLoader()
    patterns_loader.load_from_dict(patterns_config)

    # Initialize ConfigurationManager with pre-loaded loaders
    manager = ConfigurationManager(
        values_loader=values_loader,
        patterns_loader=patterns_loader
    )

    return manager


# ============================================================================
# Test DatabricksNamingGenerator Initialization
# ============================================================================

class TestDatabricksNamingGeneratorInit:
    """Test DatabricksNamingGenerator initialization"""

    def test_init_with_config_manager(self, dbx_config, config_manager):
        """Test initialization with ConfigurationManager"""
        generator = DatabricksNamingGenerator(
            config=dbx_config,
            configuration_manager=config_manager
        )

        assert generator.config == dbx_config
        assert generator.configuration_manager is config_manager
    def test_init_validates_environment(self, config_manager):
        """Test that invalid environment raises ValidationError"""
        invalid_config = DatabricksNamingConfig(
            environment="invalid",
            project="test",
            region="us-east-1"
        )

        with pytest.raises(ValidationError, match="Invalid environment"):
            DatabricksNamingGenerator(config=invalid_config, configuration_manager=config_manager)

    def test_init_validates_project_name(self, config_manager):
        """Test that invalid project name raises ValidationError"""
        invalid_config = DatabricksNamingConfig(
            environment=Environment.DEV.value,
            project="Test_Project!",  # Invalid characters
            region="us-east-1"
        )

        with pytest.raises(ValidationError, match="Invalid project name"):
            DatabricksNamingGenerator(config=invalid_config, configuration_manager=config_manager)

    def test_init_pattern_validation_success(self, dbx_config, config_manager):
        """Test that pattern validation succeeds with all required patterns"""
        # Should not raise an error
        DatabricksNamingGenerator(
            config=dbx_config,
            configuration_manager=config_manager
        )
    def test_init_pattern_validation_missing_patterns(self, dbx_config):
        """Test that missing patterns raise error during ConfigurationManager loading"""
        # Create a ConfigurationManager with incomplete patterns
        incomplete_patterns = {
            "version": "1.0",
            "patterns": {
                "dbx_cluster": "{project}-{environment}"
                # Missing other required patterns
            }
        }

        incomplete_manager = ConfigurationManager()

        # Schema validation should fail when loading incomplete patterns
        from data_platform_naming.config.naming_values_loader import SchemaValidationError
        with pytest.raises(SchemaValidationError, match="Configuration validation failed"):
            incomplete_manager.load_configs(
                values_dict={"version": "1.0", "defaults": {}},
                patterns_dict=incomplete_patterns
            )


# ============================================================================
# Test Cluster Name Generation (HIGH PRIORITY)
# ============================================================================

class TestDatabricksNamingGeneratorCluster:
    """Test Databricks cluster name generation"""

    def test_generate_cluster_name_success(self, dbx_config, config_manager):
        """Test successful cluster name generation"""
        generator = DatabricksNamingGenerator(
            config=dbx_config,
            configuration_manager=config_manager
        )

        name = generator.generate_cluster_name(
            workload="analytics",
            cluster_type="dedicated"
        )

        assert name == "testproject-analytics-dedicated-prd"

    def test_generate_cluster_name_with_version(self, dbx_config, config_manager):
        """Test cluster name generation with version parameter"""
        generator = DatabricksNamingGenerator(
            config=dbx_config,
            configuration_manager=config_manager
        )

        name = generator.generate_cluster_name(
            workload="ml",
            cluster_type="shared",
            version="v2"
        )

        assert "prd" in name
        assert "ml" in name

    def test_generate_cluster_name_with_metadata(self, dbx_config, config_manager):
        """Test cluster name generation with blueprint metadata"""
        generator = DatabricksNamingGenerator(
            config=dbx_config,
            configuration_manager=config_manager
        )

        metadata = {"cluster_type": "job"}
        name = generator.generate_cluster_name(
            workload="etl",
            cluster_type="shared",  # Should be overridden by metadata
            metadata=metadata
        )

        assert "prd" in name
        assert "etl" in name


class TestDatabricksNamingGeneratorJob:
    """Test Databricks job name generation"""

    def test_generate_job_name_with_schedule(self, dbx_config, config_manager):
        """Test successful job name generation with schedule"""
        generator = DatabricksNamingGenerator(
            config=dbx_config,
            configuration_manager=config_manager
        )

        name = generator.generate_job_name(
            job_type="batch",
            purpose="customer-load",
            schedule="hourly"
        )

        assert name == "testproject-batch-customer-load-hourly-prd"

    def test_generate_job_name_without_schedule(self, dbx_config, config_manager):
        """Test job name generation without schedule parameter"""
        generator = DatabricksNamingGenerator(
            config=dbx_config,
            configuration_manager=config_manager
        )

        name = generator.generate_job_name(
            job_type="streaming",
            purpose="events"
        )

        assert "streaming" in name
        assert "events" in name
        assert "prd" in name

    def test_generate_job_name_with_metadata(self, dbx_config, config_manager):
        """Test job name generation with blueprint metadata"""
        generator = DatabricksNamingGenerator(
            config=dbx_config,
            configuration_manager=config_manager
        )

        metadata = {"schedule": "daily"}
        name = generator.generate_job_name(
            job_type="batch",
            purpose="transform",
            metadata=metadata
        )

        assert "prd" in name
        assert "batch" in name


class TestDatabricksNamingGeneratorUnityCatalog:
    """Test Unity Catalog resource name generation"""

    # Catalog tests
    def test_generate_catalog_name_success(self, dbx_config, config_manager):
        """Test successful catalog name generation"""
        generator = DatabricksNamingGenerator(
            config=dbx_config,
            configuration_manager=config_manager
        )

        name = generator.generate_catalog_name(catalog_type="dev")

        assert name == "testproject_dev_prd"

    def test_generate_catalog_name_with_metadata(self, dbx_config, config_manager):
        """Test catalog name generation with metadata"""
        generator = DatabricksNamingGenerator(
            config=dbx_config,
            configuration_manager=config_manager
        )

        metadata = {"catalog_type": "test"}
        name = generator.generate_catalog_name(
            catalog_type="main",
            metadata=metadata
        )

        assert "prd" in name
        assert "testproject" in name

    def test_generate_schema_name_success(self, dbx_config, config_manager):
        """Test successful schema name generation"""
        generator = DatabricksNamingGenerator(
            config=dbx_config,
            configuration_manager=config_manager
        )

        name = generator.generate_schema_name(
            domain="sales",
            layer="silver"
        )

        assert name == "sales_silver"

    def test_generate_schema_name_with_metadata(self, dbx_config, config_manager):
        """Test schema name generation with metadata"""
        generator = DatabricksNamingGenerator(
            config=dbx_config,
            configuration_manager=config_manager
        )

        metadata = {"layer": "gold"}
        name = generator.generate_schema_name(
            domain="finance",
            layer="bronze",
            metadata=metadata
        )

        assert "finance" in name

    def test_generate_table_name_success(self, dbx_config, config_manager):
        """Test successful table name generation"""
        generator = DatabricksNamingGenerator(
            config=dbx_config,
            configuration_manager=config_manager
        )

        name = generator.generate_table_name(
            entity="orders",
            table_type="fact"
        )

        assert name == "fact_orders"

    def test_generate_table_name_with_metadata(self, dbx_config, config_manager):
        """Test table name generation with metadata"""
        generator = DatabricksNamingGenerator(
            config=dbx_config,
            configuration_manager=config_manager
        )

        metadata = {"table_type": "dim"}
        name = generator.generate_table_name(
            entity="customers",
            table_type="fact",
            metadata=metadata
        )

        assert "customers" in name

    def test_generate_table_name_different_types(self, dbx_config, config_manager):
        """Test table name generation with different table types"""
        generator = DatabricksNamingGenerator(
            config=dbx_config,
            configuration_manager=config_manager
        )

        dim_name = generator.generate_table_name(entity="products", table_type="dim")
        fact_name = generator.generate_table_name(entity="sales", table_type="fact")

        assert "dim" in dim_name
        assert "fact" in fact_name

    def test_generate_full_table_reference(self, dbx_config, config_manager):
        """Test full Unity Catalog table reference generation"""
        generator = DatabricksNamingGenerator(
            config=dbx_config,
            configuration_manager=config_manager
        )

        ref = generator.generate_full_table_reference(
            catalog_type="main",
            domain="finance",
            layer="gold",
            entity="customers",
            table_type="dim"
        )

        assert ref == "testproject_main_prd.finance_gold.dim_customers"

    def test_full_table_reference_format(self, dbx_config, config_manager):
        """Test that full table reference has correct 3-tier format"""
        generator = DatabricksNamingGenerator(
            config=dbx_config,
            configuration_manager=config_manager
        )

        ref = generator.generate_full_table_reference(
            catalog_type="dev",
            domain="sales",
            layer="silver",
            entity="orders",
            table_type="fact"
        )

        # Should have exactly 2 dots (3 parts)
        assert ref.count('.') == 2
        parts = ref.split('.')
        assert len(parts) == 3

    def test_unity_catalog_3tier_namespace(self, dbx_config, config_manager):
        """Test Unity Catalog 3-tier namespace structure"""
        generator = DatabricksNamingGenerator(
            config=dbx_config,
            configuration_manager=config_manager
        )

        catalog = generator.generate_catalog_name("main")
        schema = generator.generate_schema_name("finance", "gold")
        table = generator.generate_table_name("customers", "dim")

        # All should use underscores (Unity Catalog requirement)
        assert "_" in catalog
        assert "_" in schema
        assert "_" in table


# ============================================================================
# Test Workspace Name Generation (MEDIUM PRIORITY)
# ============================================================================

class TestDatabricksNamingGeneratorWorkspace:
    """Test Databricks workspace name generation"""

    def test_generate_workspace_name_success(self, dbx_config, config_manager):
        """Test successful workspace name generation"""
        generator = DatabricksNamingGenerator(
            config=dbx_config,
            configuration_manager=config_manager
        )

        name = generator.generate_workspace_name(purpose="analytics")

        assert "prd" in name
        assert "testproject" in name or "analytics" in name

    def test_generate_workspace_name_default_purpose(self, dbx_config, config_manager):
        """Test workspace name generation with default purpose"""
        generator = DatabricksNamingGenerator(
            config=dbx_config,
            configuration_manager=config_manager
        )

        name = generator.generate_workspace_name()

        assert "prd" in name

    def test_generate_workspace_name_with_metadata(self, dbx_config, config_manager):
        """Test workspace name generation with metadata"""
        generator = DatabricksNamingGenerator(
            config=dbx_config,
            configuration_manager=config_manager
        )

        metadata = {"purpose": "ml"}
        name = generator.generate_workspace_name(purpose="analytics", metadata=metadata)

        assert "prd" in name


class TestDatabricksNamingGeneratorSQLWarehouse:
    """Test Databricks SQL warehouse name generation"""

    def test_generate_sql_warehouse_name_success(self, dbx_config, config_manager):
        """Test successful SQL warehouse name generation"""
        generator = DatabricksNamingGenerator(
            config=dbx_config,
            configuration_manager=config_manager
        )

        name = generator.generate_sql_warehouse_name(size="large", purpose="reporting")

        assert "prd" in name
        assert "sql" in name or "reporting" in name or "large" in name

    def test_generate_sql_warehouse_name_defaults(self, dbx_config, config_manager):
        """Test SQL warehouse name generation with default parameters"""
        generator = DatabricksNamingGenerator(
            config=dbx_config,
            configuration_manager=config_manager
        )

        name = generator.generate_sql_warehouse_name()

        assert "prd" in name

    def test_generate_sql_warehouse_name_with_metadata(self, dbx_config, config_manager):
        """Test SQL warehouse name generation with metadata"""
        generator = DatabricksNamingGenerator(
            config=dbx_config,
            configuration_manager=config_manager
        )

        metadata = {"size": "xlarge"}
        name = generator.generate_sql_warehouse_name(
            size="medium",
            purpose="analytics",
            metadata=metadata
        )

        assert "prd" in name

    def test_generate_sql_warehouse_name_different_sizes(self, dbx_config, config_manager):
        """Test SQL warehouse names with different sizes"""
        generator = DatabricksNamingGenerator(
            config=dbx_config,
            configuration_manager=config_manager
        )

        small = generator.generate_sql_warehouse_name(size="small", purpose="adhoc")
        large = generator.generate_sql_warehouse_name(size="large", purpose="analytics")

        assert "prd" in small
        assert "prd" in large


class TestDatabricksNamingGeneratorPipeline:
    """Test Databricks Delta Live Tables pipeline name generation"""

    def test_generate_pipeline_name_success(self, dbx_config, config_manager):
        """Test successful pipeline name generation"""
        generator = DatabricksNamingGenerator(
            config=dbx_config,
            configuration_manager=config_manager
        )

        name = generator.generate_pipeline_name(
            source="s3",
            target="bronze",
            pipeline_type="dlt"
        )

        assert "prd" in name
        assert "s3" in name or "bronze" in name or "dlt" in name

    def test_generate_pipeline_name_default_type(self, dbx_config, config_manager):
        """Test pipeline name generation with default type"""
        generator = DatabricksNamingGenerator(
            config=dbx_config,
            configuration_manager=config_manager
        )

        name = generator.generate_pipeline_name(source="kafka", target="events")

        assert "prd" in name

    def test_generate_pipeline_name_with_metadata(self, dbx_config, config_manager):
        """Test pipeline name generation with metadata"""
        generator = DatabricksNamingGenerator(
            config=dbx_config,
            configuration_manager=config_manager
        )

        metadata = {"pipeline_type": "streaming"}
        name = generator.generate_pipeline_name(
            source="kinesis",
            target="realtime",
            metadata=metadata
        )

        assert "prd" in name


class TestDatabricksNamingGeneratorNotebook:
    """Test Databricks notebook path generation"""

    def test_generate_notebook_path_success(self, dbx_config, config_manager):
        """Test successful notebook path generation"""
        generator = DatabricksNamingGenerator(
            config=dbx_config,
            configuration_manager=config_manager
        )

        path = generator.generate_notebook_path(
            domain="finance",
            purpose="etl",
            notebook_name="load-customers"
        )

        assert path.startswith("/")
        assert "finance" in path
        assert "load-customers" in path

    def test_generate_notebook_path_with_metadata(self, dbx_config, config_manager):
        """Test notebook path generation with metadata"""
        generator = DatabricksNamingGenerator(
            config=dbx_config,
            configuration_manager=config_manager
        )

        metadata = {"domain": "marketing"}
        path = generator.generate_notebook_path(
            domain="finance",
            purpose="analysis",
            notebook_name="report",
            metadata=metadata
        )

        assert path.startswith("/")


class TestDatabricksNamingGeneratorRepo:
    """Test Databricks Git repo name generation"""

    def test_generate_repo_name_success(self, dbx_config, config_manager):
        """Test successful repo name generation"""
        generator = DatabricksNamingGenerator(
            config=dbx_config,
            configuration_manager=config_manager
        )

        name = generator.generate_repo_name(repo_purpose="notebooks")

        assert "prd" in name
        assert "notebooks" in name or "testproject" in name

    def test_generate_repo_name_with_metadata(self, dbx_config, config_manager):
        """Test repo name generation with metadata"""
        generator = DatabricksNamingGenerator(
            config=dbx_config,
            configuration_manager=config_manager
        )

        metadata = {"repo_purpose": "pipelines"}
        name = generator.generate_repo_name(repo_purpose="code", metadata=metadata)

        assert "prd" in name


class TestDatabricksNamingGeneratorVolume:
    """Test Unity Catalog volume name generation"""

    def test_generate_volume_name_success(self, dbx_config, config_manager):
        """Test successful volume name generation"""
        generator = DatabricksNamingGenerator(
            config=dbx_config,
            configuration_manager=config_manager
        )

        name = generator.generate_volume_name(purpose="uploads", data_type="raw")

        assert "_" in name  # Volume uses underscores
        assert "raw" in name or "uploads" in name

    def test_generate_volume_name_defaults(self, dbx_config, config_manager):
        """Test volume name generation with default data_type"""
        generator = DatabricksNamingGenerator(
            config=dbx_config,
            configuration_manager=config_manager
        )

        name = generator.generate_volume_name(purpose="landing")

        assert "_" in name

    def test_generate_volume_name_with_metadata(self, dbx_config, config_manager):
        """Test volume name generation with metadata"""
        generator = DatabricksNamingGenerator(
            config=dbx_config,
            configuration_manager=config_manager
        )

        metadata = {"data_type": "processed"}
        name = generator.generate_volume_name(purpose="archive", metadata=metadata)

        assert "_" in name


class TestDatabricksNamingGeneratorSecretScope:
    """Test Databricks secret scope name generation"""

    def test_generate_secret_scope_name_success(self, dbx_config, config_manager):
        """Test successful secret scope name generation"""
        generator = DatabricksNamingGenerator(
            config=dbx_config,
            configuration_manager=config_manager
        )

        name = generator.generate_secret_scope_name(purpose="azure")

        assert "prd" in name
        assert "azure" in name or "testproject" in name

    def test_generate_secret_scope_name_defaults(self, dbx_config, config_manager):
        """Test secret scope name generation with default purpose"""
        generator = DatabricksNamingGenerator(
            config=dbx_config,
            configuration_manager=config_manager
        )

        name = generator.generate_secret_scope_name()

        assert "prd" in name

    def test_generate_secret_scope_name_with_metadata(self, dbx_config, config_manager):
        """Test secret scope name generation with metadata"""
        generator = DatabricksNamingGenerator(
            config=dbx_config,
            configuration_manager=config_manager
        )

        metadata = {"purpose": "prod-keys"}
        name = generator.generate_secret_scope_name(purpose="dev-keys", metadata=metadata)

        assert "prd" in name


class TestDatabricksNamingGeneratorInstancePool:
    """Test Databricks instance pool name generation"""

    def test_generate_instance_pool_name_success(self, dbx_config, config_manager):
        """Test successful instance pool name generation"""
        generator = DatabricksNamingGenerator(
            config=dbx_config,
            configuration_manager=config_manager
        )

        name = generator.generate_instance_pool_name(node_type="compute", purpose="ml")

        assert "prd" in name
        assert "pool" in name or "compute" in name or "ml" in name

    def test_generate_instance_pool_name_defaults(self, dbx_config, config_manager):
        """Test instance pool name generation with default purpose"""
        generator = DatabricksNamingGenerator(
            config=dbx_config,
            configuration_manager=config_manager
        )

        name = generator.generate_instance_pool_name(node_type="memory")

        assert "prd" in name

    def test_generate_instance_pool_name_with_metadata(self, dbx_config, config_manager):
        """Test instance pool name generation with metadata"""
        generator = DatabricksNamingGenerator(
            config=dbx_config,
            configuration_manager=config_manager
        )

        metadata = {"purpose": "analytics"}
        name = generator.generate_instance_pool_name(
            node_type="compute",
            purpose="etl",
            metadata=metadata
        )

        assert "prd" in name


class TestDatabricksNamingGeneratorPolicy:
    """Test Databricks policy name generation"""

    def test_generate_policy_name_success(self, dbx_config, config_manager):
        """Test successful policy name generation"""
        generator = DatabricksNamingGenerator(
            config=dbx_config,
            configuration_manager=config_manager
        )

        name = generator.generate_policy_name(policy_type="cost", target="sql")

        assert "prd" in name
        assert "cost" in name or "sql" in name

    def test_generate_policy_name_defaults(self, dbx_config, config_manager):
        """Test policy name generation with default target"""
        generator = DatabricksNamingGenerator(
            config=dbx_config,
            configuration_manager=config_manager
        )

        name = generator.generate_policy_name(policy_type="security")

        assert "prd" in name

    def test_generate_policy_name_with_metadata(self, dbx_config, config_manager):
        """Test policy name generation with metadata"""
        generator = DatabricksNamingGenerator(
            config=dbx_config,
            configuration_manager=config_manager
        )

        metadata = {"target": "job"}
        name = generator.generate_policy_name(
            policy_type="performance",
            target="cluster",
            metadata=metadata
        )

        assert "prd" in name


class TestDatabricksNamingGeneratorUtilities:
    """Test utility functions like tags generation"""

    def test_generate_standard_tags(self, dbx_config, config_manager):
        """Test standard tags generation"""
        generator = DatabricksNamingGenerator(config=dbx_config, configuration_manager=config_manager)

        tags = generator.generate_standard_tags(DatabricksResourceType.CLUSTER)

        assert tags["Environment"] == "prd"
        assert tags["Project"] == "testproject"
        assert tags["ManagedBy"] == "terraform"
        assert tags["ResourceType"] == "dbx_cluster"
        assert tags["Team"] == "data-engineering"
        assert tags["CostCenter"] == "eng-001"

    def test_generate_standard_tags_minimal_config(self, dbx_config_minimal, config_manager):
        """Test standard tags with minimal config"""
        generator = DatabricksNamingGenerator(config=dbx_config_minimal, configuration_manager=config_manager)

        tags = generator.generate_standard_tags(DatabricksResourceType.JOB)

        assert tags["Environment"] == "dev"
        assert tags["Project"] == "testproject"
        assert "Team" not in tags  # Not provided in minimal config
        assert "CostCenter" not in tags

    def test_generate_standard_tags_with_additional(self, dbx_config, config_manager):
        """Test standard tags with additional custom tags"""
        generator = DatabricksNamingGenerator(config=dbx_config, configuration_manager=config_manager)

        additional = {"Owner": "data-team", "Critical": "true"}
        tags = generator.generate_standard_tags(
            DatabricksResourceType.WORKSPACE,
            additional_tags=additional
        )

        assert tags["Owner"] == "data-team"
        assert tags["Critical"] == "true"
        assert tags["Environment"] == "prd"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
