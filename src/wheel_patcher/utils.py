"""Utility functions for wheel validation and manipulation."""

import os
import zipfile
from pathlib import Path
from typing import List, Optional

__all__ = [
    "WheelError",
    "is_valid_wheel",
    "get_dist_info_dir",
    "list_wheel_contents",
    "normalize_path",
    "validate_path_safe",
    "generate_output_path",
]


class WheelError(Exception):
    """Base exception for wheel-related errors."""

    pass


def is_valid_wheel(path: Path) -> bool:
    """
    Check if a file is a valid wheel (ZIP archive).

    Args:
        path: Path to wheel file

    Returns:
        True if valid wheel, False otherwise
    """
    if not path.exists():
        return False

    if not path.suffix == ".whl":
        return False

    try:
        with zipfile.ZipFile(path, "r") as zf:
            zf.testzip()
            return get_dist_info_dir(zf) is not None
    except (zipfile.BadZipFile, OSError):
        return False


def get_dist_info_dir(zip_file: zipfile.ZipFile) -> Optional[str]:
    """
    Find the top-level .dist-info directory in a wheel.

    Some wheels (e.g. setuptools) bundle other packages that have their own
    .dist-info directories. This function returns only the top-level one by
    looking for directories that are direct children of the wheel root.

    Args:
        zip_file: Opened ZipFile object

    Returns:
        Name of dist-info directory, or None if not found
    """
    for name in zip_file.namelist():
        parts = name.split("/")
        # Only consider top-level .dist-info directories (depth == 1)
        if parts[0].endswith(".dist-info"):
            return parts[0]
    return None


def list_wheel_contents(path: Path) -> List[str]:
    """
    List all files in a wheel.

    Args:
        path: Path to wheel file

    Returns:
        List of file paths in wheel
    """
    with zipfile.ZipFile(path, "r") as zf:
        return zf.namelist()


def normalize_path(path: str) -> str:
    """
    Normalize a path for use in wheels.

    Args:
        path: Path to normalize

    Returns:
        Normalized path with forward slashes
    """
    # Convert backslashes to forward slashes (Windows compatibility)
    normalized = path.replace("\\", "/")

    while normalized.startswith("/"):
        normalized = normalized[1:]

    return normalized


def validate_path_safe(path: str) -> None:
    """
    Validate that a path doesn't contain path traversal attacks.

    Args:
        path: Path to validate

    Raises:
        WheelError: If path is unsafe
    """
    normalized = normalize_path(path)

    if ".." in normalized.split("/"):
        raise WheelError(f"Path traversal detected in path: {path}")

    if os.path.isabs(path):
        raise WheelError(f"Absolute paths not allowed: {path}")


def generate_output_path(input_path: Path, suffix: str = "-patched") -> Path:
    """
    Generate output path for patched wheel.

    Args:
        input_path: Original wheel path
        suffix: Suffix to add before extension

    Returns:
        New path with suffix added
    """
    stem = input_path.stem
    parent = input_path.parent
    return parent / f"{stem}{suffix}.whl"
