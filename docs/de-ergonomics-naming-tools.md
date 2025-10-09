# Data Engineer Ergonomics: Automated Naming Convention Tools

## Executive Summary

This document outlines tools and workflows to make AWS resource naming effortless for data engineers, eliminating trial-and-error through intelligent automation, context awareness, and seamless IDE/CLI integration.

---

## 1. Core Design Principles

### 1.1 Zero Friction Adoption

- **No memorization required** - Tools guide the user
- **Context-aware suggestions** - Derive values from environment
- **Instant validation** - Real-time feedback before deployment
- **Learning through usage** - Progressive disclosure of conventions

### 1.2 Smart Defaults

- **Auto-detect environment** from AWS profile, git branch, or workspace
- **Infer domain** from project structure or team assignment
- **Generate unique identifiers** automatically (hash, index)
- **Suggest purpose** based on common patterns

---

## 2. CLI Tool: `aws-name` Command

### 2.1 Interactive Mode

```bash
# Simple interactive command
$ aws-name create s3

AWS Resource Namer - S3 Bucket
================================
? Select environment: (use arrow keys)
  ❯ dev (detected from git branch: feature/dev-sprint-42)
    tst
    stg
    prd

? Select data domain:
  ❯ sales (detected from project: sales-analytics)
    marketing
    finance
    customer
    [Enter custom domain]

? Select data layer:
  ❯ raw - Unprocessed source data
    stage - Intermediate processing
    curated - Business-ready data
    archive - Long-term storage
    logs - Operational logs

? Describe purpose (e.g., "customer orders", "daily snapshots"): customer-orders

Generated Name: acme-dev-use1-sales-raw-customer-orders-7f3a
✓ Name is valid and available
✓ Copied to clipboard

Would you like to:
  1) Create CloudFormation snippet
  2) Create Terraform resource
  3) Create boto3 code
  4) Just copy the name
  
Choice: _
```

### 2.2 Parameter-Based Mode

```bash
# Quick command with parameters
$ aws-name create s3 --domain sales --layer raw --purpose "customer-orders"
acme-dev-use1-sales-raw-customer-orders-7f3a

# Using shortcuts
$ aws-name s3 -d sales -l raw -p customer-orders
acme-dev-use1-sales-raw-customer-orders-7f3a

# Batch generation
$ aws-name batch s3 --domain sales --layers "raw,stage,curated"
acme-dev-use1-sales-raw-ingest-8b2c
acme-dev-use1-sales-stage-process-9d4e
acme-dev-use1-sales-curated-analytics-1a6f
```

### 2.3 Context Detection

```bash
# Auto-detect from current directory
$ cd ~/projects/sales-etl-pipeline
$ aws-name glue-job --auto

Detected Context:
- Company: acme (from ~/.aws-name/config)
- Environment: dev (from git branch)
- Region: use1 (from AWS_DEFAULT_REGION)
- Domain: sales (from project name)
- Source: s3 (from recent commands)
- Target: redshift (from terraform files)

Suggested name: acme-dev-sales-s3-to-redshift-load-01
Accept? (Y/n): _
```

### 2.4 Validation Mode

```bash
# Validate existing name
$ aws-name validate "acme-prod-sales-raw-data"
✗ Invalid: Missing region component
  Expected: {company}-{env}-{region}-{domain}-{layer}-{purpose}-{hash}
  Provided: {company}-{env}-{domain}-{layer}-{purpose}
  
Suggested fix: acme-prod-use1-sales-raw-data-3f2a

# Bulk validation from file
$ aws-name validate-file resource-list.txt
Validating 25 resources...
✓ 22 valid
✗ 3 invalid (see report.html for details)
```

---

## 3. IDE Extensions

### 3.1 VS Code Extension: "AWS Name Helper"

**Features:**

```typescript
// Type 'awsname' and press Tab
awsname.s3 → Interactive wizard appears

// IntelliSense suggestions
const bucketName = "acme-" // Auto-completes with valid patterns

// Real-time validation
const bucket = "acme-prd-sales" // Red underline with tooltip:
                                 // "Missing region and layer components"

// Right-click menu
"Generate AWS Resource Name" > "S3 Bucket" > Wizard opens

// Code snippets
s3name<Tab> → Expands to name generator function call
```

**Live Templates:**

```javascript
// Type 's3bucket' + Tab
const bucketName = aws.name.generate({
  service: 's3',
  domain: '${1:sales}',
  layer: '${2:raw}',
  purpose: '${3:ingestion}'
});
// Result: acme-dev-use1-sales-raw-ingestion-a4f2
```

### 3.2 JetBrains (IntelliJ/PyCharm) Plugin

```python
# Type 'awsn' + Tab for live template
bucket_name = AwsNamer.s3(
    domain="${cursor}",  # Cursor starts here
    layer="raw",
    purpose="ingestion"
)

# Automatic import added:
from aws_namer import AwsNamer

# Inspection warnings for hardcoded names:
bucket = "my-test-bucket"  # Warning: Use AwsNamer for compliance
```

---

## 4. Infrastructure as Code Integration

### 4.1 Terraform Module

```hcl
# Smart naming module
module "names" {
  source = "company/aws-naming/generator"
  
  # Auto-detected from workspace/environment
  environment = local.environment
  domain      = var.project_domain
}

# Usage - generates compliant names automatically
resource "aws_s3_bucket" "raw" {
  bucket = module.names.s3_bucket("raw", "ingestion")
  # Produces: acme-dev-use1-sales-raw-ingestion-7a3f
}

resource "aws_lambda_function" "processor" {
  function_name = module.names.lambda("s3", "transform")
  # Produces: acme-dev-sales-s3-transform-01
}

# Batch generation for data pipeline
locals {
  pipeline_buckets = module.names.s3_pipeline({
    stages = ["raw", "stage", "curated"]
    base_purpose = "customer-analytics"
  })
  # Produces map with keys: raw, stage, curated
}
```

### 4.2 CDK Construct

```typescript
import { NamingHelper } from '@company/aws-naming-cdk';

export class DataPipelineStack extends Stack {
  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);
    
    // Initialize with stack context
    const namer = new NamingHelper(this, {
      domain: 'sales',
      autoDetectEnv: true
    });
    
    // Generate names with type safety
    const rawBucket = new s3.Bucket(this, 'RawBucket', {
      bucketName: namer.s3Bucket({
        layer: DataLayer.RAW,
        purpose: 'orders'
      })
    });
    
    // Linked resource naming
    const crawler = new glue.CfnCrawler(this, 'Crawler', {
      name: namer.glueCrawler({
        source: rawBucket, // Automatically extracts context
        layer: DataLayer.RAW
      })
    });
  }
}
```

### 4.3 CloudFormation Custom Resource

```yaml
Resources:
  NamingFunction:
    Type: AWS::Lambda::Function
    Properties:
      Handler: naming.handler
      Runtime: python3.9
      Code:
        ZipFile: |
          import json
          import hashlib
          import boto3
          
          def handler(event, context):
              # Custom resource for name generation
              props = event['ResourceProperties']
              service = props['Service']
              domain = props['Domain']
              
              # Generate compliant name
              name = generate_name(service, domain, **props)
              
              return {
                  'PhysicalResourceId': name,
                  'Data': {'Name': name}
              }
  
  MyBucketName:
    Type: Custom::NameGenerator
    Properties:
      ServiceToken: !GetAtt NamingFunction.Arn
      Service: s3
      Domain: sales
      Layer: raw
      Purpose: ingestion
  
  MyBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !GetAtt MyBucketName.Name
```

---

## 5. Web-Based Tools

### 5.1 Name Generator Portal

```html
<!-- Internal web app at https://naming.company.internal -->

<AWS Resource Name Generator>

[Service Dropdown: S3 Bucket ▼]

Your Context (auto-detected):
• Team: Sales Analytics
• Environment: Development
• Region: us-east-1
• Default Domain: sales

[Generate S3 Bucket Name]
  Layer: [Raw ▼] [Stage] [Curated]
  Purpose: [________________]
  
  Preview: acme-dev-use1-sales-raw-{purpose}-{hash}
  
[Generate Name] [Copy] [Export as Code]

Recent Names (your team):
• acme-dev-use1-sales-raw-orders-7f3a ✓
• acme-dev-use1-sales-stage-transform-8b4c ✓
• acme-dev-use1-sales-curated-reports-9d5e ✓
```

### 5.2 Slack Bot Integration

```md
/aws-name s3 raw customer-data

@AWSNamer:
Generated S3 bucket name:
`acme-dev-use1-sales-raw-customer-data-3f2a`

✓ Name is valid
✓ No conflicts found
📋 Copied to your clipboard (via Slack app)

React with:
👉 📄 for CloudFormation snippet
👉 🔧 for Terraform code
👉 🐍 for Python boto3 code
```

---

## 6. Python Library: `aws-namer`

### 6.1 Installation and Basic Usage

```python
# Installation
pip install aws-namer

# Basic usage
from aws_namer import ResourceNamer

namer = ResourceNamer()  # Auto-detects context

# Simple generation
bucket_name = namer.s3_bucket(
    domain="sales",
    layer="raw",
    purpose="customer-orders"
)
print(bucket_name)  # acme-dev-use1-sales-raw-customer-orders-7a3f

# Validation
namer.validate("acme-dev-sales-raw")  # Raises ValidationError

# Batch generation
buckets = namer.create_pipeline_buckets(
    domain="sales",
    purpose="etl",
    layers=["raw", "stage", "curated"]
)
```

### 6.2 Advanced Features

```python
from aws_namer import ResourceNamer, NamingConfig
from aws_namer.decorators import enforce_naming

# Custom configuration
config = NamingConfig(
    company="acme",
    environment="dev",  # or auto_detect=True
    region="us-east-1",
    strict_mode=True
)

namer = ResourceNamer(config)

# Context manager for batch operations
with namer.domain_context("sales"):
    raw_bucket = namer.s3_bucket(layer="raw", purpose="ingest")
    stage_bucket = namer.s3_bucket(layer="stage", purpose="process")
    glue_job = namer.glue_job(source="s3", target="redshift")

# Decorator for automatic naming
@enforce_naming
def create_bucket(name: S3BucketName) -> str:
    # name is automatically validated
    s3_client.create_bucket(Bucket=name)
    return name

# Integration with boto3
import boto3
from aws_namer.boto3 import patch_boto3

# Patches boto3 to auto-generate compliant names
patch_boto3()

s3 = boto3.client('s3')
s3.create_bucket(
    BucketName=namer.auto(),  # Generates compliant name
    Domain='sales',
    Layer='raw'
)
```

### 6.3 Testing Utilities

```python
from aws_namer.testing import MockNamer, name_fixtures

# In tests - consistent, predictable names
def test_data_pipeline():
    namer = MockNamer(sequential=True)
    
    bucket1 = namer.s3_bucket("sales", "raw", "test")
    bucket2 = namer.s3_bucket("sales", "stage", "test")
    
    assert bucket1 == "acme-test-mock-sales-raw-test-0001"
    assert bucket2 == "acme-test-mock-sales-stage-test-0002"

# Fixtures for common patterns
@name_fixtures.data_pipeline("sales")
def test_with_fixtures(raw_bucket, stage_bucket, curated_bucket):
    # Pre-generated compliant names for testing
    assert "raw" in raw_bucket
    assert "stage" in stage_bucket
    assert "curated" in curated_bucket
```

---

## 7. Git Hooks and CI/CD Integration

### 7.1 Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Check for non-compliant resource names in IaC files
echo "Checking AWS resource naming compliance..."

# Scan Terraform files
aws-name scan-terraform **/*.tf
if [ $? -ne 0 ]; then
    echo "❌ Non-compliant resource names found in Terraform files"
    echo "Run 'aws-name fix-terraform' to auto-fix"
    exit 1
fi

# Scan CloudFormation templates
aws-name scan-cfn **/*.yaml **/*.json
if [ $? -ne 0 ]; then
    echo "❌ Non-compliant resource names found in CloudFormation"
    echo "Run 'aws-name fix-cfn' to auto-fix"
    exit 1
fi

echo "✅ All resource names are compliant"
```

### 7.2 GitHub Actions Workflow

```yaml
name: Validate AWS Naming
on: [push, pull_request]

jobs:
  validate-naming:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Install AWS Namer
        run: pip install aws-namer
      
      - name: Validate Terraform
        run: aws-name validate-terraform ./terraform
      
      - name: Validate CloudFormation
        run: aws-name validate-cfn ./cloudformation
      
      - name: Generate Naming Report
        if: failure()
        run: |
          aws-name report --format=markdown > naming-report.md
          cat naming-report.md >> $GITHUB_STEP_SUMMARY
      
      - name: Suggest Fixes
        if: failure()
        run: |
          aws-name suggest-fixes --format=diff
          echo "::error::Non-compliant resource names found. See suggestions above."
```

---

## 8. Auto-Generation Features

### 8.1 Hash Generation Strategy

```python
class HashGenerator:
    """Generate stable, unique 4-character hashes"""
    
    @staticmethod
    def generate(components: dict) -> str:
        """
        Generate deterministic hash from components.
        Same inputs always produce same hash.
        """
        # Stable string from sorted components
        stable_string = json.dumps(components, sort_keys=True)
        
        # SHA256 hash
        hash_obj = hashlib.sha256(stable_string.encode())
        hash_hex = hash_obj.hexdigest()
        
        # Take first 4 chars, ensure alphanumeric
        hash_4 = hash_hex[:4]
        
        # Replace any numbers that could be confused
        replacements = {'0': 'q', '1': 'p'}
        for old, new in replacements.items():
            hash_4 = hash_4.replace(old, new)
        
        return hash_4
    
    @staticmethod
    def check_collision(hash_val: str, service: str) -> bool:
        """Check if hash already exists for service"""
        # Query naming service or DynamoDB table
        return naming_service.exists(hash_val, service)
```

### 8.2 Index Auto-Increment

```python
class IndexManager:
    """Manage sequential indices for resources"""
    
    def __init__(self, backend='dynamodb'):
        self.backend = backend
        self.table = 'aws-resource-indices'
    
    def get_next_index(self, prefix: str) -> str:
        """
        Get next available index for resource prefix.
        Thread-safe, distributed-safe.
        """
        if self.backend == 'dynamodb':
            # Atomic increment in DynamoDB
            response = dynamodb.update_item(
                TableName=self.table,
                Key={'prefix': {'S': prefix}},
                UpdateExpression='ADD index_value :inc',
                ExpressionAttributeValues={':inc': {'N': '1'}},
                ReturnValues='UPDATED_NEW'
            )
            index = int(response['Attributes']['index_value']['N'])
            return f"{index:02d}"  # Zero-padded 2 digits
        
        elif self.backend == 'local':
            # File-based for development
            return self._get_local_index(prefix)
    
    def reserve_indices(self, prefix: str, count: int) -> List[str]:
        """Reserve multiple indices atomically"""
        # Implementation for batch reservation
        pass
```

---

## 9. Shell Aliases and Shortcuts

### 9.1 Bash/Zsh Configuration

```bash
# ~/.bashrc or ~/.zshrc

# Quick aliases
alias awsn='aws-name'
alias awsn-s3='aws-name create s3'
alias awsn-lambda='aws-name create lambda'
alias awsn-glue='aws-name create glue-job'

# Function for quick S3 bucket creation
create-s3() {
    local purpose=$1
    local layer=${2:-raw}
    local domain=${3:-$AWS_DEFAULT_DOMAIN}
    
    name=$(aws-name create s3 -d $domain -l $layer -p $purpose)
    echo "Creating bucket: $name"
    aws s3 mb s3://$name
}

# Auto-complete for aws-name
complete -W "create validate scan fix s3 lambda glue kinesis" aws-name

# Project-specific naming defaults
if [ -f .aws-naming ]; then
    export $(cat .aws-naming | xargs)
fi
```

### 9.2 PowerShell Configuration

```powershell
# $PROFILE

# Quick functions
function New-AWSS3Name {
    param(
        [string]$Purpose,
        [string]$Layer = "raw",
        [string]$Domain = $env:AWS_DEFAULT_DOMAIN
    )
    
    $name = aws-name create s3 -d $Domain -l $Layer -p $Purpose
    Write-Host "Generated: $name" -ForegroundColor Green
    Set-Clipboard -Value $name
    return $name
}

# Aliases
Set-Alias -Name awsn -Value aws-name
Set-Alias -Name s3name -Value New-AWSS3Name

# Tab completion
Register-ArgumentCompleter -CommandName 'aws-name' -ScriptBlock {
    param($commandName, $parameterName, $wordToComplete, $commandAst, $fakeBoundParameters)
    @('create', 'validate', 'scan', 's3', 'lambda', 'glue') | 
        Where-Object { $_ -like "$wordToComplete*" }
}
```

---

## 10. Training and Onboarding

### 10.1 Interactive Tutorial

```bash
$ aws-name tutorial

Welcome to AWS Naming Convention Tutorial!
==========================================

Let's create your first compliant resource name.

Lesson 1: S3 Buckets
--------------------
S3 buckets need globally unique names. Our convention ensures uniqueness
while maintaining organization standards.

Try creating a name for a bucket that stores raw customer data:
> aws-name create s3 --interactive

[Tutorial continues with guided examples...]
```

### 10.2 Documentation Generator

```bash
# Generate team-specific documentation
$ aws-name docs --team "sales-analytics" --format markdown

Generates:
- naming-guide-sales-analytics.md
- examples-sales-analytics.md
- quick-reference.pdf
```

---

## 11. Metrics and Adoption Tracking

### 11.1 Usage Analytics

```python
# Track adoption and common patterns
class NamingAnalytics:
    def track_generation(self, resource_type, domain, user):
        """Log each name generation for analytics"""
        cloudwatch.put_metric_data(
            Namespace='AWS/Naming',
            MetricData=[
                {
                    'MetricName': 'NamesGenerated',
                    'Value': 1,
                    'Dimensions': [
                        {'Name': 'ResourceType', 'Value': resource_type},
                        {'Name': 'Domain', 'Value': domain},
                        {'Name': 'Tool', 'Value': 'cli'}
                    ]
                }
            ]
        )
    
    def identify_patterns(self):
        """Identify common naming patterns for optimization"""
        # Analyze usage to improve defaults and suggestions
        pass
```

### 11.2 Compliance Dashboard

```sql
-- Athena query for compliance metrics
SELECT 
    DATE_TRUNC('day', created_time) as date,
    COUNT(*) as total_resources,
    SUM(CASE WHEN is_compliant THEN 1 ELSE 0 END) as compliant,
    ROUND(100.0 * SUM(CASE WHEN is_compliant THEN 1 ELSE 0 END) / COUNT(*), 2) as compliance_rate,
    array_agg(DISTINCT domain) as domains
FROM resource_naming_audit
WHERE created_time > current_date - interval '30' day
GROUP BY DATE_TRUNC('day', created_time)
ORDER BY date DESC;
```

## Conclusion

By focusing on data engineer ergonomics, we transform naming compliance from a burden into a seamless part of the development workflow. The combination of intelligent CLI tools, IDE integration, and automated validation ensures that engineers can maintain naming standards without breaking their flow or memorizing complex rules.

The key to success is meeting engineers where they work - in their terminals, IDEs, and IaC tools - with context-aware assistance that makes the right thing the easy thing.
