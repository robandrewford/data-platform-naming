#!/usr/bin/env python3
"""
validators.py
Resource name validation rules and constraint enforcement
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .constants import Environment


class ValidationResult(Enum):
    """Validation outcome"""
    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"


@dataclass
class ValidationError:
    """Validation error details"""
    code: str
    message: str
    severity: ValidationResult
    field: Optional[str] = None
    suggestion: Optional[str] = None


class AWSValidator:
    """AWS resource name validation"""

    # S3 constraints
    S3_MIN_LENGTH = 3
    S3_MAX_LENGTH = 63
    S3_PATTERN = r'^[a-z0-9][a-z0-9-]*[a-z0-9]$'
    S3_RESERVED = ['xn--', 'sthree-', 'sthree-configurator']

    # Glue constraints
    GLUE_DB_MAX_LENGTH = 255
    GLUE_DB_PATTERN = r'^[a-z0-9_]+$'
    GLUE_TABLE_MAX_LENGTH = 255
    GLUE_TABLE_PATTERN = r'^[a-z0-9_]+$'

    # Lambda constraints
    LAMBDA_MAX_LENGTH = 64
    LAMBDA_PATTERN = r'^[a-zA-Z0-9-_]+$'

    # IAM constraints
    IAM_ROLE_MAX_LENGTH = 64
    IAM_POLICY_MAX_LENGTH = 128
    IAM_PATTERN = r'^[\w+=,.@-]+$'

    @staticmethod
    def validate_s3_bucket(name: str) -> tuple[bool, list[ValidationError]]:
        """Validate S3 bucket name"""
        errors = []

        # Length
        if len(name) < AWSValidator.S3_MIN_LENGTH:
            errors.append(ValidationError(
                code="S3_LENGTH_MIN",
                message=f"Length {len(name)} < minimum {AWSValidator.S3_MIN_LENGTH}",
                severity=ValidationResult.INVALID,
                field="name"
            ))

        if len(name) > AWSValidator.S3_MAX_LENGTH:
            errors.append(ValidationError(
                code="S3_LENGTH_MAX",
                message=f"Length {len(name)} > maximum {AWSValidator.S3_MAX_LENGTH}",
                severity=ValidationResult.INVALID,
                field="name"
            ))

        # Pattern
        if not re.match(AWSValidator.S3_PATTERN, name):
            errors.append(ValidationError(
                code="S3_PATTERN",
                message="Must be lowercase alphanumeric with hyphens",
                severity=ValidationResult.INVALID,
                field="name",
                suggestion=name.lower().replace('_', '-')
            ))

        # Reserved prefixes
        for reserved in AWSValidator.S3_RESERVED:
            if name.startswith(reserved):
                errors.append(ValidationError(
                    code="S3_RESERVED",
                    message=f"Cannot start with reserved prefix: {reserved}",
                    severity=ValidationResult.INVALID,
                    field="name"
                ))

        # IP address format
        if re.match(r'^\d+\.\d+\.\d+\.\d+$', name):
            errors.append(ValidationError(
                code="S3_IP_FORMAT",
                message="Cannot resemble IP address",
                severity=ValidationResult.INVALID,
                field="name"
            ))

        # Consecutive hyphens
        if '--' in name:
            errors.append(ValidationError(
                code="S3_CONSECUTIVE_HYPHENS",
                message="Cannot contain consecutive hyphens",
                severity=ValidationResult.WARNING,
                field="name"
            ))

        return len(errors) == 0, errors

    @staticmethod
    def validate_glue_database(name: str) -> tuple[bool, list[ValidationError]]:
        """Validate Glue database name"""
        errors = []

        if len(name) > AWSValidator.GLUE_DB_MAX_LENGTH:
            errors.append(ValidationError(
                code="GLUE_DB_LENGTH",
                message=f"Length {len(name)} > maximum {AWSValidator.GLUE_DB_MAX_LENGTH}",
                severity=ValidationResult.INVALID,
                field="name"
            ))

        if not re.match(AWSValidator.GLUE_DB_PATTERN, name):
            errors.append(ValidationError(
                code="GLUE_DB_PATTERN",
                message="Must be lowercase alphanumeric with underscores only",
                severity=ValidationResult.INVALID,
                field="name",
                suggestion=name.lower().replace('-', '_')
            ))

        return len(errors) == 0, errors

    @staticmethod
    def validate_glue_table(name: str) -> tuple[bool, list[ValidationError]]:
        """Validate Glue table name"""
        errors = []

        if len(name) > AWSValidator.GLUE_TABLE_MAX_LENGTH:
            errors.append(ValidationError(
                code="GLUE_TABLE_LENGTH",
                message=f"Length {len(name)} > maximum {AWSValidator.GLUE_TABLE_MAX_LENGTH}",
                severity=ValidationResult.INVALID,
                field="name"
            ))

        if not re.match(AWSValidator.GLUE_TABLE_PATTERN, name):
            errors.append(ValidationError(
                code="GLUE_TABLE_PATTERN",
                message="Must be lowercase alphanumeric with underscores only",
                severity=ValidationResult.INVALID,
                field="name",
                suggestion=name.lower().replace('-', '_')
            ))

        return len(errors) == 0, errors

    @staticmethod
    def validate_lambda_function(name: str) -> tuple[bool, list[ValidationError]]:
        """Validate Lambda function name"""
        errors = []

        if len(name) > AWSValidator.LAMBDA_MAX_LENGTH:
            errors.append(ValidationError(
                code="LAMBDA_LENGTH",
                message=f"Length {len(name)} > maximum {AWSValidator.LAMBDA_MAX_LENGTH}",
                severity=ValidationResult.INVALID,
                field="name"
            ))

        if not re.match(AWSValidator.LAMBDA_PATTERN, name):
            errors.append(ValidationError(
                code="LAMBDA_PATTERN",
                message="Must be alphanumeric with hyphens and underscores",
                severity=ValidationResult.INVALID,
                field="name"
            ))

        return len(errors) == 0, errors

    @staticmethod
    def validate_iam_role(name: str) -> tuple[bool, list[ValidationError]]:
        """Validate IAM role name"""
        errors = []

        if len(name) > AWSValidator.IAM_ROLE_MAX_LENGTH:
            errors.append(ValidationError(
                code="IAM_ROLE_LENGTH",
                message=f"Length {len(name)} > maximum {AWSValidator.IAM_ROLE_MAX_LENGTH}",
                severity=ValidationResult.INVALID,
                field="name"
            ))

        if not re.match(AWSValidator.IAM_PATTERN, name):
            errors.append(ValidationError(
                code="IAM_ROLE_PATTERN",
                message="Must be alphanumeric with +=,.@-_ only",
                severity=ValidationResult.INVALID,
                field="name"
            ))

        return len(errors) == 0, errors


class DatabricksValidator:
    """Databricks resource name validation"""

    # Cluster constraints
    CLUSTER_MAX_LENGTH = 100
    CLUSTER_PATTERN = r'^[a-zA-Z0-9_-]+$'

    # Job constraints
    JOB_MAX_LENGTH = 100
    JOB_PATTERN = r'^[a-zA-Z0-9_-]+$'

    # Unity Catalog constraints
    CATALOG_MAX_LENGTH = 255
    CATALOG_PATTERN = r'^[a-zA-Z0-9_]+$'
    SCHEMA_MAX_LENGTH = 255
    SCHEMA_PATTERN = r'^[a-zA-Z0-9_]+$'
    TABLE_MAX_LENGTH = 255
    TABLE_PATTERN = r'^[a-zA-Z0-9_]+$'

    @staticmethod
    def validate_cluster(name: str) -> tuple[bool, list[ValidationError]]:
        """Validate Databricks cluster name"""
        errors = []

        if len(name) > DatabricksValidator.CLUSTER_MAX_LENGTH:
            errors.append(ValidationError(
                code="DBX_CLUSTER_LENGTH",
                message=f"Length {len(name)} > maximum {DatabricksValidator.CLUSTER_MAX_LENGTH}",
                severity=ValidationResult.INVALID,
                field="name"
            ))

        if not re.match(DatabricksValidator.CLUSTER_PATTERN, name):
            errors.append(ValidationError(
                code="DBX_CLUSTER_PATTERN",
                message="Must be alphanumeric with hyphens and underscores",
                severity=ValidationResult.INVALID,
                field="name"
            ))

        return len(errors) == 0, errors

    @staticmethod
    def validate_job(name: str) -> tuple[bool, list[ValidationError]]:
        """Validate Databricks job name"""
        errors = []

        if len(name) > DatabricksValidator.JOB_MAX_LENGTH:
            errors.append(ValidationError(
                code="DBX_JOB_LENGTH",
                message=f"Length {len(name)} > maximum {DatabricksValidator.JOB_MAX_LENGTH}",
                severity=ValidationResult.INVALID,
                field="name"
            ))

        if not re.match(DatabricksValidator.JOB_PATTERN, name):
            errors.append(ValidationError(
                code="DBX_JOB_PATTERN",
                message="Must be alphanumeric with hyphens and underscores",
                severity=ValidationResult.INVALID,
                field="name"
            ))

        return len(errors) == 0, errors

    @staticmethod
    def validate_catalog(name: str) -> tuple[bool, list[ValidationError]]:
        """Validate Unity Catalog catalog name"""
        errors = []

        if len(name) > DatabricksValidator.CATALOG_MAX_LENGTH:
            errors.append(ValidationError(
                code="UC_CATALOG_LENGTH",
                message=f"Length {len(name)} > maximum {DatabricksValidator.CATALOG_MAX_LENGTH}",
                severity=ValidationResult.INVALID,
                field="name"
            ))

        if not re.match(DatabricksValidator.CATALOG_PATTERN, name):
            errors.append(ValidationError(
                code="UC_CATALOG_PATTERN",
                message="Must be alphanumeric with underscores only",
                severity=ValidationResult.INVALID,
                field="name",
                suggestion=name.replace('-', '_')
            ))

        return len(errors) == 0, errors

    @staticmethod
    def validate_schema(name: str) -> tuple[bool, list[ValidationError]]:
        """Validate Unity Catalog schema name"""
        errors = []

        if len(name) > DatabricksValidator.SCHEMA_MAX_LENGTH:
            errors.append(ValidationError(
                code="UC_SCHEMA_LENGTH",
                message=f"Length {len(name)} > maximum {DatabricksValidator.SCHEMA_MAX_LENGTH}",
                severity=ValidationResult.INVALID,
                field="name"
            ))

        if not re.match(DatabricksValidator.SCHEMA_PATTERN, name):
            errors.append(ValidationError(
                code="UC_SCHEMA_PATTERN",
                message="Must be alphanumeric with underscores only",
                severity=ValidationResult.INVALID,
                field="name",
                suggestion=name.replace('-', '_')
            ))

        return len(errors) == 0, errors

    @staticmethod
    def validate_table(name: str) -> tuple[bool, list[ValidationError]]:
        """Validate Unity Catalog table name"""
        errors = []

        if len(name) > DatabricksValidator.TABLE_MAX_LENGTH:
            errors.append(ValidationError(
                code="UC_TABLE_LENGTH",
                message=f"Length {len(name)} > maximum {DatabricksValidator.TABLE_MAX_LENGTH}",
                severity=ValidationResult.INVALID,
                field="name"
            ))

        if not re.match(DatabricksValidator.TABLE_PATTERN, name):
            errors.append(ValidationError(
                code="UC_TABLE_PATTERN",
                message="Must be alphanumeric with underscores only",
                severity=ValidationResult.INVALID,
                field="name",
                suggestion=name.replace('-', '_')
            ))

        return len(errors) == 0, errors


class ConventionValidator:
    """Naming convention compliance validation"""

    @staticmethod
    def validate_environment(env: str) -> tuple[bool, list[ValidationError]]:
        """Validate environment code"""
        valid_envs = [e.value for e in Environment]

        if env not in valid_envs:
            return False, [ValidationError(
                code="ENV_INVALID",
                message=f"Environment must be one of: {', '.join(valid_envs)}",
                severity=ValidationResult.INVALID,
                field="environment",
                suggestion=Environment.DEV.value
            )]

        return True, []

    @staticmethod
    def validate_project_name(name: str) -> tuple[bool, list[ValidationError]]:
        """Validate project name format"""
        errors = []

        if not re.match(r'^[a-z0-9-]+$', name):
            errors.append(ValidationError(
                code="PROJECT_PATTERN",
                message="Must be lowercase alphanumeric with hyphens",
                severity=ValidationResult.INVALID,
                field="project",
                suggestion=name.lower().replace('_', '-')
            ))

        if len(name) > 32:
            errors.append(ValidationError(
                code="PROJECT_LENGTH",
                message="Should be <= 32 characters for readability",
                severity=ValidationResult.WARNING,
                field="project"
            ))

        return len(errors) == 0, errors

    @staticmethod
    def validate_tag_value(value: str) -> tuple[bool, list[ValidationError]]:
        """Validate AWS tag value"""
        if len(value) > 256:
            return False, [ValidationError(
                code="TAG_LENGTH",
                message="Tag value > 256 characters",
                severity=ValidationResult.INVALID,
                field="tag_value"
            )]

        return True, []


# Example usage
if __name__ == "__main__":
    # AWS S3 validation
    valid, errors = AWSValidator.validate_s3_bucket("dataplatform-raw-sales-prd-use1")
    print(f"S3 Valid: {valid}")
    for error in errors:
        print(f"  {error.code}: {error.message}")

    # Glue database validation
    valid, errors = AWSValidator.validate_glue_database("dataplatform_finance_gold_prd")
    print(f"\nGlue DB Valid: {valid}")

    # Unity Catalog validation
    valid, errors = DatabricksValidator.validate_catalog("dataplatform_main_prd")
    print(f"\nUC Catalog Valid: {valid}")

    # Convention validation
    valid, errors = ConventionValidator.validate_environment("prd")
    print(f"\nEnvironment Valid: {valid}")
