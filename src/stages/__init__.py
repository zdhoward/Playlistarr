# src/stages/__init__.py
import logging
from env import get_env

env = get_env()
logging.getLogger().setLevel(logging.DEBUG if env.verbose else logging.INFO)
