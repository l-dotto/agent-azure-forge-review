#!/usr/bin/env python3
"""
Path Sanitization Utility

Provides centralized, secure path validation to prevent Path Traversal
attacks (CWE-23) across all CLI tools.
"""

from pathlib import Path
from typing import Set


def sanitize_output_path(user_input: str, allowed_extensions: Set[str] = None) -> Path:
    """
    Sanitize and validate output path to prevent Path Traversal attacks.

    Security measures:
    1. Resolve to absolute path
    2. Validate file extension (configurable, defaults to .json, .md)
    3. Ensure path is within allowed directories (findings/, current working dir)
    4. Block directory traversal sequences (../, ..\\)

    Args:
        user_input: User-provided file path
        allowed_extensions: Set of allowed file extensions (with dots).
                          Defaults to {'.json', '.md'}

    Returns:
        Validated and sanitized Path object

    Raises:
        ValueError: If path is invalid or unsafe

    Examples:
        >>> sanitize_output_path('findings/security.json')
        PosixPath('/project/findings/security.json')

        >>> sanitize_output_path('../../etc/passwd.json')
        ValueError: Invalid path: directory traversal detected
    """
    if allowed_extensions is None:
        allowed_extensions = {'.json', '.md'}

    # Security: Block obvious traversal attempts
    if '..' in user_input or user_input.startswith('/'):
        raise ValueError(
            f"Invalid path: directory traversal detected in '{user_input}'. "
            "Use relative paths within project directory."
        )

    # Convert to Path and resolve to absolute
    try:
        path = Path(user_input).resolve()
    except (OSError, RuntimeError) as e:
        raise ValueError(f"Invalid path format: {e}")

    # Security: Validate file extension (case-insensitive)
    if path.suffix.lower() not in allowed_extensions:
        raise ValueError(
            f"Invalid file extension '{path.suffix}'. "
            f"Allowed: {', '.join(sorted(allowed_extensions))}"
        )

    # Security: Ensure path is within allowed base directories
    cwd = Path.cwd().resolve()
    allowed_bases = [
        cwd,  # Current working directory
        cwd / 'findings',  # Findings directory
        cwd / 'scripts' / 'output',  # Output directory
    ]

    # Check if path is under any allowed base
    is_safe = any(
        path.is_relative_to(base) or path == base
        for base in allowed_bases
    )

    if not is_safe:
        raise ValueError(
            f"Path '{path}' is outside allowed directories. "
            f"Must be within project directory or findings/."
        )

    return path


def sanitize_input_path(user_input: str, allowed_extensions: Set[str] = None) -> Path:
    """
    Sanitize and validate input path to prevent Path Traversal attacks.

    Similar to sanitize_output_path but allows reading from more locations
    (e.g., test fixtures, docs directory).

    Security measures:
    1. Resolve to absolute path
    2. Validate file extension (configurable)
    3. Ensure path is within project directory
    4. Block directory traversal sequences (../, ..\\)

    Args:
        user_input: User-provided file path
        allowed_extensions: Set of allowed file extensions (with dots).
                          Defaults to {'.json', '.md', '.txt', '.yaml', '.yml'}

    Returns:
        Validated and sanitized Path object

    Raises:
        ValueError: If path is invalid or unsafe
    """
    if allowed_extensions is None:
        allowed_extensions = {'.json', '.md', '.txt', '.yaml', '.yml'}

    # Security: Block obvious traversal attempts
    if '..' in user_input or user_input.startswith('/'):
        raise ValueError(
            f"Invalid path: directory traversal detected in '{user_input}'. "
            "Use relative paths within project directory."
        )

    # Convert to Path and resolve to absolute
    try:
        path = Path(user_input).resolve()
    except (OSError, RuntimeError) as e:
        raise ValueError(f"Invalid path format: {e}")

    # Security: Validate file extension (case-insensitive)
    if path.suffix.lower() not in allowed_extensions:
        raise ValueError(
            f"Invalid file extension '{path.suffix}'. "
            f"Allowed: {', '.join(sorted(allowed_extensions))}"
        )

    # Security: Ensure path is within project directory
    cwd = Path.cwd().resolve()

    # More permissive for input - allow reading from project subdirectories
    if not path.is_relative_to(cwd):
        raise ValueError(
            f"Path '{path}' is outside project directory. "
            f"Must be within {cwd}."
        )

    # Security: Verify file exists (for input files)
    if not path.exists():
        raise ValueError(f"File not found: {path}")

    if not path.is_file():
        raise ValueError(f"Path is not a file: {path}")

    return path
