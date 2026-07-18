"""CLI helper: wypisuje hash bcrypt do wstawienia do USERS.PASSWORD_HASH."""

from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from backend.services.auth_service import hash_password


def _configure_stdio_utf8() -> None:
    """Konfiguruje strumienie wejścia/wyjścia na UTF-8."""
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    """Główna funkcja programu."""
    # Konfiguracja strumieni wejścia/wyjścia na UTF-8
    _configure_stdio_utf8()
    parser = argparse.ArgumentParser(
        description="Hash a password with bcrypt for USERS seed inserts")
    parser.add_argument(
        "password",
        nargs="?",
        help="Plain-text password (prompted when omitted)")
    args = parser.parse_args(argv)

    plain = args.password
    if not plain:
        plain = getpass.getpass("Password: ")
    if not plain:
        print("Password must not be empty", file=sys.stderr)

    print(hash_password(plain))


if __name__ == "__main__":
    main()