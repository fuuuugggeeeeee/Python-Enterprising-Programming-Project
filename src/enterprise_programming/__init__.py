"""Small, runnable examples of enterprise programming concepts."""

from .sensor import SensorAggregator, SensorReading, SensorStatistics
from .students import Student, StudentService
from .tasks import Task, TaskManager, TaskStatus

__all__ = [
    "SensorAggregator",
    "SensorReading",
    "SensorStatistics",
    "Student",
    "StudentService",
    "Task",
    "TaskManager",
    "TaskStatus",
]

__version__ = "1.0.0"
