"""Security helpers for SmartLogix.

* :mod:`security.auth` - bcrypt password hashing, user records, session tokens.
* :mod:`security.sanitization` - clean / validate free-text before it reaches
  the agents or the LLM.
* :mod:`security.fastapi_deps` - FastAPI dependencies (``get_current_user`` ...).
* :mod:`security.config` - environment-driven settings.

Common entry points are re-exported here for convenience::

    from security import hash_password, verify_password, login, clean_query
"""

from .auth import (
    AuthError,
    PasswordPolicyError,
    TokenData,
    User,
    UserStore,
    authenticate,
    create_access_token,
    decode_access_token,
    hash_password,
    login,
    user_store,
    validate_password_strength,
    verify_password,
)
from .sanitization import (
    SanitizationResult,
    UnsafeInputError,
    clean_query,
    sanitize_identifier,
    sanitize_query,
)

__all__ = [
    # auth
    "AuthError",
    "PasswordPolicyError",
    "TokenData",
    "User",
    "UserStore",
    "authenticate",
    "create_access_token",
    "decode_access_token",
    "hash_password",
    "login",
    "user_store",
    "validate_password_strength",
    "verify_password",
    # sanitization
    "SanitizationResult",
    "UnsafeInputError",
    "clean_query",
    "sanitize_identifier",
    "sanitize_query",
]
