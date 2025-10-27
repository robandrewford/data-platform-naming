#!/usr/bin/env python3
"""
AWS Data Platform Resource Naming Generator
Battle-tested enterprise naming conventions for AWS resources
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

# Import ConfigurationManager for type hints
from .config.configuration_manager import ConfigurationManager
from .constants import AWSResourceType, Environment, TableType
from .exceptions import PatternError, ValidationError


@dataclass
class AWSNamingConfig:
    """Configuration for AWS naming conventions"""
    environment: str  # dev, stg, prd
    project: str
    region: str  # us-east-1, eu-west-1, etc.
    team: str | None = None
    cost_center: str | None = None


class AWSNamingGenerator:
    """Generate standardized names for AWS resources"""

    # Maximum lengths per resource type
    MAX_LENGTHS = {
        AWSResourceType.S3_BUCKET: 63,
        AWSResourceType.GLUE_DATABASE: 255,
        AWSResourceType.GLUE_TABLE: 255,
        AWSResourceType.GLUE_CRAWLER: 255,
        AWSResourceType.LAMBDA_FUNCTION: 64,
        AWSResourceType.IAM_ROLE: 64,
        AWSResourceType.IAM_POLICY: 128,
        AWSResourceType.KINESIS_STREAM: 128,
        AWSResourceType.KINESIS_FIREHOSE: 64,
        AWSResourceType.DYNAMODB_TABLE: 255,
        AWSResourceType.SNS_TOPIC: 256,
        AWSResourceType.SQS_QUEUE: 80,
        AWSResourceType.STEP_FUNCTION: 80,
    }

    # Region code mappings
    REGION_CODES = {
        'us-east-1': 'use1',
        'us-east-2': 'use2',
        'us-west-1': 'usw1',
        'us-west-2': 'usw2',
        'eu-west-1': 'euw1',
        'eu-west-2': 'euw2',
        'eu-central-1': 'euc1',
        'ap-southeast-1': 'aps1',
        'ap-southeast-2': 'aps2',
        'ap-northeast-1': 'apne1',
    }

    def __init__(
        self,
        config: AWSNamingConfig,
        configuration_manager: ConfigurationManager
    ) -> None:
        """
        Initialize AWS naming generator.

        Args:
            config: AWS naming configuration
            configuration_manager: ConfigurationManager for pattern-based generation

        Raises:
            ValueError: If configuration_manager is None or required patterns missing
        """
        if configuration_manager is None:
            raise ValidationError(
                message="ConfigurationManager is required",
                field="configuration_manager",
                suggestion="Legacy mode without ConfigurationManager is no longer supported. Pass a ConfigurationManager instance."
            )
        
        self.config = config
        self.configuration_manager = configuration_manager

        self._validate_config()
        self._validate_patterns_at_init()

    def _validate_config(self) -> None:
        """Validate configuration parameters"""
        if self.config.environment not in [e.value for e in Environment]:
            raise ValidationError(
                message=f"Invalid environment: {self.config.environment}",
                field="environment",
                value=self.config.environment,
                suggestion=f"Valid environments: {', '.join(e.value for e in Environment)}"
            )

        if not re.match(r'^[a-z0-9-]+$', self.config.project):
            raise ValidationError(
                message=f"Invalid project name: {self.config.project}",
                field="project",
                value=self.config.project,
                suggestion="Project name must contain only lowercase letters, numbers, and hyphens"
            )

    def _validate_patterns_at_init(self) -> None:
        """
        Validate that all AWS resource patterns are available in ConfigurationManager.
        Called at initialization when use_config=True.
        
        Raises:
            ValueError: If any required patterns are missing or invalid
        """
        required_resource_types = [
            AWSResourceType.S3_BUCKET.value,
            AWSResourceType.GLUE_DATABASE.value,
            AWSResourceType.GLUE_TABLE.value,
            AWSResourceType.GLUE_CRAWLER.value,
            AWSResourceType.LAMBDA_FUNCTION.value,
            AWSResourceType.IAM_ROLE.value,
            AWSResourceType.IAM_POLICY.value,
            AWSResourceType.KINESIS_STREAM.value,
            AWSResourceType.KINESIS_FIREHOSE.value,
            AWSResourceType.DYNAMODB_TABLE.value,
            AWSResourceType.SNS_TOPIC.value,
            AWSResourceType.SQS_QUEUE.value,
            AWSResourceType.STEP_FUNCTION.value,
        ]

        missing_patterns = []
        invalid_patterns = []

        for resource_type in required_resource_types:
            try:
                pattern = self.configuration_manager.patterns_loader.get_pattern(resource_type)
                # Check that pattern has required variables
                pattern_vars = pattern.get_variables()
                if not pattern_vars:
                    invalid_patterns.append(
                        f"{resource_type}: Pattern has no variables"
                    )
            except Exception as e:
                missing_patterns.append(f"{resource_type}: {str(e)}")

        errors = []
        if missing_patterns:
            errors.append("Missing patterns:\n  " + "\n  ".join(missing_patterns))
        if invalid_patterns:
            errors.append("Invalid patterns:\n  " + "\n  ".join(invalid_patterns))

        if errors:
            # Collect all missing resource types
            missing_types = [rt for rt in required_resource_types 
                           if any(rt in err for err in missing_patterns)]
            raise PatternError(
                message="Pattern validation failed: " + "; ".join(errors),
                pattern="AWS resource patterns",
                missing_variables=missing_types
            )

    def _generate_with_config(
        self,
        resource_type: str,
        values: dict[str, Any],
        metadata: dict[str, Any] | None = None
    ) -> str:
        """
        Generate name using ConfigurationManager.
        
        Args:
            resource_type: AWS resource type (e.g., 'aws_s3_bucket')
            values: Dictionary of values to use for pattern substitution
            metadata: Optional blueprint metadata for additional context
        
        Returns:
            Generated resource name
        
        Raises:
            ValueError: If name generation or validation fails
        """
        # Start with config values (lowest precedence)
        merged_values = {
            "project": self.config.project,
            "region": self.config.region,
        }

        # Add environment only if not in metadata (metadata has higher precedence)
        if not metadata or "environment" not in metadata:
            merged_values["environment"] = self.config.environment

        # Add optional config values if present
        if self.config.team:
            merged_values["team"] = self.config.team
        if self.config.cost_center:
            merged_values["cost_center"] = self.config.cost_center

        # Add provided values (medium precedence)
        merged_values.update(values)

        # Generate using ConfigurationManager
        # metadata will have highest precedence in ConfigurationManager
        result = self.configuration_manager.generate_name(
            resource_type=resource_type,
            environment=self.config.environment,
            blueprint_metadata=metadata,
            value_overrides=merged_values
        )

        # Validate the generated name
        if not result.is_valid:
            raise ValidationError(
                message=f"Name validation failed for {resource_type}",
                field="generated_name",
                value=result.name,
                suggestion=", ".join(result.validation_errors),
                resource_type=resource_type
            )

        return result.name

    def _get_region_code(self) -> str:
        """Convert AWS region to short code"""
        return self.REGION_CODES.get(self.config.region, 'use1')

    def _sanitize_name(self, name: str, resource_type: AWSResourceType) -> str:
        """Sanitize name based on resource type constraints"""
        if resource_type == AWSResourceType.S3_BUCKET:
            # S3: lowercase alphanumeric and hyphens only
            name = name.lower()
            name = re.sub(r'[^a-z0-9-]', '-', name)
        elif resource_type in [AWSResourceType.GLUE_DATABASE, AWSResourceType.GLUE_TABLE]:
            # Glue: lowercase alphanumeric and underscores
            name = name.lower()
            name = re.sub(r'[^a-z0-9_]', '_', name)
        else:
            # Default: alphanumeric, dash, underscore
            name = re.sub(r'[^a-zA-Z0-9_-]', '-', name)

        # Remove consecutive special characters
        name = re.sub(r'[-_]+', lambda m: m.group()[0], name)
        name = name.strip('-_')

        return name

    def _truncate_name(self, name: str, resource_type: AWSResourceType) -> str:
        """Truncate name to maximum allowed length"""
        max_length = self.MAX_LENGTHS[resource_type]
        if len(name) <= max_length:
            return name

        # Intelligent truncation preserving suffix
        suffix_parts = name.split('-')[-2:]
        suffix = '-'.join(suffix_parts)
        prefix_length = max_length - len(suffix) - 1

        if prefix_length < 10:
            return name[:max_length]

        prefix = name[:prefix_length]
        return f"{prefix}-{suffix}"

    def generate_s3_bucket_name(
        self,
        purpose: str,
        layer: str = "raw",
        include_hash: bool = True,
        metadata: dict[str, Any] | None = None
    ) -> str:
        """
        Generate S3 bucket name.
        
        Pattern: {project}-{layer}-{purpose}-{env}-{region}
        Example: dataplatform-raw-sales-prd-use1
        
        Args:
            purpose: Bucket purpose (e.g., 'sales-data', 'logs')
            layer: Data layer ('raw', 'processed', 'curated')
            include_hash: Whether to include hash suffix for uniqueness
            metadata: Optional blueprint metadata for additional context
        
        Returns:
            Generated S3 bucket name
        
        Raises:
            ValueError: If name generation fails
        """
        return self._generate_with_config(
            resource_type=AWSResourceType.S3_BUCKET,
            values={
                "purpose": purpose,
                "layer": layer,
                "include_hash": include_hash
            },
            metadata=metadata
        )

    def generate_glue_database_name(
        self,
        domain: str,
        layer: str = "bronze",
        metadata: dict[str, Any] | None = None
    ) -> str:
        """
        Generate Glue database name.
        
        Pattern: {project}_{domain}_{layer}_{env}
        Example: dataplatform_finance_gold_prd
        
        Args:
            domain: Data domain (e.g., 'finance', 'sales', 'marketing')
            layer: Data layer ('bronze', 'silver', 'gold')
            metadata: Optional blueprint metadata for additional context
        
        Returns:
            Generated Glue database name
        
        Raises:
            ValueError: If name generation fails
        """
        return self._generate_with_config(
            resource_type=AWSResourceType.GLUE_DATABASE,
            values={
                "domain": domain,
                "layer": layer
            },
            metadata=metadata
        )

    def generate_glue_table_name(
        self,
        entity: str,
        table_type: str = TableType.FACT.value,
        metadata: dict[str, Any] | None = None
    ) -> str:
        """
        Generate Glue table name.
        
        Pattern: {type}_{entity}
        Example: fact_sales, dim_customer
        
        Args:
            entity: Business entity name (e.g., 'sales', 'customers')
            table_type: Table type ('fact', 'dim', 'bridge')
            metadata: Optional blueprint metadata for additional context
        
        Returns:
            Generated Glue table name
        
        Raises:
            ValueError: If name generation fails
        """
        return self._generate_with_config(
            resource_type=AWSResourceType.GLUE_TABLE,
            values={
                "entity": entity,
                "table_type": table_type
            },
            metadata=metadata
        )

    def generate_glue_crawler_name(
        self,
        database: str,
        source: str,
        metadata: dict[str, Any] | None = None
    ) -> str:
        """
        Generate Glue crawler name.
        
        Pattern: {project}-{env}-crawler-{database}-{source}
        Example: dataplatform-prd-crawler-sales-s3
        
        Args:
            database: Database name
            source: Source system identifier (e.g., 's3', 'rds')
            metadata: Optional blueprint metadata for additional context
        
        Returns:
            Generated Glue crawler name
        
        Raises:
            ValueError: If name generation fails
        """
        return self._generate_with_config(
            resource_type=AWSResourceType.GLUE_CRAWLER,
            values={
                "database": database,
                "source": source
            },
            metadata=metadata
        )

    def generate_lambda_function_name(
        self,
        domain: str,
        trigger: str,
        action: str,
        metadata: dict[str, Any] | None = None
    ) -> str:
        """
        Generate Lambda function name.
        
        Pattern: {project}-{env}-{domain}-{trigger}-{action}
        Example: dataplatform-prd-sales-s3-process
        
        Args:
            domain: Data domain (e.g., 'sales', 'customer')
            trigger: Trigger source (e.g., 's3', 'api', 'kinesis')
            action: Action performed (e.g., 'process', 'transform', 'validate')
            metadata: Optional blueprint metadata for additional context
        
        Returns:
            Generated Lambda function name
        
        Raises:
            ValueError: If name generation fails
        """
        return self._generate_with_config(
            resource_type=AWSResourceType.LAMBDA_FUNCTION,
            values={
                "domain": domain,
                "trigger": trigger,
                "action": action
            },
            metadata=metadata
        )

    def generate_iam_role_name(
        self,
        service: str,
        purpose: str,
        metadata: dict[str, Any] | None = None
    ) -> str:
        """
        Generate IAM role name.
        
        Pattern: {project}-{env}-{service}-{purpose}-role
        Example: dataplatform-prd-lambda-process-role
        
        Args:
            service: AWS service (e.g., 'lambda', 'glue', 'emr')
            purpose: Purpose of the role (e.g., 'execution', 'process')
            metadata: Optional blueprint metadata for additional context
        
        Returns:
            Generated IAM role name
        
        Raises:
            ValueError: If name generation fails
        """
        return self._generate_with_config(
            resource_type=AWSResourceType.IAM_ROLE,
            values={
                "service": service,
                "purpose": purpose
            },
            metadata=metadata
        )

    def generate_iam_policy_name(
        self,
        service: str,
        purpose: str,
        metadata: dict[str, Any] | None = None
    ) -> str:
        """
        Generate IAM policy name.
        
        Pattern: {project}-{env}-{service}-{purpose}-policy
        Example: dataplatform-prd-s3-read-policy
        
        Args:
            service: AWS service (e.g., 's3', 'dynamodb', 'sqs')
            purpose: Purpose of policy (e.g., 'read', 'write', 'read-write')
            metadata: Optional blueprint metadata for additional context
        
        Returns:
            Generated IAM policy name
        
        Raises:
            ValueError: If name generation fails
        """
        return self._generate_with_config(
            resource_type=AWSResourceType.IAM_POLICY,
            values={
                "service": service,
                "purpose": purpose
            },
            metadata=metadata
        )

    def generate_kinesis_stream_name(
        self,
        domain: str,
        source: str,
        metadata: dict[str, Any] | None = None
    ) -> str:
        """
        Generate Kinesis stream name.
        
        Pattern: {project}-{env}-{domain}-{source}-stream
        Example: dataplatform-prd-sales-api-stream
        
        Args:
            domain: Data domain (e.g., 'sales', 'events')
            source: Source identifier (e.g., 'api', 'iot', 'web')
            metadata: Optional blueprint metadata for additional context
        
        Returns:
            Generated Kinesis stream name
        
        Raises:
            ValueError: If name generation fails
        """
        return self._generate_with_config(
            resource_type=AWSResourceType.KINESIS_STREAM,
            values={
                "domain": domain,
                "source": source
            },
            metadata=metadata
        )

    def generate_kinesis_firehose_name(
        self,
        domain: str,
        destination: str,
        metadata: dict[str, Any] | None = None
    ) -> str:
        """
        Generate Kinesis Firehose delivery stream name.
        
        Pattern: {project}-{env}-{domain}-to-{destination}
        Example: dataplatform-prd-sales-to-s3
        
        Args:
            domain: Data domain (e.g., 'sales', 'logs')
            destination: Destination service (e.g., 's3', 'redshift', 'elasticsearch')
            metadata: Optional blueprint metadata for additional context
        
        Returns:
            Generated Kinesis Firehose name
        
        Raises:
            ValueError: If name generation fails
        """
        return self._generate_with_config(
            resource_type=AWSResourceType.KINESIS_FIREHOSE,
            values={
                "domain": domain,
                "destination": destination
            },
            metadata=metadata
        )

    def generate_dynamodb_table_name(
        self,
        entity: str,
        purpose: str = "data",
        metadata: dict[str, Any] | None = None
    ) -> str:
        """
        Generate DynamoDB table name.
        
        Pattern: {project}-{env}-{entity}-{purpose}
        Example: dataplatform-prd-customer-profile
        
        Args:
            entity: Business entity (e.g., 'customer', 'order')
            purpose: Table purpose (e.g., 'data', 'profile', 'cache')
            metadata: Optional blueprint metadata for additional context
        
        Returns:
            Generated DynamoDB table name
        
        Raises:
            ValueError: If name generation fails
        """
        return self._generate_with_config(
            resource_type=AWSResourceType.DYNAMODB_TABLE,
            values={
                "entity": entity,
                "purpose": purpose
            },
            metadata=metadata
        )

    def generate_sns_topic_name(
        self,
        event_type: str,
        purpose: str,
        metadata: dict[str, Any] | None = None
    ) -> str:
        """
        Generate SNS topic name.
        
        Pattern: {project}-{env}-{event_type}-{purpose}
        Example: dataplatform-prd-data-processed
        
        Args:
            event_type: Type of event (e.g., 'data', 'alert', 'notification')
            purpose: Purpose description (e.g., 'processed', 'failed', 'completed')
            metadata: Optional blueprint metadata for additional context
        
        Returns:
            Generated SNS topic name
        
        Raises:
            ValueError: If name generation fails
        """
        return self._generate_with_config(
            resource_type=AWSResourceType.SNS_TOPIC,
            values={
                "event_type": event_type,
                "purpose": purpose
            },
            metadata=metadata
        )

    def generate_sqs_queue_name(
        self,
        purpose: str,
        queue_type: str = "standard",
        metadata: dict[str, Any] | None = None
    ) -> str:
        """
        Generate SQS queue name.
        
        Pattern: {project}-{env}-{purpose}-{type}
        Example: dataplatform-prd-processing-fifo
        
        Args:
            purpose: Queue purpose (e.g., 'processing', 'dlq', 'events')
            queue_type: Queue type ('standard' or 'fifo')
            metadata: Optional blueprint metadata for additional context
        
        Returns:
            Generated SQS queue name
        
        Raises:
            ValueError: If name generation fails
        """
        return self._generate_with_config(
            resource_type=AWSResourceType.SQS_QUEUE,
            values={
                "purpose": purpose,
                "queue_type": queue_type
            },
            metadata=metadata
        )

    def generate_step_function_name(
        self,
        workflow: str,
        purpose: str,
        metadata: dict[str, Any] | None = None
    ) -> str:
        """
        Generate Step Functions state machine name.
        
        Pattern: {project}-{env}-{workflow}-{purpose}
        Example: dataplatform-prd-etl-orchestration
        
        Args:
            workflow: Workflow identifier (e.g., 'etl', 'ml', 'data-pipeline')
            purpose: Purpose description (e.g., 'orchestration', 'coordination')
            metadata: Optional blueprint metadata for additional context
        
        Returns:
            Generated Step Function name
        
        Raises:
            ValueError: If name generation fails
        """
        return self._generate_with_config(
            resource_type=AWSResourceType.STEP_FUNCTION,
            values={
                "workflow": workflow,
                "purpose": purpose
            },
            metadata=metadata
        )

    def generate_standard_tags(self,
                              resource_type: AWSResourceType,
                              additional_tags: dict[str, str] | None = None) -> dict[str, str]:
        """Generate standard tags for AWS resources"""
        # Strip 'aws_' prefix from resource type for cleaner tags
        resource_type_tag = resource_type.value.replace('aws_', '')
        
        tags = {
            "Environment": self.config.environment,
            "Project": self.config.project,
            "ManagedBy": "terraform",
            "ResourceType": resource_type_tag,
        }

        if self.config.team:
            tags["Team"] = self.config.team

        if self.config.cost_center:
            tags["CostCenter"] = self.config.cost_center

        if additional_tags:
            tags.update(additional_tags)

        return tags


# Example usage
if __name__ == "__main__":
    from pathlib import Path
    
    config = AWSNamingConfig(
        environment="prd",
        project="dataplatform",
        region="us-east-1",
        team="data-engineering"
    )

    # Load configuration manager
    config_mgr = ConfigurationManager()
    config_mgr.load_configs(
        values_path=Path("examples/configs/naming-values.yaml"),
        patterns_path=Path("examples/configs/naming-patterns.yaml")
    )

    generator = AWSNamingGenerator(config, config_mgr)

    # S3 Buckets
    print("\n=== S3 Buckets ===")
    print(generator.generate_s3_bucket_name("sales-data", "raw"))
    print(generator.generate_s3_bucket_name("customer-records", "curated"))

    # Glue Resources
    print("\n=== Glue Resources ===")
    print(generator.generate_glue_database_name("finance", "gold"))
    print(generator.generate_glue_table_name("customers", "dim"))
    print(generator.generate_glue_table_name("sales", "fact"))
    print(generator.generate_glue_crawler_name("sales", "s3"))

    # Lambda Functions
    print("\n=== Lambda Functions ===")
    print(generator.generate_lambda_function_name("sales", "s3", "process"))
    print(generator.generate_lambda_function_name("customer", "api", "transform"))

    # IAM Resources
    print("\n=== IAM Resources ===")
    print(generator.generate_iam_role_name("lambda", "execution"))
    print(generator.generate_iam_policy_name("s3", "read-write"))

    # Streaming
    print("\n=== Streaming ===")
    print(generator.generate_kinesis_stream_name("events", "api"))
    print(generator.generate_kinesis_firehose_name("logs", "s3"))

    # Other Services
    print("\n=== Other Services ===")
    print(generator.generate_dynamodb_table_name("customer", "profile"))
    print(generator.generate_sns_topic_name("data", "processed"))
    print(generator.generate_sqs_queue_name("processing", "fifo"))
    print(generator.generate_step_function_name("etl", "orchestration"))
