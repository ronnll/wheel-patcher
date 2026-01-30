"""Tests for RECORD file handling."""

import base64
import hashlib

from wheel_patcher import record


def test_hash_file():
    """Test SHA256 hash calculation."""
    content = b"Hello, World!"
    hash_result = record.hash_file(content)

    # Verify format
    assert hash_result.startswith("sha256=")

    # Verify hash is correct
    digest = hashlib.sha256(content).digest()
    expected_hash = base64.urlsafe_b64encode(digest).rstrip(b'=').decode('ascii')
    assert hash_result == f"sha256={expected_hash}"


def test_hash_file_empty():
    """Test hash calculation for empty file."""
    content = b""
    hash_result = record.hash_file(content)

    assert hash_result.startswith("sha256=")
    # Empty file should still have a valid hash
    assert len(hash_result) > 7  # More than just "sha256="


def test_parse_record():
    """Test parsing RECORD file content."""
    record_content = """requests/__init__.py,sha256=abcd1234,1024
requests/api.py,sha256=efgh5678,2048
requests-2.32.5.dist-info/RECORD,,
"""
    entries = record.parse_record(record_content)

    assert len(entries) == 3
    assert entries[0].path == "requests/__init__.py"
    assert entries[0].hash == "sha256=abcd1234"
    assert entries[0].size == "1024"

    # RECORD entry should have empty hash and size
    assert entries[2].path == "requests-2.32.5.dist-info/RECORD"
    assert entries[2].hash == ""
    assert entries[2].size == ""


def test_format_record_entry():
    """Test creating RECORD entries."""
    # Entry with content
    content = b"test content"
    entry = record.format_record_entry("test.txt", content)

    assert entry.path == "test.txt"
    assert entry.hash.startswith("sha256=")
    assert entry.size == str(len(content))

    # Entry without content (like RECORD itself)
    entry_no_hash = record.format_record_entry("RECORD", None)
    assert entry_no_hash.path == "RECORD"
    assert entry_no_hash.hash == ""
    assert entry_no_hash.size == ""


def test_update_record():
    """Test updating RECORD with new files."""
    existing = [
        record.RecordEntry("file1.py", "sha256=abc", "100"),
        record.RecordEntry("file2.py", "sha256=def", "200"),
        record.RecordEntry("dist-info/RECORD", "", ""),
    ]

    new_files = {
        "new_file.txt": b"new content",
    }

    updated = record.update_record(existing, new_files, "dist-info/RECORD")

    # Should have original files + new file + RECORD (2 + 1 + 1 = 4)
    assert len(updated) == 4

    # Check new file was added
    new_entry = next(e for e in updated if e.path == "new_file.txt")
    assert new_entry.hash.startswith("sha256=")
    assert new_entry.size == "11"  # len(b"new content")

    # Check RECORD is last with empty hash
    assert updated[-1].path == "dist-info/RECORD"
    assert updated[-1].hash == ""
    assert updated[-1].size == ""


def test_format_record():
    """Test formatting RECORD entries as CSV."""
    entries = [
        record.RecordEntry("file1.py", "sha256=abc", "100"),
        record.RecordEntry("file2.py", "sha256=def", "200"),
        record.RecordEntry("RECORD", "", ""),
    ]

    formatted = record.format_record(entries)

    # Should be CSV format
    lines = formatted.strip().split('\n')
    assert len(lines) == 3
    assert lines[0] == "file1.py,sha256=abc,100"
    assert lines[1] == "file2.py,sha256=def,200"
    assert lines[2] == "RECORD,,"


def test_record_entry_roundtrip():
    """Test converting RecordEntry to CSV and back."""
    original = record.RecordEntry("test.py", "sha256=xyz", "500")
    csv_row = original.to_csv_row()
    reconstructed = record.RecordEntry.from_csv_row(csv_row)

    assert reconstructed.path == original.path
    assert reconstructed.hash == original.hash
    assert reconstructed.size == original.size
