"""
Utility modules for protein passport automation.
"""
from .file_utils import (
    ensure_directory,
    safe_write_text,
    safe_write_bytes,
    safe_open_write
)

__all__ = [
    'ensure_directory',
    'safe_write_text',
    'safe_write_bytes',
    'safe_open_write'
]

