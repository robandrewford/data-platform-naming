#!/usr/bin/env python3
"""
Databricks Resource CRUD Executors
Clusters, Jobs, Unity Catalog operations with rollback support
"""

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, Optional

import requests

if TYPE_CHECKING:
    from .transaction_manager import Operation


@dataclass
class DatabricksConfig:
    """Databricks connection configuration"""
    host: Optional[str]  # https://your-workspace.cloud.databricks.com
    token: Optional[str]

    @property
    def headers(self) -> Dict[str, str]:
        return {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }


class DatabricksAPIError(Exception):
    """Databricks API error"""
    pass


class DatabricksClusterExecutor:
    """Databricks cluster operations"""

    def __init__(self, config: DatabricksConfig):
        self.config = config
        self.base_url = f"{config.host}/api/2.0"

    def create(self, operation: "Operation") -> Dict[str, Any]:
        """Create cluster"""
        cluster_name = operation.resource_id
        params = operation.params

        cluster_spec = {
            'cluster_name': cluster_name,
            'spark_version': params['spark_version'],
            'node_type_id': params['node_type'],
            'autoscale': params.get('autoscale', {
                'min_workers': 2,
                'max_workers': 8
            }),
            'autotermination_minutes': params.get('autotermination_minutes', 120),
        }

        # Cluster type
        if params.get('driver_node_type'):
            cluster_spec['driver_node_type_id'] = params['driver_node_type']

        # Custom tags
        if params.get('tags'):
            cluster_spec['custom_tags'] = params['tags']

        # Spark config
        if params.get('spark_conf'):
            cluster_spec['spark_conf'] = params['spark_conf']

        # Instance pool
        if params.get('instance_pool_id'):
            cluster_spec['instance_pool_id'] = params['instance_pool_id']

        # AWS attributes
        if params.get('aws_attributes'):
            cluster_spec['aws_attributes'] = params['aws_attributes']

        try:
            response = requests.post(
                f"{self.base_url}/clusters/create",
                headers=self.config.headers,
                json=cluster_spec
            )
            response.raise_for_status()

            result = response.json()
            cluster_id = result['cluster_id']

            # Wait for cluster to be running
            if params.get('wait_for_ready', False):
                self._wait_for_cluster(cluster_id, 'RUNNING')

            return {
                'rollback_data': {
                    'cluster_id': cluster_id,
                    'cluster_name': cluster_name
                }
            }

        except requests.exceptions.RequestException as e:
            raise DatabricksAPIError(f"Cluster create failed: {str(e)}")

    def read(self, operation: "Operation") -> Dict[str, Any]:
        """Read cluster configuration"""
        cluster_id = operation.params.get('cluster_id')

        if not cluster_id:
            # Find by name
            cluster_id = self._find_cluster_by_name(operation.resource_id)

        try:
            response = requests.get(
                f"{self.base_url}/clusters/get",
                headers=self.config.headers,
                params={'cluster_id': cluster_id}
            )
            response.raise_for_status()

            return {'cluster': response.json()}

        except requests.exceptions.RequestException as e:
            raise DatabricksAPIError(f"Cluster read failed: {str(e)}")

    def update(self, operation: "Operation") -> Dict[str, Any]:
        """Update cluster configuration"""
        cluster_id = operation.params['cluster_id']

        # Get current state
        current_state = self.read(operation)

        # Build update spec
        update_spec = {
            'cluster_id': cluster_id
        }

        # Update fields
        if 'autoscale' in operation.params:
            update_spec['autoscale'] = operation.params['autoscale']

        if 'autotermination_minutes' in operation.params:
            update_spec['autotermination_minutes'] = operation.params['autotermination_minutes']

        if 'tags' in operation.params:
            update_spec['custom_tags'] = operation.params['tags']

        try:
            response = requests.post(
                f"{self.base_url}/clusters/edit",
                headers=self.config.headers,
                json=update_spec
            )
            response.raise_for_status()

            return {'rollback_data': current_state}

        except requests.exceptions.RequestException as e:
            raise DatabricksAPIError(f"Cluster update failed: {str(e)}")

    def delete(self, operation: "Operation") -> Dict[str, Any]:
        """Delete cluster"""
        cluster_id: Optional[str] = operation.params.get('cluster_id')
        archive = operation.params.get('archive', False)

        if not cluster_id:
            cluster_id = self._find_cluster_by_name(operation.resource_id)

        # Get current state
        current_state = self.read(operation)

        try:
            if archive:
                # Archive: add archive tag
                self.update(Operation(
                    id=operation.id,
                    type=operation.type,
                    resource_type=operation.resource_type,
                    resource_id=operation.resource_id,
                    params={
                        'cluster_id': cluster_id,
                        'tags': {
                            'Status': 'Archived',
                            'ArchivedAt': str(int(time.time()))
                        }
                    }
                ))
            else:
                # Permanent delete
                response = requests.post(
                    f"{self.base_url}/clusters/permanent-delete",
                    headers=self.config.headers,
                    json={'cluster_id': cluster_id}
                )
                response.raise_for_status()

            return {'rollback_data': current_state}

        except requests.exceptions.RequestException as e:
            raise DatabricksAPIError(f"Cluster delete failed: {str(e)}")

    def rollback(self, operation: "Operation") -> None:
        """Rollback cluster operation"""
        if operation.type.value == 'create':
            try:
                if operation.rollback_data is None:
                    raise ValueError("Rollback data is None for create operation")
                cluster_id = operation.rollback_data['cluster_id']
                requests.post(
                    f"{self.base_url}/clusters/permanent-delete",
                    headers=self.config.headers,
                    json={'cluster_id': cluster_id}
                )
            except Exception:
                pass

    def _find_cluster_by_name(self, name: str) -> str:
        """Find cluster ID by name"""
        response = requests.get(
            f"{self.base_url}/clusters/list",
            headers=self.config.headers
        )
        response.raise_for_status()

        clusters: list[dict[str, Any]] = response.json().get('clusters', [])
        for cluster in clusters:
            if cluster['cluster_name'] == name:
                return str(cluster['cluster_id'])

        raise DatabricksAPIError(f"Cluster not found: {name}")

    def _wait_for_cluster(self, cluster_id: str, target_state: str, timeout: int = 600):
        """Wait for cluster to reach target state"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            response = requests.get(
                f"{self.base_url}/clusters/get",
                headers=self.config.headers,
                params={'cluster_id': cluster_id}
            )

            if response.status_code == 200:
                state = response.json().get('state')
                if state == target_state:
                    return

            time.sleep(10)

        raise DatabricksAPIError(f"Timeout waiting for cluster {target_state}")


class DatabricksJobExecutor:
    """Databricks job operations"""

    def __init__(self, config: DatabricksConfig):
        self.config = config
        self.base_url = f"{config.host}/api/2.1"

    def create(self, operation: "Operation") -> Dict[str, Any]:
        """Create job"""
        job_name = operation.resource_id
        params = operation.params

        job_spec = {
            'name': job_name,
            'tasks': params['tasks'],
            'job_clusters': params.get('job_clusters', []),
            'schedule': params.get('schedule'),
            'max_concurrent_runs': params.get('max_concurrent_runs', 1),
        }

        # Timeout
        if params.get('timeout_seconds'):
            job_spec['timeout_seconds'] = params['timeout_seconds']

        # Tags
        if params.get('tags'):
            job_spec['tags'] = params['tags']

        # Email notifications
        if params.get('email_notifications'):
            job_spec['email_notifications'] = params['email_notifications']

        try:
            response = requests.post(
                f"{self.base_url}/jobs/create",
                headers=self.config.headers,
                json=job_spec
            )
            response.raise_for_status()

            result = response.json()
            job_id = result['job_id']

            return {
                'rollback_data': {
                    'job_id': job_id,
                    'job_name': job_name
                }
            }

        except requests.exceptions.RequestException as e:
            raise DatabricksAPIError(f"Job create failed: {str(e)}")

    def read(self, operation: "Operation") -> Dict[str, Any]:
        """Read job configuration"""
        job_id = operation.params.get('job_id')

        if not job_id:
            job_id = self._find_job_by_name(operation.resource_id)

        try:
            response = requests.get(
                f"{self.base_url}/jobs/get",
                headers=self.config.headers,
                params={'job_id': job_id}
            )
            response.raise_for_status()

            return {'job': response.json()}

        except requests.exceptions.RequestException as e:
            raise DatabricksAPIError(f"Job read failed: {str(e)}")

    def update(self, operation: "Operation") -> Dict[str, Any]:
        """Update job configuration"""
        job_id = operation.params['job_id']

        # Get current state
        current_state = self.read(operation)

        # Build update spec
        update_spec = {
            'job_id': job_id,
            'new_settings': {}
        }

        # Update fields
        if 'tasks' in operation.params:
            update_spec['new_settings']['tasks'] = operation.params['tasks']

        if 'schedule' in operation.params:
            update_spec['new_settings']['schedule'] = operation.params['schedule']

        if 'tags' in operation.params:
            update_spec['new_settings']['tags'] = operation.params['tags']

        try:
            response = requests.post(
                f"{self.base_url}/jobs/update",
                headers=self.config.headers,
                json=update_spec
            )
            response.raise_for_status()

            return {'rollback_data': current_state}

        except requests.exceptions.RequestException as e:
            raise DatabricksAPIError(f"Job update failed: {str(e)}")

    def delete(self, operation: "Operation") -> Dict[str, Any]:
        """Delete job"""
        job_id = operation.params.get('job_id')

        if not job_id:
            job_id = self._find_job_by_name(operation.resource_id)

        # Get current state
        current_state = self.read(operation)

        try:
            response = requests.post(
                f"{self.base_url}/jobs/delete",
                headers=self.config.headers,
                json={'job_id': job_id}
            )
            response.raise_for_status()

            return {'rollback_data': current_state}

        except requests.exceptions.RequestException as e:
            raise DatabricksAPIError(f"Job delete failed: {str(e)}")

    def rollback(self, operation: "Operation") -> None:
        """Rollback job operation"""
        if operation.type.value == 'create':
            try:
                if operation.rollback_data is None:
                    raise ValueError("Rollback data is None for create operation")
                job_id = operation.rollback_data['job_id']
                requests.post(
                    f"{self.base_url}/jobs/delete",
                    headers=self.config.headers,
                    json={'job_id': job_id}
                )
            except Exception:
                pass

    def _find_job_by_name(self, name: str) -> str:
        """Find job ID by name"""
        response = requests.get(
            f"{self.base_url}/jobs/list",
            headers=self.config.headers
        )
        response.raise_for_status()

        jobs: list[dict[str, Any]] = response.json().get('jobs', [])
        for job in jobs:
            if job['settings']['name'] == name:
                return str(job['job_id'])

        raise DatabricksAPIError(f"Job not found: {name}")


class DatabricksUnityCatalogExecutor:
    """Unity Catalog operations"""

    def __init__(self, config: DatabricksConfig):
        self.config = config
        self.base_url = f"{config.host}/api/2.1/unity-catalog"

    def create_catalog(self, operation: "Operation") -> Dict[str, Any]:
        """Create catalog"""
        catalog_name = operation.resource_id
        params = operation.params

        catalog_spec = {
            'name': catalog_name,
            'comment': params.get('comment', ''),
            'properties': params.get('properties', {})
        }

        if params.get('storage_root'):
            catalog_spec['storage_root'] = params['storage_root']

        try:
            response = requests.post(
                f"{self.base_url}/catalogs",
                headers=self.config.headers,
                json=catalog_spec
            )
            response.raise_for_status()

            return {
                'rollback_data': {
                    'catalog_name': catalog_name
                }
            }

        except requests.exceptions.RequestException as e:
            raise DatabricksAPIError(f"Catalog create failed: {str(e)}")

    def create_schema(self, operation: "Operation") -> Dict[str, Any]:
        """Create schema"""
        schema_name = operation.resource_id
        params = operation.params

        schema_spec = {
            'name': schema_name,
            'catalog_name': params['catalog_name'],
            'comment': params.get('comment', ''),
            'properties': params.get('properties', {})
        }

        if params.get('storage_root'):
            schema_spec['storage_root'] = params['storage_root']

        try:
            response = requests.post(
                f"{self.base_url}/schemas",
                headers=self.config.headers,
                json=schema_spec
            )
            response.raise_for_status()

            return {
                'rollback_data': {
                    'catalog_name': params['catalog_name'],
                    'schema_name': schema_name
                }
            }

        except requests.exceptions.RequestException as e:
            raise DatabricksAPIError(f"Schema create failed: {str(e)}")

    def create_table(self, operation: "Operation") -> Dict[str, Any]:
        """Create table"""
        table_name = operation.resource_id
        params = operation.params

        table_spec = {
            'name': table_name,
            'catalog_name': params['catalog_name'],
            'schema_name': params['schema_name'],
            'table_type': params.get('table_type', 'MANAGED'),
            'data_source_format': params.get('data_source_format', 'DELTA'),
            'columns': params['columns'],
            'comment': params.get('comment', '')
        }

        if params.get('storage_location'):
            table_spec['storage_location'] = params['storage_location']

        if params.get('properties'):
            table_spec['properties'] = params['properties']

        try:
            response = requests.post(
                f"{self.base_url}/tables",
                headers=self.config.headers,
                json=table_spec
            )
            response.raise_for_status()

            return {
                'rollback_data': {
                    'catalog_name': params['catalog_name'],
                    'schema_name': params['schema_name'],
                    'table_name': table_name
                }
            }

        except requests.exceptions.RequestException as e:
            raise DatabricksAPIError(f"Table create failed: {str(e)}")

    def read_catalog(self, operation: "Operation") -> Dict[str, Any]:
        """Read catalog"""
        catalog_name = operation.resource_id

        try:
            response = requests.get(
                f"{self.base_url}/catalogs/{catalog_name}",
                headers=self.config.headers
            )
            response.raise_for_status()

            return {'catalog': response.json()}

        except requests.exceptions.RequestException as e:
            raise DatabricksAPIError(f"Catalog read failed: {str(e)}")

    def read_schema(self, operation: "Operation") -> Dict[str, Any]:
        """Read schema"""
        params = operation.params
        full_name = f"{params['catalog_name']}.{operation.resource_id}"

        try:
            response = requests.get(
                f"{self.base_url}/schemas/{full_name}",
                headers=self.config.headers
            )
            response.raise_for_status()

            return {'schema': response.json()}

        except requests.exceptions.RequestException as e:
            raise DatabricksAPIError(f"Schema read failed: {str(e)}")

    def read_table(self, operation: "Operation") -> Dict[str, Any]:
        """Read table"""
        params = operation.params
        full_name = f"{params['catalog_name']}.{params['schema_name']}.{operation.resource_id}"

        try:
            response = requests.get(
                f"{self.base_url}/tables/{full_name}",
                headers=self.config.headers
            )
            response.raise_for_status()

            return {'table': response.json()}

        except requests.exceptions.RequestException as e:
            raise DatabricksAPIError(f"Table read failed: {str(e)}")

    def delete_catalog(self, operation: "Operation") -> Dict[str, Any]:
        """Delete catalog"""
        catalog_name = operation.resource_id
        force = operation.params.get('force', False)

        # Get current state
        current_state = self.read_catalog(operation)

        try:
            response = requests.delete(
                f"{self.base_url}/catalogs/{catalog_name}",
                headers=self.config.headers,
                params={'force': force}
            )
            response.raise_for_status()

            return {'rollback_data': current_state}

        except requests.exceptions.RequestException as e:
            raise DatabricksAPIError(f"Catalog delete failed: {str(e)}")

    def delete_schema(self, operation: "Operation") -> Dict[str, Any]:
        """Delete schema"""
        params = operation.params
        full_name = f"{params['catalog_name']}.{operation.resource_id}"

        # Get current state
        current_state = self.read_schema(operation)

        try:
            response = requests.delete(
                f"{self.base_url}/schemas/{full_name}",
                headers=self.config.headers
            )
            response.raise_for_status()

            return {'rollback_data': current_state}

        except requests.exceptions.RequestException as e:
            raise DatabricksAPIError(f"Schema delete failed: {str(e)}")

    def delete_table(self, operation: "Operation") -> Dict[str, Any]:
        """Delete table"""
        params = operation.params
        full_name = f"{params['catalog_name']}.{params['schema_name']}.{operation.resource_id}"

        # Get current state
        current_state = self.read_table(operation)

        try:
            response = requests.delete(
                f"{self.base_url}/tables/{full_name}",
                headers=self.config.headers
            )
            response.raise_for_status()

            return {'rollback_data': current_state}

        except requests.exceptions.RequestException as e:
            raise DatabricksAPIError(f"Table delete failed: {str(e)}")

    def rollback_catalog(self, operation: "Operation") -> None:
        """Rollback catalog operation"""
        if operation.type.value == 'create':
            try:
                if operation.rollback_data is None:
                    raise ValueError("Rollback data is None for create operation")
                catalog_name = operation.rollback_data['catalog_name']
                requests.delete(
                    f"{self.base_url}/catalogs/{catalog_name}",
                    headers=self.config.headers,
                    params={'force': True}
                )
            except Exception:
                pass

    def rollback_schema(self, operation: "Operation") -> None:
        """Rollback schema operation"""
        if operation.type.value == 'create':
            try:
                if operation.rollback_data is None:
                    raise ValueError("Rollback data is None for create operation")
                catalog_name = operation.rollback_data['catalog_name']
                schema_name = operation.rollback_data['schema_name']
                full_name = f"{catalog_name}.{schema_name}"
                requests.delete(
                    f"{self.base_url}/schemas/{full_name}",
                    headers=self.config.headers
                )
            except Exception:
                pass

    def rollback_table(self, operation: "Operation") -> None:
        """Rollback table operation"""
        if operation.type.value == 'create':
            try:
                if operation.rollback_data is None:
                    raise ValueError("Rollback data is None for create operation")
                catalog_name = operation.rollback_data['catalog_name']
                schema_name = operation.rollback_data['schema_name']
                table_name = operation.rollback_data['table_name']
                full_name = f"{catalog_name}.{schema_name}.{table_name}"
                requests.delete(
                    f"{self.base_url}/tables/{full_name}",
                    headers=self.config.headers
                )
            except Exception:
                pass


class DatabricksExecutorRegistry:
    """Central Databricks executor registry"""

    def __init__(self, config: DatabricksConfig):
        self.config = config

        self.cluster = DatabricksClusterExecutor(config)
        self.job = DatabricksJobExecutor(config)
        self.uc = DatabricksUnityCatalogExecutor(config)

        # Executor map
        self.executors = {
            'dbx_cluster': {
                'create': self.cluster.create,
                'read': self.cluster.read,
                'update': self.cluster.update,
                'delete': self.cluster.delete,
                'rollback': self.cluster.rollback
            },
            'dbx_job': {
                'create': self.job.create,
                'read': self.job.read,
                'update': self.job.update,
                'delete': self.job.delete,
                'rollback': self.job.rollback
            },
            'dbx_catalog': {
                'create': self.uc.create_catalog,
                'read': self.uc.read_catalog,
                'delete': self.uc.delete_catalog,
                'rollback': self.uc.rollback_catalog
            },
            'dbx_schema': {
                'create': self.uc.create_schema,
                'read': self.uc.read_schema,
                'delete': self.uc.delete_schema,
                'rollback': self.uc.rollback_schema
            },
            'dbx_table': {
                'create': self.uc.create_table,
                'read': self.uc.read_table,
                'delete': self.uc.delete_table,
                'rollback': self.uc.rollback_table
            }
        }

    def execute(self, operation: "Operation") -> Dict[str, Any]:
        """Execute operation"""
        resource_type = operation.resource_type.value
        operation_type = operation.type.value

        if resource_type not in self.executors:
            raise ValueError(f"Unsupported resource: {resource_type}")

        if operation_type not in self.executors[resource_type]:
            raise ValueError(f"Unsupported operation: {operation_type}")

        result = self.executors[resource_type][operation_type](operation)
        if result is None:
            raise ValueError(f"Executor returned None for {resource_type}.{operation_type}")
        return result

    def rollback(self, operation: "Operation") -> None:
        """Rollback operation"""
        resource_type = operation.resource_type.value

        if resource_type in self.executors:
            self.executors[resource_type]['rollback'](operation)


# Example usage
if __name__ == "__main__":
    import os
    import uuid

    from ..constants import Environment
    from .transaction_manager import Operation, OperationType, ResourceType

    config = DatabricksConfig(
        host=os.getenv('DATABRICKS_HOST'),
        token=os.getenv('DATABRICKS_TOKEN')
    )

    registry = DatabricksExecutorRegistry(config)

    # Create cluster
    op = Operation(
        id=str(uuid.uuid4()),
        type=OperationType.CREATE,
        resource_type=ResourceType.DBX_CLUSTER,
        resource_id="dataplatform-etl-shared-prd",
        params={
            'spark_version': '13.3.x-scala2.12',
            'node_type': 'i3.xlarge',
            'autoscale': {
                'min_workers': 2,
                'max_workers': 8
            },
            'tags': {
                'Environment': Environment.PRD.value,
                'Project': 'dataplatform'
            }
        }
    )

    result = registry.execute(op)
    print(f"Created cluster: {result}")

    # Create Unity Catalog table
    uc_op = Operation(
        id=str(uuid.uuid4()),
        type=OperationType.CREATE,
        resource_type=ResourceType.DBX_TABLE,
        resource_id="dim_customers",
        params={
            'catalog_name': 'dataplatform_main_prd',
            'schema_name': 'finance_gold',
            'table_type': 'MANAGED',
            'data_source_format': 'DELTA',
            'columns': [
                {'name': 'customer_id', 'type': 'BIGINT', 'comment': 'Primary key'},
                {'name': 'customer_name', 'type': 'STRING', 'comment': 'Customer name'},
                {'name': 'created_at', 'type': 'TIMESTAMP', 'comment': 'Creation timestamp'}
            ]
        }
    )

    result = registry.execute(uc_op)
    print(f"Created table: {result}")
