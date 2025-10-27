#!/usr/bin/env python3
"""
validators.py
Resource name validation rules and constraint enforcement
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from .constants import AWSResourceType, DatabricksResourceType, Environment


class ValidationResult(Enum):
    """Validation outcome"""
    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"


@dataclass
class ValidationIssue:
    """Validation issue details"""
    code: str
    message: str
    severity: ValidationResult
    field: str | None = None
    suggestion: str | None = None
    resource_type: str | None = None
    resource_name: str | None = None
    context: dict[str, Any] | None = None

    def __str__(self) -> str:
        """String representation of validation issue"""
        parts = [f"[{self.severity.value.upper()}] {self.code}"]
        if self.resource_type and self.resource_name:
            parts.append(f"{self.resource_type}:{self.resource_name}")
        parts.append(self.message)
        if self.suggestion:
            parts.append(f"(Suggestion: {self.suggestion})")
        return " - ".join(parts)


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
    def validate_s3_bucket(name: str) -> tuple[bool, list[ValidationIssue]]:
        """Validate S3 bucket name"""
        errors = []

        # Length
        if len(name) < AWSValidator.S3_MIN_LENGTH:
            errors.append(ValidationIssue(
                code="S3_LENGTH_MIN",
                message=f"Length {len(name)} < minimum {AWSValidator.S3_MIN_LENGTH}",
                severity=ValidationResult.INVALID,
                field="name"
            ))

        if len(name) > AWSValidator.S3_MAX_LENGTH:
            errors.append(ValidationIssue(
                code="S3_LENGTH_MAX",
                message=f"Length {len(name)} > maximum {AWSValidator.S3_MAX_LENGTH}",
                severity=ValidationResult.INVALID,
                field="name"
            ))

        # Pattern
        if not re.match(AWSValidator.S3_PATTERN, name):
            errors.append(ValidationIssue(
                code="S3_PATTERN",
                message="Must be lowercase alphanumeric with hyphens",
                severity=ValidationResult.INVALID,
                field="name",
                suggestion=name.lower().replace('_', '-')
            ))

        # Reserved prefixes
        for reserved in AWSValidator.S3_RESERVED:
            if name.startswith(reserved):
                errors.append(ValidationIssue(
                    code="S3_RESERVED",
                    message=f"Cannot start with reserved prefix: {reserved}",
                    severity=ValidationResult.INVALID,
                    field="name"
                ))

        # IP address format
        if re.match(r'^\d+\.\d+\.\d+\.\d+$', name):
            errors.append(ValidationIssue(
                code="S3_IP_FORMAT",
                message="Cannot resemble IP address",
                severity=ValidationResult.INVALID,
                field="name"
            ))

        # Consecutive hyphens
        if '--' in name:
            errors.append(ValidationIssue(
                code="S3_CONSECUTIVE_HYPHENS",
                message="Cannot contain consecutive hyphens",
                severity=ValidationResult.WARNING,
                field="name"
            ))

        return len(errors) == 0, errors

    @staticmethod
    def validate_glue_database(name: str) -> tuple[bool, list[ValidationIssue]]:
        """Validate Glue database name"""
        errors = []

        if len(name) > AWSValidator.GLUE_DB_MAX_LENGTH:
            errors.append(ValidationIssue(
                code="GLUE_DB_LENGTH",
                message=f"Length {len(name)} > maximum {AWSValidator.GLUE_DB_MAX_LENGTH}",
                severity=ValidationResult.INVALID,
                field="name"
            ))

        if not re.match(AWSValidator.GLUE_DB_PATTERN, name):
            errors.append(ValidationIssue(
                code="GLUE_DB_PATTERN",
                message="Must be lowercase alphanumeric with underscores only",
                severity=ValidationResult.INVALID,
                field="name",
                suggestion=name.lower().replace('-', '_')
            ))

        return len(errors) == 0, errors

    @staticmethod
    def validate_glue_table(name: str) -> tuple[bool, list[ValidationIssue]]:
        """Validate Glue table name"""
        errors = []

        if len(name) > AWSValidator.GLUE_TABLE_MAX_LENGTH:
            errors.append(ValidationIssue(
                code="GLUE_TABLE_LENGTH",
                message=f"Length {len(name)} > maximum {AWSValidator.GLUE_TABLE_MAX_LENGTH}",
                severity=ValidationResult.INVALID,
                field="name"
            ))

        if not re.match(AWSValidator.GLUE_TABLE_PATTERN, name):
            errors.append(ValidationIssue(
                code="GLUE_TABLE_PATTERN",
                message="Must be lowercase alphanumeric with underscores only",
                severity=ValidationResult.INVALID,
                field="name",
                suggestion=name.lower().replace('-', '_')
            ))

        return len(errors) == 0, errors

    @staticmethod
    def validate_lambda_function(name: str) -> tuple[bool, list[ValidationIssue]]:
        """Validate Lambda function name"""
        errors = []

        if len(name) > AWSValidator.LAMBDA_MAX_LENGTH:
            errors.append(ValidationIssue(
                code="LAMBDA_LENGTH",
                message=f"Length {len(name)} > maximum {AWSValidator.LAMBDA_MAX_LENGTH}",
                severity=ValidationResult.INVALID,
                field="name"
            ))

        if not re.match(AWSValidator.LAMBDA_PATTERN, name):
            errors.append(ValidationIssue(
                code="LAMBDA_PATTERN",
                message="Must be alphanumeric with hyphens and underscores",
                severity=ValidationResult.INVALID,
                field="name"
            ))

        return len(errors) == 0, errors

    @staticmethod
    def validate_iam_role(name: str) -> tuple[bool, list[ValidationIssue]]:
        """Validate IAM role name"""
        errors = []

        if len(name) > AWSValidator.IAM_ROLE_MAX_LENGTH:
            errors.append(ValidationIssue(
                code="IAM_ROLE_LENGTH",
                message=f"Length {len(name)} > maximum {AWSValidator.IAM_ROLE_MAX_LENGTH}",
                severity=ValidationResult.INVALID,
                field="name"
            ))

        if not re.match(AWSValidator.IAM_PATTERN, name):
            errors.append(ValidationIssue(
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
    def validate_cluster(name: str) -> tuple[bool, list[ValidationIssue]]:
        """Validate Databricks cluster name"""
        errors = []

        if len(name) > DatabricksValidator.CLUSTER_MAX_LENGTH:
            errors.append(ValidationIssue(
                code="DBX_CLUSTER_LENGTH",
                message=f"Length {len(name)} > maximum {DatabricksValidator.CLUSTER_MAX_LENGTH}",
                severity=ValidationResult.INVALID,
                field="name"
            ))

        if not re.match(DatabricksValidator.CLUSTER_PATTERN, name):
            errors.append(ValidationIssue(
                code="DBX_CLUSTER_PATTERN",
                message="Must be alphanumeric with hyphens and underscores",
                severity=ValidationResult.INVALID,
                field="name"
            ))

        return len(errors) == 0, errors

    @staticmethod
    def validate_job(name: str) -> tuple[bool, list[ValidationIssue]]:
        """Validate Databricks job name"""
        errors = []

        if len(name) > DatabricksValidator.JOB_MAX_LENGTH:
            errors.append(ValidationIssue(
                code="DBX_JOB_LENGTH",
                message=f"Length {len(name)} > maximum {DatabricksValidator.JOB_MAX_LENGTH}",
                severity=ValidationResult.INVALID,
                field="name"
            ))

        if not re.match(DatabricksValidator.JOB_PATTERN, name):
            errors.append(ValidationIssue(
                code="DBX_JOB_PATTERN",
                message="Must be alphanumeric with hyphens and underscores",
                severity=ValidationResult.INVALID,
                field="name"
            ))

        return len(errors) == 0, errors

    @staticmethod
    def validate_catalog(name: str) -> tuple[bool, list[ValidationIssue]]:
        """Validate Unity Catalog catalog name"""
        errors = []

        if len(name) > DatabricksValidator.CATALOG_MAX_LENGTH:
            errors.append(ValidationIssue(
                code="UC_CATALOG_LENGTH",
                message=f"Length {len(name)} > maximum {DatabricksValidator.CATALOG_MAX_LENGTH}",
                severity=ValidationResult.INVALID,
                field="name"
            ))

        if not re.match(DatabricksValidator.CATALOG_PATTERN, name):
            errors.append(ValidationIssue(
                code="UC_CATALOG_PATTERN",
                message="Must be alphanumeric with underscores only",
                severity=ValidationResult.INVALID,
                field="name",
                suggestion=name.replace('-', '_')
            ))

        return len(errors) == 0, errors

    @staticmethod
    def validate_schema(name: str) -> tuple[bool, list[ValidationIssue]]:
        """Validate Unity Catalog schema name"""
        errors = []

        if len(name) > DatabricksValidator.SCHEMA_MAX_LENGTH:
            errors.append(ValidationIssue(
                code="UC_SCHEMA_LENGTH",
                message=f"Length {len(name)} > maximum {DatabricksValidator.SCHEMA_MAX_LENGTH}",
                severity=ValidationResult.INVALID,
                field="name"
            ))

        if not re.match(DatabricksValidator.SCHEMA_PATTERN, name):
            errors.append(ValidationIssue(
                code="UC_SCHEMA_PATTERN",
                message="Must be alphanumeric with underscores only",
                severity=ValidationResult.INVALID,
                field="name",
                suggestion=name.replace('-', '_')
            ))

        return len(errors) == 0, errors

    @staticmethod
    def validate_table(name: str) -> tuple[bool, list[ValidationIssue]]:
        """Validate Unity Catalog table name"""
        errors = []

        if len(name) > DatabricksValidator.TABLE_MAX_LENGTH:
            errors.append(ValidationIssue(
                code="UC_TABLE_LENGTH",
                message=f"Length {len(name)} > maximum {DatabricksValidator.TABLE_MAX_LENGTH}",
                severity=ValidationResult.INVALID,
                field="name"
            ))

        if not re.match(DatabricksValidator.TABLE_PATTERN, name):
            errors.append(ValidationIssue(
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
    def validate_environment(env: str) -> tuple[bool, list[ValidationIssue]]:
        """Validate environment code"""
        valid_envs = [e.value for e in Environment]

        if env not in valid_envs:
            return False, [ValidationIssue(
                code="ENV_INVALID",
                message=f"Environment must be one of: {', '.join(valid_envs)}",
                severity=ValidationResult.INVALID,
                field="environment",
                suggestion=Environment.DEV.value
            )]

        return True, []

    @staticmethod
    def validate_project_name(name: str) -> tuple[bool, list[ValidationIssue]]:
        """Validate project name format"""
        errors = []

        if not re.match(r'^[a-z0-9-]+$', name):
            errors.append(ValidationIssue(
                code="PROJECT_PATTERN",
                message="Must be lowercase alphanumeric with hyphens",
                severity=ValidationResult.INVALID,
                field="project",
                suggestion=name.lower().replace('_', '-')
            ))

        if len(name) > 32:
            errors.append(ValidationIssue(
                code="PROJECT_LENGTH",
                message="Should be <= 32 characters for readability",
                severity=ValidationResult.WARNING,
                field="project"
            ))

        return len(errors) == 0, errors

    @staticmethod
    def validate_tag_value(value: str) -> tuple[bool, list[ValidationIssue]]:
        """Validate AWS tag value"""
        if len(value) > 256:
            return False, [ValidationIssue(
                code="TAG_LENGTH",
                message="Tag value > 256 characters",
                severity=ValidationResult.INVALID,
                field="tag_value"
            )]

        return True, []


@dataclass
class ValidationReport:
    """Comprehensive validation report"""
    is_valid: bool
    issues: list[ValidationIssue]
    resource_type: str | None = None
    resource_name: str | None = None
    context: dict[str, Any] | None = None

    @property
    def errors(self) -> list[ValidationIssue]:
        """Get only error-level issues"""
        return [issue for issue in self.issues if issue.severity == ValidationResult.INVALID]

    @property
    def warnings(self) -> list[ValidationIssue]:
        """Get only warning-level issues"""
        return [issue for issue in self.issues if issue.severity == ValidationResult.WARNING]

    @property
    def has_errors(self) -> bool:
        """Check if report has any errors"""
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        """Check if report has any warnings"""
        return len(self.warnings) > 0

    def __str__(self) -> str:
        """String representation of validation report"""
        status = "VALID" if self.is_valid else "INVALID"
        parts = [f"Validation Report: {status}"]

        if self.resource_type and self.resource_name:
            parts.append(f"Resource: {self.resource_type}:{self.resource_name}")

        if self.issues:
            parts.append(f"Issues: {len(self.issues)} total")
            if self.errors:
                parts.append(f"Errors: {len(self.errors)}")
            if self.warnings:
                parts.append(f"Warnings: {len(self.warnings)}")

        return " | ".join(parts)


class ValidationContext:
    """Unified validation context and orchestrator"""

    def __init__(self, strict: bool = True):
        """
        Initialize validation context.

        Args:
            strict: If True, warnings are treated as failures (default: True)
        """
        self.strict = strict
        self._validators: dict[str, Any] = {}

    def register_validator(self, resource_type: str, validator_func: Any) -> None:
        """Register a validator function for a resource type"""
        self._validators[resource_type] = validator_func

    def validate_name(
        self,
        resource_type: str,
        name: str,
        context: dict[str, Any] | None = None
    ) -> ValidationReport:
        """
        Validate a resource name.

        Args:
            resource_type: Type of resource (e.g., 'dbx_cluster', 'aws_s3_bucket')
            name: Name to validate
            context: Additional context for validation

        Returns:
            ValidationReport with results
        """
        issues: list[ValidationIssue] = []

        # Add context to all issues
        issue_context = context or {}

        # Get validator function
        validator_func = self._validators.get(resource_type)
        if validator_func is None:
            issues.append(ValidationIssue(
                code="VALIDATOR_NOT_FOUND",
                message=f"No validator registered for resource type: {resource_type}",
                severity=ValidationResult.INVALID,
                resource_type=resource_type,
                resource_name=name,
                context=issue_context
            ))
        else:
            # Run validation
            try:
                is_valid, validation_issues = validator_func(name)

                # Enhance issues with context
                for issue in validation_issues:
                    issue.resource_type = resource_type
                    issue.resource_name = name
                    issue.context = issue_context
                    issues.append(issue)

                # If not valid, add a summary issue
                if not is_valid:
                    issues.append(ValidationIssue(
                        code="VALIDATION_FAILED",
                        message=f"Resource name '{name}' failed validation",
                        severity=ValidationResult.INVALID,
                        resource_type=resource_type,
                        resource_name=name,
                        context=issue_context
                    ))

            except Exception as e:
                issues.append(ValidationIssue(
                    code="VALIDATION_ERROR",
                    message=f"Validation failed with error: {str(e)}",
                    severity=ValidationResult.INVALID,
                    resource_type=resource_type,
                    resource_name=name,
                    context=issue_context
                ))

        # Determine if valid based on strict mode
        is_valid = len(issues) == 0
        if self.strict and issues:
            # In strict mode, any issue (including warnings) makes it invalid
            is_valid = False

        return ValidationReport(
            is_valid=is_valid,
            issues=issues,
            resource_type=resource_type,
            resource_name=name,
            context=context
        )

    def validate_multiple(
        self,
        validations: list[tuple[str, str]],
        context: dict[str, Any] | None = None
    ) -> dict[str, ValidationReport]:
        """
        Validate multiple resource names.

        Args:
            validations: List of (resource_type, name) tuples
            context: Additional context for validation

        Returns:
            Dictionary mapping resource identifiers to ValidationReports
        """
        results: dict[str, ValidationReport] = {}

        for i, (resource_type, name) in enumerate(validations):
            # Use index as identifier if no name provided
            identifier = name or f"{resource_type}_{i}"
            results[identifier] = self.validate_name(resource_type, name, context)

        return results

    def get_summary(self, reports: dict[str, ValidationReport]) -> dict[str, int]:
        """Get validation summary statistics"""
        total = len(reports)
        valid = sum(1 for r in reports.values() if r.is_valid)
        invalid = total - valid

        return {
            'total': total,
            'valid': valid,
            'invalid': invalid,
            'error_count': sum(len(r.errors) for r in reports.values()),
            'warning_count': sum(len(r.warnings) for r in reports.values())
        }


class ValidationPipeline:
    """Pipeline for chaining multiple validators"""

    def __init__(self, context: ValidationContext):
        self.context = context

    def validate_databricks_resource(
        self,
        resource_type: DatabricksResourceType,
        name: str,
        context: dict[str, Any] | None = None
    ) -> ValidationReport:
        """Validate a Databricks resource name"""
        # Map DatabricksResourceType to validator key
        validator_map = {
            DatabricksResourceType.CLUSTER: 'dbx_cluster',
            DatabricksResourceType.JOB: 'dbx_job',
            DatabricksResourceType.CATALOG: 'dbx_catalog',
            DatabricksResourceType.SCHEMA: 'dbx_schema',
            DatabricksResourceType.TABLE: 'dbx_table',
        }

        validator_key = validator_map.get(resource_type)
        if validator_key is None:
            return ValidationReport(
                is_valid=False,
                issues=[ValidationIssue(
                    code="UNSUPPORTED_RESOURCE_TYPE",
                    message=f"Unsupported Databricks resource type: {resource_type}",
                    severity=ValidationResult.INVALID,
                    resource_type=resource_type.value,
                    resource_name=name,
                    context=context
                )],
                resource_type=resource_type.value,
                resource_name=name,
                context=context
            )

        return self.context.validate_name(validator_key, name, context)

    def validate_aws_resource(
        self,
        resource_type: AWSResourceType,
        name: str,
        context: dict[str, Any] | None = None
    ) -> ValidationReport:
        """Validate an AWS resource name"""
        # Map AWSResourceType to validator key
        validator_map = {
            AWSResourceType.S3_BUCKET: 'aws_s3_bucket',
            AWSResourceType.GLUE_DATABASE: 'aws_glue_database',
            AWSResourceType.GLUE_TABLE: 'aws_glue_table',
            AWSResourceType.LAMBDA_FUNCTION: 'aws_lambda_function',
            AWSResourceType.IAM_ROLE: 'aws_iam_role',
        }

        validator_key = validator_map.get(resource_type)
        if validator_key is None:
            return ValidationReport(
                is_valid=False,
                issues=[ValidationIssue(
                    code="UNSUPPORTED_RESOURCE_TYPE",
                    message=f"Unsupported AWS resource type: {resource_type}",
                    severity=ValidationResult.INVALID,
                    resource_type=resource_type.value,
                    resource_name=name,
                    context=context
                )],
                resource_type=resource_type.value,
                resource_name=name,
                context=context
            )

        return self.context.validate_name(validator_key, name, context)


# Global validation context instance
validation_context = ValidationContext(strict=True)

# Register all validators
validation_context.register_validator('aws_s3_bucket', AWSValidator.validate_s3_bucket)
validation_context.register_validator('aws_glue_database', AWSValidator.validate_glue_database)
validation_context.register_validator('aws_glue_table', AWSValidator.validate_glue_table)
validation_context.register_validator('aws_lambda_function', AWSValidator.validate_lambda_function)
validation_context.register_validator('aws_iam_role', AWSValidator.validate_iam_role)

validation_context.register_validator('dbx_cluster', DatabricksValidator.validate_cluster)
validation_context.register_validator('dbx_job', DatabricksValidator.validate_job)
validation_context.register_validator('dbx_catalog', DatabricksValidator.validate_catalog)
validation_context.register_validator('dbx_schema', DatabricksValidator.validate_schema)
validation_context.register_validator('dbx_table', DatabricksValidator.validate_table)

# Create pipeline instance
validation_pipeline = ValidationPipeline(validation_context)


def validate_resource_name(
    resource_type: str,
    name: str,
    context: dict[str, Any] | None = None
) -> ValidationReport:
    """
    Convenience function to validate a resource name.

    Args:
        resource_type: Type of resource (e.g., 'dbx_cluster', 'aws_s3_bucket')
        name: Name to validate
        context: Additional context for validation

    Returns:
        ValidationReport with results
    """
    return validation_context.validate_name(resource_type, name, context)


def validate_databricks_name(
    resource_type: DatabricksResourceType,
    name: str,
    context: dict[str, Any] | None = None
) -> ValidationReport:
    """
    Convenience function to validate a Databricks resource name.

    Args:
        resource_type: Databricks resource type
        name: Name to validate
        context: Additional context for validation

    Returns:
        ValidationReport with results
    """
    return validation_pipeline.validate_databricks_resource(resource_type, name, context)


def validate_aws_name(
    resource_type: AWSResourceType,
    name: str,
    context: dict[str, Any] | None = None
) -> ValidationReport:
    """
    Convenience function to validate an AWS resource name.

    Args:
        resource_type: AWS resource type
        name: Name to validate
        context: Additional context for validation

    Returns:
        ValidationReport with results
    """
    return validation_pipeline.validate_aws_resource(resource_type, name, context)


# Example usage
if __name__ == "__main__":
    # Test unified validation system
    print("=== Unified Validation System Demo ===\n")

    # Test Databricks cluster validation
    report = validate_databricks_name(
        DatabricksResourceType.CLUSTER,
        "dataplatform-etl-shared-prd"
    )
    print(f"Databricks Cluster: {report}")
    if not report.is_valid:
        for issue in report.issues:
            print(f"  {issue}")

    # Test Unity Catalog table validation
    report = validate_databricks_name(
        DatabricksResourceType.TABLE,
        "dim_customers"
    )
    print(f"\nUnity Catalog Table: {report}")
    if not report.is_valid:
        for issue in report.issues:
            print(f"  {issue}")

    # Test AWS S3 bucket validation
    report = validate_aws_name(
        AWSResourceType.S3_BUCKET,
        "dataplatform-raw-prd-use1"
    )
    print(f"\nAWS S3 Bucket: {report}")
    if not report.is_valid:
        for issue in report.issues:
            print(f"  {issue}")

    # Test validation with context
    context = {"environment": "prd", "project": "dataplatform"}
    report = validate_databricks_name(
        DatabricksResourceType.CATALOG,
        "dataplatform_main_prd",
        context
    )
    print(f"\nDatabricks Catalog with context: {report}")
    if not report.is_valid:
        for issue in report.issues:
            print(f"  {issue}")

    # Test multiple validations
    validations = [
        ('dbx_cluster', 'dataplatform-etl-shared-prd'),
        ('dbx_catalog', 'dataplatform_main_prd'),
        ('aws_s3_bucket', 'dataplatform-raw-prd-use1'),
    ]

    results = validation_context.validate_multiple(validations, context)
    print("\n=== Multiple Validation Summary ===")
    summary = validation_context.get_summary(results)
    print(f"Total: {summary['total']}, Valid: {summary['valid']}, Invalid: {summary['invalid']}")
    print(f"Errors: {summary['error_count']}, Warnings: {summary['warning_count']}")

    for name, report in results.items():
        print(f"\n{name}: {report}")
        if not report.is_valid:
            for issue in report.issues:
                print(f"  {issue}")
