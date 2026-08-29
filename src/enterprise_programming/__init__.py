"""Small, runnable examples of enterprise programming concepts."""

from .sensor import SensorAggregator, SensorReading, SensorStatistics
from .tasks import Task, TaskManager, TaskStatus

__all__ = [
    "SensorAggregator",
    "SensorReading",
    "SensorStatistics",
    "Task",
    "TaskManager",
    "TaskStatus",
]

__version__ = "2.0.0"
