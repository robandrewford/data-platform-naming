#!/usr/bin/env python3
"""
Custom exception hierarchy for data platform naming.

Provides specific exception types for different error categories
with enhanced context and debugging information.
"""

from __future__ import annotations


class DataPlatformNamingError(Exception):
    """Base exception for all naming errors."""

    def __init__(
        self,
        message: str,
        resource_type: str | None = None,
        operation: str | None = None,
        context: dict[str, str] | None = None
    ):
        super().__init__(message)
        self.message = message
        self.resource_type = resource_type
        self.operation = operation
        self.context = context or {}

    def __str__(self) -> str:
        """Enhanced error message with context."""
        parts = [self.message]

        if self.resource_type:
            parts.append(f"Resource Type: {self.resource_type}")

        if self.operation:
            parts.append(f"Operation: {self.operation}")

        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            parts.append(f"Context: {context_str}")

        return " | ".join(parts)


class ValidationError(DataPlatformNamingError):
    """Raised when validation fails."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        value: str | None = None,
        suggestion: str | None = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.field = field
        self.value = value
        self.suggestion = suggestion

    def __str__(self) -> str:
        """Enhanced validation error with field and suggestion info."""
        parts = [self.message]

        if self.field:
            parts.append(f"Field: {self.field}")

        if self.value:
            parts.append(f"Value: {self.value}")

        if self.suggestion:
            parts.append(f"Suggestion: {self.suggestion}")

        return " | ".join(parts)


class ConfigurationError(DataPlatformNamingError):
    """Raised when configuration is invalid."""

    def __init__(
        self,
        message: str,
        config_file: str | None = None,
        config_key: str | None = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.config_file = config_file
        self.config_key = config_key

    def __str__(self) -> str:
        """Enhanced config error with file and key info."""
        parts = [self.message]

        if self.config_file:
            parts.append(f"File: {self.config_file}")

        if self.config_key:
            parts.append(f"Key: {self.config_key}")

        return " | ".join(parts)


class PatternError(DataPlatformNamingError):
    """Raised when pattern processing fails."""

    def __init__(
        self,
        message: str,
        pattern: str | None = None,
        missing_variables: list[str] | None = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.pattern = pattern
        self.missing_variables = missing_variables or []

    def __str__(self) -> str:
        """Enhanced pattern error with pattern and missing variables."""
        parts = [self.message]

        if self.pattern:
            parts.append(f"Pattern: {self.pattern}")

        if self.missing_variables:
            missing_str = ", ".join(self.missing_variables)
            parts.append(f"Missing Variables: {missing_str}")

        return " | ".join(parts)


class TransactionError(DataPlatformNamingError):
    """Raised when transaction fails."""

    def __init__(
        self,
        message: str,
        transaction_id: str | None = None,
        failed_operation: str | None = None,
        completed_operations: list[str] | None = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.transaction_id = transaction_id
        self.failed_operation = failed_operation
        self.completed_operations = completed_operations or []

    def __str__(self) -> str:
        """Enhanced transaction error with operation details."""
        parts = [self.message]

        if self.transaction_id:
            parts.append(f"Transaction ID: {self.transaction_id}")

        if self.failed_operation:
            parts.append(f"Failed Operation: {self.failed_operation}")

        if self.completed_operations:
            completed_str = ", ".join(self.completed_operations)
            parts.append(f"Completed Operations: {completed_str}")

        return " | ".join(parts)


class AWSOperationError(DataPlatformNamingError):
    """Raised when AWS operation fails."""

    def __init__(
        self,
        message: str,
        aws_service: str | None = None,
        aws_error_code: str | None = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.aws_service = aws_service
        self.aws_error_code = aws_error_code

    def __str__(self) -> str:
        """Enhanced AWS error with service and error code."""
        parts = [self.message]

        if self.aws_service:
            parts.append(f"AWS Service: {self.aws_service}")

        if self.aws_error_code:
            parts.append(f"Error Code: {self.aws_error_code}")

        return " | ".join(parts)


class DatabricksOperationError(DataPlatformNamingError):
    """Raised when Databricks operation fails."""

    def __init__(
        self,
        message: str,
        dbx_api_endpoint: str | None = None,
        http_status_code: int | None = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.dbx_api_endpoint = dbx_api_endpoint
        self.http_status_code = http_status_code

    def __str__(self) -> str:
        """Enhanced Databricks error with API details."""
        parts = [self.message]

        if self.dbx_api_endpoint:
            parts.append(f"API Endpoint: {self.dbx_api_endpoint}")

        if self.http_status_code:
            parts.append(f"HTTP Status: {self.http_status_code}")

        return " | ".join(parts)


class ConsistencyError(DataPlatformNamingError):
    """Raised when consistency validation fails."""

    def __init__(
        self,
        message: str,
        expected_state: str | None = None,
        actual_state: str | None = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.expected_state = expected_state
        self.actual_state = actual_state

    def __str__(self) -> str:
        """Enhanced consistency error with state information."""
        parts = [self.message]

        if self.expected_state:
            parts.append(f"Expected State: {self.expected_state}")

        if self.actual_state:
            parts.append(f"Actual State: {self.actual_state}")

        return " | ".join(parts)


# Convenience functions for creating common errors
def validation_error(
    message: str,
    field: str | None = None,
    value: str | None = None,
    suggestion: str | None = None,
    **context
) -> ValidationError:
    """Create a validation error with context."""
    return ValidationError(
        message=message,
        field=field,
        value=value,
        suggestion=suggestion,
        **context
    )


def configuration_error(
    message: str,
    config_file: str | None = None,
    config_key: str | None = None,
    **context
) -> ConfigurationError:
    """Create a configuration error with context."""
    return ConfigurationError(
        message=message,
        config_file=config_file,
        config_key=config_key,
        **context
    )


def pattern_error(
    message: str,
    pattern: str | None = None,
    missing_variables: list[str] | None = None,
    **context
) -> PatternError:
    """Create a pattern error with context."""
    return PatternError(
        message=message,
        pattern=pattern,
        missing_variables=missing_variables,
        **context
    )


def transaction_error(
    message: str,
    transaction_id: str | None = None,
    failed_operation: str | None = None,
    completed_operations: list[str] | None = None,
    **context
) -> TransactionError:
    """Create a transaction error with context."""
    return TransactionError(
        message=message,
        transaction_id=transaction_id,
        failed_operation=failed_operation,
        completed_operations=completed_operations,
        **context
    )


def aws_operation_error(
    message: str,
    aws_service: str | None = None,
    aws_error_code: str | None = None,
    **context
) -> AWSOperationError:
    """Create an AWS operation error with context."""
    return AWSOperationError(
        message=message,
        aws_service=aws_service,
        aws_error_code=aws_error_code,
        **context
    )


def databricks_operation_error(
    message: str,
    dbx_api_endpoint: str | None = None,
    http_status_code: int | None = None,
    **context
) -> DatabricksOperationError:
    """Create a Databricks operation error with context."""
    return DatabricksOperationError(
        message=message,
        dbx_api_endpoint=dbx_api_endpoint,
        http_status_code=http_status_code,
        **context
    )


def consistency_error(
    message: str,
    expected_state: str | None = None,
    actual_state: str | None = None,
    **context
) -> ConsistencyError:
    """Create a consistency error with context."""
    return ConsistencyError(
        message=message,
        expected_state=expected_state,
        actual_state=actual_state,
        **context
    )
