"""RECORD file handling for Python wheels (PEP 427 compliant)."""

import base64
import csv
import hashlib
from dataclasses import dataclass
from io import StringIO
from typing import Dict, List, Optional

__all__ = [
    "RecordEntry",
    "parse_record",
    "hash_file",
    "format_record_entry",
    "update_record",
    "format_record",
]


@dataclass
class RecordEntry:
    """Represents a single entry in a RECORD file."""

    path: str
    hash: str  # Format: "sha256=base64hash" or empty string
    size: str  # File size in bytes or empty string

    def to_csv_row(self) -> List[str]:
        """Convert entry to CSV row format."""
        return [self.path, self.hash, self.size]

    @classmethod
    def from_csv_row(cls, row: List[str]) -> "RecordEntry":
        """Create entry from CSV row."""
        # Handle cases where row might have fewer than 3 elements
        path = row[0] if len(row) > 0 else ""
        hash_value = row[1] if len(row) > 1 else ""
        size = row[2] if len(row) > 2 else ""
        return cls(path=path, hash=hash_value, size=size)


def parse_record(content: str) -> List[RecordEntry]:
    """
    Parse RECORD file content.

    Args:
        content: RECORD file content as string

    Returns:
        List of RecordEntry objects
    """
    entries = []
    reader = csv.reader(StringIO(content))
    for row in reader:
        if row:  # Skip empty rows
            entries.append(RecordEntry.from_csv_row(row))
    return entries


def hash_file(content: bytes) -> str:
    """
    Calculate SHA256 hash in PEP 427 format.

    Args:
        content: File content as bytes

    Returns:
        Hash string in format: "sha256=base64hash"

    Note:
        Uses urlsafe base64 encoding without padding, per PEP 427.
    """
    digest = hashlib.sha256(content).digest()
    hash_b64 = base64.urlsafe_b64encode(digest).rstrip(b'=').decode('ascii')
    return f"sha256={hash_b64}"


def format_record_entry(path: str, content: Optional[bytes] = None) -> RecordEntry:
    """
    Create a RECORD entry for a file.

    Args:
        path: Path to the file within the wheel
        content: File content as bytes. If None, creates entry with empty hash/size

    Returns:
        RecordEntry object
    """
    if content is None:
        # RECORD file itself has empty hash and size
        return RecordEntry(path=path, hash="", size="")

    hash_value = hash_file(content)
    size = str(len(content))
    return RecordEntry(path=path, hash=hash_value, size=size)


def update_record(
    existing_entries: List[RecordEntry],
    new_files: Dict[str, bytes],
    record_path: str
) -> List[RecordEntry]:
    """
    Update RECORD with new file entries.

    Args:
        existing_entries: Existing RECORD entries
        new_files: Dict mapping file paths to content
        record_path: Path to RECORD file itself

    Returns:
        Updated list of RecordEntry objects
    """
    # Remove old RECORD entry if present
    entries = [e for e in existing_entries if e.path != record_path]

    # Add new file entries
    for path, content in new_files.items():
        # Remove existing entry for this path if present (for overwrites)
        entries = [e for e in entries if e.path != path]
        entries.append(format_record_entry(path, content))

    # Add RECORD entry itself at the end with empty hash
    entries.append(format_record_entry(record_path, None))

    return entries


def format_record(entries: List[RecordEntry]) -> str:
    """
    Format RECORD entries as CSV content.

    Args:
        entries: List of RecordEntry objects

    Returns:
        RECORD file content as string
    """
    output = StringIO()
    writer = csv.writer(output, lineterminator='\n')
    for entry in entries:
        writer.writerow(entry.to_csv_row())
    return output.getvalue()
