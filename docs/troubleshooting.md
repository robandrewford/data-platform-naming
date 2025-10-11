# Troubleshooting Guide

Common issues and solutions for Data Platform Naming CLI.

## Configuration Issues

### Config Files Not Found

**Symptom:**
```bash
$ dpn plan preview dev.json
⚠ No configuration files found, using legacy mode
Run 'dpn config init' to create configuration files
```

**Cause:** Config files don't exist in `~/.dpn/` or specified location.

**Solution:**
```bash
# Initialize configuration
dpn config init

# Or specify custom location
dpn plan preview dev.json \
  --values-config /path/to/naming-values.yaml \
  --patterns-config /path/to/naming-patterns.yaml
```

---

### Invalid YAML Syntax

**Symptom:**
```bash
$ dpn config validate
✗ naming-values.yaml validation failed
Error: while parsing a block mapping
```

**Cause:** Syntax error in YAML file (indentation, special characters, etc.)

**Solution:**
```bash
# Check YAML syntax
yamllint ~/.dpn/naming-values.yaml

# Common issues:
# 1. Inconsistent indentation (use 2 spaces)
# 2. Missing quotes around special characters
# 3. Tabs instead of spaces
```

**Example Fix:**
```yaml
# ✗ Bad (inconsistent indentation)
defaults:
  project: test
   environment: dev  # Wrong indentation

# ✓ Good
defaults:
  project: test
  environment: dev
```

---

### Missing Required Fields

**Symptom:**
```bash
$ dpn config validate
✗ naming-values.yaml validation failed
Path: defaults
Error: 'project' is a required property
```

**Cause:** Required field missing from configuration.

**Solution:**
Add the missing required fields to `naming-values.yaml`:

```yaml
defaults:
  project: myproject      # Required
  environment: dev        # Required
  region: us-east-1       # Required
```

---

### Schema Validation Errors

**Symptom:**
```bash
$ dpn config validate
✗ naming-patterns.yaml validation failed
Path: patterns.aws_s3_bucket
Error: 'template' is a required property
```

**Cause:** Pattern definition is incomplete or malformed.

**Solution:**
Ensure all patterns have required fields:

```yaml
patterns:
  aws_s3_bucket:
    template: "{project}-{purpose}-{environment}"  # Required
    required_variables:                             # Required
      - project
      - purpose
      - environment
```

---

### Variable Not Defined in Pattern

**Symptom:**
```bash
$ dpn plan preview dev.json
✗ Preview failed: Variable 'purpose' not found in values
```

**Cause:** Pattern requires a variable that's not defined in naming-values.yaml

**Solution:**

**Option 1:** Add missing variable to naming-values.yaml
```yaml
defaults:
  project: myproject
  environment: dev
  purpose: analytics  # Add missing variable
```

**Option 2:** Override at runtime
```bash
dpn plan preview dev.json --override purpose=analytics
```

**Option 3:** Define in blueprint metadata
```json
{
  "metadata": {
    "environment": "dev",
    "project": "myproject",
    "purpose": "analytics"
  }
}
```

---

### Both Config Files Required

**Symptom:**
```bash
$ dpn plan preview dev.json --values-config custom.yaml
✗ Error: Must provide both --values-config and --patterns-config, or neither
```

**Cause:** Only one config file specified when both are required.

**Solution:**
```bash
# Provide both files
dpn plan preview dev.json \
  --values-config custom-values.yaml \
  --patterns-config custom-patterns.yaml

# Or use neither (defaults to ~/.dpn/)
dpn plan preview dev.json
```

---

## Runtime Issues

### Legacy Mode Warnings

**Symptom:**
```bash
$ dpn create --blueprint dev.json
⚠ No configuration files found, using legacy mode
✗ Create failed: NotImplementedError: use_config=True required
```

**Cause:** Generators require ConfigurationManager but no config files found.

**Solution:**
```bash
# Initialize configuration
dpn config init

# Then retry
dpn create --blueprint dev.json
```

---

### NotImplementedError: use_config Required

**Symptom:**
```bash
✗ NotImplementedError: Config-based naming required. 
  Set use_config=True and provide ConfigurationManager
```

**Cause:** Code trying to use generator without ConfigurationManager.

**Solution:**
This is typically an internal error. If you see this:

1. Ensure config files exist: `dpn config validate`
2. Check config files are valid
3. If issue persists, report as a bug

---

### Override Format Errors

**Symptom:**
```bash
$ dpn plan preview dev.json --override environment:dev
✗ Error: Invalid override format: 'environment:dev'
Use format: key=value (e.g., environment=dev)
```

**Cause:** Wrong separator in override flag.

**Solution:**
```bash
# ✗ Wrong (using colon)
dpn plan preview dev.json --override environment:dev

# ✓ Correct (using equals)
dpn plan preview dev.json --override environment=dev

# Multiple overrides
dpn plan preview dev.json \
  --override environment=dev \
  --override project=oncology
```

---

### File Permission Errors

**Symptom:**
```bash
$ dpn config init
✗ Initialization failed: [Errno 13] Permission denied: '~/.dpn'
```

**Cause:** No write permission to home directory.

**Solution:**
```bash
# Check permissions
ls -la ~ | grep .dpn

# Fix permissions
chmod 755 ~/.dpn

# Or use custom location
dpn plan preview dev.json \
  --values-config ./naming-values.yaml \
  --patterns-config ./naming-patterns.yaml
```

---

## Understanding Value Precedence

**Issue:** "My override isn't working!"

**Explanation:** Values are merged in order (lowest to highest priority):

1. **Defaults** (in naming-values.yaml)
   ```yaml
   defaults:
     environment: dev
   ```

2. **Environment overrides** (in naming-values.yaml)
   ```yaml
   environments:
     prd:
       environment: prd
   ```

3. **Resource type overrides** (in naming-values.yaml)
   ```yaml
   resource_types:
     aws_s3_bucket:
       purpose: analytics
   ```

4. **Blueprint metadata** (in blueprint JSON)
   ```json
   {
     "metadata": {
       "environment": "prd"
     }
   }
   ```

5. **Runtime overrides** (`--override` flags) - HIGHEST PRIORITY
   ```bash
   dpn plan preview dev.json --override environment=prd
   ```

**Solution:** Use `dpn config show` to see effective values:

```bash
# See all default values
dpn config show

# See values for specific resource type
dpn config show --resource-type aws_s3_bucket

# Values are merged from all sources
```

---

## Debugging Configuration

### Show Effective Configuration

```bash
# View all configuration
dpn config show

# View specific resource type
dpn config show --resource-type aws_s3_bucket

# Export as JSON for inspection
dpn config show --format json > config.json
```

### Validate Configuration Files

```bash
# Validate both files
dpn config validate

# Validate custom files
dpn config validate \
  --values-config custom-values.yaml \
  --patterns-config custom-patterns.yaml
```

### Check System Status

```bash
# View system health including config status
dpn status

# Output includes:
# - Config file locations
# - Config validation status
# - AWS/Databricks auth status
```

### Test Configuration Changes

```bash
# 1. Make changes
vim ~/.dpn/naming-values.yaml

# 2. Validate
dpn config validate

# 3. Preview (doesn't create resources)
dpn plan preview dev.json

# 4. Test with overrides
dpn plan preview dev.json --override environment=prd

# 5. Dry run
dpn create --blueprint dev.json --dry-run
```

---

## Common Solutions

### Reset Configuration

```bash
# Remove existing config
rm -rf ~/.dpn/

# Reinitialize
dpn config init

# Validate
dpn config validate
```

### Use Custom Configuration

```bash
# Keep configs in project directory
mkdir -p config/

# Initialize there (manual)
cp examples/configs/*.yaml config/

# Use with commands
dpn plan preview dev.json \
  --values-config config/naming-values.yaml \
  --patterns-config config/naming-patterns.yaml
```

### Version Control Configuration

```bash
# Add to .gitignore (if using defaults)
echo ".dpn/" >> .gitignore

# Or commit custom configs
git add config/naming-*.yaml
git commit -m "Add naming configuration"

# Team members can copy to ~/.dpn/
cp config/naming-*.yaml ~/.dpn/
```

---

## Getting Help

### Check Documentation

- **Configuration Guide**: [docs/configuration-migration-guide.md](configuration-migration-guide.md)
- **Schema Documentation**: [schemas/README.md](../schemas/README.md)
- **Examples**: [examples/configs/](../examples/configs/)

### Verbose Output

```bash
# Most commands don't have --verbose yet
# But you can check:
dpn status  # Shows system state
dpn config show  # Shows effective config
```

### Report Issues

If you encounter an issue not covered here:

1. **Check system status**: `dpn status`
2. **Validate config**: `dpn config validate`
3. **Try with fresh config**: Remove ~/.dpn/ and reinitialize
4. **Report bug**: https://github.com/robandrewford/data-platform-naming/issues

Include:
- Error message
- Command run
- Config files (if applicable)
- System info (`dpn status`)

---

## Quick Reference

### Configuration Checklist

- [ ] Config files exist: `ls ~/.dpn/`
- [ ] Config files valid: `dpn config validate`
- [ ] Variables defined: `dpn config show`
- [ ] Patterns correct: `vim ~/.dpn/naming-patterns.yaml`
- [ ] Test with preview: `dpn plan preview dev.json`
- [ ] Test with dry-run: `dpn create --blueprint dev.json --dry-run`

### Most Common Issues

1. **Config files not found** → Run `dpn config init`
2. **Invalid YAML** → Check indentation (use 2 spaces)
3. **Missing variable** → Add to naming-values.yaml or use `--override`
4. **Both configs required** → Provide both --values-config and --patterns-config
5. **Override not working** → Check precedence order

### Emergency Reset

```bash
# Nuclear option - start fresh
rm -rf ~/.dpn/
dpn config init
dpn config validate
dpn plan preview dev.json
