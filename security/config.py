"""
security/config.py
==================
Central settings for the SmartLogix security layer. Everything is read from
environment variables (via ``.env``) with safe development defaults, so the
project runs out of the box but can be locked down for a real deployment.
"""

from __future__ import annotations

import os
import secrets
import warnings
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # pick up .env at the project root

# security/ -> project root
PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]
SECURITY_DIR: Path = PROJECT_ROOT / "security"


# ---------------------------------------------------------------------------
# Secret key (signs session tokens)
# ---------------------------------------------------------------------------

def _load_or_create_secret_key() -> str:
    """Return the token-signing secret.

    Priority:
      1. ``SMARTLOGIX_SECRET_KEY`` environment variable (use this in production).
      2. A local ``security/.secret_key`` file (auto-created for development so
         tokens survive a server restart). This file is git-ignored.
    """
    from_env = os.getenv("SMARTLOGIX_SECRET_KEY", "").strip()
    if from_env:
        return from_env

    key_file = SECURITY_DIR / ".secret_key"
    try:
        if key_file.exists():
            existing = key_file.read_text(encoding="utf-8").strip()
            if existing:
                return existing
        generated = secrets.token_urlsafe(48)
        key_file.write_text(generated, encoding="utf-8")
        warnings.warn(
            "SMARTLOGIX_SECRET_KEY is not set. Generated a development key at "
            f"{key_file}. Set the env var for production.",
            RuntimeWarning,
            stacklevel=2,
        )
        return generated
    except OSError:
        # Read-only filesystem etc. - fall back to an in-memory key.
        warnings.warn(
            "Could not persist a secret key; using an ephemeral one. Tokens "
            "will be invalidated on restart.",
            RuntimeWarning,
            stacklevel=2,
        )
        return secrets.token_urlsafe(48)


SECRET_KEY: str = _load_or_create_secret_key()

# ---------------------------------------------------------------------------
# Tokens / sessions
# ---------------------------------------------------------------------------

# How long a login stays valid, in seconds (default 8 hours).
TOKEN_TTL_SECONDS: int = int(os.getenv("SMARTLOGIX_TOKEN_TTL", str(8 * 60 * 60)))

# When true, protected endpoints reject requests without a valid token.
# Default false so the demo frontend works without a login screen.
REQUIRE_AUTH: bool = os.getenv("SMARTLOGIX_REQUIRE_AUTH", "false").lower() in {
    "1", "true", "yes", "on",
}

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

# bcrypt work factor. 12 is a good default (~250 ms/hash). Range 4-31.
BCRYPT_ROUNDS: int = max(4, min(31, int(os.getenv("SMARTLOGIX_BCRYPT_ROUNDS", "12"))))

# Password policy.
PASSWORD_MIN_LENGTH: int = 8
PASSWORD_MAX_LENGTH: int = 128  # sane upper bound before pre-hashing

# ---------------------------------------------------------------------------
# User store
# ---------------------------------------------------------------------------

USER_DB_PATH: Path = Path(
    os.getenv("SMARTLOGIX_USER_DB", str(SECURITY_DIR / "users.json"))
)

# A default admin is seeded on first run if the store is empty.
DEFAULT_ADMIN_USERNAME: str = os.getenv("SMARTLOGIX_ADMIN_USER", "admin")
DEFAULT_ADMIN_PASSWORD: str = os.getenv("SMARTLOGIX_ADMIN_PASSWORD", "changeme123")

# ---------------------------------------------------------------------------
# Input sanitisation
# ---------------------------------------------------------------------------

QUERY_MIN_LENGTH: int = 3
QUERY_MAX_LENGTH: int = 500
USERNAME_MIN_LENGTH: int = 3
USERNAME_MAX_LENGTH: int = 32
