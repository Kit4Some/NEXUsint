"""Production configuration overlay — enforces required security settings."""

import os
import sys

from nexus.config import settings

_REQUIRED_SECRETS = [
    ("JWT_SECRET", settings.jwt_secret),
    ("NEO4J_PASSWORD", settings.neo4j_password),
    ("POSTGRES_PASSWORD", settings.postgres_password),
]

_INSECURE_DEFAULTS = {
    "change-this-to-a-random-secret-key",
    "nexus_secret_2025",
    "nexus_pg_secret",
}


def validate_production_config() -> list[str]:
    """Validate production configuration. Returns list of issues found."""
    issues: list[str] = []

    for name, value in _REQUIRED_SECRETS:
        if not value:
            issues.append(f"{name} is not set")
        elif value in _INSECURE_DEFAULTS:
            issues.append(f"{name} is using an insecure default value")

    if settings.debug:
        issues.append("DEBUG mode is enabled — disable for production")

    cors_origins = settings.cors_origin_list
    if any("*" in origin for origin in cors_origins):
        issues.append("CORS allows wildcard origins — restrict for production")

    return issues


def enforce_production_config() -> None:
    """Enforce production configuration. Exits if critical issues found."""
    if os.environ.get("NEXUS_ENV") != "production":
        return

    issues = validate_production_config()
    if issues:
        print("Production configuration errors:", file=sys.stderr)
        for issue in issues:
            print(f"  - {issue}", file=sys.stderr)
        sys.exit(1)
