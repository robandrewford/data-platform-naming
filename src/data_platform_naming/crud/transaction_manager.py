#!/usr/bin/env python3
"""
ACID Transaction Manager for Data Platform Resource Operations
Ensures Atomicity, Consistency, Isolation, Durability
"""

import fcntl
import json
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Optional, cast

if TYPE_CHECKING:
    from rich.console import Console
    from rich.progress import BarColumn, Progress, SpinnerColumn, TaskID, TextColumn, TimeElapsedColumn
    from rich.progress import Progress as ProgressType
else:
    from rich.console import Console
    from rich.progress import BarColumn, Progress, SpinnerColumn, TaskID, TextColumn, TimeElapsedColumn
    ProgressType = Progress


class OperationType(Enum):
    """CRUD operation types"""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"


class OperationStatus(Enum):
    """Operation execution status"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class ResourceType(Enum):
    """Supported resource types"""
    AWS_S3_BUCKET = "aws_s3_bucket"
    AWS_GLUE_DATABASE = "aws_glue_database"
    AWS_GLUE_TABLE = "aws_glue_table"
    DBX_WORKSPACE = "dbx_workspace"
    DBX_CLUSTER = "dbx_cluster"
    DBX_JOB = "dbx_job"
    DBX_CATALOG = "dbx_catalog"
    DBX_SCHEMA = "dbx_schema"
    DBX_TABLE = "dbx_table"


@dataclass
class Operation:
    """Single CRUD operation"""
    id: str
    type: OperationType
    resource_type: ResourceType
    resource_id: str
    params: dict[str, Any]
    status: OperationStatus = OperationStatus.PENDING
    created_at: float = 0.0
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error: Optional[str] = None
    rollback_data: Optional[dict] = None

    def __post_init__(self):
        if self.created_at == 0.0:
            self.created_at = time.time()

    def duration(self) -> Optional[float]:
        """Calculate operation duration"""
        if self.started_at is not None and self.completed_at is not None:
            return self.completed_at - self.started_at
        return None


@dataclass
class Transaction:
    """ACID transaction containing multiple operations"""
    id: str
    operations: list[Operation]
    status: OperationStatus = OperationStatus.PENDING
    created_at: float = 0.0
    committed_at: Optional[float] = None
    rolled_back_at: Optional[float] = None

    def __post_init__(self):
        if self.created_at == 0.0:
            self.created_at = time.time()


class WriteAheadLog:
    """Write-Ahead Log for durability"""

    def __init__(self, wal_dir: Path):
        self.wal_dir = wal_dir
        self.wal_dir.mkdir(parents=True, exist_ok=True)
        self.lock_file = self.wal_dir / ".wal.lock"

    @contextmanager
    def _lock(self):
        """File-based lock for WAL isolation"""
        lock_fd = open(self.lock_file, 'w')
        try:
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
            lock_fd.close()

    def write_transaction(self, transaction: Transaction) -> None:
        """Write transaction to WAL"""
        with self._lock():
            wal_file = self.wal_dir / f"{transaction.id}.wal"
            with open(wal_file, 'w') as f:
                json.dump(self._serialize_transaction(transaction), f, indent=2)

    def write_operation(self, tx_id: str, operation: Operation) -> None:
        """Write operation status to WAL"""
        with self._lock():
            wal_file = self.wal_dir / f"{tx_id}.wal"
            if not wal_file.exists():
                raise ValueError(f"Transaction {tx_id} not found in WAL")

            with open(wal_file) as f:
                tx_data = json.load(f)

            # Update operation status
            for i, op in enumerate(tx_data['operations']):
                if op['id'] == operation.id:
                    tx_data['operations'][i] = self._serialize_operation(operation)
                    break

            with open(wal_file, 'w') as f:
                json.dump(tx_data, f, indent=2)

    def mark_committed(self, tx_id: str) -> None:
        """Mark transaction as committed"""
        with self._lock():
            wal_file = self.wal_dir / f"{tx_id}.wal"
            commit_file = self.wal_dir / f"{tx_id}.committed"

            with open(wal_file) as f:
                tx_data = json.load(f)

            tx_data['status'] = OperationStatus.SUCCESS.value
            tx_data['committed_at'] = time.time()

            with open(commit_file, 'w') as f:
                json.dump(tx_data, f, indent=2)

    def mark_rolled_back(self, tx_id: str) -> None:
        """Mark transaction as rolled back"""
        with self._lock():
            wal_file = self.wal_dir / f"{tx_id}.wal"
            rollback_file = self.wal_dir / f"{tx_id}.rolled_back"

            with open(wal_file) as f:
                tx_data = json.load(f)

            tx_data['status'] = OperationStatus.ROLLED_BACK.value
            tx_data['rolled_back_at'] = time.time()

            with open(rollback_file, 'w') as f:
                json.dump(tx_data, f, indent=2)

    def recover_transactions(self) -> list[Transaction]:
        """Recover uncommitted transactions from WAL"""
        uncommitted = []

        for wal_file in self.wal_dir.glob("*.wal"):
            tx_id = wal_file.stem

            # Skip if committed or rolled back
            if (self.wal_dir / f"{tx_id}.committed").exists():
                continue
            if (self.wal_dir / f"{tx_id}.rolled_back").exists():
                continue

            with open(wal_file) as f:
                tx_data = json.load(f)

            uncommitted.append(self._deserialize_transaction(tx_data))

        return uncommitted

    def _serialize_transaction(self, tx: Transaction) -> dict[str, Any]:
        """Serialize transaction to JSON"""
        return {
            'id': tx.id,
            'status': tx.status.value,
            'created_at': tx.created_at,
            'committed_at': tx.committed_at,
            'rolled_back_at': tx.rolled_back_at,
            'operations': [self._serialize_operation(op) for op in tx.operations]
        }

    def _serialize_operation(self, op: Operation) -> dict[str, Any]:
        """Serialize operation to JSON"""
        return {
            'id': op.id,
            'type': op.type.value,
            'resource_type': op.resource_type.value,
            'resource_id': op.resource_id,
            'params': op.params,
            'status': op.status.value,
            'created_at': op.created_at,
            'started_at': op.started_at,
            'completed_at': op.completed_at,
            'error': op.error,
            'rollback_data': op.rollback_data
        }

    def _deserialize_transaction(self, data: dict[str, Any]) -> Transaction:
        """Deserialize transaction from JSON"""
        return Transaction(
            id=data['id'],
            status=OperationStatus(data['status']),
            created_at=data['created_at'],
            committed_at=data.get('committed_at'),
            rolled_back_at=data.get('rolled_back_at'),
            operations=[self._deserialize_operation(op) for op in data['operations']]
        )

    def _deserialize_operation(self, data: dict[str, Any]) -> Operation:
        """Deserialize operation from JSON"""
        return Operation(
            id=data['id'],
            type=OperationType(data['type']),
            resource_type=ResourceType(data['resource_type']),
            resource_id=data['resource_id'],
            params=data['params'],
            status=OperationStatus(data['status']),
            created_at=data['created_at'],
            started_at=data.get('started_at'),
            completed_at=data.get('completed_at'),
            error=data.get('error'),
            rollback_data=data.get('rollback_data')
        )


class StateStore:
    """In-memory state store with disk persistence"""

    def __init__(self, state_dir: Path):
        self.state_dir = state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.state_dir / "state.json"
        self.state: dict[str, dict[str, Any]] = self._load_state()
        self._lock = threading.Lock()

    def _load_state(self) -> dict[str, dict[str, Any]]:
        """Load state from disk"""
        if self.state_file.exists():
            with open(self.state_file) as f:
                return cast(dict[str, dict[str, Any]], json.load(f))
        return {}

    def _persist_state(self) -> None:
        """Persist state to disk"""
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)

    def get(self, resource_id: str) -> Optional[dict[str, Any]]:
        """Get resource state"""
        with self._lock:
            return self.state.get(resource_id)

    def set(self, resource_id: str, state: dict[str, Any]) -> None:
        """Set resource state"""
        with self._lock:
            self.state[resource_id] = state
            self._persist_state()

    def delete(self, resource_id: str) -> None:
        """Delete resource state"""
        with self._lock:
            if resource_id in self.state:
                del self.state[resource_id]
                self._persist_state()

    def exists(self, resource_id: str) -> bool:
        """Check if resource exists"""
        with self._lock:
            return resource_id in self.state


class ProgressTracker:
    """Real-time progress tracking with Rich"""

    def __init__(self, console: Optional["Console"] = None):
        self.console = console or Console()
        self.progress: "ProgressType" = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=self.console
        )
        self.task_id: Optional["TaskID"] = None
        self.start_time: Optional[float] = None

    def start(self, total: int, description: str = "Processing") -> None:
        """Start progress tracking"""
        self.start_time = time.time()
        self.progress.start()
        self.task_id = self.progress.add_task(description, total=total)

    def update(self, status: str, advance: int = 1) -> None:
        """Update progress"""
        if self.task_id is not None and self.start_time is not None:
            elapsed = time.time() - self.start_time
            self.progress.update(
                self.task_id,
                description=f"[{elapsed:.1f}s] {status}",
                advance=advance
            )

    def complete(self) -> None:
        """Complete progress tracking"""
        if self.task_id is not None:
            self.progress.stop()

    def error(self, message: str) -> None:
        """Display error"""
        self.console.print(f"[red]✗ {message}[/red]")

    def success(self, message: str) -> None:
        """Display success"""
        self.console.print(f"[green]✓ {message}[/green]")


class TransactionManager:
    """ACID transaction manager for resource operations"""

    def __init__(self, base_dir: Path = Path.cwd() / ".dpn"):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.wal = WriteAheadLog(self.base_dir / "wal")
        self.state = StateStore(self.base_dir / "state")
        self.console = Console()

        # Operation executors (injected)
        self.executors: dict[ResourceType, Callable] = {}
        self.rollback_handlers: dict[ResourceType, Callable] = {}

    def register_executor(self,
                         resource_type: ResourceType,
                         executor: Callable,
                         rollback_handler: Callable) -> None:
        """Register operation executor and rollback handler"""
        self.executors[resource_type] = executor
        self.rollback_handlers[resource_type] = rollback_handler

    def begin_transaction(self, operations: list[Operation]) -> Transaction:
        """Begin new transaction"""
        tx = Transaction(
            id=str(uuid.uuid4()),
            operations=operations
        )

        # Write to WAL (Durability)
        self.wal.write_transaction(tx)

        return tx

    def execute_transaction(self, transaction: Transaction) -> bool:
        """Execute transaction with ACID guarantees"""
        tracker = ProgressTracker(self.console)
        tracker.start(len(transaction.operations), "Executing transaction")

        completed_operations: list[Operation] = []

        try:
            # Validate pre-conditions (Consistency)
            self._validate_preconditions(transaction)

            # Execute operations (Atomicity)
            for operation in transaction.operations:
                operation.status = OperationStatus.RUNNING
                operation.started_at = time.time()
                self.wal.write_operation(transaction.id, operation)

                try:
                    # Execute operation
                    tracker.update(f"Executing {operation.type.value}: {operation.resource_id}")
                    result = self._execute_operation(operation)

                    # Store rollback data
                    operation.rollback_data = result.get('rollback_data')
                    operation.status = OperationStatus.SUCCESS
                    operation.completed_at = time.time()

                    completed_operations.append(operation)
                    self.wal.write_operation(transaction.id, operation)

                except Exception as e:
                    operation.status = OperationStatus.FAILED
                    operation.error = str(e)
                    operation.completed_at = time.time()
                    self.wal.write_operation(transaction.id, operation)

                    raise TransactionError(
                        f"Operation failed: {operation.id}",
                        operation=operation,
                        completed_operations=completed_operations
                    )

            # Validate post-conditions (Consistency)
            self._validate_postconditions(transaction)

            # Commit (Durability)
            self.wal.mark_committed(transaction.id)
            transaction.status = OperationStatus.SUCCESS
            transaction.committed_at = time.time()

            tracker.complete()
            tracker.success(f"Transaction {transaction.id} committed successfully")

            return True

        except TransactionError as e:
            # Rollback (Atomicity)
            tracker.error(f"Transaction failed: {e.message}")
            self._rollback_transaction(transaction, e.completed_operations)
            tracker.error(f"Transaction {transaction.id} rolled back")
            return False

        except Exception as e:
            tracker.error(f"Unexpected error: {str(e)}")
            self._rollback_transaction(transaction, completed_operations)
            tracker.error(f"Transaction {transaction.id} rolled back")
            return False

    def _validate_preconditions(self, transaction: Transaction) -> None:
        """Validate transaction pre-conditions"""
        for operation in transaction.operations:
            if operation.type == OperationType.CREATE:
                # Resource must not exist
                if self.state.exists(operation.resource_id):
                    raise ConsistencyError(
                        f"Resource already exists: {operation.resource_id}"
                    )

            elif operation.type in [OperationType.UPDATE, OperationType.DELETE]:
                # Resource must exist
                if not self.state.exists(operation.resource_id):
                    raise ConsistencyError(
                        f"Resource not found: {operation.resource_id}"
                    )

    def _validate_postconditions(self, transaction: Transaction) -> None:
        """Validate transaction post-conditions"""
        for operation in transaction.operations:
            if operation.type == OperationType.CREATE:
                # Resource must exist
                if not self.state.exists(operation.resource_id):
                    raise ConsistencyError(
                        f"Resource creation failed: {operation.resource_id}"
                    )

            elif operation.type == OperationType.DELETE:
                # Resource must not exist
                if self.state.exists(operation.resource_id):
                    raise ConsistencyError(
                        f"Resource deletion failed: {operation.resource_id}"
                    )

    def _execute_operation(self, operation: Operation) -> dict[str, Any]:
        """Execute single operation"""
        if operation.resource_type not in self.executors:
            raise ValueError(
                f"No executor registered for {operation.resource_type.value}"
            )

        executor = self.executors[operation.resource_type]
        result = cast(dict[str, Any], executor(operation))

        # Update state store
        if operation.type == OperationType.CREATE:
            self.state.set(operation.resource_id, {
                'resource_type': operation.resource_type.value,
                'params': operation.params,
                'created_at': operation.completed_at
            })
        elif operation.type == OperationType.DELETE:
            self.state.delete(operation.resource_id)
        elif operation.type == OperationType.UPDATE:
            current_state = self.state.get(operation.resource_id)
            if current_state is not None:
                current_state.update(operation.params)
                self.state.set(operation.resource_id, current_state)

        return result

    def _rollback_transaction(self,
                             transaction: Transaction,
                             completed_operations: list[Operation]) -> None:
        """Rollback completed operations"""
        self.console.print("[yellow]Rolling back transaction...[/yellow]")

        # Reverse order rollback
        for operation in reversed(completed_operations):
            try:
                if operation.resource_type in self.rollback_handlers:
                    handler = self.rollback_handlers[operation.resource_type]
                    handler(operation)

                    # Revert state
                    if operation.type == OperationType.CREATE:
                        self.state.delete(operation.resource_id)
                    elif operation.type == OperationType.DELETE:
                        if operation.rollback_data is not None:
                            self.state.set(operation.resource_id, operation.rollback_data)

                    operation.status = OperationStatus.ROLLED_BACK
                    self.wal.write_operation(transaction.id, operation)

            except Exception as e:
                self.console.print(
                    f"[red]Rollback failed for {operation.resource_id}: {str(e)}[/red]"
                )

        self.wal.mark_rolled_back(transaction.id)
        transaction.status = OperationStatus.ROLLED_BACK
        transaction.rolled_back_at = time.time()

    def recover(self) -> None:
        """Recover from WAL on startup"""
        self.console.print("[yellow]Checking for uncommitted transactions...[/yellow]")

        uncommitted = self.wal.recover_transactions()

        if not uncommitted:
            self.console.print("[green]No recovery needed[/green]")
            return

        self.console.print(f"[yellow]Found {len(uncommitted)} uncommitted transactions[/yellow]")

        for tx in uncommitted:
            self.console.print(f"[yellow]Rolling back transaction {tx.id}[/yellow]")

            completed_ops = [
                op for op in tx.operations
                if op.status == OperationStatus.SUCCESS
            ]

            self._rollback_transaction(tx, completed_ops)

        self.console.print("[green]Recovery complete[/green]")


class TransactionError(Exception):
    """Transaction execution error"""

    def __init__(self, message: str, operation: Operation, completed_operations: list[Operation]):
        super().__init__(message)
        self.message = message
        self.operation = operation
        self.completed_operations = completed_operations


class ConsistencyError(Exception):
    """Consistency validation error"""
    pass


# Example usage
if __name__ == "__main__":
    # Initialize transaction manager
    tm = TransactionManager()

    def mock_create_cluster(operation: Operation) -> dict:
        time.sleep(0.5)  # Simulate API call
        return {'rollback_data': {'cluster_id': operation.resource_id}}

    def mock_rollback_cluster(operation: Operation) -> None:
        time.sleep(0.3)  # Simulate API call
        pass

    # Register executors
    tm.register_executor(
        ResourceType.DBX_CLUSTER,
        mock_create_cluster,
        mock_rollback_cluster
    )

    # Create transaction
    operations = [
        Operation(
            id=str(uuid.uuid4()),
            type=OperationType.CREATE,
            resource_type=ResourceType.DBX_CLUSTER,
            resource_id="dataplatform-etl-shared-prd",
            params={'node_type': 'i3.xlarge', 'autoscale': {'min': 2, 'max': 8}}
        ),
        Operation(
            id=str(uuid.uuid4()),
            type=OperationType.CREATE,
            resource_type=ResourceType.DBX_CLUSTER,
            resource_id="dataplatform-ml-dedicated-prd",
            params={'node_type': 'g4dn.xlarge', 'workers': 4}
        )
    ]

    tx = tm.begin_transaction(operations)

    # Execute transaction
    success = tm.execute_transaction(tx)

    if success:
        print(f"\n✓ Transaction completed: {tx.id}")
        if tx.committed_at is not None:
            print(f"  Duration: {tx.committed_at - tx.created_at:.2f}s")
    else:
        print(f"\n✗ Transaction failed: {tx.id}")
