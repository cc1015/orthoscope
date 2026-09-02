"""
Utility functions for file operations with proper error handling and permissions.
Handles macOS permission issues and provides helpful error messages.
"""
import os
import stat
from pathlib import Path
from typing import Optional
from contextlib import contextmanager


def ensure_directory(path: Path, mode: int = 0o755) -> Path:
    """
    Ensure a directory exists with proper permissions.
    
    Args:
        path: Path to the directory
        mode: Permission mode (default 0o755 for read/write/execute for owner, read/execute for others)
        
    Returns:
        Path object of the created/existing directory
        
    Raises:
        PermissionError: If directory cannot be created due to permissions
        OSError: For other filesystem errors
    """
    try:
        # Create parent directories first with proper permissions
        path.parent.mkdir(parents=True, exist_ok=True, mode=mode)
        # Create the directory itself
        path.mkdir(parents=True, exist_ok=True, mode=mode)
        
        # Ensure permissions are set correctly (in case directory already existed)
        os.chmod(path, mode)
        
        return path
    except PermissionError as e:
        error_msg = (
            f"Permission denied when creating directory: {path}\n"
            f"Error: {str(e)}\n\n"
            "On macOS, this may be due to:\n"
            "1. Full Disk Access not granted to Terminal/Python\n"
            "2. Directory is in a protected location (e.g., /System, /usr)\n"
            "3. Insufficient user permissions\n\n"
            "Solutions:\n"
            "1. Grant Full Disk Access: System Settings > Privacy & Security > Full Disk Access\n"
            "2. Run from a user-writable directory (e.g., ~/Documents, ~/Desktop)\n"
            "3. Check directory permissions: ls -ld {path}\n"
            "4. Try running with sudo (not recommended for regular use)"
        )
        raise PermissionError(error_msg) from e
    except OSError as e:
        error_msg = (
            f"Failed to create directory: {path}\n"
            f"Error: {str(e)}\n\n"
            "Please ensure:\n"
            "1. The path is valid and accessible\n"
            "2. You have write permissions to the parent directory\n"
            "3. There is sufficient disk space"
        )
        raise OSError(error_msg) from e


def safe_write_text(path: Path, content: str, mode: int = 0o644) -> None:
    """
    Safely write text content to a file with proper error handling.
    
    Args:
        path: Path to the file
        content: Text content to write
        mode: File permission mode (default 0o644)
        
    Raises:
        PermissionError: If file cannot be written due to permissions
        OSError: For other filesystem errors
    """
    try:
        # Ensure parent directory exists
        ensure_directory(path.parent)
        
        # Write file with proper permissions
        path.write_text(content, encoding='utf-8')
        os.chmod(path, mode)
        
    except PermissionError as e:
        error_msg = (
            f"Permission denied when writing file: {path}\n"
            f"Error: {str(e)}\n\n"
            "On macOS, this may be due to:\n"
            "1. Full Disk Access not granted to Terminal/Python\n"
            "2. File is read-only or in a protected location\n"
            "3. Insufficient user permissions\n\n"
            "Solutions:\n"
            "1. Grant Full Disk Access: System Settings > Privacy & Security > Full Disk Access\n"
            "2. Check file permissions: ls -l {path}\n"
            "3. Ensure the output directory is writable"
        )
        raise PermissionError(error_msg) from e
    except OSError as e:
        error_msg = (
            f"Failed to write file: {path}\n"
            f"Error: {str(e)}\n\n"
            "Please ensure:\n"
            "1. The path is valid and accessible\n"
            "2. You have write permissions\n"
            "3. There is sufficient disk space"
        )
        raise OSError(error_msg) from e


def safe_write_bytes(path: Path, content: bytes, mode: int = 0o644) -> None:
    """
    Safely write binary content to a file with proper error handling.
    
    Args:
        path: Path to the file
        content: Binary content to write
        mode: File permission mode (default 0o644)
        
    Raises:
        PermissionError: If file cannot be written due to permissions
        OSError: For other filesystem errors
    """
    try:
        # Ensure parent directory exists
        ensure_directory(path.parent)
        
        # Write file with proper permissions
        path.write_bytes(content)
        os.chmod(path, mode)
        
    except PermissionError as e:
        error_msg = (
            f"Permission denied when writing file: {path}\n"
            f"Error: {str(e)}\n\n"
            "On macOS, this may be due to:\n"
            "1. Full Disk Access not granted to Terminal/Python\n"
            "2. File is read-only or in a protected location\n"
            "3. Insufficient user permissions\n\n"
            "Solutions:\n"
            "1. Grant Full Disk Access: System Settings > Privacy & Security > Full Disk Access\n"
            "2. Check file permissions: ls -l {path}\n"
            "3. Ensure the output directory is writable"
        )
        raise PermissionError(error_msg) from e
    except OSError as e:
        error_msg = (
            f"Failed to write file: {path}\n"
            f"Error: {str(e)}\n\n"
            "Please ensure:\n"
            "1. The path is valid and accessible\n"
            "2. You have write permissions\n"
            "3. There is sufficient disk space"
        )
        raise OSError(error_msg) from e


from contextlib import contextmanager

@contextmanager
def safe_open_write(path: Path, mode: str = 'wb', file_mode: int = 0o644):
    """
    Context manager for safely opening files for writing.
    
    Args:
        path: Path to the file
        mode: File open mode ('w', 'wb', etc.)
        file_mode: File permission mode (default 0o644)
        
    Yields:
        File handle
        
    Raises:
        PermissionError: If file cannot be opened due to permissions
        OSError: For other filesystem errors
    """
    try:
        # Ensure parent directory exists
        ensure_directory(path.parent)
        
        # Open and yield file handle
        with open(path, mode) as f:
            yield f
        
        # Set permissions after writing
        os.chmod(path, file_mode)
        
    except PermissionError as e:
        error_msg = (
            f"Permission denied when opening file: {path}\n"
            f"Error: {str(e)}\n\n"
            "On macOS, this may be due to:\n"
            "1. Full Disk Access not granted to Terminal/Python\n"
            "2. File is read-only or in a protected location\n"
            "3. Insufficient user permissions\n\n"
            "Solutions:\n"
            "1. Grant Full Disk Access: System Settings > Privacy & Security > Full Disk Access\n"
            "2. Check file permissions: ls -l {path}\n"
            "3. Ensure the output directory is writable"
        )
        raise PermissionError(error_msg) from e
    except OSError as e:
        error_msg = (
            f"Failed to open file: {path}\n"
            f"Error: {str(e)}\n\n"
            "Please ensure:\n"
            "1. The path is valid and accessible\n"
            "2. You have write permissions\n"
            "3. There is sufficient disk space"
        )
        raise OSError(error_msg) from e

