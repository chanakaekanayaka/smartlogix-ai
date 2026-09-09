"""
security/manage.py
==================
Tiny command-line tool for the SmartLogix user store.

    python -m security.manage list
    python -m security.manage add <username> <password> [--admin]
    python -m security.manage passwd <username> <new-password>
    python -m security.manage disable <username>
    python -m security.manage enable <username>

The first thing to do after setup is change the seeded admin password:

    python -m security.manage passwd admin "A-Much-Better-Pass-1"
"""

from __future__ import annotations

import argparse
import sys

from .auth import PasswordPolicyError, user_store
from .sanitization import UnsafeInputError


def _cmd_list(_args: argparse.Namespace) -> int:
    users = user_store.list_users()
    if not users:
        print("(no users)")
        return 0
    for user in users:
        flags = " ".join(
            tag for tag, on in (("admin", user.is_admin), ("disabled", user.disabled)) if on
        )
        print(f"  {user.username:<20} {user.role:<7} {user.created_at}  {flags}".rstrip())
    return 0


def _cmd_add(args: argparse.Namespace) -> int:
    try:
        user = user_store.create_user(
            args.username, args.password, role="admin" if args.admin else "user"
        )
    except (ValueError, PasswordPolicyError, UnsafeInputError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"created {user.role} '{user.username}'")
    return 0


def _cmd_passwd(args: argparse.Namespace) -> int:
    try:
        user_store.set_password(args.username, args.password)
    except (ValueError, PasswordPolicyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"password updated for '{args.username}'")
    return 0


def _cmd_set_disabled(args: argparse.Namespace, disabled: bool) -> int:
    try:
        user_store.set_disabled(args.username, disabled)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"'{args.username}' {'disabled' if disabled else 'enabled'}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m security.manage")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="list all users").set_defaults(func=_cmd_list)

    add = sub.add_parser("add", help="create a user")
    add.add_argument("username")
    add.add_argument("password")
    add.add_argument("--admin", action="store_true", help="give the admin role")
    add.set_defaults(func=_cmd_add)

    passwd = sub.add_parser("passwd", help="change a user's password")
    passwd.add_argument("username")
    passwd.add_argument("password")
    passwd.set_defaults(func=_cmd_passwd)

    disable = sub.add_parser("disable", help="disable a user")
    disable.add_argument("username")
    disable.set_defaults(func=lambda a: _cmd_set_disabled(a, True))

    enable = sub.add_parser("enable", help="re-enable a user")
    enable.add_argument("username")
    enable.set_defaults(func=lambda a: _cmd_set_disabled(a, False))

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
