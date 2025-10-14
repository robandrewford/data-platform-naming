#!/usr/bin/env python3
"""
AWS Resource CRUD Executors
S3, Glue, IAM operations with rollback support
"""

import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import ClientError


@dataclass
class AWSOperationResult:
    """AWS operation result with rollback data"""
    success: bool
    resource_id: str
    rollback_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class AWSS3Executor:
    """S3 bucket operations"""

    def __init__(self, session: Optional[boto3.Session] = None):
        self.session = session or boto3.Session()
        self.s3 = self.session.client('s3')

    def create(self, operation) -> Dict[str, Any]:
        """Create S3 bucket"""
        bucket_name = operation.resource_id
        params = operation.params

        try:
            # Create bucket
            location = params.get('region', 'us-east-1')

            if location == 'us-east-1':
                self.s3.create_bucket(Bucket=bucket_name)
            else:
                self.s3.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': location}
                )

            # Versioning
            if params.get('versioning'):
                self.s3.put_bucket_versioning(
                    Bucket=bucket_name,
                    VersioningConfiguration={'Status': 'Enabled'}
                )

            # Encryption
            if params.get('encryption', True):
                self.s3.put_bucket_encryption(
                    Bucket=bucket_name,
                    ServerSideEncryptionConfiguration={
                        'Rules': [{
                            'ApplyServerSideEncryptionByDefault': {
                                'SSEAlgorithm': 'AES256'
                            }
                        }]
                    }
                )

            # Lifecycle
            if params.get('lifecycle_rules'):
                self.s3.put_bucket_lifecycle_configuration(
                    Bucket=bucket_name,
                    LifecycleConfiguration={
                        'Rules': params['lifecycle_rules']
                    }
                )

            # Tags
            if params.get('tags'):
                self.s3.put_bucket_tagging(
                    Bucket=bucket_name,
                    Tagging={'TagSet': [
                        {'Key': k, 'Value': v}
                        for k, v in params['tags'].items()
                    ]}
                )

            # Block public access
            self.s3.put_public_access_block(
                Bucket=bucket_name,
                PublicAccessBlockConfiguration={
                    'BlockPublicAcls': True,
                    'IgnorePublicAcls': True,
                    'BlockPublicPolicy': True,
                    'RestrictPublicBuckets': True
                }
            )

            return {
                'rollback_data': {
                    'bucket_name': bucket_name,
                    'region': location
                }
            }

        except ClientError as e:
            raise RuntimeError(f"S3 create failed: {e.response['Error']['Message']}")

    def read(self, operation) -> Dict[str, Any]:
        """Read S3 bucket configuration"""
        bucket_name = operation.resource_id

        try:
            config = {
                'bucket_name': bucket_name,
                'location': self.s3.get_bucket_location(Bucket=bucket_name)['LocationConstraint'],
                'versioning': self.s3.get_bucket_versioning(Bucket=bucket_name),
                'encryption': None,
                'tags': {}
            }

            # Encryption
            try:
                config['encryption'] = self.s3.get_bucket_encryption(Bucket=bucket_name)
            except ClientError:
                pass

            # Tags
            try:
                tag_response = self.s3.get_bucket_tagging(Bucket=bucket_name)
                config['tags'] = {
                    tag['Key']: tag['Value']
                    for tag in tag_response['TagSet']
                }
            except ClientError:
                pass

            return {'config': config}

        except ClientError as e:
            raise RuntimeError(f"S3 read failed: {e.response['Error']['Message']}")

    def update(self, operation) -> Dict[str, Any]:
        """Update S3 bucket configuration"""
        bucket_name = operation.resource_id
        params = operation.params

        # Store current state
        current_state = self.read(operation)

        try:
            # Update tags
            if 'tags' in params:
                self.s3.put_bucket_tagging(
                    Bucket=bucket_name,
                    Tagging={'TagSet': [
                        {'Key': k, 'Value': v}
                        for k, v in params['tags'].items()
                    ]}
                )

            # Update lifecycle
            if 'lifecycle_rules' in params:
                self.s3.put_bucket_lifecycle_configuration(
                    Bucket=bucket_name,
                    LifecycleConfiguration={'Rules': params['lifecycle_rules']}
                )

            return {'rollback_data': current_state}

        except ClientError as e:
            raise RuntimeError(f"S3 update failed: {e.response['Error']['Message']}")

    def delete(self, operation) -> Dict[str, Any]:
        """Delete S3 bucket"""
        bucket_name = operation.resource_id
        archive = operation.params.get('archive', False)

        # Store state before deletion
        current_state = self.read(operation)

        try:
            if archive:
                # Archive: disable versioning, add deletion tag
                self.s3.put_bucket_tagging(
                    Bucket=bucket_name,
                    Tagging={'TagSet': [
                        {'Key': 'Status', 'Value': 'Archived'},
                        {'Key': 'ArchivedAt', 'Value': str(int(time.time()))}
                    ]}
                )
                return {'rollback_data': current_state}

            # Empty bucket first
            self._empty_bucket(bucket_name)

            # Delete bucket
            self.s3.delete_bucket(Bucket=bucket_name)

            return {'rollback_data': current_state}

        except ClientError as e:
            raise RuntimeError(f"S3 delete failed: {e.response['Error']['Message']}")

    def rollback(self, operation) -> None:
        """Rollback S3 operation"""
        if operation.type.value == 'create':
            # Delete created bucket
            try:
                bucket_name = operation.rollback_data['bucket_name']
                self._empty_bucket(bucket_name)
                self.s3.delete_bucket(Bucket=bucket_name)
            except ClientError:
                pass

        elif operation.type.value == 'delete':
            # Recreate deleted bucket
            rollback_data = operation.rollback_data
            if rollback_data and not operation.params.get('archive'):
                # Note: Cannot restore contents without versioning
                pass

    def _empty_bucket(self, bucket_name: str) -> None:
        """Empty all objects from bucket"""
        paginator = self.s3.get_paginator('list_object_versions')

        for page in paginator.paginate(Bucket=bucket_name):
            objects = []

            # Versions
            if 'Versions' in page:
                objects.extend([
                    {'Key': obj['Key'], 'VersionId': obj['VersionId']}
                    for obj in page['Versions']
                ])

            # Delete markers
            if 'DeleteMarkers' in page:
                objects.extend([
                    {'Key': obj['Key'], 'VersionId': obj['VersionId']}
                    for obj in page['DeleteMarkers']
                ])

            if objects:
                self.s3.delete_objects(
                    Bucket=bucket_name,
                    Delete={'Objects': objects}
                )


class AWSGlueExecutor:
    """Glue database and table operations"""

    def __init__(self, session: Optional[boto3.Session] = None):
        self.session = session or boto3.Session()
        self.glue = self.session.client('glue')

    def create_database(self, operation) -> Dict[str, Any]:
        """Create Glue database"""
        db_name = operation.resource_id
        params = operation.params

        try:
            db_input = {
                'Name': db_name,
                'Description': params.get('description', ''),
            }

            if params.get('location_uri'):
                db_input['LocationUri'] = params['location_uri']

            if params.get('parameters'):
                db_input['Parameters'] = params['parameters']

            self.glue.create_database(
                DatabaseInput=db_input
            )

            return {
                'rollback_data': {
                    'database_name': db_name
                }
            }

        except ClientError as e:
            raise RuntimeError(f"Glue DB create failed: {e.response['Error']['Message']}")

    def create_table(self, operation) -> Dict[str, Any]:
        """Create Glue table"""
        table_name = operation.resource_id
        params = operation.params

        try:
            table_input = {
                'Name': table_name,
                'StorageDescriptor': {
                    'Columns': params['columns'],
                    'Location': params['location'],
                    'InputFormat': params.get('input_format', 'org.apache.hadoop.mapred.TextInputFormat'),
                    'OutputFormat': params.get('output_format', 'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat'),
                    'SerdeInfo': {
                        'SerializationLibrary': params.get('serde', 'org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe')
                    }
                }
            }

            if params.get('partition_keys'):
                table_input['PartitionKeys'] = params['partition_keys']

            if params.get('parameters'):
                table_input['Parameters'] = params['parameters']

            self.glue.create_table(
                DatabaseName=params['database_name'],
                TableInput=table_input
            )

            return {
                'rollback_data': {
                    'database_name': params['database_name'],
                    'table_name': table_name
                }
            }

        except ClientError as e:
            raise RuntimeError(f"Glue table create failed: {e.response['Error']['Message']}")

    def read_database(self, operation) -> Dict[str, Any]:
        """Read Glue database"""
        db_name = operation.resource_id

        try:
            response = self.glue.get_database(Name=db_name)
            return {'database': response['Database']}

        except ClientError as e:
            raise RuntimeError(f"Glue DB read failed: {e.response['Error']['Message']}")

    def read_table(self, operation) -> Dict[str, Any]:
        """Read Glue table"""
        params = operation.params

        try:
            response = self.glue.get_table(
                DatabaseName=params['database_name'],
                Name=operation.resource_id
            )
            return {'table': response['Table']}

        except ClientError as e:
            raise RuntimeError(f"Glue table read failed: {e.response['Error']['Message']}")

    def delete_database(self, operation) -> Dict[str, Any]:
        """Delete Glue database"""
        db_name = operation.resource_id

        # Store state
        current_state = self.read_database(operation)

        try:
            self.glue.delete_database(Name=db_name)
            return {'rollback_data': current_state}

        except ClientError as e:
            raise RuntimeError(f"Glue DB delete failed: {e.response['Error']['Message']}")

    def delete_table(self, operation) -> Dict[str, Any]:
        """Delete Glue table"""
        params = operation.params

        # Store state
        current_state = self.read_table(operation)

        try:
            self.glue.delete_table(
                DatabaseName=params['database_name'],
                Name=operation.resource_id
            )
            return {'rollback_data': current_state}

        except ClientError as e:
            raise RuntimeError(f"Glue table delete failed: {e.response['Error']['Message']}")

    def rollback_database(self, operation) -> None:
        """Rollback database operation"""
        if operation.type.value == 'create':
            try:
                self.glue.delete_database(
                    Name=operation.rollback_data['database_name']
                )
            except ClientError:
                pass

    def rollback_table(self, operation) -> None:
        """Rollback table operation"""
        if operation.type.value == 'create':
            try:
                self.glue.delete_table(
                    DatabaseName=operation.rollback_data['database_name'],
                    Name=operation.rollback_data['table_name']
                )
            except ClientError:
                pass


class AWSExecutorRegistry:
    """Central AWS executor registry"""

    def __init__(self, session: Optional[boto3.Session] = None):
        self.session = session or boto3.Session()

        self.s3 = AWSS3Executor(self.session)
        self.glue = AWSGlueExecutor(self.session)

        # Executor map
        self.executors = {
            'aws_s3_bucket': {
                'create': self.s3.create,
                'read': self.s3.read,
                'update': self.s3.update,
                'delete': self.s3.delete,
                'rollback': self.s3.rollback
            },
            'aws_glue_database': {
                'create': self.glue.create_database,
                'read': self.glue.read_database,
                'delete': self.glue.delete_database,
                'rollback': self.glue.rollback_database
            },
            'aws_glue_table': {
                'create': self.glue.create_table,
                'read': self.glue.read_table,
                'delete': self.glue.delete_table,
                'rollback': self.glue.rollback_table
            }
        }

    def execute(self, operation) -> Dict[str, Any]:
        """Execute operation"""
        resource_type = operation.resource_type.value
        operation_type = operation.type.value

        if resource_type not in self.executors:
            raise ValueError(f"Unsupported resource: {resource_type}")

        if operation_type not in self.executors[resource_type]:
            raise ValueError(f"Unsupported operation: {operation_type}")

        return self.executors[resource_type][operation_type](operation)

    def rollback(self, operation) -> None:
        """Rollback operation"""
        resource_type = operation.resource_type.value

        if resource_type in self.executors:
            self.executors[resource_type]['rollback'](operation)


# Example usage
if __name__ == "__main__":
    import uuid

    from transaction_manager import Operation, OperationType, ResourceType

    registry = AWSExecutorRegistry()

    # Create S3 bucket
    op = Operation(
        id=str(uuid.uuid4()),
        type=OperationType.CREATE,
        resource_type=ResourceType.AWS_S3_BUCKET,
        resource_id="dataplatform-raw-prd-useast1",
        params={
            'region': 'us-east-1',
            'versioning': True,
            'encryption': True,
            'tags': {
                'Environment': 'prd',
                'Project': 'dataplatform'
            }
        }
    )

    result = registry.execute(op)
    print(f"Created: {result}")
