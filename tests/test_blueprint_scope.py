#!/usr/bin/env python3
"""
Unit tests for blueprint scope filtering functionality.
"""

import json
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

from data_platform_naming.aws_naming import AWSNamingConfig, AWSNamingGenerator
from data_platform_naming.dbx_naming import DatabricksNamingConfig, DatabricksNamingGenerator
from data_platform_naming.plan.blueprint import BlueprintParser


@pytest.fixture
def naming_generators():
    """Create naming generators for testing"""
    aws_config = AWSNamingConfig(
        environment='dev',
        project='testproject',
        region='us-east-1'
    )

    dbx_config = DatabricksNamingConfig(
        environment='dev',
        project='testproject',
        region='us-east-1'
    )

    return {
        'aws': AWSNamingGenerator(aws_config),
        'databricks': DatabricksNamingGenerator(dbx_config)
    }


@pytest.fixture
def sample_blueprint():
    """Create a sample blueprint with various resource types"""
    return {
        "version": "1.0",
        "metadata": {
            "environment": "dev",
            "project": "testproject",
            "region": "us-east-1"
        },
        "resources": {
            "aws": {
                "s3_buckets": [
                    {"purpose": "raw", "layer": "raw"}
                ],
                "glue_databases": [
                    {"domain": "sales", "layer": "bronze"}
                ]
            },
            "databricks": {
                "clusters": [
                    {"workload": "etl", "cluster_type": "shared", "node_type": "i3.xlarge"}
                ],
                "jobs": [
                    {"job_type": "batch", "purpose": "daily-load", "cluster_ref": "etl"}
                ]
            }
        }
    }


def create_temp_blueprint(blueprint_data):
    """Helper to create temporary blueprint file"""
    temp_file = NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    json.dump(blueprint_data, temp_file)
    temp_file.close()
    return Path(temp_file.name)


class TestBlueprintScopeValidation:
    """Test scope configuration validation"""

    def test_valid_include_scope(self, sample_blueprint, naming_generators):
        """Test valid include scope configuration"""
        sample_blueprint['scope'] = {
            "mode": "include",
            "patterns": ["aws_*"]
        }

        temp_path = create_temp_blueprint(sample_blueprint)
        try:
            parser = BlueprintParser(naming_generators)
            parsed = parser.parse(temp_path)
            assert parsed.scope_config is not None
            assert parsed.scope_config['mode'] == 'include'
            assert parsed.scope_config['patterns'] == ['aws_*']
        finally:
            temp_path.unlink()

    def test_valid_exclude_scope(self, sample_blueprint, naming_generators):
        """Test valid exclude scope configuration"""
        sample_blueprint['scope'] = {
            "mode": "exclude",
            "patterns": ["dbx_*"]
        }

        temp_path = create_temp_blueprint(sample_blueprint)
        try:
            parser = BlueprintParser(naming_generators)
            parsed = parser.parse(temp_path)
            assert parsed.scope_config is not None
            assert parsed.scope_config['mode'] == 'exclude'
        finally:
            temp_path.unlink()

    def test_invalid_mode(self, sample_blueprint, naming_generators):
        """Test invalid mode raises validation error"""
        sample_blueprint['scope'] = {
            "mode": "invalid",
            "patterns": ["aws_*"]
        }

        temp_path = create_temp_blueprint(sample_blueprint)
        try:
            parser = BlueprintParser(naming_generators)
            with pytest.raises(ValueError, match="Blueprint validation failed"):
                parser.parse(temp_path)
        finally:
            temp_path.unlink()

    def test_missing_patterns(self, sample_blueprint, naming_generators):
        """Test missing patterns raises validation error"""
        sample_blueprint['scope'] = {
            "mode": "include"
        }

        temp_path = create_temp_blueprint(sample_blueprint)
        try:
            parser = BlueprintParser(naming_generators)
            with pytest.raises(ValueError, match="Blueprint validation failed"):
                parser.parse(temp_path)
        finally:
            temp_path.unlink()

    def test_empty_patterns(self, sample_blueprint, naming_generators):
        """Test empty patterns array raises validation error"""
        sample_blueprint['scope'] = {
            "mode": "include",
            "patterns": []
        }

        temp_path = create_temp_blueprint(sample_blueprint)
        try:
            parser = BlueprintParser(naming_generators)
            with pytest.raises(ValueError, match="Blueprint validation failed"):
                parser.parse(temp_path)
        finally:
            temp_path.unlink()


class TestBlueprintScopeFiltering:
    """Test scope filtering logic"""

    def test_include_aws_only(self, sample_blueprint, naming_generators):
        """Test include mode with AWS resources only"""
        sample_blueprint['scope'] = {
            "mode": "include",
            "patterns": ["aws_*"]
        }

        temp_path = create_temp_blueprint(sample_blueprint)
        try:
            parser = BlueprintParser(naming_generators)
            parsed = parser.parse(temp_path)

            # Should only have AWS resources
            resource_types = [r.resource_type for r in parsed.resources]
            assert all(rt.startswith('aws_') for rt in resource_types)
            assert not any(rt.startswith('dbx_') for rt in resource_types)
            assert len(parsed.resources) == 2  # 1 S3 bucket + 1 Glue database
        finally:
            temp_path.unlink()

    def test_include_databricks_only(self, sample_blueprint, naming_generators):
        """Test include mode with Databricks resources only"""
        sample_blueprint['scope'] = {
            "mode": "include",
            "patterns": ["dbx_*"]
        }

        temp_path = create_temp_blueprint(sample_blueprint)
        try:
            parser = BlueprintParser(naming_generators)
            parsed = parser.parse(temp_path)

            # Should only have Databricks resources
            resource_types = [r.resource_type for r in parsed.resources]
            assert all(rt.startswith('dbx_') for rt in resource_types)
            assert not any(rt.startswith('aws_') for rt in resource_types)
            assert len(parsed.resources) == 2  # 1 cluster + 1 job
        finally:
            temp_path.unlink()

    def test_exclude_aws(self, sample_blueprint, naming_generators):
        """Test exclude mode with AWS resources"""
        sample_blueprint['scope'] = {
            "mode": "exclude",
            "patterns": ["aws_*"]
        }

        temp_path = create_temp_blueprint(sample_blueprint)
        try:
            parser = BlueprintParser(naming_generators)
            parsed = parser.parse(temp_path)

            # Should only have Databricks resources
            resource_types = [r.resource_type for r in parsed.resources]
            assert all(rt.startswith('dbx_') for rt in resource_types)
            assert len(parsed.resources) == 2  # 1 cluster + 1 job
        finally:
            temp_path.unlink()

    def test_exclude_databricks(self, sample_blueprint, naming_generators):
        """Test exclude mode with Databricks resources"""
        sample_blueprint['scope'] = {
            "mode": "exclude",
            "patterns": ["dbx_*"]
        }

        temp_path = create_temp_blueprint(sample_blueprint)
        try:
            parser = BlueprintParser(naming_generators)
            parsed = parser.parse(temp_path)

            # Should only have AWS resources
            resource_types = [r.resource_type for r in parsed.resources]
            assert all(rt.startswith('aws_') for rt in resource_types)
            assert len(parsed.resources) == 2  # 1 S3 bucket + 1 Glue database
        finally:
            temp_path.unlink()

    def test_include_specific_type(self, sample_blueprint, naming_generators):
        """Test include mode with specific resource type"""
        sample_blueprint['scope'] = {
            "mode": "include",
            "patterns": ["aws_s3_bucket"]
        }

        temp_path = create_temp_blueprint(sample_blueprint)
        try:
            parser = BlueprintParser(naming_generators)
            parsed = parser.parse(temp_path)

            # Should only have S3 buckets
            assert len(parsed.resources) == 1
            assert parsed.resources[0].resource_type == 'aws_s3_bucket'
        finally:
            temp_path.unlink()

    def test_multiple_patterns(self, sample_blueprint, naming_generators):
        """Test multiple patterns in include mode"""
        sample_blueprint['scope'] = {
            "mode": "include",
            "patterns": ["aws_s3_*", "dbx_cluster"]
        }

        temp_path = create_temp_blueprint(sample_blueprint)
        try:
            parser = BlueprintParser(naming_generators)
            parsed = parser.parse(temp_path)

            # Should have S3 buckets and Databricks clusters
            resource_types = [r.resource_type for r in parsed.resources]
            assert 'aws_s3_bucket' in resource_types
            assert 'dbx_cluster' in resource_types
            assert 'aws_glue_database' not in resource_types
            assert 'dbx_job' not in resource_types
            assert len(parsed.resources) == 2
        finally:
            temp_path.unlink()

    def test_wildcard_suffix(self, sample_blueprint, naming_generators):
        """Test wildcard suffix pattern"""
        sample_blueprint['scope'] = {
            "mode": "include",
            "patterns": ["*_cluster"]
        }

        temp_path = create_temp_blueprint(sample_blueprint)
        try:
            parser = BlueprintParser(naming_generators)
            parsed = parser.parse(temp_path)

            # Should only have cluster resources
            assert len(parsed.resources) == 1
            assert parsed.resources[0].resource_type == 'dbx_cluster'
        finally:
            temp_path.unlink()

    def test_no_scope_processes_all(self, sample_blueprint, naming_generators):
        """Test that no scope configuration processes all resources"""
        # No scope added to sample_blueprint

        temp_path = create_temp_blueprint(sample_blueprint)
        try:
            parser = BlueprintParser(naming_generators)
            parsed = parser.parse(temp_path)

            # Should have all resources
            assert len(parsed.resources) == 4  # 2 AWS + 2 Databricks
            assert parsed.scope_config is None
        finally:
            temp_path.unlink()


class TestBlueprintScopeBackwardCompatibility:
    """Test backward compatibility with blueprints without scope"""

    def test_blueprint_without_scope_works(self, sample_blueprint, naming_generators):
        """Test that blueprints without scope still work"""
        # Ensure no scope in blueprint
        assert 'scope' not in sample_blueprint

        temp_path = create_temp_blueprint(sample_blueprint)
        try:
            parser = BlueprintParser(naming_generators)
            parsed = parser.parse(temp_path)

            # Should process all resources
            assert len(parsed.resources) == 4
            assert parsed.scope_config is None
        finally:
            temp_path.unlink()

    def test_scope_config_stored_in_parsed_blueprint(self, sample_blueprint, naming_generators):
        """Test that scope config is stored in ParsedBlueprint"""
        sample_blueprint['scope'] = {
            "mode": "include",
            "patterns": ["aws_*"]
        }

        temp_path = create_temp_blueprint(sample_blueprint)
        try:
            parser = BlueprintParser(naming_generators)
            parsed = parser.parse(temp_path)

            # Scope config should be stored
            assert parsed.scope_config is not None
            assert parsed.scope_config['mode'] == 'include'
            assert parsed.scope_config['patterns'] == ['aws_*']
        finally:
            temp_path.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
