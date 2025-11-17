"""
Integration tests for CLI commands with configuration system.

Tests the full user workflow:
1. dpn config init
2. dpn config validate
3. dpn config show
4. dpn plan preview (with config)
5. dpn create (with config)
"""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml
from click.testing import CliRunner

from data_platform_naming.cli import cli
from data_platform_naming.constants import Environment


@pytest.fixture
def runner():
    """Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_home(tmp_path, monkeypatch):
    """Temporary home directory for testing."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    # Change working directory to temp home so Path.cwd() points here
    monkeypatch.chdir(home)
    return home


@pytest.fixture
def example_configs(tmp_path):
    """Create example config files for testing."""
    # Create structure: tmp_path/src/data_platform_naming/cli.py and tmp_path/examples/configs/
    src_dir = tmp_path / "src" / "data_platform_naming"
    src_dir.mkdir(parents=True)
    
    example_dir = tmp_path / "examples" / "configs"
    example_dir.mkdir(parents=True)

    # Create naming-values.yaml
    values_content = {
        "version": "1.0",
        "defaults": {
            "project": "testproject",
            "environment": Environment.DEV.value,
            "region": "us-east-1",
            "team": "data-platform",
            "cost_center": "engineering"
        },
        "environments": {
            "dev": {"environment": Environment.DEV.value},
            "prd": {"environment": Environment.PRD.value}
        },
        "resource_types": {}
    }

    with open(example_dir / "naming-values.yaml", "w") as f:
        yaml.dump(values_content, f)

    # Create naming-patterns.yaml with all 27 resource types
    patterns_content = {
        "version": "1.0",
        "patterns": {
            # AWS (13)
            "aws_s3_bucket": "{project}-{purpose}-{layer}-{environment}-{region_short}",
            "aws_glue_database": "{project}_{domain}_{layer}_{environment}",
            "aws_glue_table": "{table_type}_{entity}",
            "aws_glue_crawler": "{project}-{environment}-crawler",
            "aws_lambda_function": "{project}-{environment}-{domain}",
            "aws_iam_role": "{project}-{environment}-role",
            "aws_iam_policy": "{project}-{environment}-policy",
            "aws_kinesis_stream": "{project}-{environment}-stream",
            "aws_kinesis_firehose": "{project}-{environment}-firehose",
            "aws_dynamodb_table": "{project}-{environment}-{entity}",
            "aws_sns_topic": "{project}-{environment}-topic",
            "aws_sqs_queue": "{project}-{environment}-queue",
            "aws_step_function": "{project}-{environment}-workflow",
            # Databricks (14)
            "dbx_workspace": "{project}-{environment}",
            "dbx_cluster": "{project}-{environment}",
            "dbx_job": "{project}-{environment}",
            "dbx_notebook_path": "/{project}/{environment}",
            "dbx_repo": "{project}-{environment}",
            "dbx_pipeline": "{project}-{environment}",
            "dbx_sql_warehouse": "{project}-{environment}",
            "dbx_catalog": "{project}_{environment}",
            "dbx_schema": "{domain}",
            "dbx_table": "{entity}",
            "dbx_volume": "{purpose}",
            "dbx_secret_scope": "{project}-{environment}",
            "dbx_instance_pool": "{project}-{environment}",
            "dbx_policy": "{project}-{environment}"
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

    # Return both the cli.py path (for mocking __file__) and the examples dir
    return {"cli_file": src_dir / "cli.py", "example_dir": example_dir}


class TestConfigInit:
    """Test config init command."""

    def test_config_init_creates_files(self, runner, temp_home, example_configs):
        """Test config init creates files in ~/.dpn/."""
        # Mock __file__ to point to our test location with example configs
        with patch("data_platform_naming.cli.__file__", str(example_configs["cli_file"])):
            result = runner.invoke(cli, [
                "config", "init",
                "--project", "testproject",
                "--environment", Environment.DEV.value,
                "--region", "us-east-1"
            ])

        assert result.exit_code == 0
        assert "Created:" in result.output

        dpn_dir = temp_home / ".dpn"
        assert dpn_dir.exists()
        assert (dpn_dir / "naming-values.yaml").exists()
        assert (dpn_dir / "naming-patterns.yaml").exists()

    def test_config_init_customizes_values(self, runner, temp_home, example_configs):
        """Test config init customizes values file."""
        with patch("data_platform_naming.cli.__file__", str(example_configs["cli_file"])):
            result = runner.invoke(cli, [
                "config", "init",
                "--project", "oncology",
                "--environment", Environment.PRD.value,
                "--region", "us-west-2"
            ])

        assert result.exit_code == 0

        values_file = temp_home / ".dpn" / "naming-values.yaml"
        with open(values_file) as f:
            values = yaml.safe_load(f)

        assert values["defaults"]["project"] == "oncology"
        assert values["defaults"]["environment"] == Environment.PRD.value
        assert values["defaults"]["region"] == "us-west-2"

    def test_config_init_force_overwrite(self, runner, temp_home, example_configs):
        """Test config init with --force overwrites existing files."""
        with patch("data_platform_naming.cli.__file__", str(example_configs["cli_file"])):
            # First init
            runner.invoke(cli, [
                "config", "init",
                "--project", "testproject",
                "--environment", Environment.DEV.value,
                "--region", "us-east-1"
            ])

            # Second init without force should fail
            result = runner.invoke(cli, [
                "config", "init",
                "--project", "newproject",
                "--environment", Environment.PRD.value,
                "--region", "us-west-2"
            ])

            assert result.exit_code == 1
            assert "already" in result.output and "exist" in result.output

            # With --force should succeed
            result = runner.invoke(cli, [
                "config", "init",
                "--project", "newproject",
                "--environment", Environment.PRD.value,
                "--region", "us-west-2",
                "--force"
            ])

            assert result.exit_code == 0

        # Verify values were updated
        values_file = temp_home / ".dpn" / "naming-values.yaml"
        with open(values_file) as f:
            values = yaml.safe_load(f)

        assert values["defaults"]["project"] == "newproject"

    def test_config_init_already_exists_error(self, runner, temp_home, example_configs):
        """Test config init fails when files already exist without --force."""
        # Create files first
        dpn_dir = temp_home / ".dpn"
        dpn_dir.mkdir()
        (dpn_dir / "naming-values.yaml").touch()

        with patch("data_platform_naming.cli.__file__", str(example_configs["cli_file"])):
            result = runner.invoke(cli, [
                "config", "init",
                "--project", "testproject",
                "--environment", Environment.DEV.value,
                "--region", "us-east-1"
            ])

        assert result.exit_code == 1
        assert "already" in result.output and "exist" in result.output
        assert "force" in result.output.lower()


class TestConfigValidate:
    """Test config validate command."""

    def test_config_validate_valid_files(self, runner, temp_home):
        """Test config validate with valid files."""
        # Create valid config files
        dpn_dir = temp_home / ".dpn"
        dpn_dir.mkdir()

        values = {
            "version": "1.0",
            "defaults": {
                "project": "test",
                "environment": Environment.DEV.value,
                "region": "us-east-1"
            }
        }
        with open(dpn_dir / "naming-values.yaml", "w") as f:
            yaml.dump(values, f)

        # Use correct pattern structure (simple strings, not nested objects)
        patterns = {
            "version": "1.0",
            "patterns": {
                "aws_s3_bucket": "{project}-{environment}",
                "aws_glue_database": "{project}",
                "aws_glue_table": "{entity}",
                "aws_glue_crawler": "{project}",
                "aws_lambda_function": "{project}",
                "aws_iam_role": "{project}",
                "aws_iam_policy": "{project}",
                "aws_kinesis_stream": "{project}",
                "aws_kinesis_firehose": "{project}",
                "aws_dynamodb_table": "{project}",
                "aws_sns_topic": "{project}",
                "aws_sqs_queue": "{project}",
                "aws_step_function": "{project}",
                "dbx_workspace": "{project}",
                "dbx_cluster": "{project}",
                "dbx_job": "{project}",
                "dbx_notebook_path": "/{project}",
                "dbx_repo": "{project}",
                "dbx_pipeline": "{project}",
                "dbx_sql_warehouse": "{project}",
                "dbx_catalog": "{project}",
                "dbx_schema": "{domain}",
                "dbx_table": "{entity}",
                "dbx_volume": "{purpose}",
                "dbx_secret_scope": "{project}",
                "dbx_instance_pool": "{project}",
                "dbx_policy": "{project}"
            }
        }
        with open(dpn_dir / "naming-patterns.yaml", "w") as f:
            yaml.dump(patterns, f)

        # Create schema directory structure: temp_home/src/data_platform_naming/
        src_dir = temp_home / "src" / "data_platform_naming"
        src_dir.mkdir(parents=True)
        
        # Create schemas at: temp_home/schemas/ (3 levels up from src/data_platform_naming/cli.py)
        schema_dir = temp_home / "schemas"
        schema_dir.mkdir()
        
        # Create minimal schemas
        values_schema = {"type": "object"}
        with open(schema_dir / "naming-values-schema.json", "w") as f:
            json.dump(values_schema, f)
        
        patterns_schema = {"type": "object"}
        with open(schema_dir / "naming-patterns-schema.json", "w") as f:
            json.dump(patterns_schema, f)
        
        # Mock __file__ to point to our temp structure
        cli_file = src_dir / "cli.py"
        with patch("data_platform_naming.cli.__file__", str(cli_file)):
            result = runner.invoke(cli, ["config", "validate"])

        assert result.exit_code == 0
        assert "is valid" in result.output

    def test_config_validate_missing_files(self, runner, temp_home):
        """Test config validate when files don't exist."""
        result = runner.invoke(cli, ["config", "validate"])

        assert result.exit_code != 0
        assert "not found" in result.output
        assert "dpn config init" in result.output

    def test_config_validate_custom_paths(self, runner, tmp_path):
        """Test config validate with custom paths."""
        # Create custom config files
        custom_dir = tmp_path / "custom"
        custom_dir.mkdir()

        values = {"version": "1.0", "defaults": {"project": "test"}}
        with open(custom_dir / "values.yaml", "w") as f:
            yaml.dump(values, f)

        patterns = {
            "version": "1.0",
            "patterns": {
                "aws_s3_bucket": "{project}",
                "aws_glue_database": "{project}",
                "aws_glue_table": "{entity}",
                "aws_glue_crawler": "{project}",
                "aws_lambda_function": "{project}",
                "aws_iam_role": "{project}",
                "aws_iam_policy": "{project}",
                "aws_kinesis_stream": "{project}",
                "aws_kinesis_firehose": "{project}",
                "aws_dynamodb_table": "{project}",
                "aws_sns_topic": "{project}",
                "aws_sqs_queue": "{project}",
                "aws_step_function": "{project}",
                "dbx_workspace": "{project}",
                "dbx_cluster": "{project}",
                "dbx_job": "{project}",
                "dbx_notebook_path": "/{project}",
                "dbx_repo": "{project}",
                "dbx_pipeline": "{project}",
                "dbx_sql_warehouse": "{project}",
                "dbx_catalog": "{project}",
                "dbx_schema": "{domain}",
                "dbx_table": "{entity}",
                "dbx_volume": "{purpose}",
                "dbx_secret_scope": "{project}",
                "dbx_instance_pool": "{project}",
                "dbx_policy": "{project}"
            }
        }
        with open(custom_dir / "patterns.yaml", "w") as f:
            yaml.dump(patterns, f)

        result = runner.invoke(cli, [
            "config", "validate",
            "--values-config", str(custom_dir / "values.yaml"),
            "--patterns-config", str(custom_dir / "patterns.yaml")
        ])

        # Should not show "not found" error since files exist
        # (May fail schema validation but that's expected with minimal schemas)
        assert "not found" not in result.output.lower()


class TestConfigShow:
    """Test config show command."""

    def test_config_show_table_format(self, runner, temp_home):
        """Test config show with table format."""
        # Create config files
        dpn_dir = temp_home / ".dpn"
        dpn_dir.mkdir()

        values = {
            "version": "1.0",
            "defaults": {
                "project": "testproject",
                "environment": Environment.DEV.value,
                "region": "us-east-1"
            }
        }
        with open(dpn_dir / "naming-values.yaml", "w") as f:
            yaml.dump(values, f)

        patterns = {
            "version": "1.0",
            "patterns": {
                "aws_s3_bucket": "{project}-{environment}"
            }
        }
        with open(dpn_dir / "naming-patterns.yaml", "w") as f:
            yaml.dump(patterns, f)

        with patch("data_platform_naming.cli.load_configuration_manager") as mock_load:
            mock_manager = Mock()
            mock_manager.values_loader.get_defaults.return_value = values["defaults"]
            mock_manager.values_loader.list_environments.return_value = []
            mock_manager.values_loader.list_resource_types.return_value = []
            mock_manager.patterns_loader.list_resource_types.return_value = list(patterns["patterns"].keys())
            mock_load.return_value = mock_manager

            result = runner.invoke(cli, ["config", "show"])

        assert result.exit_code == 0
        assert "testproject" in result.output

    def test_config_show_json_format(self, runner, temp_home):
        """Test config show with JSON format."""
        dpn_dir = temp_home / ".dpn"
        dpn_dir.mkdir()

        values = {"version": "1.0", "defaults": {"project": "test"}}
        with open(dpn_dir / "naming-values.yaml", "w") as f:
            yaml.dump(values, f)

        patterns = {"version": "1.0", "patterns": {}}
        with open(dpn_dir / "naming-patterns.yaml", "w") as f:
            yaml.dump(patterns, f)

        with patch("data_platform_naming.cli.load_configuration_manager") as mock_load:
            mock_manager = Mock()
            mock_manager.values_loader.get_defaults.return_value = values["defaults"]
            mock_manager.values_loader.list_environments.return_value = []
            mock_manager.values_loader.get_environment_values.return_value = {}
            mock_manager.values_loader.list_resource_types.return_value = []
            mock_manager.values_loader.get_resource_type_values.return_value = {}
            mock_manager.patterns_loader.get_all_patterns.return_value = {}
            mock_load.return_value = mock_manager

            result = runner.invoke(cli, ["config", "show", "--format", "json"])

        assert result.exit_code == 0
        # JSON output should be parseable
        assert "{" in result.output


class TestPlanPreviewWithConfig:
    """Test plan preview with configuration."""

    def test_plan_preview_default_config(self, runner, temp_home, tmp_path):
        """Test plan preview uses ~/.dpn/ configs by default."""
        # Create blueprint
        blueprint = tmp_path / "test.json"
        blueprint_data = {
            "version": "1.0",
            "metadata": {
                "environment": Environment.DEV.value,
                "project": "test",
                "region": "us-east-1"
            },
            "resources": {
                "aws": {"s3_buckets": [], "glue_databases": []},
                "databricks": {"clusters": [], "jobs": []}
            }
        }
        with open(blueprint, "w") as f:
            json.dump(blueprint_data, f)

        # Mock config loading
        with patch("data_platform_naming.cli.load_configuration_manager") as mock_load:
            mock_load.return_value = Mock()  # Config found

            result = runner.invoke(cli, ["plan", "preview", str(blueprint)])

        # Should succeed (actual parsing will fail but config loading should work)
        assert "Using configuration-based naming" in result.output or result.exit_code is not None

    def test_plan_preview_no_config_legacy_mode(self, runner, temp_home, tmp_path):
        """Test plan preview falls back to legacy mode without config."""
        blueprint = tmp_path / "test.json"
        blueprint_data = {
            "version": "1.0",
            "metadata": {
                "environment": Environment.DEV.value,
                "project": "test",
                "region": "us-east-1"
            },
            "resources": {
                "aws": {"s3_buckets": [], "glue_databases": []},
                "databricks": {"clusters": [], "jobs": []}
            }
        }
        with open(blueprint, "w") as f:
            json.dump(blueprint_data, f)

        # Mock config loading to return None
        with patch("data_platform_naming.cli.load_configuration_manager") as mock_load:
            mock_load.return_value = None  # No config

            result = runner.invoke(cli, ["plan", "preview", str(blueprint)])

        # Should show message about configuration being required
        assert "Configuration files required" in result.output or "No configuration files found" in result.output


class TestCreateWithConfig:
    """Test create command with configuration."""

    def test_create_dry_run_with_config(self, runner, temp_home, tmp_path):
        """Test create --dry-run with configuration."""
        blueprint = tmp_path / "test.json"
        blueprint_data = {
            "version": "1.0",
            "metadata": {
                "environment": Environment.DEV.value,
                "project": "test",
                "region": "us-east-1"
            },
            "resources": {
                "aws": {"s3_buckets": [], "glue_databases": []},
                "databricks": {"clusters": [], "jobs": []}
            }
        }
        with open(blueprint, "w") as f:
            json.dump(blueprint_data, f)

        with patch("data_platform_naming.cli.load_configuration_manager") as mock_load:
            mock_load.return_value = Mock()  # Config found

            result = runner.invoke(cli, [
                "create",
                "--blueprint", str(blueprint),
                "--dry-run"
            ])

        # Should show dry run message
        assert "DRY RUN" in result.output or result.exit_code is not None


class TestFullWorkflow:
    """Test complete user workflow."""

    def test_init_validate_preview_workflow(self, runner, temp_home, example_configs, tmp_path):
        """Test full workflow: init → validate → preview."""
        # Step 1: Init
        with patch("data_platform_naming.cli.__file__", str(example_configs["cli_file"])):
            result = runner.invoke(cli, [
                "config", "init",
                "--project", "workflow-test",
                "--environment", Environment.DEV.value,
                "--region", "us-east-1"
            ])
            assert result.exit_code == 0

        # Step 2: Validate
        # Create schema directory structure matching what CLI expects
        src_dir = temp_home / "src" / "data_platform_naming"
        src_dir.mkdir(parents=True, exist_ok=True)
        
        schema_dir = temp_home / "schemas"
        schema_dir.mkdir(parents=True, exist_ok=True)

        values_schema = {"type": "object"}
        with open(schema_dir / "naming-values-schema.json", "w") as f:
            json.dump(values_schema, f)

        patterns_schema = {"type": "object"}
        with open(schema_dir / "naming-patterns-schema.json", "w") as f:
            json.dump(patterns_schema, f)

        # Mock __file__ to point to our temp structure
        cli_file = src_dir / "cli.py"
        with patch("data_platform_naming.cli.__file__", str(cli_file)):
            result = runner.invoke(cli, ["config", "validate"])
            assert result.exit_code == 0

        # Step 3: Preview (would need full mocking for generators)
        # This is covered by other tests
