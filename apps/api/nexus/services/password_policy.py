"""Password policy enforcement and hashing utilities."""

import re

import bcrypt

from nexus.config import settings


class PasswordPolicyError(ValueError):
    """Raised when a password does not meet policy requirements."""


class PasswordPolicy:
    """Enforces password complexity requirements."""

    @staticmethod
    def validate(password: str) -> None:
        """Validate password against policy. Raises PasswordPolicyError on failure."""
        min_len = settings.password_min_length
        errors: list[str] = []

        if len(password) < min_len:
            errors.append(f"Password must be at least {min_len} characters")
        if not re.search(r"[A-Z]", password):
            errors.append("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", password):
            errors.append("Password must contain at least one lowercase letter")
        if not re.search(r"\d", password):
            errors.append("Password must contain at least one digit")
        if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?`~]", password):
            errors.append("Password must contain at least one special character")

        if errors:
            raise PasswordPolicyError("; ".join(errors))

    @staticmethod
    def hash(password: str) -> str:
        """Hash a password with bcrypt."""
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    @staticmethod
    def verify(password: str, hashed: str) -> bool:
        """Verify a password against its bcrypt hash."""
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
