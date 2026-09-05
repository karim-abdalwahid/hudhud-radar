"""
Structured Logger for SocailManager with sensitive data masking.
"""
import logging
import re
import sys
from typing import Any, Dict

# Regex patterns to sanitize sensitive tokens, keys, and passwords
SENSITIVE_PATTERNS = [
    (re.compile(r'(token["\s:=]+)([a-zA-Z0-9_\-\.]{8,})', re.IGNORECASE), r'\1***REDACTED***'),
    (re.compile(r'(key["\s:=]+)([a-zA-Z0-9_\-\.]{8,})', re.IGNORECASE), r'\1***REDACTED***'),
    (re.compile(r'(secret["\s:=]+)([a-zA-Z0-9_\-\.]{8,})', re.IGNORECASE), r'\1***REDACTED***'),
    (re.compile(r'(password["\s:=]+)(.+)', re.IGNORECASE), r'\1***REDACTED***'),
]


class SensitiveDataFilter(logging.Filter):
    """Filter that masks sensitive tokens and credentials from log messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            for pattern, repl in SENSITIVE_PATTERNS:
                record.msg = pattern.sub(repl, record.msg)
        return True


def get_logger(name: str = "SocailManager") -> logging.Logger:
    """Returns a configured logger instance with security filtering."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)

        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        handler.addFilter(SensitiveDataFilter())
        logger.addHandler(handler)
        logger.propagate = False

    return logger


logger = get_logger()
