"""
security/fastapi_deps.py
========================
FastAPI dependency-injection helpers that turn a ``Authorization: Bearer
<token>`` header into a :class:`~security.auth.User`.

Usage in an endpoint::

    from security.fastapi_deps import get_current_user, require_admin, enforce_auth

    @app.get("/api/auth/me")
    def me(user = Depends(get_current_user)):        # 401 without a valid token
        return user.public_dict()

    @app.post("/api/delivery")
    def delivery(_user = Depends(enforce_auth)):      # public unless REQUIRE_AUTH
        ...
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .auth import User, decode_access_token, user_store
from .config import REQUIRE_AUTH

__all__ = [
    "get_current_user",
    "get_optional_user",
    "require_admin",
    "enforce_auth",
    "bearer_scheme",
]

# auto_error=False -> we return None instead of FastAPI raising 403 itself,
# so each dependency can craft its own 401 message.
bearer_scheme = HTTPBearer(
    auto_error=False,
    description="Session token returned by POST /api/auth/login",
)

_UNAUTHENTICATED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated. Log in via POST /api/auth/login.",
    headers={"WWW-Authenticate": "Bearer"},
)


def _resolve_user(
    credentials: HTTPAuthorizationCredentials | None,
) -> User | None:
    """Validate the bearer token and load the (active) user, or return None."""
    if credentials is None or not credentials.credentials:
        return None
    token_data = decode_access_token(credentials.credentials)
    if token_data is None:
        return None
    user = user_store.get(token_data.username)
    if user is None or user.disabled:
        return None
    return user


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> User:
    """Dependency: require a valid session token (401 otherwise)."""
    user = _resolve_user(credentials)
    if user is None:
        raise _UNAUTHENTICATED
    return user


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> User | None:
    """Dependency: the user when a valid token is supplied, else ``None``."""
    return _resolve_user(credentials)


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Dependency: require a valid token belonging to an admin (403 otherwise)."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires an administrator account.",
        )
    return user


def enforce_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> User | None:
    """Dependency for endpoints that are public by default but lockable.

    * ``SMARTLOGIX_REQUIRE_AUTH`` off (default): behaves like
      :func:`get_optional_user`.
    * ``SMARTLOGIX_REQUIRE_AUTH`` on: behaves like :func:`get_current_user`.
    """
    user = _resolve_user(credentials)
    if REQUIRE_AUTH and user is None:
        raise _UNAUTHENTICATED
    return user
