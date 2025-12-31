from __future__ import annotations

import logging


class ContextFilter(logging.Filter):
    """
    Injects contextual attributes into LogRecord.
    Does not mutate message, args, or level.
    """

    def __init__(self, **context):
        super().__init__()
        self.context = context

    def filter(self, record: logging.LogRecord) -> bool:
        for k, v in self.context.items():
            setattr(record, k, v)
        return True
