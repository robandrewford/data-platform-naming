"""
Comprehensive tests for interactive config init command.

Tests both interactive prompts and non-interactive flag modes.
"""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml
from click.testing import CliRunner

from data_platform_naming.cli import cli, _parse_resource_type_selection


@pytest.fixture
def runner():
    """Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_project(tmp_path, monkeypatch):
    """Temporary project directory."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)
    return project_dir


@pytest.fixture
def example_configs(tmp_path):
    """Create example config files for testing."""
    # Mimic the package structure
    example_dir = tmp_path / "examples" / "configs"
    example_dir.mkdir(parents=True)

    # Create naming-values.yaml template
    values_content = {
        "version": "1.0",
        "defaults": {
            "project": "template",
            "environment": "dev",
            "region": "us-east-1",
            "team": "data-platform",
            "cost_center": "engineering"
        },
        "environments": {
            "dev": {"environment": "dev"},
            "prd": {"environment": "prd"}
        },
        "resource_types": {}
    }

    with open(example_dir / "naming-values.yaml", "w") as f:
        yaml.dump(values_content, f)

    # Create naming-patterns.yaml
    patterns_content = {
        "version": "1.0",
        "patterns": {
            "aws_s3_bucket": "{project}-{purpose}-{layer}-{environment}-{region_code}",
            "aws_glue_database": "{project}_{domain}_{layer}_{environment}",
            "aws_lambda_function": "{project}-{environment}-{domain}",
            "dbx_catalog": "{project}_{environment}",
            "dbx_cluster": "{project}-{environment}"
        },
        "transformations": {
            "region_mapping": {
                "us-east-1": "use1",
                "us-west-2": "usw2"
            }
        },
        "validation": {
            "max_length": {
                "aws_s3_bucket": 63
            }
        }
    }

    with open(example_dir / "naming-patterns.yaml", "w") as f:
        yaml.dump(patterns_content, f)

    return example_dir


class TestResourceTypeSelectionParser:
    """Test the resource type selection parser."""

    def test_parse_all(self):
        """Test 'all' selection."""
        types = ["aws_s3_bucket", "aws_glue_database", "dbx_catalog"]
        result = _parse_resource_type_selection("all", types)
        assert result == types

    def test_parse_single_numbers(self):
        """Test single number selection."""
        types = ["aws_s3_bucket", "aws_glue_database", "dbx_catalog"]
        result = _parse_resource_type_selection("1,3", types)
        assert result == ["aws_s3_bucket", "dbx_catalog"]

    def test_parse_range(self):
        """Test range selection."""
        types = ["type1", "type2", "type3", "type4", "type5"]
        result = _parse_resource_type_selection("2-4", types)
        assert result == ["type2", "type3", "type4"]

    def test_parse_mixed(self):
        """Test mixed selection."""
        types = ["type1", "type2", "type3", "type4", "type5"]
        result = _parse_resource_type_selection("1,3-4,5", types)
        assert result == ["type1", "type3", "type4", "type5"]

    def test_parse_invalid_numbers_ignored(self):
        """Test invalid numbers are ignored."""
        types = ["type1", "type2", "type3"]
        result = _parse_resource_type_selection("1,5,10", types)
        assert result == ["type1"]

    def test_parse_empty_returns_empty(self):
        """Test empty selection returns empty list."""
        types = ["type1", "type2", "type3"]
        result = _parse_resource_type_selection("", types)
        assert result == []


class TestInteractiveMode:
    """Test interactive prompts."""

    def test_interactive_prompts_all_values(self, runner, temp_project, example_configs):
        """Test all interactive prompts work correctly."""
        # Mock the example directory path
        with patch("data_platform_naming.cli.Path") as mock_path_cls:
            def path_side_effect(arg):
                if "__file__" in str(arg):
                    # Return mock file location
                    return Path(example_configs.parent.parent) / "cli.py"
                return Path(arg)
            
            mock_path_cls.side_effect = path_side_effect

            # Provide inputs for all prompts
            inputs = [
                "engineering",  # cost_center
                "prd",          # environment
                "oncology",     # project
                "us-west-2",    # region
                "data-platform",  # team
                "1,3",          # resource types
            ]

            result = runner.invoke(cli, ["config", "init"], input="\n".join(inputs))

        assert result.exit_code == 0
        assert "Created:" in result.output
        
        # Check files were created
        dpn_dir = temp_project / ".dpn"
        assert dpn_dir.exists()
        assert (dpn_dir / "naming-values.yaml").exists()
        assert (dpn_dir / "naming-patterns.yaml").exists()

        # Check values were customized
        with open(dpn_dir / "naming-values.yaml") as f:
            values = yaml.safe_load(f)
        
        assert values["defaults"]["project"] == "oncology"
        assert values["defaults"]["environment"] == "prd"
        assert values["defaults"]["region"] == "us-west-2"
        assert values["defaults"]["cost_center"] == "engineering"
        assert values["defaults"]["team"] == "data-platform"

    def test_interactive_with_defaults(self, runner, temp_project, example_configs):
        """Test interactive mode with default values."""
        with patch("data_platform_naming.cli.Path") as mock_path_cls:
            def path_side_effect(arg):
                if "__file__" in str(arg):
                    return Path(example_configs.parent.parent) / "cli.py"
                return Path(arg)
            
            mock_path_cls.side_effect = path_side_effect

            # Just press enter for defaults, except project (required)
            inputs = [
                "",             # cost_center (use default)
                "",             # environment (use default)
                "testproj",     # project (required)
                "",             # region (use default)
                "",             # team (use default)
                "all",          # resource types (all)
            ]

            result = runner.invoke(cli, ["config", "init"], input="\n".join(inputs))

        assert result.exit_code == 0

        with open(temp_project / ".dpn" / "naming-values.yaml") as f:
            values = yaml.safe_load(f)
        
        assert values["defaults"]["project"] == "testproj"
        assert values["defaults"]["environment"] == "dev"
        assert values["defaults"]["cost_center"] == "engineering"


class TestNonInteractiveMode:
    """Test non-interactive flag mode."""

    def test_fully_non_interactive(self, runner, temp_project, example_configs):
        """Test fully non-interactive with all flags."""
        with patch("data_platform_naming.cli.Path") as mock_path_cls:
            def path_side_effect(arg):
                if "__file__" in str(arg):
                    return Path(example_configs.parent.parent) / "cli.py"
                return Path(arg)
            
            mock_path_cls.side_effect = path_side_effect

            result = runner.invoke(cli, [
                "config", "init",
                "--project", "analytics",
                "--environment", "prd",
                "--region", "us-west-2",
                "--team", "data-eng",
                "--cost-center", "analytics-dept",
                "--resource-types", "1,3",
                "--force"
            ])

        assert result.exit_code == 0
        assert "Created:" in result.output

        with open(temp_project / ".dpn" / "naming-values.yaml") as f:
            values = yaml.safe_load(f)
        
        assert values["defaults"]["project"] == "analytics"
        assert values["defaults"]["environment"] == "prd"
        assert values["defaults"]["region"] == "us-west-2"
        assert values["defaults"]["team"] == "data-eng"
        assert values["defaults"]["cost_center"] == "analytics-dept"

    def test_partial_flags_prompts_missing(self, runner, temp_project, example_configs):
        """Test partial flags prompts for missing values."""
        with patch("data_platform_naming.cli.Path") as mock_path_cls:
            def path_side_effect(arg):
                if "__file__" in str(arg):
                    return Path(example_configs.parent.parent) / "cli.py"
                return Path(arg)
            
            mock_path_cls.side_effect = path_side_effect

            # Provide some flags, let others be prompted
            inputs = [
                "",         # cost_center (use default)
                "testproj", # project (prompted)
                "",         # region (use default)
                "all",      # resource types
            ]

            result = runner.invoke(
                cli,
                ["config", "init", "--environment", "prd", "--team", "data-platform"],
                input="\n".join(inputs)
            )

        assert result.exit_code == 0

        with open(temp_project / ".dpn" / "naming-values.yaml") as f:
            values = yaml.safe_load(f)
        
        assert values["defaults"]["project"] == "testproj"
        assert values["defaults"]["environment"] == "prd"  # From flag
        assert values["defaults"]["team"] == "data-platform"  # From flag


class TestResourceTypeSelection:
    """Test resource type multi-select."""

    def test_select_specific_types(self, runner, temp_project, example_configs):
        """Test selecting specific resource types."""
        with patch("data_platform_naming.cli.Path") as mock_path_cls:
            def path_side_effect(arg):
                if "__file__" in str(arg):
                    return Path(example_configs.parent.parent) / "cli.py"
                return Path(arg)
            
            mock_path_cls.side_effect = path_side_effect

            result = runner.invoke(cli, [
                "config", "init",
                "--project", "test",
                "--environment", "dev",
                "--region", "us-east-1",
                "--team", "test-team",
                "--cost-center", "test-center",
                "--resource-types", "1,3",
                "--force"
            ])

        assert result.exit_code == 0

        with open(temp_project / ".dpn" / "naming-values.yaml") as f:
            values = yaml.safe_load(f)
        
        # Should have 2 resource types
        assert len(values["resource_types"]) == 2
        assert "aws_s3_bucket" in values["resource_types"]
        assert "aws_lambda_function" in values["resource_types"]

    def test_select_range_types(self, runner, temp_project, example_configs):
        """Test selecting range of resource types."""
        with patch("data_platform_naming.cli.Path") as mock_path_cls:
            def path_side_effect(arg):
                if "__file__" in str(arg):
                    return Path(example_configs.parent.parent) / "cli.py"
                return Path(arg)
            
            mock_path_cls.side_effect = path_side_effect

            result = runner.invoke(cli, [
                "config", "init",
                "--project", "test",
                "--environment", "dev",
                "--region", "us-east-1",
                "--team", "test",
                "--cost-center", "test",
                "--resource-types", "1-3",
                "--force"
            ])

        assert result.exit_code == 0

        with open(temp_project / ".dpn" / "naming-values.yaml") as f:
            values = yaml.safe_load(f)
        
        # Should have 3 resource types (indices 1,2,3)
        assert len(values["resource_types"]) == 3

    def test_select_all_types(self, runner, temp_project, example_configs):
        """Test selecting all resource types."""
        with patch("data_platform_naming.cli.Path") as mock_path_cls:
            def path_side_effect(arg):
                if "__file__" in str(arg):
                    return Path(example_configs.parent.parent) / "cli.py"
                return Path(arg)
            
            mock_path_cls.side_effect = path_side_effect

            result = runner.invoke(cli, [
                "config", "init",
                "--project", "test",
                "--environment", "dev",
                "--region", "us-east-1",
                "--team", "test",
                "--cost-center", "test",
                "--resource-types", "all",
                "--force"
            ])

        assert result.exit_code == 0

        with open(temp_project / ".dpn" / "naming-values.yaml") as f:
            values = yaml.safe_load(f)
        
        # Should have all 5 resource types from patterns
        assert len(values["resource_types"]) == 5


class TestOverwriteConfirmation:
    """Test overwrite confirmation logic."""

    def test_no_prompt_when_files_dont_exist(self, runner, temp_project, example_configs):
        """Test no confirmation prompt when files don't exist."""
        with patch("data_platform_naming.cli.Path") as mock_path_cls:
            def path_side_effect(arg):
                if "__file__" in str(arg):
                    return Path(example_configs.parent.parent) / "cli.py"
                return Path(arg)
            
            mock_path_cls.side_effect = path_side_effect

            result = runner.invoke(cli, [
                "config", "init",
                "--project", "test",
                "--environment", "dev",
                "--region", "us-east-1",
                "--team", "test",
                "--cost-center", "test",
                "--resource-types", "all",
            ])

        assert result.exit_code == 0
        # Should not contain confirmation prompt
        assert "overwrite existing files" not in result.output.lower()

    def test_confirmation_yes_overwrites(self, runner, temp_project, example_configs):
        """Test Y confirmation overwrites files."""
        with patch("data_platform_naming.cli.Path") as mock_path_cls:
            def path_side_effect(arg):
                if "__file__" in str(arg):
                    return Path(example_configs.parent.parent) / "cli.py"
                return Path(arg)
            
            mock_path_cls.side_effect = path_side_effect

            # Create existing files first
            dpn_dir = temp_project / ".dpn"
            dpn_dir.mkdir()
            (dpn_dir / "naming-values.yaml").write_text("existing: data")

            inputs = [
                "",         # cost_center
                "",         # environment
                "newproj",  # project
                "",         # region
                "",         # team
                "all",      # resource types
                "y",        # overwrite confirmation
            ]

            result = runner.invoke(cli, ["config", "init"], input="\n".join(inputs))

        assert result.exit_code == 0
        assert "Created:" in result.output

        # Check file was overwritten
        with open(dpn_dir / "naming-values.yaml") as f:
            values = yaml.safe_load(f)
        
        assert values["defaults"]["project"] == "newproj"

    def test_confirmation_no_cancels(self, runner, temp_project, example_configs):
        """Test N confirmation cancels operation."""
        with patch("data_platform_naming.cli.Path") as mock_path_cls:
            def path_side_effect(arg):
                if "__file__" in str(arg):
                    return Path(example_configs.parent.parent) / "cli.py"
                return Path(arg)
            
            mock_path_cls.side_effect = path_side_effect

            # Create existing files
            dpn_dir = temp_project / ".dpn"
            dpn_dir.mkdir()
            (dpn_dir / "naming-values.yaml").write_text("existing: data")

            inputs = [
                "",         # cost_center
                "",         # environment
                "newproj",  # project
                "",         # region
                "",         # team
                "all",      # resource types
                "n",        # overwrite confirmation - NO
            ]

            result = runner.invoke(cli, ["config", "init"], input="\n".join(inputs))

        assert result.exit_code == 0
        assert "No changes were made" in result.output

        # Check file was NOT overwritten
        content = (dpn_dir / "naming-values.yaml").read_text()
        assert content == "existing: data"

    def test_force_flag_skips_confirmation(self, runner, temp_project, example_configs):
        """Test --force flag skips confirmation prompt."""
        with patch("data_platform_naming.cli.Path") as mock_path_cls:
            def path_side_effect(arg):
                if "__file__" in str(arg):
                    return Path(example_configs.parent.parent) / "cli.py"
                return Path(arg)
            
            mock_path_cls.side_effect = path_side_effect

            # Create existing files
            dpn_dir = temp_project / ".dpn"
            dpn_dir.mkdir()
            (dpn_dir / "naming-values.yaml").write_text("existing: data")

            result = runner.invoke(cli, [
                "config", "init",
                "--project", "forced",
                "--environment", "dev",
                "--region", "us-east-1",
                "--team", "test",
                "--cost-center", "test",
                "--resource-types", "all",
                "--force"
            ])

        assert result.exit_code == 0
        assert "overwrite" not in result.output.lower()

        # Check file was overwritten
        with open(dpn_dir / "naming-values.yaml") as f:
            values = yaml.safe_load(f)
        
        assert values["defaults"]["project"] == "forced"


class TestValidStructure:
    """Test generated YAML structure is valid."""

    def test_creates_valid_yaml_structure(self, runner, temp_project, example_configs):
        """Test generated YAML has correct structure."""
        with patch("data_platform_naming.cli.Path") as mock_path_cls:
            def path_side_effect(arg):
                if "__file__" in str(arg):
                    return Path(example_configs.parent.parent) / "cli.py"
                return Path(arg)
            
            mock_path_cls.side_effect = path_side_effect

            result = runner.invoke(cli, [
                "config", "init",
                "--project", "test",
                "--environment", "prd",
                "--region", "us-west-2",
                "--team", "data-eng",
                "--cost-center", "engineering",
                "--resource-types", "1,3",
                "--force"
            ])

        assert result.exit_code == 0

        # Load and validate structure
        with open(temp_project / ".dpn" / "naming-values.yaml") as f:
            values = yaml.safe_load(f)
        
        # Check top-level structure
        assert "version" in values
        assert "defaults" in values
        assert "environments" in values
        assert "resource_types" in values

        # Check defaults
        assert "cost_center" in values["defaults"]
        assert "environment" in values["defaults"]
        assert "project" in values["defaults"]
        assert "region" in values["defaults"]
        assert "team" in values["defaults"]

        # Check resource_types are dicts
        for rt, config in values["resource_types"].items():
            assert isinstance(config, dict)

    def test_resource_types_populated_correctly(self, runner, temp_project, example_configs):
        """Test resource_types section is correctly populated."""
        with patch("data_platform_naming.cli.Path") as mock_path_cls:
            def path_side_effect(arg):
                if "__file__" in str(arg):
                    return Path(example_configs.parent.parent) / "cli.py"
                return Path(arg)
            
            mock_path_cls.side_effect = path_side_effect

            result = runner.invoke(cli, [
                "config", "init",
                "--project", "test",
                "--environment", "dev",
                "--region", "us-east-1",
                "--team", "test",
                "--cost-center", "test",
                "--resource-types", "1,2",
                "--force"
            ])

        assert result.exit_code == 0

        with open(temp_project / ".dpn" / "naming-values.yaml") as f:
            values = yaml.safe_load(f)
        
        # Check selected types are present as empty dicts
        assert "aws_s3_bucket" in values["resource_types"]
        assert "aws_glue_database" in values["resource_types"]
        assert values["resource_types"]["aws_s3_bucket"] == {}
        assert values["resource_types"]["aws_glue_database"] == {}

    def test_patterns_file_copied(self, runner, temp_project, example_configs):
        """Test patterns file is copied correctly."""
        with patch("data_platform_naming.cli.Path") as mock_path_cls:
            def path_side_effect(arg):
                if "__file__" in str(arg):
                    return Path(example_configs.parent.parent) / "cli.py"
                return Path(arg)
            
            mock_path_cls.side_effect = path_side_effect

            result = runner.invoke(cli, [
                "config", "init",
                "--project", "test",
                "--environment", "dev",
                "--region", "us-east-1",
                "--team", "test",
                "--cost-center", "test",
                "--resource-types", "all",
                "--force"
            ])

        assert result.exit_code == 0

        # Check patterns file exists and has correct structure
        patterns_path = temp_project / ".dpn" / "naming-patterns.yaml"
        assert patterns_path.exists()

        with open(patterns_path) as f:
            patterns = yaml.safe_load(f)
        
        assert "patterns" in patterns
        assert "transformations" in patterns
        assert "validation" in patterns
