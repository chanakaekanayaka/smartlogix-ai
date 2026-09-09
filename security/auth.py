"""
security/auth.py
================
Password hashing, user records and session tokens for SmartLogix.

* :func:`hash_password` / :func:`verify_password` - bcrypt (with a SHA-256
  pre-hash so long passwords are not silently truncated at 72 bytes).
* :class:`UserStore` - a small JSON-file-backed user table with a default
  admin seeded on first run.
* :func:`create_access_token` / :func:`decode_access_token` - stateless
  HMAC-signed session tokens with an expiry (no extra dependencies).
* :func:`authenticate` / :func:`login` - the functions the FastAPI layer
  calls.

This module has **no FastAPI dependency** - the request-time glue lives in
``security/fastapi_deps.py``.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import warnings
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import bcrypt

from .config import (
    BCRYPT_ROUNDS,
    DEFAULT_ADMIN_PASSWORD,
    DEFAULT_ADMIN_USERNAME,
    PASSWORD_MAX_LENGTH,
    PASSWORD_MIN_LENGTH,
    SECRET_KEY,
    TOKEN_TTL_SECONDS,
    USER_DB_PATH,
    USERNAME_MAX_LENGTH,
    USERNAME_MIN_LENGTH,
)
from .sanitization import UnsafeInputError, sanitize_identifier

__all__ = [
    "AuthError",
    "PasswordPolicyError",
    "User",
    "UserStore",
    "TokenData",
    "hash_password",
    "verify_password",
    "validate_password_strength",
    "create_access_token",
    "decode_access_token",
    "authenticate",
    "login",
    "user_store",
]


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class AuthError(Exception):
    """Login failed (bad credentials, disabled account, ...)."""


class PasswordPolicyError(ValueError):
    """A password does not meet the strength policy."""


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

def _prehash(password: str) -> bytes:
    """SHA-256 + base64 so any-length password fits bcrypt's 72-byte input.

    Without this, bcrypt silently ignores everything past the 72nd byte -
    a subtle way for long passwords to become weak. (passlib / Django use
    the same trick.)
    """
    digest = hashlib.sha256(password.encode("utf-8")).digest()
    return base64.b64encode(digest)  # 44 ASCII bytes


def hash_password(password: str) -> str:
    """Return a bcrypt hash string for ``password``.

    Raises:
        ValueError: the password is empty or not a string.
    """
    if not isinstance(password, str) or not password:
        raise ValueError("Password must be a non-empty string.")
    hashed = bcrypt.hashpw(_prehash(password), bcrypt.gensalt(rounds=BCRYPT_ROUNDS))
    return hashed.decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    """Return True if ``password`` matches ``password_hash``. Never raises."""
    try:
        return bcrypt.checkpw(_prehash(password), password_hash.encode("ascii"))
    except (ValueError, TypeError, AttributeError):
        return False


# A real hash of a random string, compared against when a username is unknown
# so that "user not found" and "wrong password" take a similar amount of time.
_DUMMY_HASH: str = hash_password("smartlogix-timing-equaliser")

_COMMON_PASSWORDS: frozenset[str] = frozenset({
    "password", "password1", "password123", "12345678", "123456789",
    "qwerty", "qwerty123", "admin", "admin123", "letmein", "welcome",
    "iloveyou", "abc12345", "changeme",
})


def validate_password_strength(password: str) -> None:
    """Raise :class:`PasswordPolicyError` if the password is too weak."""
    if not isinstance(password, str):
        raise PasswordPolicyError("Password must be text.")
    if len(password) < PASSWORD_MIN_LENGTH:
        raise PasswordPolicyError(
            f"Password must be at least {PASSWORD_MIN_LENGTH} characters."
        )
    if len(password) > PASSWORD_MAX_LENGTH:
        raise PasswordPolicyError(
            f"Password must be at most {PASSWORD_MAX_LENGTH} characters."
        )
    if password.lower() in _COMMON_PASSWORDS:
        raise PasswordPolicyError("That password is too common.")
    character_classes = sum((
        any(c.islower() for c in password),
        any(c.isupper() for c in password),
        any(c.isdigit() for c in password),
        any(not c.isalnum() for c in password),
    ))
    if character_classes < 2:
        raise PasswordPolicyError(
            "Password must combine at least two of: lower case, upper case, "
            "digits, symbols."
        )


# ---------------------------------------------------------------------------
# Session tokens (stateless, HMAC-signed)
# ---------------------------------------------------------------------------

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sign(body: str) -> str:
    digest = hmac.new(SECRET_KEY.encode("utf-8"), body.encode("ascii"), hashlib.sha256)
    return _b64url_encode(digest.digest())


@dataclass(frozen=True)
class TokenData:
    """The verified contents of a session token."""

    username: str
    role: str
    expires_at: int


def create_access_token(
    username: str, role: str = "user", ttl_seconds: int | None = None
) -> str:
    """Create a signed ``<payload>.<signature>`` session token."""
    now = int(time.time())
    payload = {
        "sub": username,
        "role": role,
        "iat": now,
        "exp": now + int(ttl_seconds if ttl_seconds is not None else TOKEN_TTL_SECONDS),
    }
    body = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    return f"{body}.{_sign(body)}"


def decode_access_token(token: str) -> TokenData | None:
    """Verify a token's signature + expiry. Return its data, or ``None``."""
    if not isinstance(token, str) or token.count(".") != 1:
        return None
    body, signature = token.split(".", 1)

    # Constant-time signature check.
    if not hmac.compare_digest(signature, _sign(body)):
        return None

    try:
        payload = json.loads(_b64url_decode(body))
    except (ValueError, json.JSONDecodeError):
        return None

    if not isinstance(payload, dict) or "sub" not in payload or "exp" not in payload:
        return None
    try:
        expires_at = int(payload["exp"])
    except (TypeError, ValueError):
        return None
    if expires_at < int(time.time()):
        return None

    return TokenData(
        username=str(payload["sub"]),
        role=str(payload.get("role", "user")),
        expires_at=expires_at,
    )


# ---------------------------------------------------------------------------
# User records + store
# ---------------------------------------------------------------------------

@dataclass
class User:
    """A stored user account."""

    username: str
    password_hash: str
    role: str = "user"
    disabled: bool = False
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    def public_dict(self) -> dict[str, object]:
        """The account without its password hash - safe to send to a client."""
        return {
            "username": self.username,
            "role": self.role,
            "disabled": self.disabled,
            "created_at": self.created_at,
        }


class UserStore:
    """A tiny JSON-file-backed user table.

    Fine for a coursework project / small deployment. Swap the ``_load`` /
    ``_save`` methods for a real database to scale up.
    """

    def __init__(self, path: str | Path = USER_DB_PATH, *, seed_admin: bool = True) -> None:
        self._path = Path(path)
        self._users: dict[str, User] = {}
        self._load()
        if seed_admin:
            self._seed_default_admin()

    # --- persistence -----------------------------------------------------

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"User store at {self._path} is unreadable: {exc}") from exc
        if not isinstance(raw, dict):
            raise RuntimeError(f"User store at {self._path} has an invalid format.")
        for record in raw.values():
            try:
                user = User(**record)
            except TypeError:
                continue  # skip malformed rows rather than crash
            self._users[user.username.lower()] = user

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {user.username: asdict(user) for user in self._users.values()}
        tmp = self._path.with_name(self._path.name + ".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp.replace(self._path)  # atomic on the same filesystem

    def _seed_default_admin(self) -> None:
        if self._users:
            return
        try:
            self.create_user(
                DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD, role="admin"
            )
            warnings.warn(
                f"No users found - seeded default admin "
                f"'{DEFAULT_ADMIN_USERNAME}'. Change its password immediately "
                f"(set SMARTLOGIX_ADMIN_PASSWORD or use UserStore.set_password).",
                RuntimeWarning,
                stacklevel=2,
            )
        except (ValueError, UnsafeInputError) as exc:
            warnings.warn(f"Could not seed default admin: {exc}", RuntimeWarning)

    # --- queries -------------------------------------------------------

    def get(self, username: str) -> User | None:
        return self._users.get(str(username).strip().lower())

    def list_users(self) -> list[User]:
        return sorted(self._users.values(), key=lambda u: u.username.lower())

    # --- mutations ---------------------------------------------------

    def create_user(self, username: str, password: str, *, role: str = "user") -> User:
        """Register a new user. Raises ``ValueError`` on any policy violation."""
        clean_name = sanitize_identifier(username, field_name="username")
        if not USERNAME_MIN_LENGTH <= len(clean_name) <= USERNAME_MAX_LENGTH:
            raise ValueError(
                f"Username must be {USERNAME_MIN_LENGTH}-{USERNAME_MAX_LENGTH} "
                f"characters (letters, digits, . _ -)."
            )
        if role not in {"user", "admin"}:
            raise ValueError("Role must be 'user' or 'admin'.")
        if self.get(clean_name) is not None:
            raise ValueError(f"User '{clean_name}' already exists.")

        validate_password_strength(password)
        user = User(
            username=clean_name, password_hash=hash_password(password), role=role
        )
        self._users[clean_name.lower()] = user
        self._save()
        return user

    def set_password(self, username: str, new_password: str) -> None:
        user = self.get(username)
        if user is None:
            raise ValueError(f"No such user: {username}")
        validate_password_strength(new_password)
        user.password_hash = hash_password(new_password)
        self._save()

    def set_disabled(self, username: str, disabled: bool) -> None:
        user = self.get(username)
        if user is None:
            raise ValueError(f"No such user: {username}")
        user.disabled = disabled
        self._save()

    def verify_credentials(self, username: str, password: str) -> User | None:
        """Return the user if the password is correct, else ``None``."""
        user = self.get(username)
        if user is None:
            verify_password(password, _DUMMY_HASH)  # equalise timing
            return None
        if user.disabled:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user


# Module-level singleton used by the FastAPI layer.
user_store = UserStore()


# ---------------------------------------------------------------------------
# High-level auth functions
# ---------------------------------------------------------------------------

def authenticate(username: str, password: str) -> User:
    """Return the :class:`User` for valid credentials, else raise :class:`AuthError`."""
    user = user_store.verify_credentials(username, password)
    if user is None:
        raise AuthError("Invalid username or password.")
    return user


def login(username: str, password: str) -> dict[str, object]:
    """Authenticate and return a token bundle ready to hand back to a client.

    Raises:
        AuthError: the credentials are wrong or the account is disabled.
    """
    user = authenticate(username, password)
    token = create_access_token(user.username, user.role)
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": TOKEN_TTL_SECONDS,
        "user": user.public_dict(),
    }


# ---------------------------------------------------------------------------
# Standalone test hook
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import tempfile

    print("SmartLogix auth - self test")
    print("=" * 60)

    # --- password hashing ---------------------------------------------
    pw = "Sl-Str0ng!pass"
    h = hash_password(pw)
    print(f"\nhash_password('{pw}') -> {h[:32]}...")
    print("verify correct password :", verify_password(pw, h))
    print("verify wrong password   :", verify_password("wrong", h))
    print("verify against garbage  :", verify_password(pw, "not-a-hash"))
    long_pw = "A1!" + "x" * 200
    print("long (>72 byte) password roundtrip:", verify_password(long_pw, hash_password(long_pw)))

    # --- password policy --------------------------------------------
    for candidate in ["short", "alllowercase", "password123", "Good-Pass-9"]:
        try:
            validate_password_strength(candidate)
            print(f"policy OK      : {candidate!r}")
        except PasswordPolicyError as exc:
            print(f"policy rejects : {candidate!r} -> {exc}")

    # --- tokens ----------------------------------------------------
    tok = create_access_token("alice", role="admin", ttl_seconds=60)
    print(f"\ntoken: {tok[:40]}...")
    data = decode_access_token(tok)
    print("decoded:", data)
    print("tampered token rejected:", decode_access_token(tok[:-2] + "xx") is None)
    expired = create_access_token("bob", ttl_seconds=-10)
    print("expired token rejected :", decode_access_token(expired) is None)

    # --- user store (temp file) --------------------------------
    with tempfile.TemporaryDirectory() as tmp:
        store = UserStore(Path(tmp) / "users.json", seed_admin=False)
        store.create_user("chanaka", "Logi5tix!23", role="admin")
        print("\ncreated user:", store.get("chanaka").public_dict())
        print("login OK  :", store.verify_credentials("chanaka", "Logi5tix!23") is not None)
        print("login bad :", store.verify_credentials("chanaka", "nope") is None)
        print("unknown   :", store.verify_credentials("ghost", "whatever") is None)
        try:
            store.create_user("chanaka", "Another1!")
        except ValueError as exc:
            print("duplicate rejected:", exc)
