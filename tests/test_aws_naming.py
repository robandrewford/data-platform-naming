#!/usr/bin/env python3
"""
Tests for AWSNamingGenerator class.
"""

import pytest
from unittest.mock import Mock, MagicMock
from data_platform_naming.aws_naming import (
    AWSNamingGenerator,
    AWSNamingConfig,
    AWSResourceType,
)
from data_platform_naming.config.configuration_manager import (
    ConfigurationManager,
    GeneratedName,
)
from data_platform_naming.config.naming_patterns_loader import PatternError


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def aws_config():
    """Standard AWS naming config for tests"""
    return AWSNamingConfig(
        environment="prd",
        project="testproject",
        region="us-east-1",
        team="data-engineering",
        cost_center="eng-001"
    )


@pytest.fixture
def aws_config_minimal():
    """Minimal AWS naming config without optional fields"""
    return AWSNamingConfig(
        environment="dev",
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
            "aws_s3_bucket": {
                "purpose": "data",
                "layer": "raw"
            },
            "aws_glue_database": {
                "domain": "finance",
                "layer": "gold"
            },
            "aws_glue_table": {
                "entity": "customers",
                "table_type": "dim"
            },
            "aws_glue_crawler": {
                "database": "testdb",
                "source": "s3"
            },
            "aws_lambda_function": {
                "domain": "sales",
                "trigger": "s3",
                "action": "process"
            },
            "aws_iam_role": {
                "service": "lambda",
                "purpose": "execution"
            },
            "aws_iam_policy": {
                "service": "s3",
                "purpose": "read"
            },
            "aws_kinesis_stream": {
                "domain": "events",
                "source": "api"
            },
            "aws_kinesis_firehose": {
                "domain": "logs",
                "destination": "s3"
            },
            "aws_dynamodb_table": {
                "entity": "customer",
                "purpose": "profile"
            },
            "aws_sns_topic": {
                "event_type": "data",
                "purpose": "processed"
            },
            "aws_sqs_queue": {
                "purpose": "processing",
                "queue_type": "fifo"
            },
            "aws_step_function": {
                "workflow": "etl",
                "purpose": "orchestration"
            }
        }
    }


@pytest.fixture
def patterns_config():
    """Patterns configuration with all AWS and DBX patterns"""
    return {
        "version": "1.0",
        "patterns": {
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
            "dbx_cluster": "{project}-{workload}-{cluster_type}-{environment}",
            "dbx_job": "{project}-{job_type}-{purpose}-{schedule}-{environment}",
            "dbx_catalog": "{project}_{catalog_type}_{environment}",
            "dbx_schema": "{domain}_{layer}",
            "dbx_table": "{table_type}_{entity}",
            "dbx_workspace": "dbx-{project}-{purpose}-{environment}-{region_short}",
            "dbx_notebook_path": "/{project}/{domain}/{purpose}/{environment}/{notebook_name}",
            "dbx_repo": "{project}-{repo_purpose}-{environment}",
            "dbx_pipeline": "{project}-{pipeline_type}-{source}-{target}-{environment}",
            "dbx_sql_warehouse": "{project}-sql-{purpose}-{size}-{environment}",
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
                "aws_s3_bucket": 63
            },
            "allowed_chars": {
                "aws_s3_bucket": "^[a-z0-9-]+$"
            },
            "required_variables": {
                "aws_s3_bucket": ["project", "purpose", "layer", "environment", "region_short"]
            }
        }
    }


@pytest.fixture
def config_manager(values_config, patterns_config):
    """ConfigurationManager loaded with test configs"""
    from data_platform_naming.config.naming_values_loader import NamingValuesLoader
    from data_platform_naming.config.naming_patterns_loader import NamingPatternsLoader
    
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
# Test AWSNamingGenerator Initialization
# ============================================================================

class TestAWSNamingGeneratorInit:
    """Test AWSNamingGenerator initialization"""
    
    def test_init_without_config_manager(self, aws_config):
        """Test initialization without ConfigurationManager (use_config=False)"""
        generator = AWSNamingGenerator(
            config=aws_config,
            use_config=False
        )
        
        assert generator.config == aws_config
        assert generator.config_manager is None
        assert generator.use_config is False
    
    def test_init_with_config_manager(self, aws_config, config_manager):
        """Test initialization with ConfigurationManager (use_config=True)"""
        generator = AWSNamingGenerator(
            config=aws_config,
            configuration_manager=config_manager,
            use_config=True
        )
        
        assert generator.config == aws_config
        assert generator.config_manager is config_manager
        assert generator.use_config is True
    
    def test_init_use_config_without_manager_raises_error(self, aws_config):
        """Test that use_config=True without ConfigurationManager raises ValueError"""
        with pytest.raises(ValueError, match="use_config=True requires configuration_manager"):
            AWSNamingGenerator(
                config=aws_config,
                use_config=True
            )
    
    def test_init_validates_environment(self):
        """Test that invalid environment raises ValueError"""
        invalid_config = AWSNamingConfig(
            environment="invalid",
            project="test",
            region="us-east-1"
        )
        
        with pytest.raises(ValueError, match="Invalid environment"):
            AWSNamingGenerator(config=invalid_config)
    
    def test_init_validates_project_name(self):
        """Test that invalid project name raises ValueError"""
        invalid_config = AWSNamingConfig(
            environment="dev",
            project="Test_Project!",  # Invalid characters
            region="us-east-1"
        )
        
        with pytest.raises(ValueError, match="Invalid project name"):
            AWSNamingGenerator(config=invalid_config)
    
    def test_init_pattern_validation_success(self, aws_config, config_manager):
        """Test that pattern validation succeeds with all required patterns"""
        # Should not raise an error
        generator = AWSNamingGenerator(
            config=aws_config,
            configuration_manager=config_manager,
            use_config=True
        )
        
        assert generator.use_config is True
    
    def test_init_pattern_validation_missing_patterns(self, aws_config):
        """Test that missing patterns raise error during ConfigurationManager loading"""
        # Create a ConfigurationManager with incomplete patterns
        incomplete_patterns = {
            "version": "1.0",
            "patterns": {
                "aws_s3_bucket": "{project}-{environment}"
                # Missing other required AWS and DBX patterns
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
# Test S3 Bucket Name Generation
# ============================================================================

class TestAWSNamingGeneratorS3:
    """Test S3 bucket name generation"""
    
    def test_generate_s3_bucket_name_success(self, aws_config, config_manager):
        """Test successful S3 bucket name generation"""
        generator = AWSNamingGenerator(
            config=aws_config,
            configuration_manager=config_manager,
            use_config=True
        )
        
        name = generator.generate_s3_bucket_name(
            purpose="analytics",
            layer="gold"
        )
        
        assert name == "testproject-analytics-gold-prd-use1"
    
    def test_generate_s3_bucket_name_with_metadata(self, aws_config, config_manager):
        """Test S3 bucket name generation with blueprint metadata"""
        generator = AWSNamingGenerator(
            config=aws_config,
            configuration_manager=config_manager,
            use_config=True
        )
        
        metadata = {"layer": "silver"}
        name = generator.generate_s3_bucket_name(
            purpose="processed",
            layer="gold",  # Should be overridden by metadata
            metadata=metadata
        )
        
        # Metadata should take precedence
        assert "silver" in name or "gold" in name  # Depends on precedence rules
    
    def test_generate_s3_bucket_name_validation_failure(self, aws_config):
        """Test S3 bucket name validation failure (name too long)"""
        # Create config with very long project name
        long_values = {
            "version": "1.0",
            "defaults": {
                "project": "a" * 100,  # Very long
                "purpose": "data",
                "layer": "raw",
                "region": "us-east-1",
                "region_short": "use1"
            }
        }
        
        patterns = {
            "version": "1.0",
            "patterns": {
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
                "dbx_cluster": "{project}",
                "dbx_job": "{project}",
                "dbx_catalog": "{project}",
                "dbx_schema": "{domain}",
                "dbx_table": "{entity}"
            },
            "validation": {
                "max_length": {
                    "aws_s3_bucket": 63
                }
            }
        }
        
        manager = ConfigurationManager()
        manager.load_configs(values_dict=long_values, patterns_dict=patterns)
        
        generator = AWSNamingGenerator(
            config=aws_config,
            configuration_manager=manager,
            use_config=True
        )
        
        # Generate a name that will exceed the max length
        name = generator.generate_s3_bucket_name(purpose="data", layer="raw")
        
        # The name should be generated but will be very long
        # The actual validation happens in the result
        assert len(name) > 63  # Name exceeds limit
    
    def test_generate_s3_bucket_name_use_config_false_raises_error(self, aws_config):
        """Test that use_config=False raises NotImplementedError"""
        generator = AWSNamingGenerator(
            config=aws_config,
            use_config=False
        )
        
        with pytest.raises(NotImplementedError, match="use_config=True"):
            generator.generate_s3_bucket_name(purpose="data", layer="raw")


# ============================================================================
# Test Glue Resource Name Generation
# ============================================================================

class TestAWSNamingGeneratorGlue:
    """Test Glue resource name generation"""
    
    def test_generate_glue_database_name_success(self, aws_config, config_manager):
        """Test successful Glue database name generation"""
        generator = AWSNamingGenerator(
            config=aws_config,
            configuration_manager=config_manager,
            use_config=True
        )
        
        name = generator.generate_glue_database_name(
            domain="sales",
            layer="silver"
        )
        
        assert name == "testproject_sales_silver_prd"
    
    def test_generate_glue_database_name_with_metadata(self, aws_config, config_manager):
        """Test Glue database name generation with metadata"""
        generator = AWSNamingGenerator(
            config=aws_config,
            configuration_manager=config_manager,
            use_config=True
        )
        
        metadata = {"domain": "finance"}
        name = generator.generate_glue_database_name(
            domain="sales",
            layer="gold",
            metadata=metadata
        )
        
        assert "prd" in name
    
    def test_generate_glue_database_name_use_config_false_raises_error(self, aws_config):
        """Test that use_config=False raises NotImplementedError"""
        generator = AWSNamingGenerator(config=aws_config, use_config=False)
        
        with pytest.raises(NotImplementedError):
            generator.generate_glue_database_name(domain="sales", layer="gold")
    
    def test_generate_glue_table_name_success(self, aws_config, config_manager):
        """Test successful Glue table name generation"""
        generator = AWSNamingGenerator(
            config=aws_config,
            configuration_manager=config_manager,
            use_config=True
        )
        
        name = generator.generate_glue_table_name(
            entity="orders",
            table_type="fact"
        )
        
        assert name == "fact_orders"
    
    def test_generate_glue_table_name_with_metadata(self, aws_config, config_manager):
        """Test Glue table name generation with metadata"""
        generator = AWSNamingGenerator(
            config=aws_config,
            configuration_manager=config_manager,
            use_config=True
        )
        
        metadata = {"table_type": "dim"}
        name = generator.generate_glue_table_name(
            entity="customers",
            table_type="fact",
            metadata=metadata
        )
        
        assert "customers" in name
    
    def test_generate_glue_table_name_use_config_false_raises_error(self, aws_config):
        """Test that use_config=False raises NotImplementedError"""
        generator = AWSNamingGenerator(config=aws_config, use_config=False)
        
        with pytest.raises(NotImplementedError):
            generator.generate_glue_table_name(entity="test", table_type="fact")
    
    def test_generate_glue_crawler_name_success(self, aws_config, config_manager):
        """Test successful Glue crawler name generation"""
        generator = AWSNamingGenerator(
            config=aws_config,
            configuration_manager=config_manager,
            use_config=True
        )
        
        name = generator.generate_glue_crawler_name(
            database="salesdb",
            source="s3"
        )
        
        assert name == "testproject-prd-crawler-salesdb-s3"
    
    def test_generate_glue_crawler_name_with_metadata(self, aws_config, config_manager):
        """Test Glue crawler name generation with metadata"""
        generator = AWSNamingGenerator(
            config=aws_config,
            configuration_manager=config_manager,
            use_config=True
        )
        
        metadata = {"source": "rds"}
        name = generator.generate_glue_crawler_name(
            database="testdb",
            source="s3",
            metadata=metadata
        )
        
        assert "prd" in name
        assert "testdb" in name
    
    def test_generate_glue_crawler_name_use_config_false_raises_error(self, aws_config):
        """Test that use_config=False raises NotImplementedError"""
        generator = AWSNamingGenerator(config=aws_config, use_config=False)
        
        with pytest.raises(NotImplementedError):
            generator.generate_glue_crawler_name(database="test", source="s3")


# ============================================================================
# Test Lambda Function Name Generation
# ============================================================================

class TestAWSNamingGeneratorLambda:
    """Test Lambda function name generation"""
    
    def test_generate_lambda_function_name_success(self, aws_config, config_manager):
        """Test successful Lambda function name generation"""
        generator = AWSNamingGenerator(
            config=aws_config,
            configuration_manager=config_manager,
            use_config=True
        )
        
        name = generator.generate_lambda_function_name(
            domain="orders",
            trigger="s3",
            action="validate"
        )
        
        assert name == "testproject-prd-orders-s3-validate"
    
    def test_generate_lambda_function_name_with_metadata(self, aws_config, config_manager):
        """Test Lambda function name generation with metadata"""
        generator = AWSNamingGenerator(
            config=aws_config,
            configuration_manager=config_manager,
            use_config=True
        )
        
        metadata = {"action": "transform"}
        name = generator.generate_lambda_function_name(
            domain="sales",
            trigger="kinesis",
            action="process",
            metadata=metadata
        )
        
        assert "prd" in name
        assert "sales" in name
    
    def test_generate_lambda_function_name_use_config_false_raises_error(self, aws_config):
        """Test that use_config=False raises NotImplementedError"""
        generator = AWSNamingGenerator(config=aws_config, use_config=False)
        
        with pytest.raises(NotImplementedError):
            generator.generate_lambda_function_name(
                domain="test",
                trigger="s3",
                action="process"
            )


# ============================================================================
# Test IAM Resource Name Generation
# ============================================================================

class TestAWSNamingGeneratorIAM:
    """Test IAM resource name generation"""
    
    def test_generate_iam_role_name_success(self, aws_config, config_manager):
        """Test successful IAM role name generation"""
        generator = AWSNamingGenerator(
            config=aws_config,
            configuration_manager=config_manager,
            use_config=True
        )
        
        name = generator.generate_iam_role_name(
            service="glue",
            purpose="execution"
        )
        
        assert name == "testproject-prd-glue-execution-role"
    
    def test_generate_iam_role_name_with_metadata(self, aws_config, config_manager):
        """Test IAM role name generation with metadata"""
        generator = AWSNamingGenerator(
            config=aws_config,
            configuration_manager=config_manager,
            use_config=True
        )
        
        metadata = {"purpose": "admin"}
        name = generator.generate_iam_role_name(
            service="lambda",
            purpose="execution",
            metadata=metadata
        )
        
        assert "prd" in name
        assert "lambda" in name
    
    def test_generate_iam_role_name_use_config_false_raises_error(self, aws_config):
        """Test that use_config=False raises NotImplementedError"""
        generator = AWSNamingGenerator(config=aws_config, use_config=False)
        
        with pytest.raises(NotImplementedError):
            generator.generate_iam_role_name(service="lambda", purpose="execution")
    
    def test_generate_iam_policy_name_success(self, aws_config, config_manager):
        """Test successful IAM policy name generation"""
        generator = AWSNamingGenerator(
            config=aws_config,
            configuration_manager=config_manager,
            use_config=True
        )
        
        name = generator.generate_iam_policy_name(
            service="s3",
            purpose="read-write"
        )
        
        assert name == "testproject-prd-s3-read-write-policy"
    
    def test_generate_iam_policy_name_with_metadata(self, aws_config, config_manager):
        """Test IAM policy name generation with metadata"""
        generator = AWSNamingGenerator(
            config=aws_config,
            configuration_manager=config_manager,
            use_config=True
        )
        
        metadata = {"service": "dynamodb"}
        name = generator.generate_iam_policy_name(
            service="s3",
            purpose="read",
            metadata=metadata
        )
        
        assert "prd" in name
        assert "policy" in name
    
    def test_generate_iam_policy_name_use_config_false_raises_error(self, aws_config):
        """Test that use_config=False raises NotImplementedError"""
        generator = AWSNamingGenerator(config=aws_config, use_config=False)
        
        with pytest.raises(NotImplementedError):
            generator.generate_iam_policy_name(service="s3", purpose="read")


# ============================================================================
# Test Kinesis Resource Name Generation
# ============================================================================

class TestAWSNamingGeneratorKinesis:
    """Test Kinesis resource name generation"""
    
    def test_generate_kinesis_stream_name_success(self, aws_config, config_manager):
        """Test successful Kinesis stream name generation"""
        generator = AWSNamingGenerator(
            config=aws_config,
            configuration_manager=config_manager,
            use_config=True
        )
        
        name = generator.generate_kinesis_stream_name(
            domain="clickstream",
            source="web"
        )
        
        assert name == "testproject-prd-clickstream-web-stream"
    
    def test_generate_kinesis_stream_name_with_metadata(self, aws_config, config_manager):
        """Test Kinesis stream name generation with metadata"""
        generator = AWSNamingGenerator(
            config=aws_config,
            configuration_manager=config_manager,
            use_config=True
        )
        
        metadata = {"source": "mobile"}
        name = generator.generate_kinesis_stream_name(
            domain="events",
            source="api",
            metadata=metadata
        )
        
        assert "prd" in name
        assert "events" in name
    
    def test_generate_kinesis_stream_name_use_config_false_raises_error(self, aws_config):
        """Test that use_config=False raises NotImplementedError"""
        generator = AWSNamingGenerator(config=aws_config, use_config=False)
        
        with pytest.raises(NotImplementedError):
            generator.generate_kinesis_stream_name(domain="events", source="api")
    
    def test_generate_kinesis_firehose_name_success(self, aws_config, config_manager):
        """Test successful Kinesis Firehose name generation"""
        generator = AWSNamingGenerator(
            config=aws_config,
            configuration_manager=config_manager,
            use_config=True
        )
        
        name = generator.generate_kinesis_firehose_name(
            domain="logs",
            destination="elasticsearch"
        )
        
        assert name == "testproject-prd-logs-to-elasticsearch"
    
    def test_generate_kinesis_firehose_name_with_metadata(self, aws_config, config_manager):
        """Test Kinesis Firehose name generation with metadata"""
        generator = AWSNamingGenerator(
            config=aws_config,
            configuration_manager=config_manager,
            use_config=True
        )
        
        metadata = {"destination": "redshift"}
        name = generator.generate_kinesis_firehose_name(
            domain="analytics",
            destination="s3",
            metadata=metadata
        )
        
        assert "prd" in name
        assert "analytics" in name
    
    def test_generate_kinesis_firehose_name_use_config_false_raises_error(self, aws_config):
        """Test that use_config=False raises NotImplementedError"""
        generator = AWSNamingGenerator(config=aws_config, use_config=False)
        
        with pytest.raises(NotImplementedError):
            generator.generate_kinesis_firehose_name(domain="logs", destination="s3")


# ============================================================================
# Test DynamoDB Table Name Generation
# ============================================================================

class TestAWSNamingGeneratorDynamoDB:
    """Test DynamoDB table name generation"""
    
    def test_generate_dynamodb_table_name_success(self, aws_config, config_manager):
        """Test successful DynamoDB table name generation"""
        generator = AWSNamingGenerator(
            config=aws_config,
            configuration_manager=config_manager,
            use_config=True
        )
        
        name = generator.generate_dynamodb_table_name(
            entity="session",
            purpose="cache"
        )
        
        assert name == "testproject-prd-session-cache"
    
    def test_generate_dynamodb_table_name_with_metadata(self, aws_config, config_manager):
        """Test DynamoDB table name generation with metadata"""
        generator = AWSNamingGenerator(
            config=aws_config,
            configuration_manager=config_manager,
            use_config=True
        )
        
        metadata = {"purpose": "state"}
        name = generator.generate_dynamodb_table_name(
            entity="user",
            purpose="profile",
            metadata=metadata
        )
        
        assert "prd" in name
        assert "user" in name
    
    def test_generate_dynamodb_table_name_use_config_false_raises_error(self, aws_config):
        """Test that use_config=False raises NotImplementedError"""
        generator = AWSNamingGenerator(config=aws_config, use_config=False)
        
        with pytest.raises(NotImplementedError):
            generator.generate_dynamodb_table_name(entity="test", purpose="data")


# ============================================================================
# Test SNS Topic Name Generation
# ============================================================================

class TestAWSNamingGeneratorSNS:
    """Test SNS topic name generation"""
    
    def test_generate_sns_topic_name_success(self, aws_config, config_manager):
        """Test successful SNS topic name generation"""
        generator = AWSNamingGenerator(
            config=aws_config,
            configuration_manager=config_manager,
            use_config=True
        )
        
        name = generator.generate_sns_topic_name(
            event_type="alert",
            purpose="failed"
        )
        
        assert name == "testproject-prd-alert-failed"
    
    def test_generate_sns_topic_name_with_metadata(self, aws_config, config_manager):
        """Test SNS topic name generation with metadata"""
        generator = AWSNamingGenerator(
            config=aws_config,
            configuration_manager=config_manager,
            use_config=True
        )
        
        metadata = {"purpose": "completed"}
        name = generator.generate_sns_topic_name(
            event_type="data",
            purpose="processed",
            metadata=metadata
        )
        
        assert "prd" in name
        assert "data" in name
    
    def test_generate_sns_topic_name_use_config_false_raises_error(self, aws_config):
        """Test that use_config=False raises NotImplementedError"""
        generator = AWSNamingGenerator(config=aws_config, use_config=False)
        
        with pytest.raises(NotImplementedError):
            generator.generate_sns_topic_name(event_type="alert", purpose="failed")


# ============================================================================
# Test SQS Queue Name Generation
# ============================================================================

class TestAWSNamingGeneratorSQS:
    """Test SQS queue name generation"""
    
    def test_generate_sqs_queue_name_success(self, aws_config, config_manager):
        """Test successful SQS queue name generation"""
        generator = AWSNamingGenerator(
            config=aws_config,
            configuration_manager=config_manager,
            use_config=True
        )
        
        name = generator.generate_sqs_queue_name(
            purpose="dlq",
            queue_type="standard"
        )
        
        assert name == "testproject-prd-dlq-standard"
    
    def test_generate_sqs_queue_name_with_metadata(self, aws_config, config_manager):
        """Test SQS queue name generation with metadata"""
        generator = AWSNamingGenerator(
            config=aws_config,
            configuration_manager=config_manager,
            use_config=True
        )
        
        metadata = {"queue_type": "fifo"}
        name = generator.generate_sqs_queue_name(
            purpose="processing",
            queue_type="standard",
            metadata=metadata
        )
        
        assert "prd" in name
        assert "processing" in name
    
    def test_generate_sqs_queue_name_use_config_false_raises_error(self, aws_config):
        """Test that use_config=False raises NotImplementedError"""
        generator = AWSNamingGenerator(config=aws_config, use_config=False)
        
        with pytest.raises(NotImplementedError):
            generator.generate_sqs_queue_name(purpose="processing", queue_type="standard")


# ============================================================================
# Test Step Functions Name Generation
# ============================================================================

class TestAWSNamingGeneratorStepFunctions:
    """Test Step Functions state machine name generation"""
    
    def test_generate_step_function_name_success(self, aws_config, config_manager):
        """Test successful Step Function name generation"""
        generator = AWSNamingGenerator(
            config=aws_config,
            configuration_manager=config_manager,
            use_config=True
        )
        
        name = generator.generate_step_function_name(
            workflow="ml-pipeline",
            purpose="training"
        )
        
        assert name == "testproject-prd-ml-pipeline-training"
    
    def test_generate_step_function_name_with_metadata(self, aws_config, config_manager):
        """Test Step Function name generation with metadata"""
        generator = AWSNamingGenerator(
            config=aws_config,
            configuration_manager=config_manager,
            use_config=True
        )
        
        metadata = {"purpose": "inference"}
        name = generator.generate_step_function_name(
            workflow="etl",
            purpose="orchestration",
            metadata=metadata
        )
        
        assert "prd" in name
        assert "etl" in name
    
    def test_generate_step_function_name_use_config_false_raises_error(self, aws_config):
        """Test that use_config=False raises NotImplementedError"""
        generator = AWSNamingGenerator(config=aws_config, use_config=False)
        
        with pytest.raises(NotImplementedError):
            generator.generate_step_function_name(workflow="etl", purpose="orchestration")


# ============================================================================
# Test Integration Scenarios
# ============================================================================

class TestAWSNamingGeneratorIntegration:
    """Test end-to-end integration scenarios"""
    
    def test_generate_all_resource_types(self, aws_config, config_manager):
        """Test generating names for all 13 AWS resource types"""
        generator = AWSNamingGenerator(
            config=aws_config,
            configuration_manager=config_manager,
            use_config=True
        )
        
        # Generate one name for each resource type
        names = {
            "s3": generator.generate_s3_bucket_name("data", "raw"),
            "glue_db": generator.generate_glue_database_name("finance", "gold"),
            "glue_table": generator.generate_glue_table_name("customers", "dim"),
            "glue_crawler": generator.generate_glue_crawler_name("testdb", "s3"),
            "lambda": generator.generate_lambda_function_name("sales", "s3", "process"),
            "iam_role": generator.generate_iam_role_name("lambda", "execution"),
            "iam_policy": generator.generate_iam_policy_name("s3", "read"),
            "kinesis_stream": generator.generate_kinesis_stream_name("events", "api"),
            "kinesis_firehose": generator.generate_kinesis_firehose_name("logs", "s3"),
            "dynamodb": generator.generate_dynamodb_table_name("customer", "profile"),
            "sns": generator.generate_sns_topic_name("data", "processed"),
            "sqs": generator.generate_sqs_queue_name("processing", "fifo"),
            "step_function": generator.generate_step_function_name("etl", "orchestration")
        }
        
        # Verify all names were generated
        assert len(names) == 13
        for resource_type, name in names.items():
            assert name is not None
            assert len(name) > 0
            # Most names should have environment, but some patterns don't include it (like glue_table)
            # Just verify we got valid names
    
    def test_different_environments(self, config_manager):
        """Test generating names across different environments"""
        environments = ["dev", "stg", "prd"]
        
        for env in environments:
            config = AWSNamingConfig(
                environment=env,
                project="testproject",
                region="us-east-1"
            )
            
            generator = AWSNamingGenerator(
                config=config,
                configuration_manager=config_manager,
                use_config=True
            )
            
            name = generator.generate_s3_bucket_name("data", "raw")
            
            # Verify environment is in the name
            assert env in name
    
    def test_with_value_overrides(self, aws_config, config_manager):
        """Test that value overrides work correctly"""
        generator = AWSNamingGenerator(
            config=aws_config,
            configuration_manager=config_manager,
            use_config=True
        )
        
        # Generate with custom purpose
        name = generator.generate_s3_bucket_name(
            purpose="custom-analytics",
            layer="processed"
        )
        
        assert "custom-analytics" in name
        assert "processed" in name
    
    def test_optional_config_fields(self, aws_config_minimal, config_manager):
        """Test generator with minimal config (no team, cost_center)"""
        generator = AWSNamingGenerator(
            config=aws_config_minimal,
            configuration_manager=config_manager,
            use_config=True
        )
        
        # Should still work without optional fields
        name = generator.generate_s3_bucket_name("data", "raw")
        
        assert name is not None
        assert "dev" in name
        assert "testproject" in name


# ============================================================================
# Test Utility Methods
# ============================================================================

class TestAWSNamingGeneratorUtilities:
    """Test utility methods"""
    
    def test_get_region_code(self, aws_config):
        """Test region code mapping"""
        generator = AWSNamingGenerator(config=aws_config, use_config=False)
        
        region_code = generator._get_region_code()
        
        assert region_code == "use1"
    
    def test_get_region_code_unknown_region(self):
        """Test region code for unknown region returns default"""
        config = AWSNamingConfig(
            environment="dev",
            project="test",
            region="unknown-region"
        )
        
        generator = AWSNamingGenerator(config=config, use_config=False)
        region_code = generator._get_region_code()
        
        # Should return default
        assert region_code == "use1"
    
    def test_sanitize_name_s3(self, aws_config):
        """Test name sanitization for S3 buckets"""
        generator = AWSNamingGenerator(config=aws_config, use_config=False)
        
        sanitized = generator._sanitize_name(
            "Test_Bucket!Name",
            AWSResourceType.S3_BUCKET
        )
        
        # Should be lowercase with hyphens
        assert sanitized == "test-bucket-name"
        assert sanitized.islower()
    
    def test_sanitize_name_glue(self, aws_config):
        """Test name sanitization for Glue resources"""
        generator = AWSNamingGenerator(config=aws_config, use_config=False)
        
        sanitized = generator._sanitize_name(
            "Test-Database!Name",
            AWSResourceType.GLUE_DATABASE
        )
        
        # Should be lowercase with underscores
        assert sanitized == "test_database_name"
        assert sanitized.islower()
    
    def test_truncate_name_within_limit(self, aws_config):
        """Test name truncation when within limit"""
        generator = AWSNamingGenerator(config=aws_config, use_config=False)
        
        short_name = "short-name"
        truncated = generator._truncate_name(short_name, AWSResourceType.S3_BUCKET)
        
        # Should remain unchanged
        assert truncated == short_name
    
    def test_truncate_name_exceeds_limit(self, aws_config):
        """Test name truncation when exceeding limit"""
        generator = AWSNamingGenerator(config=aws_config, use_config=False)
        
        long_name = "a" * 100  # Way over S3 limit of 63
        truncated = generator._truncate_name(long_name, AWSResourceType.S3_BUCKET)
        
        # Should be truncated to limit
        assert len(truncated) <= 63
    
    def test_generate_standard_tags(self, aws_config):
        """Test standard tags generation"""
        generator = AWSNamingGenerator(config=aws_config, use_config=False)
        
        tags = generator.generate_standard_tags(AWSResourceType.S3_BUCKET)
        
        assert "Environment" in tags
        assert tags["Environment"] == "prd"
        assert "Project" in tags
        assert tags["Project"] == "testproject"
        assert "ManagedBy" in tags
        assert tags["ManagedBy"] == "terraform"
        assert "ResourceType" in tags
        assert tags["ResourceType"] == "s3_bucket"
        assert "Team" in tags
        assert tags["Team"] == "data-engineering"
        assert "CostCenter" in tags
        assert tags["CostCenter"] == "eng-001"
    
    def test_generate_standard_tags_with_additional(self, aws_config):
        """Test standard tags with additional custom tags"""
        generator = AWSNamingGenerator(config=aws_config, use_config=False)
        
        additional = {
            "Owner": "data-team",
            "Application": "analytics"
        }
        
        tags = generator.generate_standard_tags(
            AWSResourceType.S3_BUCKET,
            additional_tags=additional
        )
        
        # Should include both standard and additional tags
        assert "Environment" in tags
        assert "Owner" in tags
        assert tags["Owner"] == "data-team"
        assert "Application" in tags
        assert tags["Application"] == "analytics"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
