#!/usr/bin/env python3
"""
Tests for ScopeFilter class.
"""

import pytest

from data_platform_naming.config.scope_filter import (
    FilterMode,
    ScopeConfig,
    ScopeFilter,
)


class TestFilterMode:
    """Test FilterMode enum"""

    def test_include_mode(self):
        """Test INCLUDE mode value"""
        assert FilterMode.INCLUDE.value == "include"

    def test_exclude_mode(self):
        """Test EXCLUDE mode value"""
        assert FilterMode.EXCLUDE.value == "exclude"


class TestScopeConfig:
    """Test ScopeConfig dataclass"""

    def test_valid_config(self):
        """Test valid configuration"""
        config = ScopeConfig(
            mode=FilterMode.INCLUDE,
            patterns=["aws_*", "dbx_*"]
        )
        assert config.mode == FilterMode.INCLUDE
        assert config.patterns == ["aws_*", "dbx_*"]

    def test_empty_patterns_raises_error(self):
        """Test that empty patterns list raises error"""
        with pytest.raises(ValueError, match="At least one pattern"):
            ScopeConfig(mode=FilterMode.INCLUDE, patterns=[])

    def test_invalid_pattern_type(self):
        """Test that invalid pattern type raises error"""
        with pytest.raises(ValueError, match="Invalid pattern"):
            ScopeConfig(mode=FilterMode.INCLUDE, patterns=[123])  # type: ignore

    def test_empty_string_pattern(self):
        """Test that empty string pattern raises error"""
        with pytest.raises(ValueError, match="Invalid pattern"):
            ScopeConfig(mode=FilterMode.INCLUDE, patterns=[""])


class TestScopeFilter:
    """Test ScopeFilter class"""

    def test_init_default(self):
        """Test default initialization"""
        filter = ScopeFilter()
        assert filter.mode == FilterMode.INCLUDE
        assert filter.patterns == ["*"]

    def test_init_with_mode_and_patterns(self):
        """Test initialization with mode and patterns"""
        filter = ScopeFilter(
            mode=FilterMode.EXCLUDE,
            patterns=["dbx_*", "aws_glue_*"]
        )
        assert filter.mode == FilterMode.EXCLUDE
        assert filter.patterns == ["dbx_*", "aws_glue_*"]

    def test_wildcard_to_regex_exact_match(self):
        """Test wildcard conversion for exact match"""
        pattern = ScopeFilter._wildcard_to_regex("aws_s3_bucket")
        assert pattern.match("aws_s3_bucket")
        assert not pattern.match("aws_s3")
        assert not pattern.match("aws_s3_bucket_extra")

    def test_wildcard_to_regex_prefix_wildcard(self):
        """Test wildcard conversion for prefix match"""
        pattern = ScopeFilter._wildcard_to_regex("aws_*")
        assert pattern.match("aws_s3_bucket")
        assert pattern.match("aws_glue_database")
        assert pattern.match("aws_")
        assert not pattern.match("dbx_cluster")

    def test_wildcard_to_regex_suffix_wildcard(self):
        """Test wildcard conversion for suffix match"""
        pattern = ScopeFilter._wildcard_to_regex("*_bucket")
        assert pattern.match("aws_s3_bucket")
        assert pattern.match("my_bucket")
        assert not pattern.match("bucket")
        assert not pattern.match("aws_s3_bucket_extra")

    def test_wildcard_to_regex_contains_wildcard(self):
        """Test wildcard conversion for contains match"""
        pattern = ScopeFilter._wildcard_to_regex("*s3*")
        assert pattern.match("aws_s3_bucket")
        assert pattern.match("s3")
        assert pattern.match("my_s3_storage")
        assert not pattern.match("aws_glue")

    def test_wildcard_to_regex_question_mark(self):
        """Test wildcard conversion for single character match"""
        pattern = ScopeFilter._wildcard_to_regex("aws_s?_bucket")
        assert pattern.match("aws_s3_bucket")
        assert pattern.match("aws_sx_bucket")
        assert not pattern.match("aws_s_bucket")
        assert not pattern.match("aws_s33_bucket")

    def test_wildcard_to_regex_special_chars(self):
        """Test that regex special characters are escaped"""
        pattern = ScopeFilter._wildcard_to_regex("test.resource")
        assert pattern.match("test.resource")
        assert not pattern.match("testXresource")

    def test_matches_any_pattern_single_match(self):
        """Test matching against single pattern"""
        filter = ScopeFilter(patterns=["aws_*"])
        assert filter.matches_any_pattern("aws_s3_bucket")
        assert not filter.matches_any_pattern("dbx_cluster")

    def test_matches_any_pattern_multiple_patterns(self):
        """Test matching against multiple patterns"""
        filter = ScopeFilter(patterns=["aws_s3_*", "aws_glue_*"])
        assert filter.matches_any_pattern("aws_s3_bucket")
        assert filter.matches_any_pattern("aws_glue_database")
        assert not filter.matches_any_pattern("aws_iam_role")
        assert not filter.matches_any_pattern("dbx_cluster")

    def test_should_process_include_mode(self):
        """Test should_process with INCLUDE mode"""
        filter = ScopeFilter(
            mode=FilterMode.INCLUDE,
            patterns=["aws_*"]
        )
        assert filter.should_process("aws_s3_bucket") is True
        assert filter.should_process("dbx_cluster") is False

    def test_should_process_exclude_mode(self):
        """Test should_process with EXCLUDE mode"""
        filter = ScopeFilter(
            mode=FilterMode.EXCLUDE,
            patterns=["dbx_*"]
        )
        assert filter.should_process("aws_s3_bucket") is True
        assert filter.should_process("dbx_cluster") is False

    def test_filter_resources(self):
        """Test filtering a list of resources"""
        resources = [
            {"type": "aws_s3_bucket", "id": "bucket1"},
            {"type": "aws_glue_database", "id": "db1"},
            {"type": "dbx_cluster", "id": "cluster1"},
            {"type": "dbx_job", "id": "job1"},
        ]

        filter = ScopeFilter.include(["aws_*"])
        filtered = filter.filter_resources(resources)

        assert len(filtered) == 2
        assert filtered[0]["type"] == "aws_s3_bucket"
        assert filtered[1]["type"] == "aws_glue_database"

    def test_filter_resources_empty_type(self):
        """Test filtering resources with missing or empty type"""
        resources = [
            {"type": "aws_s3_bucket", "id": "bucket1"},
            {"id": "no_type"},  # Missing type
            {"type": "", "id": "empty_type"},  # Empty type
        ]

        filter = ScopeFilter.include(["aws_*"])
        filtered = filter.filter_resources(resources)

        assert len(filtered) == 1
        assert filtered[0]["type"] == "aws_s3_bucket"

    def test_get_matching_types(self):
        """Test getting matching resource types"""
        resource_types = [
            "aws_s3_bucket",
            "aws_glue_database",
            "aws_glue_table",
            "dbx_cluster",
            "dbx_job",
        ]

        filter = ScopeFilter.include(["aws_glue_*"])
        matching = filter.get_matching_types(resource_types)

        assert len(matching) == 2
        assert "aws_glue_database" in matching
        assert "aws_glue_table" in matching

    def test_from_config(self):
        """Test creating filter from ScopeConfig"""
        config = ScopeConfig(
            mode=FilterMode.EXCLUDE,
            patterns=["dbx_*"]
        )
        filter = ScopeFilter.from_config(config)

        assert filter.mode == FilterMode.EXCLUDE
        assert filter.patterns == ["dbx_*"]

    def test_include_classmethod(self):
        """Test include() classmethod"""
        filter = ScopeFilter.include(["aws_*", "dbx_*"])
        assert filter.mode == FilterMode.INCLUDE
        assert filter.patterns == ["aws_*", "dbx_*"]

    def test_exclude_classmethod(self):
        """Test exclude() classmethod"""
        filter = ScopeFilter.exclude(["test_*"])
        assert filter.mode == FilterMode.EXCLUDE
        assert filter.patterns == ["test_*"]

    def test_allow_all_classmethod(self):
        """Test allow_all() classmethod"""
        filter = ScopeFilter.allow_all()
        assert filter.should_process("aws_s3_bucket") is True
        assert filter.should_process("dbx_cluster") is True
        assert filter.should_process("anything") is True

    def test_deny_all_classmethod(self):
        """Test deny_all() classmethod"""
        filter = ScopeFilter.deny_all()
        assert filter.should_process("aws_s3_bucket") is False
        assert filter.should_process("dbx_cluster") is False
        assert filter.should_process("anything") is False

    def test_repr(self):
        """Test string representation"""
        filter = ScopeFilter(
            mode=FilterMode.INCLUDE,
            patterns=["aws_*", "dbx_*"]
        )
        repr_str = repr(filter)
        assert "ScopeFilter" in repr_str
        assert "mode=include" in repr_str
        assert "'aws_*'" in repr_str
        assert "'dbx_*'" in repr_str

    def test_complex_wildcard_patterns(self):
        """Test complex wildcard patterns"""
        filter = ScopeFilter.include(["aws_*_bucket", "*_database", "dbx_job"])

        assert filter.should_process("aws_s3_bucket") is True
        assert filter.should_process("aws_glacier_bucket") is True
        assert filter.should_process("aws_glue_database") is True
        assert filter.should_process("my_database") is True
        assert filter.should_process("dbx_job") is True
        assert filter.should_process("dbx_cluster") is False
        assert filter.should_process("aws_iam_role") is False

    def test_case_sensitive_matching(self):
        """Test that matching is case-sensitive"""
        filter = ScopeFilter.include(["aws_*"])
        assert filter.should_process("aws_s3_bucket") is True
        assert filter.should_process("AWS_S3_BUCKET") is False
        assert filter.should_process("Aws_S3_Bucket") is False

    def test_multiple_wildcards_in_pattern(self):
        """Test patterns with multiple wildcards"""
        filter = ScopeFilter.include(["*_s3_*"])
        assert filter.should_process("aws_s3_bucket") is True
        assert filter.should_process("my_s3_storage") is True
        assert filter.should_process("s3_anything") is False  # Doesn't start with *

    def test_exclude_mode_with_multiple_patterns(self):
        """Test EXCLUDE mode with multiple patterns"""
        filter = ScopeFilter.exclude(["dbx_*", "aws_iam_*"])

        # Should process (not excluded)
        assert filter.should_process("aws_s3_bucket") is True
        assert filter.should_process("aws_glue_database") is True

        # Should not process (excluded)
        assert filter.should_process("dbx_cluster") is False
        assert filter.should_process("dbx_job") is False
        assert filter.should_process("aws_iam_role") is False

    def test_empty_resource_type(self):
        """Test handling of empty resource type"""
        filter = ScopeFilter.include(["aws_*"])
        assert filter.should_process("") is False

    def test_filter_preserves_order(self):
        """Test that filtering preserves resource order"""
        resources = [
            {"type": "dbx_cluster", "id": "1"},
            {"type": "aws_s3_bucket", "id": "2"},
            {"type": "dbx_job", "id": "3"},
            {"type": "aws_glue_database", "id": "4"},
        ]

        filter = ScopeFilter.include(["aws_*"])
        filtered = filter.filter_resources(resources)

        assert len(filtered) == 2
        assert filtered[0]["id"] == "2"  # Order preserved
        assert filtered[1]["id"] == "4"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
