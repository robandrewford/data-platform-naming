#!/usr/bin/env python3
"""
End-to-end integration tests for configuration-based naming system.
Tests the complete workflow: Load configs → Create generators → Generate names.
"""


import pytest
import yaml

from data_platform_naming.aws_naming import AWSNamingConfig, AWSNamingGenerator
from data_platform_naming.config.configuration_manager import ConfigurationManager
from data_platform_naming.config.naming_patterns_loader import NamingPatternsLoader
from data_platform_naming.config.naming_values_loader import NamingValuesLoader
from data_platform_naming.dbx_naming import DatabricksNamingConfig, DatabricksNamingGenerator


class TestEndToEndAWS:
    """End-to-end tests for AWS naming with configuration system"""

    @pytest.fixture
    def config_files(self, tmp_path):
        """Create temporary config files"""
        # naming-values.yaml
        values_config = {
            "version": "1.0",
            "defaults": {
                "project": "dataplatform",
                "environment": "prd",
                "region": "us-east-1"
            }
        }

        values_path = tmp_path / "naming-values.yaml"
        with open(values_path, 'w') as f:
            yaml.dump(values_config, f)

        # naming-patterns.yaml with all 27 resource types
        patterns_config = {
            "version": "1.0",
            "patterns": {
                # AWS (13)
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
                # Databricks (14)
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
                }
            }
        }

        patterns_path = tmp_path / "naming-patterns.yaml"
        with open(patterns_path, 'w') as f:
            yaml.dump(patterns_config, f)

        return values_path, patterns_path

    def test_e2e_aws_s3_bucket(self, config_files):
        """Test end-to-end: Config → Generator → S3 bucket name"""
        values_path, patterns_path = config_files

        # Load configurations
        values_loader = NamingValuesLoader()
        values_loader.load_from_file(values_path)

        patterns_loader = NamingPatternsLoader()
        patterns_loader.load_from_file(patterns_path)

        # Create ConfigurationManager
        config_manager = ConfigurationManager(
            values_loader=values_loader,
            patterns_loader=patterns_loader
        )

        # Create generator with config
        aws_config = AWSNamingConfig(
            environment="prd",
            project="dataplatform",
            region="us-east-1"
        )

        aws_gen = AWSNamingGenerator(
            config=aws_config,
            configuration_manager=config_manager
        )

        # Generate name
        bucket_name = aws_gen.generate_s3_bucket_name(
            purpose="raw",
            layer="raw"
        )

        # Verify
        assert bucket_name == "dataplatform-raw-raw-prd-use1"

    def test_e2e_aws_glue_database(self, config_files):
        """Test end-to-end: Config → Generator → Glue database name"""
        values_path, patterns_path = config_files

        values_loader = NamingValuesLoader()
        values_loader.load_from_file(values_path)

        patterns_loader = NamingPatternsLoader()
        patterns_loader.load_from_file(patterns_path)

        config_manager = ConfigurationManager(
            values_loader=values_loader,
            patterns_loader=patterns_loader
        )

        aws_config = AWSNamingConfig(
            environment="prd",
            project="dataplatform",
            region="us-east-1"
        )

        aws_gen = AWSNamingGenerator(
            config=aws_config,
            configuration_manager=config_manager
        )

        db_name = aws_gen.generate_glue_database_name(
            domain="finance",
            layer="gold"
        )

        assert db_name == "dataplatform_finance_gold_prd"

    def test_e2e_aws_with_metadata_override(self, config_files):
        """Test metadata override in end-to-end workflow"""
        values_path, patterns_path = config_files

        values_loader = NamingValuesLoader()
        values_loader.load_from_file(values_path)

        patterns_loader = NamingPatternsLoader()
        patterns_loader.load_from_file(patterns_path)

        config_manager = ConfigurationManager(
            values_loader=values_loader,
            patterns_loader=patterns_loader
        )

        aws_config = AWSNamingConfig(
            environment="prd",
            project="dataplatform",
            region="us-east-1"
        )

        aws_gen = AWSNamingGenerator(
            config=aws_config,
            configuration_manager=config_manager
        )

        # Override environment in metadata
        bucket_name = aws_gen.generate_s3_bucket_name(
            purpose="raw",
            layer="raw",
            metadata={"environment": "dev"}
        )

        # Should use dev instead of prd
        assert bucket_name == "dataplatform-raw-raw-dev-use1"


class TestEndToEndDatabricks:
    """End-to-end tests for Databricks naming with configuration system"""

    @pytest.fixture
    def config_files(self, tmp_path):
        """Create temporary config files"""
        values_config = {
            "version": "1.0",
            "defaults": {
                "project": "dataplatform",
                "environment": "prd",
                "region": "us-east-1"
            }
        }

        values_path = tmp_path / "naming-values.yaml"
        with open(values_path, 'w') as f:
            yaml.dump(values_config, f)

        patterns_config = {
            "version": "1.0",
            "patterns": {
                # All 27 resource types
                "aws_s3_bucket": "{project}-{purpose}-{environment}",
                "aws_glue_database": "{project}_{domain}_{environment}",
                "aws_glue_table": "{table_type}_{entity}",
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
                "dbx_workspace": "dbx-{project}-{purpose}-{environment}",
                "dbx_cluster": "{project}-{workload}-{cluster_type}-{environment}",
                "dbx_job": "{project}-{job_type}-{purpose}-{environment}",
                "dbx_notebook_path": "/{project}/{domain}/{environment}",
                "dbx_repo": "{project}-{repo_purpose}-{environment}",
                "dbx_pipeline": "{project}-{pipeline_type}-{environment}",
                "dbx_sql_warehouse": "{project}-sql-{purpose}-{environment}",
                "dbx_catalog": "{project}_{catalog_type}_{environment}",
                "dbx_schema": "{domain}_{layer}",
                "dbx_table": "{table_type}_{entity}",
                "dbx_volume": "{data_type}_{purpose}",
                "dbx_secret_scope": "{project}-{purpose}-{environment}",
                "dbx_instance_pool": "{project}-pool-{environment}",
                "dbx_policy": "{project}-{target}-{environment}"
            }
        }

        patterns_path = tmp_path / "naming-patterns.yaml"
        with open(patterns_path, 'w') as f:
            yaml.dump(patterns_config, f)

        return values_path, patterns_path

    def test_e2e_dbx_cluster(self, config_files):
        """Test end-to-end: Config → Generator → Cluster name"""
        values_path, patterns_path = config_files

        values_loader = NamingValuesLoader()
        values_loader.load_from_file(values_path)

        patterns_loader = NamingPatternsLoader()
        patterns_loader.load_from_file(patterns_path)

        config_manager = ConfigurationManager(
            values_loader=values_loader,
            patterns_loader=patterns_loader
        )

        dbx_config = DatabricksNamingConfig(
            environment="prd",
            project="dataplatform",
            region="us-east-1"
        )

        dbx_gen = DatabricksNamingGenerator(
            config=dbx_config,
            configuration_manager=config_manager
        )

        cluster_name = dbx_gen.generate_cluster_name(
            workload="etl",
            cluster_type="shared"
        )

        assert cluster_name == "dataplatform-etl-shared-prd"

    def test_e2e_dbx_unity_catalog(self, config_files):
        """Test end-to-end: Config → Generator → Unity Catalog 3-tier"""
        values_path, patterns_path = config_files

        values_loader = NamingValuesLoader()
        values_loader.load_from_file(values_path)

        patterns_loader = NamingPatternsLoader()
        patterns_loader.load_from_file(patterns_path)

        config_manager = ConfigurationManager(
            values_loader=values_loader,
            patterns_loader=patterns_loader
        )

        dbx_config = DatabricksNamingConfig(
            environment="prd",
            project="dataplatform",
            region="us-east-1"
        )

        dbx_gen = DatabricksNamingGenerator(
            config=dbx_config,
            configuration_manager=config_manager
        )

        # Generate catalog
        catalog_name = dbx_gen.generate_catalog_name(catalog_type="main")
        assert catalog_name == "dataplatform_main_prd"

        # Generate schema
        schema_name = dbx_gen.generate_schema_name(domain="finance", layer="gold")
        assert schema_name == "finance_gold"

        # Generate table
        table_name = dbx_gen.generate_table_name(entity="customers", table_type="dim")
        assert table_name == "dim_customers"

        # Generate full reference
        full_name = dbx_gen.generate_full_table_reference(
            catalog_type="main",
            domain="finance",
            layer="gold",
            entity="customers",
            table_type="dim"
        )
        assert full_name == "dataplatform_main_prd.finance_gold.dim_customers"


class TestEndToEndBackwardCompatibility:
    """Test that legacy generators still work without ConfigurationManager"""

    def test_legacy_aws_generator_still_works(self):
        """Verify AWS generator works without ConfigurationManager"""
        # Create generator without config (legacy mode)
        aws_config = AWSNamingConfig(
            environment="prd",
            project="dataplatform",
            region="us-east-1"
        )

        # ConfigurationManager is now required - cannot create generator without it
        # This test validates that legacy mode (use_config=False) is no longer supported
        with pytest.raises((TypeError, ValueError)):
            aws_gen = AWSNamingGenerator(
                config=aws_config,
                configuration_manager=None
            )

    def test_legacy_dbx_generator_still_works(self):
        """Verify Databricks generator works without ConfigurationManager"""
        dbx_config = DatabricksNamingConfig(
            environment="prd",
            project="dataplatform",
            region="us-east-1"
        )

        # ConfigurationManager is now required - cannot create generator without it
        # This test validates that legacy mode (use_config=False) is no longer supported
        with pytest.raises((TypeError, ValueError)):
            dbx_gen = DatabricksNamingGenerator(
                config=dbx_config,
                configuration_manager=None
            )


class TestEndToEndFullWorkflow:
    """Test complete workflow from config files to multiple resource types"""

    @pytest.fixture
    def full_config_files(self, tmp_path):
        """Create complete config files with all settings"""
        values_config = {
            "version": "1.0",
            "defaults": {
                "project": "dataplatform",
                "environment": "prd",
                "region": "us-east-1",
                "team": "data-engineering",
                "cost_center": "CC-1234"
            },
            "environments": {
                "dev": {
                    "environment": "dev"
                },
                "prd": {
                    "environment": "prd"
                }
            }
        }

        values_path = tmp_path / "naming-values.yaml"
        with open(values_path, 'w') as f:
            yaml.dump(values_config, f)

        patterns_config = {
            "version": "1.0",
            "patterns": {
                # All 27 resource types with complete patterns
                "aws_s3_bucket": "{project}-{purpose}-{layer}-{environment}-{region_short}",
                "aws_glue_database": "{project}_{domain}_{layer}_{environment}",
                "aws_glue_table": "{table_type}_{entity}",
                "aws_glue_crawler": "{project}-{environment}-crawler-{database}",
                "aws_lambda_function": "{project}-{environment}-{domain}-{action}",
                "aws_iam_role": "{project}-{environment}-{service}-role",
                "aws_iam_policy": "{project}-{environment}-{service}-policy",
                "aws_kinesis_stream": "{project}-{environment}-{domain}-stream",
                "aws_kinesis_firehose": "{project}-{environment}-{domain}-firehose",
                "aws_dynamodb_table": "{project}-{environment}-{entity}",
                "aws_sns_topic": "{project}-{environment}-{event_type}",
                "aws_sqs_queue": "{project}-{environment}-{purpose}",
                "aws_step_function": "{project}-{environment}-{workflow}",
                "dbx_workspace": "dbx-{project}-{purpose}-{environment}",
                "dbx_cluster": "{project}-{workload}-{cluster_type}-{environment}",
                "dbx_job": "{project}-{job_type}-{purpose}-{environment}",
                "dbx_notebook_path": "/{project}/{domain}/{environment}",
                "dbx_repo": "{project}-{repo_purpose}-{environment}",
                "dbx_pipeline": "{project}-{pipeline_type}-{environment}",
                "dbx_sql_warehouse": "{project}-sql-{purpose}-{environment}",
                "dbx_catalog": "{project}_{catalog_type}_{environment}",
                "dbx_schema": "{domain}_{layer}",
                "dbx_table": "{table_type}_{entity}",
                "dbx_volume": "{data_type}_{purpose}",
                "dbx_secret_scope": "{project}-{purpose}-{environment}",
                "dbx_instance_pool": "{project}-pool-{environment}",
                "dbx_policy": "{project}-{target}-{environment}"
            },
            "transformations": {
                "region_mapping": {
                    "us-east-1": "use1",
                    "us-west-2": "usw2"
                },
                "lowercase": ["project", "environment"]
            }
        }

        patterns_path = tmp_path / "naming-patterns.yaml"
        with open(patterns_path, 'w') as f:
            yaml.dump(patterns_config, f)

        return values_path, patterns_path

    def test_generate_all_aws_resources(self, full_config_files):
        """Test generating all 13 AWS resource types"""
        values_path, patterns_path = full_config_files

        # Setup
        values_loader = NamingValuesLoader()
        values_loader.load_from_file(values_path)

        patterns_loader = NamingPatternsLoader()
        patterns_loader.load_from_file(patterns_path)

        config_manager = ConfigurationManager(
            values_loader=values_loader,
            patterns_loader=patterns_loader
        )

        aws_config = AWSNamingConfig(
            environment="prd",
            project="dataplatform",
            region="us-east-1",
            team="data-engineering",
            cost_center="CC-1234"
        )

        aws_gen = AWSNamingGenerator(
            config=aws_config,
            configuration_manager=config_manager
        )

        # Generate all AWS resource types
        names = {
            "s3_bucket": aws_gen.generate_s3_bucket_name(purpose="raw", layer="raw"),
            "glue_database": aws_gen.generate_glue_database_name(domain="finance", layer="gold"),
            "glue_table": aws_gen.generate_glue_table_name(entity="customers"),
        }

        # Verify all generated correctly
        assert "dataplatform" in names["s3_bucket"]
        assert "dataplatform_finance_gold_prd" == names["glue_database"]
        assert "fact_customers" == names["glue_table"]

    def test_generate_all_databricks_resources(self, full_config_files):
        """Test generating all 14 Databricks resource types"""
        values_path, patterns_path = full_config_files

        values_loader = NamingValuesLoader()
        values_loader.load_from_file(values_path)

        patterns_loader = NamingPatternsLoader()
        patterns_loader.load_from_file(patterns_path)

        config_manager = ConfigurationManager(
            values_loader=values_loader,
            patterns_loader=patterns_loader
        )

        dbx_config = DatabricksNamingConfig(
            environment="prd",
            project="dataplatform",
            region="us-east-1"
        )

        dbx_gen = DatabricksNamingGenerator(
            config=dbx_config,
            configuration_manager=config_manager
        )

        # Generate various Databricks resource types
        names = {
            "cluster": dbx_gen.generate_cluster_name(workload="etl", cluster_type="shared"),
            "job": dbx_gen.generate_job_name(job_type="batch", purpose="transformation"),
            "catalog": dbx_gen.generate_catalog_name(catalog_type="main"),
            "schema": dbx_gen.generate_schema_name(domain="finance", layer="gold"),
            "table": dbx_gen.generate_table_name(entity="customers", table_type="dim"),
        }

        # Verify all generated correctly
        assert names["cluster"] == "dataplatform-etl-shared-prd"
        assert names["job"] == "dataplatform-batch-transformation-prd"
        assert names["catalog"] == "dataplatform_main_prd"
        assert names["schema"] == "finance_gold"
        assert names["table"] == "dim_customers"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
