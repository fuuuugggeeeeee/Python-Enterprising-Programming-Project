"""FastAPI application factory."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHttpException
from starlette.middleware.gzip import GZipMiddleware

from enterprise_programming import __version__

from .config import Settings
from .database import Database
from .errors import ApiError
from .observability import RequestObservabilityMiddleware, configure_logging
from .rate_limit import RateLimitMiddleware
from .routers import audit, auth, health, students, users
from .services import ApiService


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


def create_app(
    settings: Optional[Settings] = None,
    database: Optional[Database] = None,
) -> FastAPI:
    application_settings = settings or Settings()
    application_database = database or Database(application_settings.database_url)
    configure_logging(application_settings.log_level, application_settings.json_logs)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if application_settings.bootstrap_admin_password:
            with application_database.session() as session:
                ApiService(session).create_bootstrap_admin(
                    application_settings.bootstrap_admin_username,
                    application_settings.bootstrap_admin_password,
                )
        yield
        application_database.dispose()

    app = FastAPI(
        title=application_settings.app_name,
        version=__version__,
        summary="Authenticated student-management API with auditable persistence",
        description=(
            "A portfolio backend demonstrating PostgreSQL persistence, JWT authentication, "
            "role-based access, optimistic concurrency, migrations, metrics, and structured logs."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.state.settings = application_settings
    app.state.database = application_database

    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=application_settings.rate_limit_per_minute,
    )
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    if application_settings.allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=application_settings.allowed_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
            allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        )
    app.add_middleware(RequestObservabilityMiddleware)

    app.include_router(health.router)
    api_prefix = "/api/v1"
    app.include_router(auth.router, prefix=api_prefix)
    app.include_router(users.router, prefix=api_prefix)
    app.include_router(students.router, prefix=api_prefix)
    app.include_router(audit.router, prefix=api_prefix)

    @app.get("/", tags=["operations"])
    def index() -> dict:
        return {
            "name": application_settings.app_name,
            "version": __version__,
            "documentation": "/docs",
            "health": "/health/ready",
        }

    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, error: ApiError) -> JSONResponse:
        headers = {"WWW-Authenticate": "Bearer"} if error.status_code == 401 else None
        return JSONResponse(
            status_code=error.status_code,
            headers=headers,
            content={
                "error": {
                    "code": error.code,
                    "message": error.message,
                    "request_id": _request_id(request),
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request,
        error: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Request validation failed",
                    "request_id": _request_id(request),
                    "details": jsonable_encoder(error.errors()),
                }
            },
        )

    @app.exception_handler(StarletteHttpException)
    async def http_error_handler(
        request: Request,
        error: StarletteHttpException,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=error.status_code,
            content={
                "error": {
                    "code": "http_error",
                    "message": str(error.detail),
                    "request_id": _request_id(request),
                }
            },
        )

    @app.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, error: Exception) -> JSONResponse:
        logging.getLogger("enterprise_programming.api").exception(
            "request.failed",
            extra={"request_id": _request_id(request)},
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "An unexpected error occurred",
                    "request_id": _request_id(request),
                }
            },
        )

    return app
