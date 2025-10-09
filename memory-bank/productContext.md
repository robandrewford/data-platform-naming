# Product Context

## Why This Project Exists

Data platform teams face critical naming challenges that impact operational efficiency, cost management, and governance:

- **Inconsistency**: Manual naming leads to varied patterns across environments, making resources difficult to find and manage
- **Human Error**: Typos and formatting mistakes create confusion and potential security risks
- **No Governance**: Without enforced standards, teams create ad-hoc names that don't align with organizational requirements
- **Cross-Platform Complexity**: Managing AWS and Databricks resources separately increases maintenance burden
- **Audit Trail Gaps**: Manual provisioning provides no transaction history or rollback capability

## Problems It Solves

### 1. Naming Standardization

Enforces consistent, predictable naming patterns across:

- AWS S3 buckets, Glue databases and tables
- Databricks clusters, jobs, and Unity Catalog (3-tier)
- Multiple environments (dev, stg, prd)
- Different data layers (raw, bronze, silver, gold)

### 2. Safe Resource Provisioning

- **ACID Transactions**: All-or-nothing execution prevents partial deployments
- **Preview Mode**: Dry-run capability lets teams review names before creation
- **Rollback**: Automatic recovery from failures maintains system integrity
- **Archive Option**: Soft-delete preserves resources for potential restoration

### 3. Declarative Infrastructure

- **Blueprint-Based**: JSON configuration defines desired state
- **Validation**: JSON Schema enforcement catches errors before execution
- **Dependency Resolution**: Automatic ordering of operations based on references
- **Version Control**: Blueprints live in Git for change tracking and review

### 4. Operational Efficiency

- **Batch Operations**: Provision multiple resources in a single command
- **Progress Tracking**: Real-time feedback with visual progress bars
- **Error Handling**: Clear error messages with recovery guidance
- **State Management**: Persistent state enables inspection and updates

## How It Should Work

### User Workflow

1. **Plan Phase**

   ```bash
   # Initialize blueprint with environment context
   dpn plan init --env prd --project platform --output prod.json
   
   # Validate schema compliance
   dpn plan validate prod.json
   
   # Preview all generated names
   dpn plan preview prod.json
   ```

2. **Execution Phase**

   ```bash
   # Dry run to verify operations
   dpn create --blueprint prod.json --dry-run
   
   # Execute with progress tracking
   dpn create --blueprint prod.json
   ```

3. **Management Phase**

   ```bash
   # Inspect resources
   dpn read --resource-id cluster-name --type cluster
   
   # Update configuration
   dpn update --resource-id bucket-name --params updates.json
   
   # Archive or delete
   dpn delete --resource-id old-job --type job --archive
   ```

### Core Principles

**Declarative Over Imperative**: Users describe desired state, not steps to achieve it

**Safety First**: Multiple validation layers prevent errors:

- JSON Schema validation
- Pre-execution checks
- Transactional guarantees
- Rollback on failure

**Progressive Disclosure**: Simple commands for common tasks, advanced options for complex needs

**Transparency**: Clear feedback at every step:

- What will be created (preview)
- What's happening (progress)
- What went wrong (errors)
- How to fix it (recovery)

## User Experience Goals

### Simplicity

- **Single Command Installation**: `uv sync` or `pip install`
- **Intuitive CLI**: Verb-based commands (create, read, update, delete)
- **Smart Defaults**: Minimal required parameters
- **Clear Documentation**: Examples for every use case

### Confidence

- **Preview Before Apply**: See all names before creation
- **Validation Feedback**: Catch errors early with helpful messages
- **Transaction Logging**: Full audit trail of all operations
- **Recovery Tools**: Simple commands to fix failed operations

### Flexibility

- **Multi-Environment**: Support dev, staging, production workflows
- **Multi-Platform**: Unified interface for AWS and Databricks
- **Extensible**: JSON blueprint format enables tooling integration
- **CI/CD Ready**: Non-interactive mode for automation pipelines

### Performance

- **Batch Operations**: Efficient bulk provisioning
- **Parallel Execution**: Concurrent resource creation where safe
- **Caching**: Minimize redundant API calls
- **Progress Feedback**: Real-time status updates prevent waiting uncertainty

## Success Metrics

### For Users

- Time to provision resources: < 2 minutes for typical blueprints
- Error rate: < 5% (most errors caught in validation)
- Recovery time: < 30 seconds with automated rollback
- Learning curve: Can create first blueprint in < 10 minutes

### For Teams

- Naming consistency: 100% compliance with standards
- Audit coverage: Complete transaction history
- Cross-platform alignment: Identical patterns in AWS and Databricks
- Reduced incidents: Fewer naming-related errors in production

### For Organizations

- Governance enforcement: Automated compliance with policies
- Cost attribution: Clear tagging and naming for chargeback
- Security posture: Consistent IAM and access control patterns
- Change management: Git-based workflow for all infrastructure
