from __future__ import annotations

import argparse
import os

from auth import check, AuthHealthStatus
from logger import init_logging, get_logger
from paths import CACHE_DIR
from rich.console import Console
from rich.text import Text
from env import reset_env_caches


# ------------------------------------------------------------
# Parser
# ------------------------------------------------------------


def build_auth_parser(subparsers: argparse._SubParsersAction) -> None:
    auth = subparsers.add_parser(
        "auth",
        help="Check OAuth health and reauthenticate if required",
    )

    auth.add_argument("--verbose", action="store_true", help="Verbose console output")
    auth.add_argument("--quiet", action="store_true", help="Suppress console output")

    # future-proofing: provider selection, default youtube
    auth.add_argument(
        "--provider",
        default="youtube",
        help="Auth provider to check (default: youtube)",
    )

    auth.set_defaults(action="auth")


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------


def _set_output_env(args: argparse.Namespace) -> None:
    os.environ["PLAYLISTARR_VERBOSE"] = "1" if args.verbose else "0"
    os.environ["PLAYLISTARR_QUIET"] = "1" if args.quiet else "0"


def _seed_minimal_required_env() -> None:
    """
    Satisfy Environment() requirements without introducing
    profile or log-routing side effects.
    """
    dummy = CACHE_DIR / "auth_dummy.csv"
    if not dummy.exists():
        dummy.write_text("artist\n", encoding="utf-8")

    os.environ.setdefault("PLAYLISTARR_ARTISTS_CSV", str(dummy))
    os.environ.setdefault("PLAYLISTARR_PLAYLIST_ID", "AUTH_CHECK")


def _is_quiet() -> bool:
    return os.environ.get("PLAYLISTARR_QUIET") == "1"


def _is_verbose() -> bool:
    return os.environ.get("PLAYLISTARR_VERBOSE") == "1"


# ------------------------------------------------------------
# Handler
# ------------------------------------------------------------


def handle_auth(args: argparse.Namespace) -> int:
    _set_output_env(args)
    _seed_minimal_required_env()

    # We mutate os.environ in this command; invalidate cached env views.
    reset_env_caches()

    # Ensure auth is global
    os.environ.pop("PLAYLISTARR_PROFILE", None)
    os.environ.pop("PLAYLISTARR_PROFILE_NAME", None)
    os.environ.pop("PLAYLISTARR_RUN_LOG_DIR", None)

    init_logging()
    logger = get_logger("auth")

    console = Console()
    quiet = _is_quiet()
    verbose = _is_verbose()

    # Provider health check is already logged by provider, but keep module-level entry
    logger.info("oauth.check.start")

    result = check(args.provider)

    if result.status == AuthHealthStatus.OK:
        if not quiet:
            msg = Text("OAuth OK", style="green")
            if verbose:
                msg.append(" (token valid and usable)", style="dim")
            console.print(msg)
        return 0

    if result.status == AuthHealthStatus.OK_API_QUOTA:
        if not quiet:
            msg = Text("OAuth OK", style="green")
            msg.append(" (API quota exhausted)", style="yellow")
            console.print(msg)
        return 0

    if result.status == AuthHealthStatus.AUTH_INVALID:
        if not quiet:
            console.print(
                Text("OAuth INVALID – reauthentication required", style="red")
            )
        return 2

    # FAILED
    if not quiet:
        console.print(Text("OAuth check failed (unexpected error)", style="red"))
    return 2
