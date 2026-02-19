"""Core wheel patching logic."""

import os
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import record as record_module
from .record import RecordEntry
from .utils import (
    WheelError,
    get_dist_info_dir,
    normalize_path,
    validate_path_safe,
)

__all__ = ["WheelPatcher"]


class WheelPatcher:
    """Handles patching of Python wheel files."""

    def __init__(self, wheel_path: Path):
        """
        Initialize patcher with a wheel file.

        Args:
            wheel_path: Path to the wheel file

        Raises:
            WheelError: If wheel is invalid
        """
        if not wheel_path.exists():
            raise WheelError(f"Wheel file not found: {wheel_path}")

        if not wheel_path.suffix == ".whl":
            raise WheelError(f"Not a wheel file: {wheel_path}")

        try:
            self.wheel_path = wheel_path
            self._zip_file = zipfile.ZipFile(wheel_path, "r")
            self._dist_info_dir = get_dist_info_dir(self._zip_file)

            if not self._dist_info_dir:
                raise WheelError(f"No .dist-info directory found in {wheel_path}")

            self._record_path = f"{self._dist_info_dir}/RECORD"
            self._files_to_add: Dict[str, bytes] = {}
            self._existing_record = self._read_record()

        except zipfile.BadZipFile as e:
            raise WheelError(f"Invalid ZIP file: {wheel_path}") from e

    def _read_record(self) -> List[RecordEntry]:
        """Read and parse the RECORD file."""
        try:
            record_content = self._zip_file.read(self._record_path).decode("utf-8")
            return record_module.parse_record(record_content)
        except KeyError:
            raise WheelError(f"RECORD file not found: {self._record_path}")

    def get_dist_info_dir(self) -> str:
        """Get the name of the dist-info directory."""
        assert self._dist_info_dir is not None
        return self._dist_info_dir

    def _resolve_dist_info_path(self, path: str) -> str:
        """
        Resolve .dist-info/ prefix in path to actual dist-info directory.

        Args:
            path: Path that may contain .dist-info/ prefix

        Returns:
            Path with .dist-info/ replaced by actual dist-info directory name
        """
        if path.startswith(".dist-info/"):
            assert self._dist_info_dir is not None
            return self._dist_info_dir + path[len(".dist-info") :]
        return path

    def add_file(
        self, source: Path, dest: Optional[str] = None, overwrite: bool = False
    ) -> None:
        """
        Add a file to the wheel.

        Args:
            source: Path to source file to add
            dest: Destination path within wheel. If None, uses source filename
            overwrite: Whether to overwrite existing files

        Raises:
            WheelError: If file doesn't exist or path is invalid
        """
        if not source.exists():
            raise WheelError(f"Source file not found: {source}")

        if not source.is_file():
            raise WheelError(f"Source must be a file: {source}")

        if dest is None:
            dest = source.name

        dest = self._resolve_dist_info_path(dest)
        dest = normalize_path(dest)
        validate_path_safe(dest)

        if not overwrite:
            if dest in self._zip_file.namelist():
                raise WheelError(
                    f"File already exists in wheel: {dest} (use --force to overwrite)"
                )
            if dest in self._files_to_add:
                raise WheelError(f"File already queued for addition: {dest}")

        content = source.read_bytes()
        self._files_to_add[dest] = content

    def add_files(self, file_map: Dict[str, Path], overwrite: bool = False) -> None:
        """
        Add multiple files to the wheel.

        Args:
            file_map: Dict mapping destination paths to source file paths
            overwrite: Whether to overwrite existing files

        Raises:
            WheelError: If any file operation fails
        """
        for dest, source in file_map.items():
            self.add_file(source, dest, overwrite)

    def save(self, output_path: Path) -> None:
        """
        Save the patched wheel.

        Args:
            output_path: Path where patched wheel should be saved

        Raises:
            WheelError: If save fails
        """
        if not self._files_to_add:
            raise WheelError("No files to add. Use add_file() first.")

        # Create temp file in the same directory as the output to avoid
        # cross-device link errors when renaming. os.rename() (used by
        # Path.replace()) cannot move files across filesystem boundaries.
        temp_fd, temp_path_str = tempfile.mkstemp(
            suffix=".whl", dir=output_path.parent
        )
        temp_path = Path(temp_path_str)

        try:
            with zipfile.ZipFile(temp_path, "w", zipfile.ZIP_DEFLATED) as new_zip:
                for item in self._zip_file.namelist():
                    if item != self._record_path:
                        data = self._zip_file.read(item)
                        new_zip.writestr(item, data)

                for dest, content in self._files_to_add.items():
                    new_zip.writestr(dest, content)

                updated_record = record_module.update_record(
                    self._existing_record, self._files_to_add, self._record_path
                )
                record_content = record_module.format_record(updated_record)
                new_zip.writestr(self._record_path, record_content)

            temp_path.replace(output_path)

        except Exception as e:
            try:
                temp_path.unlink()
            except Exception:
                pass
            raise WheelError(f"Failed to save patched wheel: {e}") from e

        finally:
            try:
                os.close(temp_fd)
            except Exception:
                pass

    def close(self) -> None:
        """Close the wheel file."""
        self._zip_file.close()

    def __enter__(self) -> "WheelPatcher":
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Any,
    ) -> None:
        """Context manager exit."""
        self.close()
