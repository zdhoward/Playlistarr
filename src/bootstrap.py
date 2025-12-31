from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from env import PROJECT_ROOT, reset_env_caches, _load_dotenv


def bootstrap_base_env(
    config_dir: str = "config",
    env_file: str = ".env",
    required: bool = False,
) -> None:
    """
    Load PROJECT_ROOT/<config_dir>/<env_file> into os.environ.

    - Silent
    - Never overrides existing vars
    - Can be required if you want (required=True)
    """
    dotenv_path = (PROJECT_ROOT / config_dir / env_file).resolve()

    if required and not dotenv_path.exists():
        raise RuntimeError(
            f"Missing required env file: {dotenv_path}\n"
            f"Expected {config_dir}/{env_file} relative to project root."
        )

    _load_dotenv(dotenv_path)
    reset_env_caches()


def bootstrap_run_context(
    command: Optional[str] = None,
    profile_name: Optional[str] = None,
    profile_path: Optional[str] = None,
    artists_csv: Optional[str] = None,
    playlist_id: Optional[str] = None,
    verbose: Optional[bool] = None,
    quiet: Optional[bool] = None,
    interactive: Optional[bool] = None,
) -> None:
    """
    Stamp run context into environment variables so subprocess stages inherit them.
    """
    if command is not None:
        os.environ["PLAYLISTARR_COMMAND"] = str(command)

    if profile_path is not None:
        os.environ["PLAYLISTARR_PROFILE_PATH"] = str(profile_path)

    if artists_csv is not None:
        os.environ["PLAYLISTARR_ARTISTS_CSV"] = str(artists_csv)

    if playlist_id is not None:
        os.environ["PLAYLISTARR_PLAYLIST_ID"] = str(playlist_id)

    if profile_name is not None:
        os.environ["PLAYLISTARR_PROFILE_NAME"] = str(profile_name)
    else:
        os.environ.pop("PLAYLISTARR_PROFILE_NAME", None)

    if verbose is not None:
        os.environ["PLAYLISTARR_VERBOSE"] = "1" if verbose else "0"

    if quiet is not None:
        os.environ["PLAYLISTARR_QUIET"] = "1" if quiet else "0"

    if interactive is not None:
        os.environ["PLAYLISTARR_UI"] = "1" if interactive else "0"

    reset_env_caches()
