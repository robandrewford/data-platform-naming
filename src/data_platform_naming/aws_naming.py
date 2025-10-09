#!/usr/bin/env python3
"""
AWS Data Platform Resource Naming Generator
Battle-tested enterprise naming conventions for AWS resources
"""

import re
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum


class AWSResourceType(Enum):
    """AWS resource types with naming patterns"""
    S3_BUCKET = "s3_bucket"
    GLUE_DATABASE = "glue_database"
    GLUE_TABLE = "glue_table"
    GLUE_CRAWLER = "glue_crawler"
    LAMBDA_FUNCTION = "lambda_function"
    IAM_ROLE = "iam_role"
    IAM_POLICY = "iam_policy"
    KINESIS_STREAM = "kinesis_stream"
    KINESIS_FIREHOSE = "kinesis_firehose"
    DYNAMODB_TABLE = "dynamodb_table"
    SNS_TOPIC = "sns_topic"
    SQS_QUEUE = "sqs_queue"
    STEP_FUNCTION = "step_function"


@dataclass
class AWSNamingConfig:
    """Configuration for AWS naming conventions"""
    environment: str  # dev, stg, prd
    project: str
    region: str  # us-east-1, eu-west-1, etc.
    team: Optional[str] = None
    cost_center: Optional[str] = None


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
    
    def __init__(self, config: AWSNamingConfig):
        self.config = config
        self._validate_config()
    
    def _validate_config(self):
        """Validate configuration parameters"""
        if self.config.environment not in ['dev', 'stg', 'prd']:
            raise ValueError(f"Invalid environment: {self.config.environment}")
        
        if not re.match(r'^[a-z0-9-]+$', self.config.project):
            raise ValueError(f"Invalid project name: {self.config.project}")
    
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
    
    def generate_s3_bucket_name(self, 
                                purpose: str,
                                layer: str = "raw",
                                include_hash: bool = True) -> str:
        """Generate S3 bucket name
        
        Pattern: {project}-{layer}-{purpose}-{env}-{region}
        Example: dataplatform-raw-sales-prd-use1
        """
        import hashlib
        
        parts = [
            self.config.project,
            layer,
            purpose,
            self.config.environment,
            self._get_region_code()
        ]
        
        name = '-'.join(parts)
        
        if include_hash:
            hash_input = f"{name}-{self.config.team or 'default'}"
            hash_val = hashlib.md5(hash_input.encode()).hexdigest()[:4]
            name = f"{name}-{hash_val}"
        
        return self._truncate_name(
            self._sanitize_name(name, AWSResourceType.S3_BUCKET),
            AWSResourceType.S3_BUCKET
        )
    
    def generate_glue_database_name(self,
                                   domain: str,
                                   layer: str = "bronze") -> str:
        """Generate Glue database name
        
        Pattern: {project}_{domain}_{layer}_{env}
        Example: dataplatform_finance_gold_prd
        """
        parts = [
            self.config.project,
            domain,
            layer,
            self.config.environment
        ]
        
        name = '_'.join(parts)
        return self._truncate_name(
            self._sanitize_name(name, AWSResourceType.GLUE_DATABASE),
            AWSResourceType.GLUE_DATABASE
        )
    
    def generate_glue_table_name(self,
                                entity: str,
                                table_type: str = "fact") -> str:
        """Generate Glue table name
        
        Pattern: {type}_{entity}
        Example: fact_sales, dim_customer
        """
        if table_type == "fact":
            name = f"fact_{entity}"
        elif table_type == "dim":
            name = f"dim_{entity}"
        else:
            name = f"{table_type}_{entity}"
        
        return self._truncate_name(
            self._sanitize_name(name, AWSResourceType.GLUE_TABLE),
            AWSResourceType.GLUE_TABLE
        )
    
    def generate_glue_crawler_name(self,
                                   database: str,
                                   source: str) -> str:
        """Generate Glue crawler name
        
        Pattern: {project}-{env}-crawler-{database}-{source}
        Example: dataplatform-prd-crawler-sales-s3
        """
        parts = [
            self.config.project,
            self.config.environment,
            "crawler",
            database,
            source
        ]
        
        name = '-'.join(parts)
        return self._truncate_name(
            self._sanitize_name(name, AWSResourceType.GLUE_CRAWLER),
            AWSResourceType.GLUE_CRAWLER
        )
    
    def generate_lambda_function_name(self,
                                     domain: str,
                                     trigger: str,
                                     action: str) -> str:
        """Generate Lambda function name
        
        Pattern: {project}-{env}-{domain}-{trigger}-{action}
        Example: dataplatform-prd-sales-s3-process
        """
        parts = [
            self.config.project,
            self.config.environment,
            domain,
            trigger,
            action
        ]
        
        name = '-'.join(parts)
        return self._truncate_name(
            self._sanitize_name(name, AWSResourceType.LAMBDA_FUNCTION),
            AWSResourceType.LAMBDA_FUNCTION
        )
    
    def generate_iam_role_name(self,
                              service: str,
                              purpose: str) -> str:
        """Generate IAM role name
        
        Pattern: {project}-{env}-{service}-{purpose}-role
        Example: dataplatform-prd-lambda-process-role
        """
        parts = [
            self.config.project,
            self.config.environment,
            service,
            purpose,
            "role"
        ]
        
        name = '-'.join(parts)
        return self._truncate_name(
            self._sanitize_name(name, AWSResourceType.IAM_ROLE),
            AWSResourceType.IAM_ROLE
        )
    
    def generate_iam_policy_name(self,
                                service: str,
                                purpose: str) -> str:
        """Generate IAM policy name
        
        Pattern: {project}-{env}-{service}-{purpose}-policy
        Example: dataplatform-prd-s3-read-policy
        """
        parts = [
            self.config.project,
            self.config.environment,
            service,
            purpose,
            "policy"
        ]
        
        name = '-'.join(parts)
        return self._truncate_name(
            self._sanitize_name(name, AWSResourceType.IAM_POLICY),
            AWSResourceType.IAM_POLICY
        )
    
    def generate_kinesis_stream_name(self,
                                    domain: str,
                                    source: str) -> str:
        """Generate Kinesis stream name
        
        Pattern: {project}-{env}-{domain}-{source}-stream
        Example: dataplatform-prd-sales-api-stream
        """
        parts = [
            self.config.project,
            self.config.environment,
            domain,
            source,
            "stream"
        ]
        
        name = '-'.join(parts)
        return self._truncate_name(
            self._sanitize_name(name, AWSResourceType.KINESIS_STREAM),
            AWSResourceType.KINESIS_STREAM
        )
    
    def generate_kinesis_firehose_name(self,
                                      domain: str,
                                      destination: str) -> str:
        """Generate Kinesis Firehose delivery stream name
        
        Pattern: {project}-{env}-{domain}-to-{destination}
        Example: dataplatform-prd-sales-to-s3
        """
        parts = [
            self.config.project,
            self.config.environment,
            domain,
            "to",
            destination
        ]
        
        name = '-'.join(parts)
        return self._truncate_name(
            self._sanitize_name(name, AWSResourceType.KINESIS_FIREHOSE),
            AWSResourceType.KINESIS_FIREHOSE
        )
    
    def generate_dynamodb_table_name(self,
                                    entity: str,
                                    purpose: str = "data") -> str:
        """Generate DynamoDB table name
        
        Pattern: {project}-{env}-{entity}-{purpose}
        Example: dataplatform-prd-customer-profile
        """
        parts = [
            self.config.project,
            self.config.environment,
            entity,
            purpose
        ]
        
        name = '-'.join(parts)
        return self._truncate_name(
            self._sanitize_name(name, AWSResourceType.DYNAMODB_TABLE),
            AWSResourceType.DYNAMODB_TABLE
        )
    
    def generate_sns_topic_name(self,
                               event_type: str,
                               purpose: str) -> str:
        """Generate SNS topic name
        
        Pattern: {project}-{env}-{event_type}-{purpose}
        Example: dataplatform-prd-data-processed
        """
        parts = [
            self.config.project,
            self.config.environment,
            event_type,
            purpose
        ]
        
        name = '-'.join(parts)
        return self._truncate_name(
            self._sanitize_name(name, AWSResourceType.SNS_TOPIC),
            AWSResourceType.SNS_TOPIC
        )
    
    def generate_sqs_queue_name(self,
                               purpose: str,
                               queue_type: str = "standard") -> str:
        """Generate SQS queue name
        
        Pattern: {project}-{env}-{purpose}-{type}
        Example: dataplatform-prd-processing-fifo
        """
        parts = [
            self.config.project,
            self.config.environment,
            purpose,
            queue_type
        ]
        
        name = '-'.join(parts)
        
        if queue_type == "fifo":
            name = f"{name}.fifo"
        
        return self._truncate_name(
            self._sanitize_name(name, AWSResourceType.SQS_QUEUE),
            AWSResourceType.SQS_QUEUE
        )
    
    def generate_step_function_name(self,
                                   workflow: str,
                                   purpose: str) -> str:
        """Generate Step Functions state machine name
        
        Pattern: {project}-{env}-{workflow}-{purpose}
        Example: dataplatform-prd-etl-orchestration
        """
        parts = [
            self.config.project,
            self.config.environment,
            workflow,
            purpose
        ]
        
        name = '-'.join(parts)
        return self._truncate_name(
            self._sanitize_name(name, AWSResourceType.STEP_FUNCTION),
            AWSResourceType.STEP_FUNCTION
        )
    
    def generate_standard_tags(self,
                              resource_type: AWSResourceType,
                              additional_tags: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Generate standard tags for AWS resources"""
        tags = {
            "Environment": self.config.environment,
            "Project": self.config.project,
            "ManagedBy": "terraform",
            "ResourceType": resource_type.value,
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
    config = AWSNamingConfig(
        environment="prd",
        project="dataplatform",
        region="us-east-1",
        team="data-engineering"
    )
    
    generator = AWSNamingGenerator(config)
    
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
