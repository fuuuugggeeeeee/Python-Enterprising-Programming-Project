"""Command-line entry points for the project demos."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Optional

from .sensor import generate_readings, process_readings
from .students import create_student_server
from .tasks import ConsoleObserver, TaskManager, TaskPriority, TaskStatus


def _sensor_demo(args: argparse.Namespace) -> int:
    statistics = process_readings(
        generate_readings(args.sensors, args.readings, args.seed),
        worker_count=args.workers,
    )
    total = sum(item.count for item in statistics.values())
    reading_label = "reading" if total == 1 else "readings"
    worker_label = "worker" if args.workers == 1 else "workers"
    print(
        "Processed {} {} with {} {}".format(
            total,
            reading_label,
            args.workers,
            worker_label,
        )
    )
    print("sensor       count       min       max       avg")
    for sensor_id, item in statistics.items():
        print(
            "{:<12} {:>5} {:>9.3f} {:>9.3f} {:>9.3f}".format(
                sensor_id,
                item.count,
                item.minimum,
                item.maximum,
                item.average,
            )
        )
    return 0


def _task_demo(args: argparse.Namespace) -> int:
    manager = TaskManager()
    manager.reset()
    reviewer = ConsoleObserver("Repository reviewer")
    implementation = manager.create_task(
        "Implement sensor engine",
        priority=TaskPriority.URGENT,
        observers=(reviewer,),
    )
    documentation = manager.create_task(
        "Document HTTP API",
        observers=(reviewer,),
    )
    manager.update_status(implementation.task_id, TaskStatus.IN_PROGRESS)
    manager.update_status(implementation.task_id, TaskStatus.DONE)
    manager.update_status(documentation.task_id, TaskStatus.IN_PROGRESS)
    print("{} tasks tracked; {} completed".format(
        len(manager.list_tasks()),
        len(manager.list_tasks(TaskStatus.DONE)),
    ))
    return 0


def _student_api(args: argparse.Namespace) -> int:
    server = create_student_server(
        host=args.host,
        port=args.port,
        data_path=args.data,
    )
    host, port = server.server_address[:2]
    print("Student API listening on http://{}:{}".format(host, port))
    print("Data file: {}".format(args.data))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping student API")
    finally:
        server.server_close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="enterprise-project",
        description="Run the Enterprise Programming Project examples.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    sensor = subparsers.add_parser("sensor-demo", help="aggregate simulated readings")
    sensor.add_argument("--sensors", type=int, default=3)
    sensor.add_argument("--readings", type=int, default=100, help="readings per sensor")
    sensor.add_argument("--workers", type=int, default=4)
    sensor.add_argument("--seed", type=int, default=42)
    sensor.set_defaults(handler=_sensor_demo)

    tasks = subparsers.add_parser("task-demo", help="run the task workflow")
    tasks.set_defaults(handler=_task_demo)

    students = subparsers.add_parser("student-api", help="start the student HTTP API")
    students.add_argument("--host", default="127.0.0.1")
    students.add_argument("--port", type=int, default=8000)
    students.add_argument("--data", type=Path, default=Path("students.json"))
    students.set_defaults(handler=_student_api)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.handler(args))
