"""ASGI application and executable server entry point."""

import argparse
from typing import List, Optional

import uvicorn

from .app import create_app
from .config import Settings

app = create_app()


def build_parser() -> argparse.ArgumentParser:
    settings = Settings()
    parser = argparse.ArgumentParser(description="Run the Enterprise Programming API")
    parser.add_argument("--host", default=settings.host)
    parser.add_argument("--port", type=int, default=settings.port)
    parser.add_argument("--workers", type=int, default=settings.workers)
    parser.add_argument("--reload", action="store_true")
    return parser


def run(argv: Optional[List[str]] = None) -> None:
    args = build_parser().parse_args(argv)
    uvicorn.run(
        "enterprise_programming.api.main:app",
        host=args.host,
        port=args.port,
        workers=args.workers,
        reload=args.reload,
        proxy_headers=True,
    )
