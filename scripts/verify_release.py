#!/usr/bin/env python3
"""
verify_release.py

Quick verification that the project is ready for public release.
Run this before your first git commit.
This script can be run from anywhere but operates on the project root.
"""

import os
import sys
from pathlib import Path
from typing import List
import re

# Change to project root (parent of scripts directory)
script_dir = Path(__file__).parent
project_root = script_dir.parent
os.chdir(project_root)

# ANSI color codes
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


def check_mark(passed: bool) -> str:
    """Return checkmark or X based on pass/fail."""
    return f"{GREEN}Pass{RESET}" if passed else f"{RED}FAIL{RESET}"


def check_file_exists(path: str, description: str) -> bool:
    """Check if a file exists."""
    exists = Path(path).exists()
    logger.debug(f"{check_mark(exists)}: {description}")
    return exists


def check_file_not_exists(path: str, description: str) -> bool:
    """Check that a sensitive file doesn't exist."""
    exists = Path(path).exists()
    not_exists = not exists
    symbol = check_mark(not_exists)
    status = "not present (good)" if not_exists else "exists (SHOULD BE IN .gitignore)"
    logger.debug(f"{symbol}: {description} - {status}")
    return not_exists


def check_no_secrets(
    pattern: str, description: str, exclude_files: List[str] = None
) -> bool:
    """Check that no files contain the secret pattern."""
    exclude_files = exclude_files or []
    found_in = []

    for root, dirs, files in os.walk("."):
        # Skip directories
        dirs[:] = [
            d
            for d in dirs
            if d
            not in [".git", ".venv", "venv", "__pycache__", "node_modules", "scripts"]
        ]

        for file in files:
            if not file.endswith(".py") and not file.endswith(".md"):
                continue
            if file in exclude_files:
                continue

            filepath = Path(root) / file
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    if re.search(pattern, content):
                        found_in.append(str(filepath))
            except Exception:
                pass

    passed = len(found_in) == 0
    logger.debug(f"{check_mark(passed)}: No {description}")

    if not passed:
        for filepath in found_in:
            logger.debug(f"  {RED}Found in: {filepath}{RESET}")

    return passed


def check_imports() -> bool:
    """Test that all core modules can be imported."""
    modules = ["config", "filters", "utils", "api_manager"]
    all_passed = True

    for module in modules:
        try:
            __import__(module)
            logger.debug(f"{GREEN}Pass{RESET}: {module}.py imports OK")
        except Exception as e:
            logger.debug(f"{RED}FAIL{RESET}: {module}.py import failed: {e}")
            all_passed = False

    return all_passed


def main():
    """Main verification function."""
    logger.debug(f"{BOLD}{BLUE}{'=' * 60}{RESET}")
    logger.debug(f"{BOLD}{BLUE}Playlistarr - Release Verification{RESET}")
    logger.debug(f"{BOLD}{BLUE}{'=' * 60}{RESET}")
    logger.debug(f"Working directory: {project_root}\n")

    errors = 0
    warnings = 0

    # 1. Required Files
    logger.debug(f"{BOLD}{YELLOW}1. Checking Required Files...{RESET}")
    required_files = [
        ("README.md", "README"),
        ("LICENSE", "License"),
        ("CONTRIBUTING.md", "Contributing guide"),
        ("CHANGELOG.md", "Changelog"),
        (".gitignore", ".gitignore"),
        ("requirements.txt", "Requirements"),
        (".env.example", ".env example"),
        ("config.sample.py", "Config sample"),
    ]

    for path, desc in required_files:
        if not check_file_exists(path, desc):
            errors += 1

    logger.debug()

    # 2. Core Scripts
    logger.debug(f"{BOLD}{YELLOW}2. Checking Core Scripts...{RESET}")
    core_scripts = [
        ("config.py", "Config"),
        ("filters.py", "Filters"),
        ("utils.py", "Utils"),
        ("api_manager.py", "API Manager"),
        ("client.py", "Client"),
        ("discover_music_videos.py", "Discovery script"),
        ("youtube_playlist_sync.py", "Sync script"),
        ("playlist_invalidate.py", "Invalidation plan"),
        ("playlist_apply_invalidation.py", "Invalidation apply"),
    ]

    for path, desc in core_scripts:
        if not check_file_exists(path, desc):
            errors += 1

    logger.debug()

    # 3. Security - Sensitive Files
    logger.debug(f"{BOLD}{YELLOW}3. Security Check - Sensitive Files...{RESET}")
    sensitive_files = [
        ("auth/client_secrets.json", "OAuth secrets"),
        ("auth/oauth_token.json", "OAuth token"),
        (".env", ".env file"),
        ("config_local.py", "Local config"),
    ]

    for path, desc in sensitive_files:
        if not check_file_not_exists(path, desc):
            warnings += 1

    logger.debug()

    # 4. Security - API Keys in Code
    logger.debug(f"{BOLD}{YELLOW}4. Security Check - API Keys in Code...{RESET}")

    # Note: We exclude files that are samples/documentation/scripts
    exclude_list = [
        "verify_release.py",
        "cleanup_for_release.ps1",
        "REFACTORING_SUMMARY.md",
        "config.sample.py",
        "SETUP.md",
    ]

    GOOGLE_API_KEY_REGEX = r"AIzaSy[A-Za-z0-9_-]{33}"

    if not check_no_secrets(GOOGLE_API_KEY_REGEX, "exposed API keys", exclude_list):
        errors += 1

    # Don't check for "client_secret" in client.py since it's the module name
    exclude_list_client = exclude_list + ["client.py"]

    logger.debug()

    # 5. Import Tests
    logger.debug(f"{BOLD}{YELLOW}5. Testing Python Imports...{RESET}")
    if not check_imports():
        errors += 1

    logger.debug()

    # 6. .gitignore Check
    logger.debug(f"{BOLD}{YELLOW}6. Checking .gitignore...{RESET}")
    if Path(".gitignore").exists():
        with open(".gitignore", "r") as f:
            gitignore = f.read()

        required_patterns = ["auth/", "cache/", "out/", ".env", "*.pyc", "__pycache__"]
        for pattern in required_patterns:
            if pattern in gitignore:
                logger.debug(f"{GREEN}Pass{RESET}: .gitignore contains '{pattern}'")
            else:
                logger.debug(f"{RED}FAIL{RESET}: .gitignore missing '{pattern}'")
                errors += 1
    else:
        logger.debug(f"{RED}FAIL{RESET}: .gitignore file missing!")
        errors += 1

    logger.debug()

    # 7. GitHub Configuration
    logger.debug(f"{BOLD}{YELLOW}7. Checking GitHub Configuration...{RESET}")
    github_files = [
        (".github/workflows/ci.yml", "GitHub Actions CI"),
        (".github/ISSUE_TEMPLATE/bug_report.md", "Bug report template"),
        (".github/ISSUE_TEMPLATE/feature_request.md", "Feature request template"),
    ]

    for path, desc in github_files:
        if not check_file_exists(path, desc):
            errors += 1

    logger.debug()

    # Summary
    logger.debug(f"{BOLD}{BLUE}{'=' * 60}{RESET}\n")

    if errors == 0 and warnings == 0:
        logger.debug(f"{BOLD}{GREEN}SUCCESS! Project is ready for public release!{RESET}\n")
        logger.debug(f"{BLUE}Next steps:{RESET}")
        logger.debug("  1. Review all files one more time")
        logger.debug("  2. Create GitHub repository")
        logger.debug("  3. git init")
        logger.debug("  4. git add .")
        logger.debug("  5. git commit -m 'Initial commit - v1.0.0'")
        logger.debug("  6. git push\n")
        return 0
    elif errors == 0:
        logger.debug(
            f"{BOLD}{YELLOW}Project has {warnings} warnings but is OK to release{RESET}\n"
        )
        logger.debug("Review warnings above and fix if needed.\n")
        return 0
    else:
        logger.debug(
            f"{BOLD}{RED}Project has {errors} errors and {warnings} warnings!{RESET}\n"
        )
        logger.debug("Fix all errors before releasing!\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
