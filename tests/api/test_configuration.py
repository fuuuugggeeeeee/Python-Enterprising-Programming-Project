import pytest
from pydantic import ValidationError

from enterprise_programming.api.config import Settings


def test_production_rejects_default_security_values() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            environment="production",
            bootstrap_admin_password="strong-admin-password",
        )


def test_production_accepts_explicit_secrets() -> None:
    settings = Settings(
        _env_file=None,
        environment="production",
        jwt_secret="a-unique-production-secret-with-more-than-32-characters",
        bootstrap_admin_password="strong-admin-password",
    )
    assert settings.environment == "production"


def test_production_rejects_placeholder_admin_password() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            environment="production",
            jwt_secret="a-unique-production-secret-with-more-than-32-characters",
            bootstrap_admin_password="replace-with-a-password",
        )
