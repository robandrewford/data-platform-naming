#!/usr/bin/env python3
"""
constants.py
Global constants for AWS and Databricks naming conventions
"""



# =============================================================================
# ENVIRONMENT DEFINITIONS
# =============================================================================

ENVIRONMENTS = {
    'dev': 'Development',
    'stg': 'Staging',
    'prd': 'Production'
}

ENVIRONMENT_CODES = ['dev', 'stg', 'prd']


# =============================================================================
# AWS REGION MAPPINGS
# =============================================================================

AWS_REGION_CODES = {
    # US Regions
    'us-east-1': 'use1',
    'us-east-2': 'use2',
    'us-west-1': 'usw1',
    'us-west-2': 'usw2',

    # EU Regions
    'eu-west-1': 'euw1',
    'eu-west-2': 'euw2',
    'eu-west-3': 'euw3',
    'eu-central-1': 'euc1',
    'eu-north-1': 'eun1',

    # Asia Pacific
    'ap-south-1': 'aps1',
    'ap-southeast-1': 'apse1',
    'ap-southeast-2': 'apse2',
    'ap-northeast-1': 'apne1',
    'ap-northeast-2': 'apne2',
    'ap-northeast-3': 'apne3',

    # Canada
    'ca-central-1': 'cac1',

    # South America
    'sa-east-1': 'sae1',
}


# =============================================================================
# AWS SERVICE CONSTRAINTS
# =============================================================================

AWS_MAX_LENGTHS = {
    's3_bucket': 63,
    'glue_database': 255,
    'glue_table': 255,
    'glue_crawler': 255,
    'glue_job': 255,
    'lambda_function': 64,
    'iam_role': 64,
    'iam_policy': 128,
    'iam_user': 64,
    'kinesis_stream': 128,
    'kinesis_firehose': 64,
    'dynamodb_table': 255,
    'sns_topic': 256,
    'sqs_queue': 80,
    'step_function': 80,
    'cloudwatch_log_group': 512,
    'ecr_repository': 256,
    'ecs_cluster': 255,
    'ecs_service': 255,
    'ecs_task_definition': 255,
}

AWS_MIN_LENGTHS = {
    's3_bucket': 3,
}

# S3 specific
S3_RESERVED_PREFIXES = ['xn--', 'sthree-', 'sthree-configurator']
S3_FORBIDDEN_SUFFIXES = ['-s3alias', '--ol-s3']


# =============================================================================
# DATABRICKS SERVICE CONSTRAINTS
# =============================================================================

DATABRICKS_MAX_LENGTHS = {
    'workspace': 64,
    'cluster': 100,
    'job': 100,
    'notebook': 256,
    'repo': 100,
    'pipeline': 100,
    'sql_warehouse': 64,
    'catalog': 255,
    'schema': 255,
    'table': 255,
    'volume': 255,
    'secret_scope': 128,
    'instance_pool': 100,
    'policy': 100,
    'token': 100,
}


# =============================================================================
# DATA LAYERS (MEDALLION ARCHITECTURE)
# =============================================================================

DATA_LAYERS = {
    'bronze': 'Raw ingestion layer',
    'silver': 'Cleaned and conformed',
    'gold': 'Business-level aggregates'
}

DATA_LAYER_CODES = ['bronze', 'silver', 'gold']

# S3 specific layers
S3_LAYERS = {
    'raw': 'Unprocessed source data',
    'stage': 'Intermediate processing',
    'curated': 'Business-ready data',
    'archive': 'Long-term storage',
    'logs': 'Operational logs'
}

S3_LAYER_CODES = ['raw', 'stage', 'curated', 'archive', 'logs']


# =============================================================================
# DATA DOMAINS
# =============================================================================

COMMON_DOMAINS = [
    'sales',
    'marketing',
    'finance',
    'customer',
    'product',
    'inventory',
    'hr',
    'operations',
    'analytics',
    'engineering'
]


# =============================================================================
# TABLE TYPES (DATA WAREHOUSE)
# =============================================================================

TABLE_TYPES = {
    'fact': 'Fact table (measurements)',
    'dim': 'Dimension table (descriptive)',
    'bridge': 'Bridge table (many-to-many)',
    'staging': 'Staging table (temporary)',
    'reference': 'Reference/lookup table'
}

TABLE_TYPE_CODES = ['fact', 'dim', 'bridge', 'staging', 'reference']


# =============================================================================
# WORKLOAD TYPES
# =============================================================================

WORKLOAD_TYPES = {
    'etl': 'Extract-Transform-Load pipelines',
    'ml': 'Machine Learning workloads',
    'analytics': 'Ad-hoc analytics queries',
    'streaming': 'Real-time streaming processing',
    'batch': 'Batch processing jobs',
    'api': 'API service workloads'
}


# =============================================================================
# CLUSTER TYPES (DATABRICKS)
# =============================================================================

CLUSTER_TYPES = {
    'shared': 'Shared multi-user cluster',
    'dedicated': 'Single-purpose cluster',
    'job': 'Job-specific ephemeral cluster'
}


# =============================================================================
# SPARK VERSIONS (DATABRICKS)
# =============================================================================

SPARK_VERSIONS = [
    '13.3.x-scala2.12',
    '13.2.x-scala2.12',
    '12.2.x-scala2.12',
    '11.3.x-scala2.12',
]

DEFAULT_SPARK_VERSION = '13.3.x-scala2.12'


# =============================================================================
# NODE TYPES (COMMON)
# =============================================================================

AWS_NODE_TYPES = {
    # Compute Optimized
    'c5.xlarge': {'vcpu': 4, 'memory': 8},
    'c5.2xlarge': {'vcpu': 8, 'memory': 16},
    'c5.4xlarge': {'vcpu': 16, 'memory': 32},

    # Memory Optimized
    'r5.xlarge': {'vcpu': 4, 'memory': 32},
    'r5.2xlarge': {'vcpu': 8, 'memory': 64},
    'r5.4xlarge': {'vcpu': 16, 'memory': 128},

    # Storage Optimized
    'i3.xlarge': {'vcpu': 4, 'memory': 30.5},
    'i3.2xlarge': {'vcpu': 8, 'memory': 61},
    'i3.4xlarge': {'vcpu': 16, 'memory': 122},

    # GPU
    'g4dn.xlarge': {'vcpu': 4, 'memory': 16, 'gpu': 1},
    'g4dn.2xlarge': {'vcpu': 8, 'memory': 32, 'gpu': 1},
}


# =============================================================================
# NAMING PATTERNS (REGEX)
# =============================================================================

PATTERNS = {
    # AWS
    's3_bucket': r'^[a-z0-9][a-z0-9-]*[a-z0-9]$',
    'glue_database': r'^[a-z0-9_]+$',
    'glue_table': r'^[a-z0-9_]+$',
    'lambda_function': r'^[a-zA-Z0-9-_]+$',
    'iam_role': r'^[\w+=,.@-]+$',

    # Databricks
    'dbx_cluster': r'^[a-zA-Z0-9_-]+$',
    'dbx_job': r'^[a-zA-Z0-9_-]+$',
    'uc_catalog': r'^[a-zA-Z0-9_]+$',
    'uc_schema': r'^[a-zA-Z0-9_]+$',
    'uc_table': r'^[a-zA-Z0-9_]+$',

    # Convention
    'environment': r'^(dev|stg|prd)$',
    'project': r'^[a-z0-9-]+$',
}


# =============================================================================
# TAG TEMPLATES
# =============================================================================

STANDARD_TAGS = {
    'Environment': '{environment}',
    'Project': '{project}',
    'ManagedBy': 'terraform',
    'Team': '{team}',
    'CostCenter': '{cost_center}',
    'DataClassification': '{classification}',
    'CreatedDate': '{created_date}',
}

TAG_MAX_LENGTH = 256


# =============================================================================
# DATA CLASSIFICATION LEVELS
# =============================================================================

DATA_CLASSIFICATIONS = {
    'public': 'Publicly available data',
    'internal': 'Internal use only',
    'confidential': 'Confidential business data',
    'restricted': 'Highly restricted (PII, PHI, PCI)'
}


# =============================================================================
# RETRY POLICIES
# =============================================================================

RETRY_CONFIG = {
    'max_attempts': 3,
    'initial_delay': 1.0,  # seconds
    'max_delay': 60.0,
    'exponential_base': 2.0,
    'jitter': True
}


# =============================================================================
# TRANSACTION TIMEOUTS
# =============================================================================

TIMEOUTS = {
    'operation_default': 300,  # 5 minutes
    'operation_create': 600,   # 10 minutes
    'operation_delete': 300,   # 5 minutes
    'transaction_max': 1800,   # 30 minutes
    'cluster_ready': 600,      # 10 minutes
}


# =============================================================================
# STATE STORE PATHS
# =============================================================================

DEFAULT_BASE_DIR = '.dpn'
WAL_DIR = 'wal'
STATE_DIR = 'state'
CACHE_DIR = 'cache'
LOG_DIR = 'logs'


# =============================================================================
# CLI OUTPUT FORMATS
# =============================================================================

OUTPUT_FORMATS = ['json', 'yaml', 'table', 'csv']
DEFAULT_OUTPUT_FORMAT = 'table'


# =============================================================================
# VALIDATION ERROR CODES
# =============================================================================

ERROR_CODES = {
    # Length errors
    'LENGTH_MIN': 'Length below minimum',
    'LENGTH_MAX': 'Length exceeds maximum',

    # Pattern errors
    'PATTERN_INVALID': 'Does not match required pattern',
    'CHARS_INVALID': 'Contains invalid characters',

    # AWS specific
    'S3_RESERVED': 'Uses reserved prefix',
    'S3_IP_FORMAT': 'Resembles IP address',

    # Convention errors
    'ENV_INVALID': 'Invalid environment code',
    'REGION_INVALID': 'Invalid region code',
    'PROJECT_INVALID': 'Invalid project name',

    # Dependency errors
    'DEPENDENCY_MISSING': 'Missing required dependency',
    'DEPENDENCY_CYCLE': 'Circular dependency detected',
}


# =============================================================================
# API RATE LIMITS
# =============================================================================

RATE_LIMITS = {
    'aws_api_calls_per_second': 10,
    'databricks_api_calls_per_second': 10,
    'burst_capacity': 50
}


# =============================================================================
# FEATURE FLAGS
# =============================================================================

FEATURES = {
    'auto_tagging': True,
    'cost_estimation': False,
    'drift_detection': False,
    'auto_remediation': False,
}


# =============================================================================
# VERSION INFO
# =============================================================================

VERSION = '0.1.0'
API_VERSION = 'v1'
MIN_PYTHON_VERSION = (3, 9)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_region_code(region: str) -> str:
    """Get short code for AWS region"""
    return AWS_REGION_CODES.get(region, 'use1')


def get_max_length(resource_type: str) -> int:
    """Get maximum length for resource type"""
    return AWS_MAX_LENGTHS.get(resource_type) or \
           DATABRICKS_MAX_LENGTHS.get(resource_type) or \
           255


def is_valid_environment(env: str) -> bool:
    """Check if environment code is valid"""
    return env in ENVIRONMENT_CODES


def is_valid_layer(layer: str, platform: str = 'databricks') -> bool:
    """Check if layer code is valid"""
    if platform == 'databricks':
        return layer in DATA_LAYER_CODES
    elif platform == 'aws':
        return layer in S3_LAYER_CODES
    return False


# =============================================================================
# EXPORT
# =============================================================================

__all__ = [
    # Environments
    'ENVIRONMENTS',
    'ENVIRONMENT_CODES',

    # Regions
    'AWS_REGION_CODES',

    # Constraints
    'AWS_MAX_LENGTHS',
    'AWS_MIN_LENGTHS',
    'DATABRICKS_MAX_LENGTHS',

    # Layers
    'DATA_LAYERS',
    'DATA_LAYER_CODES',
    'S3_LAYERS',
    'S3_LAYER_CODES',

    # Domains
    'COMMON_DOMAINS',

    # Types
    'TABLE_TYPES',
    'TABLE_TYPE_CODES',
    'WORKLOAD_TYPES',
    'CLUSTER_TYPES',

    # Patterns
    'PATTERNS',

    # Tags
    'STANDARD_TAGS',
    'TAG_MAX_LENGTH',
    'DATA_CLASSIFICATIONS',

    # Config
    'RETRY_CONFIG',
    'TIMEOUTS',
    'RATE_LIMITS',

    # Paths
    'DEFAULT_BASE_DIR',
    'WAL_DIR',
    'STATE_DIR',

    # Version
    'VERSION',
    'API_VERSION',

    # Functions
    'get_region_code',
    'get_max_length',
    'is_valid_environment',
    'is_valid_layer',
]
