"""
Tests for CLI input validation in data_platform_naming.cli
"""

import pytest
from click.testing import CliRunner

from data_platform_naming.cli import cli


class TestOverrideValidation:
    """Test validation of --override parameter in CLI commands"""

    @pytest.fixture
    def runner(self):
        """Create CLI runner"""
        return CliRunner()

    def test_valid_override_environment(self, runner):
        """Test valid environment override"""
        result = runner.invoke(
            cli,
            ['plan', 'preview', 'test.json', '--override', 'environment=dev'],
            catch_exceptions=False
        )
        # Command will fail due to missing test.json, but validation should pass
        assert 'Invalid override key' not in result.output
        assert 'Invalid environment' not in result.output

    def test_valid_override_project(self, runner):
        """Test valid project override"""
        result = runner.invoke(
            cli,
            ['plan', 'preview', 'test.json', '--override', 'project=my-project'],
            catch_exceptions=False
        )
        # Command will fail due to missing test.json, but validation should pass
        assert 'Invalid override key' not in result.output
        assert 'Invalid project name' not in result.output

    def test_valid_multiple_overrides(self, runner):
        """Test multiple valid overrides"""
        result = runner.invoke(
            cli,
            [
                'plan', 'preview', 'test.json',
                '--override', 'environment=stg',
                '--override', 'project=data-platform',
                '--override', 'region=us-west-2'
            ],
            catch_exceptions=False
        )
        # Command will fail due to missing test.json, but validation should pass
        assert 'Invalid override key' not in result.output
        assert 'Invalid environment' not in result.output
        assert 'Invalid project name' not in result.output

    def test_invalid_override_key(self, runner):
        """Test invalid override key rejected"""
        result = runner.invoke(
            cli,
            ['plan', 'preview', 'test.json', '--override', 'invalid_key=value'],
            catch_exceptions=False
        )
        assert result.exit_code != 0
        assert 'Invalid override key' in result.output
        assert 'invalid_key' in result.output
        assert 'Allowed keys:' in result.output

    def test_invalid_environment_value(self, runner):
        """Test invalid environment value rejected"""
        result = runner.invoke(
            cli,
            ['plan', 'preview', 'test.json', '--override', 'environment=prod'],
            catch_exceptions=False
        )
        assert result.exit_code != 0
        assert 'Invalid environment' in result.output
        assert 'prod' in result.output
        assert 'Allowed values:' in result.output

    def test_invalid_project_uppercase(self, runner):
        """Test project name with uppercase rejected"""
        result = runner.invoke(
            cli,
            ['plan', 'preview', 'test.json', '--override', 'project=MyProject'],
            catch_exceptions=False
        )
        assert result.exit_code != 0
        assert 'Invalid project name' in result.output
        assert 'MyProject' in result.output
        assert 'lowercase' in result.output

    def test_invalid_project_special_chars(self, runner):
        """Test project name with special characters rejected"""
        result = runner.invoke(
            cli,
            ['plan', 'preview', 'test.json', '--override', 'project=my_project!'],
            catch_exceptions=False
        )
        assert result.exit_code != 0
        assert 'Invalid project name' in result.output
        assert 'my_project!' in result.output

    def test_invalid_project_spaces(self, runner):
        """Test project name with spaces rejected"""
        result = runner.invoke(
            cli,
            ['plan', 'preview', 'test.json', '--override', 'project=my project'],
            catch_exceptions=False
        )
        assert result.exit_code != 0
        assert 'Invalid project name' in result.output
        assert 'my project' in result.output

    def test_invalid_override_format_missing_equals(self, runner):
        """Test override format without equals sign rejected"""
        result = runner.invoke(
            cli,
            ['plan', 'preview', 'test.json', '--override', 'environmentdev'],
            catch_exceptions=False
        )
        assert result.exit_code != 0
        assert 'Invalid override format' in result.output
        assert 'environmentdev' in result.output
        assert 'key=value' in result.output

    def test_override_whitespace_trimmed(self, runner):
        """Test that whitespace in override is trimmed"""
        result = runner.invoke(
            cli,
            ['plan', 'preview', 'test.json', '--override', ' environment = dev '],
            catch_exceptions=False
        )
        # Validation should pass (whitespace trimmed), command fails on missing file
        assert 'Invalid override key' not in result.output
        assert 'Invalid environment' not in result.output


class TestOverrideValidationInCreateCommand:
    """Test validation works in create command as well"""

    @pytest.fixture
    def runner(self):
        """Create CLI runner"""
        return CliRunner()

    def test_create_invalid_override_key(self, runner):
        """Test invalid override key rejected in create command"""
        result = runner.invoke(
            cli,
            ['create', '--blueprint', 'test.json', '--override', 'bad_key=value'],
            catch_exceptions=False
        )
        assert result.exit_code != 0
        assert 'Invalid override key' in result.output
        assert 'bad_key' in result.output

    def test_create_invalid_environment(self, runner):
        """Test invalid environment rejected in create command"""
        result = runner.invoke(
            cli,
            ['create', '--blueprint', 'test.json', '--override', 'environment=production'],
            catch_exceptions=False
        )
        assert result.exit_code != 0
        assert 'Invalid environment' in result.output
        assert 'production' in result.output


class TestAllowedOverrideKeys:
    """Test all allowed override keys are accepted"""

    @pytest.fixture
    def runner(self):
        """Create CLI runner"""
        return CliRunner()

    @pytest.mark.parametrize('key', [
        'environment',
        'project',
        'region',
        'team',
        'cost_center',
        'data_classification'
    ])
    def test_allowed_keys_accepted(self, runner, key):
        """Test that all allowed keys are accepted"""
        result = runner.invoke(
            cli,
            ['plan', 'preview', 'test.json', '--override', f'{key}=test-value'],
            catch_exceptions=False
        )
        # Validation should pass, command fails on missing file
        assert 'Invalid override key' not in result.output


class TestEnvironmentValues:
    """Test all valid environment values are accepted"""

    @pytest.fixture
    def runner(self):
        """Create CLI runner"""
        return CliRunner()

    @pytest.mark.parametrize('env', ['dev', 'stg', 'prd'])
    def test_valid_environments_accepted(self, runner, env):
        """Test that all valid environments are accepted"""
        result = runner.invoke(
            cli,
            ['plan', 'preview', 'test.json', '--override', f'environment={env}'],
            catch_exceptions=False
        )
        # Validation should pass, command fails on missing file
        assert 'Invalid environment' not in result.output


class TestProjectNameValidation:
    """Test project name format validation"""

    @pytest.fixture
    def runner(self):
        """Create CLI runner"""
        return CliRunner()

    @pytest.mark.parametrize('project', [
        'myproject',
        'my-project',
        'project123',
        'my-project-123',
        'a',
        '123'
    ])
    def test_valid_project_names(self, runner, project):
        """Test valid project name formats are accepted"""
        result = runner.invoke(
            cli,
            ['plan', 'preview', 'test.json', '--override', f'project={project}'],
            catch_exceptions=False
        )
        # Validation should pass, command fails on missing file
        assert 'Invalid project name' not in result.output

    @pytest.mark.parametrize('project', [
        'MyProject',           # uppercase
        'my_project',          # underscore
        'my.project',          # period
        'my project',          # space
        'my-project!',         # special char
        'my-project@',         # special char
        'my-project#'          # special char
    ])
    def test_invalid_project_names(self, runner, project):
        """Test invalid project name formats are rejected"""
        result = runner.invoke(
            cli,
            ['plan', 'preview', 'test.json', '--override', f'project={project}'],
            catch_exceptions=False
        )
        assert result.exit_code != 0
        assert 'Invalid project name' in result.output
        assert project in result.output
