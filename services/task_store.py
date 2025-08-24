"""
Centralized task and result storage service.
Replaces shared mutable class variables with explicit, testable state management.
Following Single Responsibility Principle and explicit dependency injection.
"""
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskInfo:
    """Information about a task."""
    operation_id: str
    status: TaskStatus
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    task: Optional[asyncio.Task] = None


class TaskStore:
    """
    Centralized storage for async tasks and results.
    This replaces the anti-pattern of shared class variables.
    
    For production, this should be backed by Redis or a database.
    Current implementation is in-memory for simplicity.
    """
    
    def __init__(self):
        self._tasks: Dict[str, TaskInfo] = {}
        self._lock = asyncio.Lock()
    
    async def create_task(self, operation_id: str) -> TaskInfo:
        """Create a new task entry."""
        async with self._lock:
            if operation_id in self._tasks:
                logger.warning(f"Task {operation_id} already exists")
                return self._tasks[operation_id]
            
            task_info = TaskInfo(
                operation_id=operation_id,
                status=TaskStatus.PENDING
            )
            self._tasks[operation_id] = task_info
            logger.info(f"Created task: {operation_id}")
            return task_info
    
    async def update_status(
        self, 
        operation_id: str, 
        status: TaskStatus,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> Optional[TaskInfo]:
        """Update task status and optionally set result or error."""
        async with self._lock:
            if operation_id not in self._tasks:
                logger.error(f"Task {operation_id} not found")
                return None
            
            task_info = self._tasks[operation_id]
            task_info.status = status
            
            if status == TaskStatus.RUNNING and not task_info.started_at:
                task_info.started_at = datetime.utcnow()
            elif status in (TaskStatus.SUCCEEDED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                task_info.completed_at = datetime.utcnow()
            
            if result is not None:
                task_info.result = result
            if error is not None:
                task_info.error = error
            
            logger.info(f"Updated task {operation_id}: status={status}")
            return task_info
    
    async def set_async_task(self, operation_id: str, task: asyncio.Task) -> bool:
        """Associate an asyncio Task with an operation."""
        async with self._lock:
            if operation_id not in self._tasks:
                logger.error(f"Task {operation_id} not found")
                return False
            
            self._tasks[operation_id].task = task
            return True
    
    async def get_task(self, operation_id: str) -> Optional[TaskInfo]:
        """Get task information."""
        async with self._lock:
            return self._tasks.get(operation_id)
    
    async def get_result(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """Get task result if available."""
        task_info = await self.get_task(operation_id)
        return task_info.result if task_info else None
    
    async def cancel_task(self, operation_id: str) -> bool:
        """Cancel a running task."""
        async with self._lock:
            if operation_id not in self._tasks:
                return False
            
            task_info = self._tasks[operation_id]
            if task_info.task and not task_info.task.done():
                task_info.task.cancel()
                task_info.status = TaskStatus.CANCELLED
                task_info.completed_at = datetime.utcnow()
                logger.info(f"Cancelled task: {operation_id}")
                return True
            
            return False
    
    async def cleanup_completed(self, max_age_seconds: int = 3600):
        """
        Clean up completed tasks older than max_age_seconds.
        Prevents memory leaks from accumulating results.
        """
        async with self._lock:
            now = datetime.utcnow()
            to_remove = []
            
            for op_id, task_info in self._tasks.items():
                if task_info.completed_at:
                    age = (now - task_info.completed_at).total_seconds()
                    if age > max_age_seconds:
                        to_remove.append(op_id)
            
            for op_id in to_remove:
                del self._tasks[op_id]
                logger.debug(f"Cleaned up old task: {op_id}")
            
            if to_remove:
                logger.info(f"Cleaned up {len(to_remove)} old tasks")
    
    def get_all_tasks(self) -> Dict[str, TaskInfo]:
        """Get all tasks (for debugging/monitoring)."""
        return dict(self._tasks)


class TaskStoreService:
    """
    Service wrapper for task storage with singleton pattern.
    This ensures all parts of the application use the same store.
    """
    
    _instance: Optional[TaskStore] = None
    
    @classmethod
    def get_store(cls) -> TaskStore:
        """Get the singleton task store instance."""
        if cls._instance is None:
            cls._instance = TaskStore()
        return cls._instance
    
    @classmethod
    def reset(cls):
        """Reset the store (mainly for testing)."""
        cls._instance = None


def get_task_store() -> TaskStore:
    """Get the global task store instance."""
    return TaskStoreService.get_store()