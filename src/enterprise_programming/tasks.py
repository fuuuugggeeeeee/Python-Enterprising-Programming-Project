"""Task workflow using factory, observer, and singleton patterns."""

from __future__ import annotations

import threading
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Sequence, Set


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    NORMAL = "normal"
    URGENT = "urgent"


class TaskNotFoundError(KeyError):
    """Raised when a task identifier is unknown."""


class InvalidTransitionError(ValueError):
    """Raised when a task lifecycle transition is not allowed."""


@dataclass(frozen=True)
class TaskEvent:
    task_id: str
    task_name: str
    previous_status: TaskStatus
    current_status: TaskStatus
    occurred_at: float


class TaskObserver(ABC):
    @abstractmethod
    def update(self, event: TaskEvent) -> None:
        """React to a task status change."""


class ConsoleObserver(TaskObserver):
    """A small notification adapter used by the command-line demo."""

    def __init__(self, name: str) -> None:
        if not name.strip():
            raise ValueError("observer name must not be empty")
        self.name = name.strip()

    def update(self, event: TaskEvent) -> None:
        print(
            "{} notified: {!r} changed from {} to {}".format(
                self.name,
                event.task_name,
                event.previous_status.value,
                event.current_status.value,
            )
        )


_ALLOWED_TRANSITIONS: Dict[TaskStatus, Set[TaskStatus]] = {
    TaskStatus.PENDING: {TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED},
    TaskStatus.IN_PROGRESS: {
        TaskStatus.BLOCKED,
        TaskStatus.DONE,
        TaskStatus.CANCELLED,
    },
    TaskStatus.BLOCKED: {TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED},
    TaskStatus.DONE: set(),
    TaskStatus.CANCELLED: set(),
}


class Task:
    """A task whose status can change only through validated transitions."""

    def __init__(
        self,
        task_id: str,
        name: str,
        description: str = "",
        priority: TaskPriority = TaskPriority.NORMAL,
    ) -> None:
        self.task_id = task_id
        self.name = name
        self.description = description
        self.priority = priority
        self._status = TaskStatus.PENDING
        self._observers: List[TaskObserver] = []
        self._lock = threading.RLock()

    @property
    def status(self) -> TaskStatus:
        with self._lock:
            return self._status

    def attach(self, observer: TaskObserver) -> None:
        if not isinstance(observer, TaskObserver):
            raise TypeError("observer must implement TaskObserver")
        with self._lock:
            if observer not in self._observers:
                self._observers.append(observer)

    def detach(self, observer: TaskObserver) -> None:
        with self._lock:
            if observer in self._observers:
                self._observers.remove(observer)

    def transition_to(self, new_status: TaskStatus) -> TaskEvent:
        if not isinstance(new_status, TaskStatus):
            raise TypeError("new_status must be a TaskStatus")

        with self._lock:
            if new_status not in _ALLOWED_TRANSITIONS[self._status]:
                raise InvalidTransitionError(
                    "cannot transition from {} to {}".format(
                        self._status.value,
                        new_status.value,
                    )
                )
            previous_status = self._status
            self._status = new_status
            observers = tuple(self._observers)

        event = TaskEvent(
            task_id=self.task_id,
            task_name=self.name,
            previous_status=previous_status,
            current_status=new_status,
            occurred_at=time.time(),
        )
        for observer in observers:
            observer.update(event)
        return event


class TaskFactory:
    """Construct validated tasks without exposing identifier generation."""

    @staticmethod
    def create(
        name: str,
        description: str = "",
        priority: TaskPriority = TaskPriority.NORMAL,
        task_id: Optional[str] = None,
    ) -> Task:
        normalized_name = name.strip()
        if not normalized_name:
            raise ValueError("task name must not be empty")
        if not isinstance(priority, TaskPriority):
            raise TypeError("priority must be a TaskPriority")
        return Task(
            task_id=task_id or str(uuid.uuid4()),
            name=normalized_name,
            description=description.strip(),
            priority=priority,
        )


class TaskManager:
    """Process-wide task registry.

    This intentionally demonstrates the singleton pattern. Most applications
    should inject a manager instance instead; ``reset`` keeps this educational
    implementation deterministic in tests and repeatable demos.
    """

    _instance: Optional["TaskManager"] = None
    _instance_lock = threading.Lock()
    _tasks: Dict[str, Task]
    _lock: threading.RLock

    def __new__(cls) -> "TaskManager":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._tasks = {}
                cls._instance._lock = threading.RLock()
        return cls._instance

    def reset(self) -> None:
        with self._lock:
            self._tasks.clear()

    def create_task(
        self,
        name: str,
        description: str = "",
        priority: TaskPriority = TaskPriority.NORMAL,
        observers: Sequence[TaskObserver] = (),
    ) -> Task:
        task = TaskFactory.create(name, description, priority)
        for observer in observers:
            task.attach(observer)
        with self._lock:
            self._tasks[task.task_id] = task
        return task

    def get_task(self, task_id: str) -> Task:
        with self._lock:
            try:
                return self._tasks[task_id]
            except KeyError as error:
                raise TaskNotFoundError(task_id) from error

    def list_tasks(self, status: Optional[TaskStatus] = None) -> List[Task]:
        with self._lock:
            tasks = list(self._tasks.values())
        if status is not None:
            tasks = [task for task in tasks if task.status is status]
        return sorted(
            tasks,
            key=lambda task: (task.priority is not TaskPriority.URGENT, task.name),
        )

    def update_status(self, task_id: str, new_status: TaskStatus) -> TaskEvent:
        return self.get_task(task_id).transition_to(new_status)
