# AWS Data Platform Naming Convention Specification v1.0

## Executive Summary

This specification defines the naming convention standards for all AWS data platform resources. The convention follows a **hierarchical, domain-driven approach** using **kebab-case** as the primary naming style, ensuring consistency, scalability, and operational excellence across the platform.

---

## 1. Core Naming Pattern

### 1.1 Universal Pattern Structure

```
{company}-{env}-{region}-{domain}-{service}-{function}-{index}-{hash}
```

**Pattern Components:**
- `{company}`: 3-5 character company/business unit abbreviation
- `{env}`: Environment identifier (dev/tst/stg/prd)
- `{region}`: AWS region code (use1/usw2/euc1)
- `{domain}`: Data domain or business area (3-15 characters)
- `{service}`: AWS service abbreviation
- `{function}`: Resource function/purpose (5-20 characters)
- `{index}`: Numeric index for multiple instances (01, 02, etc.)
- `{hash}`: Optional 4-character unique suffix for global resources

### 1.2 Naming Style Rules

- **Primary Style**: kebab-case (lowercase with hyphens)
- **No underscores** in resource names (except where required by service)
- **No special characters** beyond hyphens
- **Maximum length**: Service-specific, but design for 63 characters
- **Minimum length**: 15 characters for traceability

---

## 2. Service-Specific Patterns

### 2.1 S3 Buckets
```
Pattern: {company}-{env}-{region}-{domain}-{layer}-{purpose}-{hash}
Example: acme-prd-use1-sales-raw-ingestion-a7b2
```

**Layer Values:**
- `raw`: Unprocessed source data
- `stage`: Intermediate processing
- `curated`: Business-ready data
- `archive`: Long-term storage
- `logs`: Operational logs

### 2.2 Glue Resources

**Glue Jobs:**
```
Pattern: {company}-{env}-{domain}-{source}-to-{target}-{action}-{index}
Example: acme-prd-sales-s3-to-redshift-load-01
```

**Glue Crawlers:**
```
Pattern: {company}-{env}-{domain}-{layer}-{source}-crawler-{index}
Example: acme-prd-sales-raw-rds-crawler-01
```

**Glue Catalog Databases:**
```
Pattern: {company}_{env}_{domain}_{layer}_db
Example: acme_prd_sales_curated_db
Note: Underscores required for Athena compatibility
```

**Glue Catalog Tables:**
```
Pattern: {domain}_{entity}_{version}
Example: sales_transactions_v1
```

### 2.3 Lambda Functions
```
Pattern: {company}-{env}-{domain}-{trigger}-{action}-{index}
Example: acme-prd-sales-s3-process-01
```

### 2.4 Kinesis Streams
```
Pattern: {company}-{env}-{domain}-{source}-stream-{index}
Example: acme-prd-sales-pos-stream-01
```

### 2.5 EMR Clusters
```
Pattern: {company}-{env}-{domain}-{workload}-emr-{date}
Example: acme-prd-analytics-spark-emr-20250913
```

### 2.6 Redshift Resources

**Clusters:**
```
Pattern: {company}-{env}-{domain}-rs-{index}
Example: acme-prd-analytics-rs-01
```

**Schemas:**
```
Pattern: {domain}_{layer}
Example: sales_curated
```

### 2.7 DMS Resources

**Replication Instances:**
```
Pattern: {company}-{env}-dms-{source}-to-{target}-{index}
Example: acme-prd-dms-oracle-to-s3-01
```

**Endpoints:**
```
Pattern: {company}-{env}-{system}-{type}-ep
Example: acme-prd-erp-source-ep
```

**Tasks:**
```
Pattern: {company}-{env}-{source}-{target}-{table}-task
Example: acme-prd-oracle-s3-customers-task
```

### 2.8 Step Functions
```
Pattern: {company}-{env}-{domain}-{workflow}-sf-{index}
Example: acme-prd-sales-etl-pipeline-sf-01
```

### 2.9 EventBridge Rules
```
Pattern: {company}-{env}-{domain}-{trigger}-{action}-rule
Example: acme-prd-sales-s3-glue-trigger-rule
```

### 2.10 Athena Resources

**Workgroups:**
```
Pattern: {company}-{env}-{domain}-{team}-wg
Example: acme-prd-analytics-data-science-wg
```

**Named Queries:**
```
Pattern: {domain}-{report}-{frequency}-query
Example: sales-revenue-daily-query
```

---

## 3. Metadata Components

### 3.1 Company Abbreviations
```
Examples:
- acme: Acme Corporation
- rsm: Resource Management Inc
- finc: Financial Corp
```

### 3.2 Environment Codes
```
Required Values:
- dev: Development
- tst: Testing
- stg: Staging
- prd: Production
- sbx: Sandbox (optional)
- dr: Disaster Recovery (optional)
```

### 3.3 Region Codes
```
Mapping:
- use1: us-east-1 (N. Virginia)
- use2: us-east-2 (Ohio)
- usw1: us-west-1 (N. California)
- usw2: us-west-2 (Oregon)
- euc1: eu-central-1 (Frankfurt)
- euw1: eu-west-1 (Ireland)
- aps1: ap-southeast-1 (Singapore)
- apne1: ap-northeast-1 (Tokyo)
```

### 3.4 Service Abbreviations
```
Standard Mappings:
- s3: S3 Bucket
- lambda: Lambda Function
- glue: Glue Job/Crawler
- rs: Redshift
- rds: RDS Database
- dms: Database Migration Service
- kinesis: Kinesis Stream
- emr: EMR Cluster
- sf: Step Functions
- eb: EventBridge
- sns: SNS Topic
- sqs: SQS Queue
```

### 3.5 Data Domains
```
Examples (customize per organization):
- sales: Sales data
- marketing: Marketing data
- finance: Financial data
- customer: Customer data
- product: Product catalog
- inventory: Inventory management
- hr: Human resources
- ops: Operations
```

---

## 4. Resource Tagging Standards

### 4.1 Required Tags

All resources MUST include these tags:

```yaml
Environment: {dev|tst|stg|prd}
Domain: {data-domain}
Owner: {team-email}
CostCenter: {cost-center-code}
Project: {project-identifier}
CreatedDate: {YYYY-MM-DD}
CreatedBy: {creator-email}
ManagedBy: {terraform|cloudformation|console|cdk}
```

### 4.2 Optional Tags

```yaml
DataClassification: {public|internal|confidential|restricted}
Compliance: {pci|hipaa|gdpr|sox}
BackupPolicy: {daily|weekly|monthly|none}
RetentionDays: {number}
Version: {semantic-version}
```

### 4.3 Tag Naming Rules

- Use **PascalCase** for tag keys
- Use **lowercase** for tag values (except emails/URLs)
- Maximum 50 tags per resource
- Tag keys: 1-128 characters
- Tag values: 0-256 characters

---

## 5. Billing and Cost Management

### 5.1 Cost Allocation Pattern

Include in resource names for Cost Explorer visibility:
```
{company}-{cost-center}-{env}-{project}-{service}-{function}
Example: acme-cc1001-prd-datalake-s3-raw
```

### 5.2 Cost Tags

Activate these tags for AWS Cost Allocation:
- `CostCenter`
- `Project`
- `Environment`
- `Owner`
- `Domain`

---

## 6. CloudFormation Guard Rules

### 6.1 Basic Guard Rule Set

```ruby
# AWS CloudFormation Guard Rules for Naming Convention
# Version: 1.0
# Last Updated: 2024-12-20

# Rule 1: S3 Bucket Naming Convention
rule s3_bucket_naming_convention {
  when {
    resourceType == "AWS::S3::Bucket"
  }
  assert {
    BucketName exists
    BucketName is_string
    BucketName regex_match "^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$"
    BucketName regex_match "^(acme|rsm|finc)-(dev|tst|stg|prd|sbx|dr)-[a-z0-9-]+"
  }
  violation_message "S3 bucket names must follow pattern: {company}-{env}-{region}-{domain}-{layer}-{purpose}"
}

# Rule 2: Lambda Function Naming Convention
rule lambda_function_naming_convention {
  when {
    resourceType == "AWS::Lambda::Function"
  }
  assert {
    FunctionName exists
    FunctionName is_string
    FunctionName regex_match "^[a-zA-Z0-9-_]{1,64}$"
    FunctionName regex_match "^(acme|rsm|finc)-(dev|tst|stg|prd|sbx|dr)-[a-z0-9-]+"
  }
  violation_message "Lambda function names must follow pattern: {company}-{env}-{domain}-{trigger}-{action}"
}

# Rule 3: Glue Job Naming Convention
rule glue_job_naming_convention {
  when {
    resourceType == "AWS::Glue::Job"
  }
  assert {
    Name exists
    Name is_string
    Name regex_match "^[a-zA-Z0-9-_]{1,255}$"
    Name regex_match "^(acme|rsm|finc)-(dev|tst|stg|prd|sbx|dr)-[a-z0-9-]+-to-[a-z0-9-]+"
  }
  violation_message "Glue job names must follow pattern: {company}-{env}-{domain}-{source}-to-{target}-{action}"
}

# Rule 4: Required Tags Validation
rule required_tags {
  when {
    Tags exists
  }
  assert {
    Tags[?Key == 'Environment'] not empty
    Tags[?Key == 'Domain'] not empty
    Tags[?Key == 'Owner'] not empty
    Tags[?Key == 'CostCenter'] not empty
    Tags[?Key == 'Project'] not empty
    Tags[?Key == 'CreatedDate'] not empty
    Tags[?Key == 'CreatedBy'] not empty
    Tags[?Key == 'ManagedBy'] not empty
  }
  violation_message "All resources must have required tags: Environment, Domain, Owner, CostCenter, Project, CreatedDate, CreatedBy, ManagedBy"
}

# Rule 5: Environment Tag Values
rule environment_tag_values {
  when {
    Tags exists
    Tags[?Key == 'Environment'] exists
  }
  assert {
    Tags[?Key == 'Environment'].Value in ['dev', 'tst', 'stg', 'prd', 'sbx', 'dr']
  }
  violation_message "Environment tag must be one of: dev, tst, stg, prd, sbx, dr"
}

# Rule 6: Redshift Cluster Naming
rule redshift_cluster_naming {
  when {
    resourceType == "AWS::Redshift::Cluster"
  }
  assert {
    ClusterIdentifier exists
    ClusterIdentifier regex_match "^[a-z][a-z0-9-]{0,62}$"
    ClusterIdentifier regex_match "^(acme|rsm|finc)-(dev|tst|stg|prd|sbx|dr)-[a-z0-9-]+-rs-[0-9]{2}$"
  }
  violation_message "Redshift cluster names must follow pattern: {company}-{env}-{domain}-rs-{index}"
}

# Rule 7: Kinesis Stream Naming
rule kinesis_stream_naming {
  when {
    resourceType == "AWS::Kinesis::Stream"
  }
  assert {
    Name exists
    Name regex_match "^[a-zA-Z0-9_.-]{1,128}$"
    Name regex_match "^(acme|rsm|finc)-(dev|tst|stg|prd|sbx|dr)-[a-z0-9-]+-stream-[0-9]{2}$"
  }
  violation_message "Kinesis stream names must follow pattern: {company}-{env}-{domain}-{source}-stream-{index}"
}

# Rule 8: SNS Topic Naming
rule sns_topic_naming {
  when {
    resourceType == "AWS::SNS::Topic"
  }
  assert {
    TopicName exists
    TopicName regex_match "^[a-zA-Z0-9_-]{1,256}$"
    TopicName regex_match "^(acme|rsm|finc)-(dev|tst|stg|prd|sbx|dr)-[a-z0-9-]+-topic"
  }
  violation_message "SNS topic names must follow pattern: {company}-{env}-{domain}-{purpose}-topic"
}

# Rule 9: SQS Queue Naming
rule sqs_queue_naming {
  when {
    resourceType == "AWS::SQS::Queue"
  }
  assert {
    QueueName exists
    QueueName regex_match "^[a-zA-Z0-9_-]{1,80}$"
    QueueName regex_match "^(acme|rsm|finc)-(dev|tst|stg|prd|sbx|dr)-[a-z0-9-]+-queue"
  }
  violation_message "SQS queue names must follow pattern: {company}-{env}-{domain}-{purpose}-queue"
}

# Rule 10: No Hardcoded Secrets in Names
rule no_secrets_in_names {
  when {
    * exists
  }
  assert {
    * not regex_match "(?i)(password|pwd|secret|key|token|api)"
  }
  violation_message "Resource names must not contain sensitive information like passwords or keys"
}
```

### 6.2 Advanced Guard Rules

```ruby
# Advanced CloudFormation Guard Rules

# Rule 11: Cross-Resource Naming Consistency
rule cross_resource_consistency {
  let all_names = Resources.*.Properties.Name
  when {
    all_names not empty
  }
  assert {
    all_names[*] regex_match "^(acme|rsm|finc)-(dev|tst|stg|prd|sbx|dr)-"
  }
  violation_message "All named resources must start with {company}-{env}-"
}

# Rule 12: Data Classification Tag Required for S3
rule s3_data_classification {
  when {
    resourceType == "AWS::S3::Bucket"
  }
  assert {
    Tags[?Key == 'DataClassification'] exists
    Tags[?Key == 'DataClassification'].Value in ['public', 'internal', 'confidential', 'restricted']
  }
  violation_message "S3 buckets must have DataClassification tag with value: public, internal, confidential, or restricted"
}

# Rule 13: Production Resource Protection
rule production_resource_naming {
  when {
    * regex_match ".*-prd-.*"
  }
  assert {
    Tags[?Key == 'Environment'].Value == 'prd'
    Tags[?Key == 'Owner'] exists
    Tags[?Key == 'Owner'].Value regex_match "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
  }
  violation_message "Production resources must have matching Environment tag and valid Owner email"
}

# Rule 14: Glue Catalog Database Naming
rule glue_database_naming {
  when {
    resourceType == "AWS::Glue::Database"
  }
  assert {
    DatabaseInput.Name exists
    DatabaseInput.Name regex_match "^[a-z0-9_]{1,252}$"
    DatabaseInput.Name regex_match "^(acme|rsm|finc)_(dev|tst|stg|prd|sbx|dr)_[a-z0-9_]+_db$"
  }
  violation_message "Glue database names must follow pattern: {company}_{env}_{domain}_{layer}_db"
}

# Rule 15: Date Format Validation
rule created_date_format {
  when {
    Tags[?Key == 'CreatedDate'] exists
  }
  assert {
    Tags[?Key == 'CreatedDate'].Value regex_match "^[0-9]{4}-[0-9]{2}-[0-9]{2}$"
  }
  violation_message "CreatedDate tag must be in YYYY-MM-DD format"
}
```

---

## 7. Implementation Checklist

### 7.1 Week 1 Tasks

- [ ] Review and customize company abbreviations
- [ ] Define data domain list
- [ ] Configure AWS Config rules based on Guard rules
- [ ] Create naming convention documentation in Wiki/Confluence
- [ ] Set up CloudFormation Guard CLI tools

### 7.2 Week 2 Tasks

- [ ] Deploy Guard rules to CI/CD pipeline
- [ ] Create example CloudFormation templates
- [ ] Develop training materials
- [ ] Configure Cost Allocation tags
- [ ] Create automated validation scripts

---

## 8. Validation Tools

### 8.1 CLI Validation Script

```bash
#!/bin/bash
# validate-naming.sh - Validate resource naming

validate_s3_name() {
    local name=$1
    if [[ $name =~ ^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$ ]] && \
       [[ $name =~ ^(acme|rsm|finc)-(dev|tst|stg|prd|sbx|dr)- ]]; then
        echo "✓ Valid S3 bucket name: $name"
        return 0
    else
        echo "✗ Invalid S3 bucket name: $name"
        return 1
    fi
}

validate_lambda_name() {
    local name=$1
    if [[ $name =~ ^[a-zA-Z0-9-_]{1,64}$ ]] && \
       [[ $name =~ ^(acme|rsm|finc)-(dev|tst|stg|prd|sbx|dr)- ]]; then
        echo "✓ Valid Lambda function name: $name"
        return 0
    else
        echo "✗ Invalid Lambda function name: $name"
        return 1
    fi
}

# Usage
validate_s3_name "acme-prd-use1-sales-raw-ingestion-a7b2"
validate_lambda_name "acme-prd-sales-s3-process-01"
```

### 8.2 Python Validation Library

```python
# naming_validator.py

import re
from typing import Dict, List, Tuple, Optional
from enum import Enum

class Environment(Enum):
    DEV = "dev"
    TEST = "tst"
    STAGE = "stg"
    PROD = "prd"
    SANDBOX = "sbx"
    DR = "dr"

class AWSService(Enum):
    S3 = "s3"
    LAMBDA = "lambda"
    GLUE = "glue"
    REDSHIFT = "rs"
    KINESIS = "kinesis"

class NamingValidator:
    def __init__(self, company_codes: List[str]):
        self.company_codes = company_codes
        self.env_pattern = "|".join([e.value for e in Environment])
        self.company_pattern = "|".join(company_codes)
    
    def validate_s3_bucket(self, name: str) -> Tuple[bool, Optional[str]]:
        """Validate S3 bucket naming convention."""
        # Check AWS constraints
        if not re.match(r'^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$', name):
            return False, "S3 name must be 3-63 chars, lowercase, start/end with alphanumeric"
        
        # Check naming convention
        pattern = f'^({self.company_pattern})-({self.env_pattern})-[a-z0-9-]+-(raw|stage|curated|archive|logs)-[a-z0-9-]+'
        if not re.match(pattern, name):
            return False, f"Must follow pattern: {{company}}-{{env}}-{{region}}-{{domain}}-{{layer}}-{{purpose}}"
        
        return True, None
    
    def validate_lambda_function(self, name: str) -> Tuple[bool, Optional[str]]:
        """Validate Lambda function naming convention."""
        # Check AWS constraints
        if not re.match(r'^[a-zA-Z0-9-_]{1,64}$', name):
            return False, "Lambda name must be 1-64 chars, alphanumeric, hyphens, underscores"
        
        # Check naming convention
        pattern = f'^({self.company_pattern})-({self.env_pattern})-[a-z0-9-]+-[a-z0-9-]+-[0-9]{{2}}$'
        if not re.match(pattern, name):
            return False, f"Must follow pattern: {{company}}-{{env}}-{{domain}}-{{trigger}}-{{action}}-{{index}}"
        
        return True, None
    
    def parse_resource_name(self, name: str) -> Dict[str, str]:
        """Parse resource name into components."""
        parts = name.split('-')
        
        if len(parts) < 4:
            return {}
        
        return {
            'company': parts[0],
            'environment': parts[1],
            'region': parts[2] if len(parts) > 2 else None,
            'domain': parts[3] if len(parts) > 3 else None,
            'remainder': '-'.join(parts[4:]) if len(parts) > 4 else None
        }

# Usage Example
validator = NamingValidator(['acme', 'rsm', 'finc'])

# Validate S3 bucket
is_valid, error = validator.validate_s3_bucket("acme-prd-use1-sales-raw-ingestion")
print(f"Valid: {is_valid}, Error: {error}")

# Parse resource name
components = validator.parse_resource_name("acme-prd-use1-sales-raw-ingestion")
print(f"Components: {components}")
```

---

## 9. Exception Handling

### 9.1 Legacy Resource Migration

For existing resources that cannot be renamed:
1. Add `Legacy: true` tag
2. Document in exception registry
3. Plan migration timeline
4. Use aliases where possible

### 9.2 Third-Party Integration Requirements

When external systems require specific naming:
1. Document exception with business justification
2. Add `ExternalConstraint: {system}` tag
3. Maintain mapping table
4. Use proxy resources where feasible

---

## 10. Governance and Review

### 10.1 Quarterly Review Process

- Review naming convention effectiveness
- Analyze compliance metrics
- Update for new AWS services
- Refine based on operational feedback

### 10.2 Change Management

All naming convention changes require:
1. Impact assessment
2. Stakeholder approval
3. Migration plan for existing resources
4. Update to automation tools
5. Team training

### 10.3 Compliance Metrics

Track monthly:
- Naming convention compliance rate (target: >95%)
- Cost allocation tag coverage (target: 100%)
- Automated validation success rate
- Exception count and trends

---

## Appendix A: Quick Reference Card

```
S3:        {co}-{env}-{reg}-{dom}-{layer}-{purpose}-{hash}
Lambda:    {co}-{env}-{dom}-{trigger}-{action}-{idx}
Glue Job:  {co}-{env}-{dom}-{src}-to-{tgt}-{action}-{idx}
Kinesis:   {co}-{env}-{dom}-{source}-stream-{idx}
Redshift:  {co}-{env}-{dom}-rs-{idx}
DMS:       {co}-{env}-dms-{src}-to-{tgt}-{idx}

Environments: dev | tst | stg | prd | sbx | dr
Regions: use1 | use2 | usw1 | usw2 | euc1 | euw1
Layers: raw | stage | curated | archive | logs
```

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2024-12-20 | Data Architecture Team | Initial specification |

---

**Document Status:** DRAFT - Pending Review
**Next Review Date:** 2025-01-20
**Owner:** Data Platform Team
**Contact:** data-platform@company.com