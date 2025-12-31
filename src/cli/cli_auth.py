from __future__ import annotations

import argparse

from env import reset_env_caches
from logger import get_logger

log = get_logger(__name__)


def build_auth_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "auth",
        help="Check OAuth health and reauthenticate if required",
    )
    parser.set_defaults(command="auth")


def handle_auth(args: argparse.Namespace) -> int:
    """
    Auth command entrypoint.
    Logging is already initialized by playlistarr.py.
    """

    # Import lazily to avoid side effects at import time
    from auth.health import check

    log.info("Checking OAuth health")

    # This may mutate env vars (token refresh, etc.)
    check()

    # Ensure env consumers see updated state
    reset_env_caches()

    log.info("OAuth check complete")
    return 0
