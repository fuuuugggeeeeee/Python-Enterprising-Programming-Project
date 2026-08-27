import unittest

from enterprise_programming.tasks import (
    InvalidTransitionError,
    TaskFactory,
    TaskManager,
    TaskNotFoundError,
    TaskObserver,
    TaskPriority,
    TaskStatus,
)


class RecordingObserver(TaskObserver):
    def __init__(self):
        self.events = []

    def update(self, event):
        self.events.append(event)


class TaskFactoryTests(unittest.TestCase):
    def test_creates_valid_unique_tasks(self):
        first = TaskFactory.create("Build API")
        second = TaskFactory.create("Build API")
        self.assertNotEqual(first.task_id, second.task_id)
        self.assertEqual(first.status, TaskStatus.PENDING)

    def test_rejects_empty_name(self):
        with self.assertRaises(ValueError):
            TaskFactory.create("  ")


class TaskManagerTests(unittest.TestCase):
    def setUp(self):
        self.manager = TaskManager()
        self.manager.reset()

    def test_is_a_process_wide_singleton(self):
        self.assertIs(self.manager, TaskManager())

    def test_observer_receives_transition_event(self):
        observer = RecordingObserver()
        task = self.manager.create_task("Review", observers=(observer,))
        event = self.manager.update_status(task.task_id, TaskStatus.IN_PROGRESS)
        self.assertEqual(observer.events, [event])
        self.assertEqual(event.previous_status, TaskStatus.PENDING)
        self.assertEqual(event.current_status, TaskStatus.IN_PROGRESS)

    def test_invalid_transition_keeps_current_status(self):
        task = self.manager.create_task("Review")
        with self.assertRaises(InvalidTransitionError):
            self.manager.update_status(task.task_id, TaskStatus.DONE)
        self.assertEqual(task.status, TaskStatus.PENDING)

    def test_status_cannot_be_assigned_directly(self):
        task = self.manager.create_task("Review")
        with self.assertRaises(AttributeError):
            task.status = TaskStatus.DONE
        self.assertEqual(task.status, TaskStatus.PENDING)

    def test_filters_and_prioritizes_tasks(self):
        normal = self.manager.create_task("Normal task")
        urgent = self.manager.create_task("Urgent task", priority=TaskPriority.URGENT)
        self.manager.update_status(normal.task_id, TaskStatus.IN_PROGRESS)
        self.assertEqual(self.manager.list_tasks()[0], urgent)
        self.assertEqual(self.manager.list_tasks(TaskStatus.IN_PROGRESS), [normal])

    def test_unknown_task_raises_domain_error(self):
        with self.assertRaises(TaskNotFoundError):
            self.manager.get_task("missing")


if __name__ == "__main__":
    unittest.main()
