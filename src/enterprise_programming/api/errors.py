"""Stable API error types."""


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


class AuthenticationError(ApiError):
    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(401, "authentication_required", message)


class AuthorizationError(ApiError):
    def __init__(self, message: str = "Administrator access required") -> None:
        super().__init__(403, "forbidden", message)


class NotFoundError(ApiError):
    def __init__(self, resource: str) -> None:
        super().__init__(404, "not_found", "{} not found".format(resource))


class ConflictError(ApiError):
    def __init__(self, message: str) -> None:
        super().__init__(409, "conflict", message)
