import json
import logging

from enterprise_programming.api.main import build_parser
from enterprise_programming.api.observability import JsonFormatter


def test_json_formatter_emits_structured_request_fields() -> None:
    record = logging.LogRecord(
        name="enterprise_programming.api",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="request.completed",
        args=(),
        exc_info=None,
    )
    record.request_id = "request-123"
    record.method = "GET"
    record.path = "/health/ready"
    record.status_code = 200
    record.duration_ms = 1.25
    document = json.loads(JsonFormatter().format(record))
    assert document["message"] == "request.completed"
    assert document["request_id"] == "request-123"
    assert document["status_code"] == 200
    assert document["duration_ms"] == 1.25


def test_api_command_parser_accepts_deployment_options() -> None:
    args = build_parser().parse_args(["--host", "0.0.0.0", "--port", "9000", "--workers", "3"])
    assert args.host == "0.0.0.0"
    assert args.port == 9000
    assert args.workers == 3
