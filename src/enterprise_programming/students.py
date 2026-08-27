"""Student service, persistence adapters, and an HTTP transport."""

from __future__ import annotations

import json
import os
import tempfile
import threading
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Type
from urllib.parse import unquote, urlparse


class StudentError(Exception):
    """Base class for expected student-service errors."""


class StudentValidationError(StudentError, ValueError):
    pass


class DuplicateStudentError(StudentError):
    pass


class StudentNotFoundError(StudentError, KeyError):
    pass


def _normalize_student_id(student_id: str) -> str:
    if not isinstance(student_id, str):
        raise StudentValidationError("student_id must be a string")
    normalized = student_id.strip()
    if not normalized:
        raise StudentValidationError("student_id must not be empty")
    if len(normalized) > 64:
        raise StudentValidationError("student_id must be 64 characters or fewer")
    return normalized


@dataclass(frozen=True)
class Student:
    student_id: str
    name: str
    course: str

    @classmethod
    def create(cls, student_id: str, name: str, course: str) -> "Student":
        raw_values = {"student_id": student_id, "name": name, "course": course}
        for field_name, value in raw_values.items():
            if not isinstance(value, str):
                raise StudentValidationError("{} must be a string".format(field_name))
        values = {field_name: value.strip() for field_name, value in raw_values.items()}
        for field_name, value in values.items():
            if not value:
                raise StudentValidationError("{} must not be empty".format(field_name))
        values["student_id"] = _normalize_student_id(values["student_id"])
        return cls(**values)

    def as_dict(self) -> Dict[str, str]:
        return asdict(self)


class StudentRepository(ABC):
    @abstractmethod
    def add(self, student: Student) -> None:
        pass

    @abstractmethod
    def get(self, student_id: str) -> Student:
        pass

    @abstractmethod
    def list_all(self) -> List[Student]:
        pass

    @abstractmethod
    def update(self, student: Student) -> None:
        pass

    @abstractmethod
    def delete(self, student_id: str) -> None:
        pass


class InMemoryStudentRepository(StudentRepository):
    def __init__(self) -> None:
        self._students: Dict[str, Student] = {}
        self._lock = threading.RLock()

    def add(self, student: Student) -> None:
        with self._lock:
            if student.student_id in self._students:
                raise DuplicateStudentError(student.student_id)
            self._students[student.student_id] = student

    def get(self, student_id: str) -> Student:
        with self._lock:
            try:
                return self._students[student_id]
            except KeyError as error:
                raise StudentNotFoundError(student_id) from error

    def list_all(self) -> List[Student]:
        with self._lock:
            return sorted(self._students.values(), key=lambda student: student.student_id)

    def update(self, student: Student) -> None:
        with self._lock:
            if student.student_id not in self._students:
                raise StudentNotFoundError(student.student_id)
            self._students[student.student_id] = student

    def delete(self, student_id: str) -> None:
        with self._lock:
            if student_id not in self._students:
                raise StudentNotFoundError(student_id)
            del self._students[student_id]


class JsonStudentRepository(InMemoryStudentRepository):
    """Thread-safe repository persisted as an atomically replaced JSON file."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        super().__init__()
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            document = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError("could not read student data from {}".format(self.path)) from error
        if not isinstance(document, list):
            raise ValueError("student data must be a JSON array")
        for item in document:
            if not isinstance(item, dict):
                raise ValueError("each student record must be a JSON object")
            student = Student.create(
                item.get("student_id", ""),
                item.get("name", ""),
                item.get("course", ""),
            )
            if student.student_id in self._students:
                raise ValueError("duplicate student_id in data file")
            self._students[student.student_id] = student

    def _persist(self, students: Mapping[str, Student]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        file_descriptor, temporary_name = tempfile.mkstemp(
            prefix=".students-",
            suffix=".json",
            dir=str(self.path.parent),
            text=True,
        )
        try:
            with os.fdopen(file_descriptor, "w", encoding="utf-8") as temporary_file:
                json.dump(
                    [students[key].as_dict() for key in sorted(students)],
                    temporary_file,
                    indent=2,
                    sort_keys=True,
                )
                temporary_file.write("\n")
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_name, self.path)
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)

    def add(self, student: Student) -> None:
        with self._lock:
            if student.student_id in self._students:
                raise DuplicateStudentError(student.student_id)
            updated = dict(self._students)
            updated[student.student_id] = student
            self._persist(updated)
            self._students = updated

    def update(self, student: Student) -> None:
        with self._lock:
            if student.student_id not in self._students:
                raise StudentNotFoundError(student.student_id)
            updated = dict(self._students)
            updated[student.student_id] = student
            self._persist(updated)
            self._students = updated

    def delete(self, student_id: str) -> None:
        with self._lock:
            if student_id not in self._students:
                raise StudentNotFoundError(student_id)
            updated = dict(self._students)
            del updated[student_id]
            self._persist(updated)
            self._students = updated


class StudentService:
    """Application layer independent of console, HTTP, and storage details."""

    def __init__(self, repository: Optional[StudentRepository] = None) -> None:
        self.repository = repository or InMemoryStudentRepository()

    def create_student(self, student_id: str, name: str, course: str) -> Student:
        student = Student.create(student_id, name, course)
        self.repository.add(student)
        return student

    def get_student(self, student_id: str) -> Student:
        return self.repository.get(_normalize_student_id(student_id))

    def list_students(self) -> List[Student]:
        return self.repository.list_all()

    def update_student(self, student_id: str, name: str, course: str) -> Student:
        student = Student.create(student_id, name, course)
        self.repository.update(student)
        return student

    def delete_student(self, student_id: str) -> None:
        self.repository.delete(_normalize_student_id(student_id))


class StudentRequestHandler(BaseHTTPRequestHandler):
    """JSON HTTP adapter for :class:`StudentService`."""

    service: StudentService
    quiet = False
    max_body_size = 1_000_000

    def do_GET(self) -> None:
        try:
            segments = self._segments()
            if segments == ["health"]:
                self._send_json(200, {"status": "ok"})
            elif segments == ["students"]:
                students = [student.as_dict() for student in self.service.list_students()]
                self._send_json(200, {"students": students})
            elif len(segments) == 2 and segments[0] == "students":
                self._send_json(200, self.service.get_student(segments[1]).as_dict())
            else:
                self._send_error(404, "route_not_found", "Route not found")
        except StudentError as error:
            self._handle_student_error(error)

    def do_POST(self) -> None:
        try:
            if self._segments() != ["students"]:
                self._send_error(404, "route_not_found", "Route not found")
                return
            payload = self._read_json()
            student = self.service.create_student(
                self._field(payload, "student_id"),
                self._field(payload, "name"),
                self._field(payload, "course"),
            )
            self._send_json(201, student.as_dict())
        except StudentError as error:
            self._handle_student_error(error)
        except ValueError as error:
            self._send_error(400, "invalid_request", str(error))

    def do_PUT(self) -> None:
        try:
            segments = self._segments()
            if len(segments) != 2 or segments[0] != "students":
                self._send_error(404, "route_not_found", "Route not found")
                return
            payload = self._read_json()
            student = self.service.update_student(
                segments[1],
                self._field(payload, "name"),
                self._field(payload, "course"),
            )
            self._send_json(200, student.as_dict())
        except StudentError as error:
            self._handle_student_error(error)
        except ValueError as error:
            self._send_error(400, "invalid_request", str(error))

    def do_DELETE(self) -> None:
        try:
            segments = self._segments()
            if len(segments) != 2 or segments[0] != "students":
                self._send_error(404, "route_not_found", "Route not found")
                return
            self.service.delete_student(segments[1])
            self.send_response(204)
            self.end_headers()
        except StudentError as error:
            self._handle_student_error(error)

    def _segments(self) -> List[str]:
        path = urlparse(self.path).path
        return [unquote(segment) for segment in path.split("/") if segment]

    def _read_json(self) -> Mapping[str, object]:
        content_type = self.headers.get_content_type()
        if content_type != "application/json":
            raise ValueError("Content-Type must be application/json")
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError as error:
            raise ValueError("Content-Length must be an integer") from error
        if content_length <= 0:
            raise ValueError("request body must not be empty")
        if content_length > self.max_body_size:
            raise ValueError("request body is too large")
        try:
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("request body must contain valid JSON") from error
        if not isinstance(payload, dict):
            raise ValueError("request body must be a JSON object")
        return payload

    @staticmethod
    def _field(payload: Mapping[str, object], name: str) -> str:
        value = payload.get(name)
        if not isinstance(value, str):
            raise ValueError("{} must be a string".format(name))
        return value

    def _handle_student_error(self, error: StudentError) -> None:
        if isinstance(error, DuplicateStudentError):
            self._send_error(409, "student_exists", "Student already exists")
        elif isinstance(error, StudentNotFoundError):
            self._send_error(404, "student_not_found", "Student not found")
        else:
            self._send_error(400, "validation_error", str(error))

    def _send_error(self, status: int, code: str, message: str) -> None:
        self._send_json(status, {"error": {"code": code, "message": message}})

    def _send_json(self, status: int, payload: Mapping[str, object]) -> None:
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format_string: str, *args: object) -> None:
        if not self.quiet:
            super().log_message(format_string, *args)


def build_student_handler(
    service: StudentService,
    quiet: bool = False,
) -> Type[StudentRequestHandler]:
    class ConfiguredStudentHandler(StudentRequestHandler):
        pass

    ConfiguredStudentHandler.service = service
    ConfiguredStudentHandler.quiet = quiet
    return ConfiguredStudentHandler


def create_student_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    data_path: Optional[Path] = None,
    quiet: bool = False,
) -> ThreadingHTTPServer:
    repository: StudentRepository
    if data_path is None:
        repository = InMemoryStudentRepository()
    else:
        repository = JsonStudentRepository(data_path)
    handler = build_student_handler(StudentService(repository), quiet=quiet)
    return ThreadingHTTPServer((host, port), handler)
