import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from enterprise_programming.students import (
    DuplicateStudentError,
    JsonStudentRepository,
    StudentNotFoundError,
    StudentService,
    StudentValidationError,
    create_student_server,
)


class StudentServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = StudentService()

    def test_crud_lifecycle(self):
        created = self.service.create_student("S001", "Amina Patel", "Computer Science")
        self.assertEqual(self.service.get_student("S001"), created)
        updated = self.service.update_student("S001", "Amina Patel", "Data Science")
        self.assertEqual(updated.course, "Data Science")
        self.assertEqual(self.service.list_students(), [updated])
        self.service.delete_student("S001")
        with self.assertRaises(StudentNotFoundError):
            self.service.get_student("S001")

    def test_duplicate_student_is_rejected(self):
        self.service.create_student("S001", "Amina Patel", "Computer Science")
        with self.assertRaises(DuplicateStudentError):
            self.service.create_student("S001", "Another Person", "Engineering")

    def test_invalid_student_is_rejected(self):
        with self.assertRaises(StudentValidationError):
            self.service.create_student("S001", " ", "Computer Science")
        with self.assertRaises(StudentValidationError):
            self.service.get_student(" ")


class JsonStudentRepositoryTests(unittest.TestCase):
    def test_data_survives_repository_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "students.json"
            service = StudentService(JsonStudentRepository(path))
            service.create_student("S001", "Amina Patel", "Computer Science")
            service.create_student("S002", "Lebo Nkosi", "Engineering")
            service.update_student("S001", "Amina Patel", "Data Science")
            service.delete_student("S002")
            restarted = StudentService(JsonStudentRepository(path))
            self.assertEqual(restarted.get_student("S001").name, "Amina Patel")
            self.assertEqual(restarted.get_student("S001").course, "Data Science")
            with self.assertRaises(StudentNotFoundError):
                restarted.get_student("S002")
            document = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(document[0]["student_id"], "S001")

    def test_corrupt_data_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "students.json"
            path.write_text("not-json", encoding="utf-8")
            with self.assertRaises(ValueError):
                JsonStudentRepository(path)


class StudentHttpApiTests(unittest.TestCase):
    def setUp(self):
        self.server = create_student_server(port=0, quiet=True)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address[:2]
        self.base_url = "http://{}:{}".format(host, port)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2.0)

    def request(self, method, path, payload=None):
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {} if body is None else {"Content-Type": "application/json"}
        request = Request(self.base_url + path, data=body, headers=headers, method=method)
        with urlopen(request, timeout=2.0) as response:
            content = response.read()
            return response.status, None if not content else json.loads(content)

    def test_health_endpoint(self):
        status, payload = self.request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(payload, {"status": "ok"})

    def test_http_crud_lifecycle(self):
        status, created = self.request(
            "POST",
            "/students",
            {"student_id": "S001", "name": "Amina Patel", "course": "Computer Science"},
        )
        self.assertEqual(status, 201)
        self.assertEqual(created["student_id"], "S001")
        status, listing = self.request("GET", "/students")
        self.assertEqual(status, 200)
        self.assertEqual(len(listing["students"]), 1)
        status, updated = self.request(
            "PUT",
            "/students/S001",
            {"name": "Amina Patel", "course": "Data Science"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(updated["course"], "Data Science")
        status, payload = self.request("DELETE", "/students/S001")
        self.assertEqual(status, 204)
        self.assertIsNone(payload)

    def test_expected_errors_are_json(self):
        with self.assertRaises(HTTPError) as context:
            self.request("GET", "/students/missing")
        self.assertEqual(context.exception.code, 404)
        payload = json.loads(context.exception.read())
        self.assertEqual(payload["error"]["code"], "student_not_found")

    def test_invalid_content_type_is_rejected(self):
        request = Request(
            self.base_url + "/students",
            data=b"{}",
            method="POST",
            headers={"Content-Type": "text/plain"},
        )
        with self.assertRaises(HTTPError) as context:
            urlopen(request, timeout=2.0)
        self.assertEqual(context.exception.code, 400)


if __name__ == "__main__":
    unittest.main()
