#!/usr/bin/env python3
"""
ScopeFilter - Filter resources by type with wildcard support.

This module provides functionality to filter resources based on type patterns,
supporting include/exclude modes with wildcard matching (e.g., 'aws_*', 'dbx_*').
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from ..exceptions import ValidationError


class FilterMode(Enum):
    """Filter mode: include or exclude"""
    INCLUDE = "include"
    EXCLUDE = "exclude"


@dataclass
class ScopeConfig:
    """Configuration for scope filtering"""
    mode: FilterMode
    patterns: list[str]

    def __post_init__(self):
        """Validate patterns"""
        if not self.patterns:
            raise ValidationError(
                message="At least one pattern must be provided",
                field="patterns",
                suggestion="Provide at least one pattern (e.g., ['aws_*', 'dbx_*'])"
            )

        # Validate each pattern
        for pattern in self.patterns:
            if not isinstance(pattern, str) or not pattern.strip():
                raise ValidationError(
                    message=f"Invalid pattern: {pattern}",
                    field="pattern",
                    value=str(pattern),
                    suggestion="Pattern must be a non-empty string"
                )


class ScopeFilter:
    """
    Filter resources by type using wildcard patterns.
    
    Supports two modes:
    - INCLUDE: Only process resources matching the patterns
    - EXCLUDE: Process all resources except those matching the patterns
    
    Wildcard patterns:
    - `*` matches any characters
    - `?` matches any single character
    - Exact matches: `aws_s3_bucket`
    - Prefix matches: `aws_*`
    - Suffix matches: `*_bucket`
    - Contains: `*s3*`
    
    Example:
        >>> # Include only AWS resources
        >>> filter = ScopeFilter(mode=FilterMode.INCLUDE, patterns=["aws_*"])
        >>> filter.should_process("aws_s3_bucket")  # True
        >>> filter.should_process("dbx_cluster")    # False
        
        >>> # Exclude Databricks resources
        >>> filter = ScopeFilter(mode=FilterMode.EXCLUDE, patterns=["dbx_*"])
        >>> filter.should_process("aws_s3_bucket")  # True
        >>> filter.should_process("dbx_cluster")    # False
    """

    def __init__(
        self,
        mode: FilterMode = FilterMode.INCLUDE,
        patterns: list[str] | None = None
    ):
        """
        Initialize ScopeFilter.

        Args:
            mode: Filter mode (INCLUDE or EXCLUDE)
            patterns: List of wildcard patterns
        """
        self.mode = mode
        self.patterns = patterns or ["*"]  # Default: match all

        # Compile patterns to regex for efficient matching
        self._compiled_patterns = [
            self._wildcard_to_regex(pattern)
            for pattern in self.patterns
        ]

    @staticmethod
    def _wildcard_to_regex(pattern: str) -> re.Pattern:
        """
        Convert wildcard pattern to compiled regex.
        
        Wildcards:
        - `*` matches zero or more characters
        - `?` matches exactly one character
        
        Args:
            pattern: Wildcard pattern string
            
        Returns:
            Compiled regex pattern
        """
        # Escape special regex characters except * and ?
        escaped = re.escape(pattern)

        # Replace escaped wildcards with regex equivalents
        # \* becomes .* (zero or more of any character)
        # \? becomes . (exactly one of any character)
        regex_pattern = (
            escaped
            .replace(r'\*', '.*')
            .replace(r'\?', '.')
        )

        # Anchor to match full string
        regex_pattern = f'^{regex_pattern}$'

        return re.compile(regex_pattern)

    def matches_any_pattern(self, resource_type: str) -> bool:
        """
        Check if resource type matches any of the patterns.
        
        Args:
            resource_type: Resource type to check
            
        Returns:
            True if matches any pattern, False otherwise
        """
        return any(
            pattern.match(resource_type)
            for pattern in self._compiled_patterns
        )

    def should_process(self, resource_type: str) -> bool:
        """
        Determine if resource should be processed based on filter.
        
        Args:
            resource_type: Resource type to check
            
        Returns:
            True if resource should be processed, False otherwise
        """
        matches = self.matches_any_pattern(resource_type)

        if self.mode == FilterMode.INCLUDE:
            # In INCLUDE mode, process only if it matches
            return matches
        else:
            # In EXCLUDE mode, process only if it doesn't match
            return not matches

    def filter_resources(
        self,
        resources: list[dict]
    ) -> list[dict]:
        """
        Filter a list of resources based on their types.

        Args:
            resources: List of resource dictionaries with 'type' field

        Returns:
            Filtered list of resources that should be processed
        """
        return [
            resource
            for resource in resources
            if self.should_process(resource.get("type", ""))
        ]

    def get_matching_types(
        self,
        resource_types: list[str]
    ) -> list[str]:
        """
        Get list of resource types that match the filter.

        Args:
            resource_types: List of resource type strings

        Returns:
            List of matching resource types
        """
        return [
            resource_type
            for resource_type in resource_types
            if self.should_process(resource_type)
        ]

    @classmethod
    def from_config(cls, config: ScopeConfig) -> "ScopeFilter":
        """
        Create ScopeFilter from ScopeConfig.
        
        Args:
            config: Scope configuration
            
        Returns:
            ScopeFilter instance
        """
        return cls(mode=config.mode, patterns=config.patterns)

    @classmethod
    def include(cls, patterns: list[str]) -> "ScopeFilter":
        """
        Create an INCLUDE mode filter.

        Args:
            patterns: List of wildcard patterns to include

        Returns:
            ScopeFilter in INCLUDE mode
        """
        return cls(mode=FilterMode.INCLUDE, patterns=patterns)

    @classmethod
    def exclude(cls, patterns: list[str]) -> "ScopeFilter":
        """
        Create an EXCLUDE mode filter.

        Args:
            patterns: List of wildcard patterns to exclude

        Returns:
            ScopeFilter in EXCLUDE mode
        """
        return cls(mode=FilterMode.EXCLUDE, patterns=patterns)

    @classmethod
    def allow_all(cls) -> "ScopeFilter":
        """
        Create a filter that allows all resources.
        
        Returns:
            ScopeFilter that matches everything
        """
        return cls(mode=FilterMode.INCLUDE, patterns=["*"])

    @classmethod
    def deny_all(cls) -> "ScopeFilter":
        """
        Create a filter that denies all resources.
        
        Returns:
            ScopeFilter that matches nothing
        """
        return cls(mode=FilterMode.EXCLUDE, patterns=["*"])

    def __repr__(self) -> str:
        """String representation of filter"""
        patterns_str = ", ".join(f"'{p}'" for p in self.patterns)
        return f"ScopeFilter(mode={self.mode.value}, patterns=[{patterns_str}])"


# Example usage
if __name__ == "__main__":
    # Example 1: Include only AWS resources
    print("Example 1: Include only AWS resources")
    aws_filter = ScopeFilter.include(["aws_*"])
    print(f"Filter: {aws_filter}")
    print(f"aws_s3_bucket: {aws_filter.should_process('aws_s3_bucket')}")
    print(f"aws_glue_database: {aws_filter.should_process('aws_glue_database')}")
    print(f"dbx_cluster: {aws_filter.should_process('dbx_cluster')}")
    print()

    # Example 2: Exclude Databricks resources
    print("Example 2: Exclude Databricks resources")
    no_dbx_filter = ScopeFilter.exclude(["dbx_*"])
    print(f"Filter: {no_dbx_filter}")
    print(f"aws_s3_bucket: {no_dbx_filter.should_process('aws_s3_bucket')}")
    print(f"dbx_cluster: {no_dbx_filter.should_process('dbx_cluster')}")
    print()

    # Example 3: Multiple patterns
    print("Example 3: Include S3 and Glue resources")
    multi_filter = ScopeFilter.include(["aws_s3_*", "aws_glue_*"])
    print(f"Filter: {multi_filter}")
    print(f"aws_s3_bucket: {multi_filter.should_process('aws_s3_bucket')}")
    print(f"aws_glue_database: {multi_filter.should_process('aws_glue_database')}")
    print(f"dbx_cluster: {multi_filter.should_process('dbx_cluster')}")
    print()

    # Example 4: Filter a list of resources
    print("Example 4: Filter resource list")
    resources = [
        {"type": "aws_s3_bucket", "id": "bucket1"},
        {"type": "aws_glue_database", "id": "db1"},
        {"type": "dbx_cluster", "id": "cluster1"},
        {"type": "dbx_job", "id": "job1"},
    ]

    aws_only = ScopeFilter.include(["aws_*"])
    filtered = aws_only.filter_resources(resources)
    print(f"Original: {len(resources)} resources")
    print(f"Filtered: {len(filtered)} resources")
    for resource in filtered:
        print(f"  - {resource['type']}: {resource['id']}")
