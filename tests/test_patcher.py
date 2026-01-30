"""Tests for wheel patcher."""

import tempfile
import zipfile
from pathlib import Path

import pytest

from wheel_patcher.patcher import WheelPatcher
from wheel_patcher.utils import WheelError


# Path to test fixture
FIXTURES_DIR = Path(__file__).parent / "fixtures"
TEST_WHEEL = FIXTURES_DIR / "requests-2.32.5-py3-none-any.whl"


def test_wheel_patcher_init():
    """Test WheelPatcher initialization."""
    if not TEST_WHEEL.exists():
        pytest.skip("Test wheel not found")

    patcher = WheelPatcher(TEST_WHEEL)
    assert patcher.get_dist_info_dir() == "requests-2.32.5.dist-info"
    patcher.close()


def test_wheel_patcher_invalid_file():
    """Test WheelPatcher with invalid file."""
    with pytest.raises(WheelError, match="not found"):
        WheelPatcher(Path("nonexistent.whl"))


def test_add_file():
    """Test adding a file to a wheel."""
    if not TEST_WHEEL.exists():
        pytest.skip("Test wheel not found")

    # Create a temporary file to add
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("Test SBOM content")
        temp_file = Path(f.name)

    try:
        # Create output path
        with tempfile.TemporaryDirectory() as tmpdir:
            output_wheel = Path(tmpdir) / "patched.whl"

            # Patch the wheel
            with WheelPatcher(TEST_WHEEL) as patcher:
                dest_path = f"{patcher.get_dist_info_dir()}/sbom.txt"
                patcher.add_file(temp_file, dest_path)
                patcher.save(output_wheel)

            # Verify the patched wheel
            assert output_wheel.exists()

            # Check that the new file is in the wheel
            with zipfile.ZipFile(output_wheel, "r") as zf:
                assert dest_path in zf.namelist()
                content = zf.read(dest_path).decode("utf-8")
                assert content == "Test SBOM content"

                # Verify RECORD was updated
                record_path = f"{patcher.get_dist_info_dir()}/RECORD"
                record_content = zf.read(record_path).decode("utf-8")
                assert dest_path in record_content
                assert "sha256=" in record_content

    finally:
        temp_file.unlink()


def test_add_file_no_dest():
    """Test adding a file without specifying destination."""
    if not TEST_WHEEL.exists():
        pytest.skip("Test wheel not found")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write('{"test": "data"}')
        temp_file = Path(f.name)

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_wheel = Path(tmpdir) / "patched.whl"

            with WheelPatcher(TEST_WHEEL) as patcher:
                patcher.add_file(temp_file)  # No dest specified
                patcher.save(output_wheel)

            # File should be at root with original name
            with zipfile.ZipFile(output_wheel, "r") as zf:
                assert temp_file.name in zf.namelist()

    finally:
        temp_file.unlink()


def test_add_file_already_exists():
    """Test adding a file that already exists without force."""
    if not TEST_WHEEL.exists():
        pytest.skip("Test wheel not found")

    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("content")
        temp_file = Path(f.name)

    try:
        with WheelPatcher(TEST_WHEEL) as patcher:
            # Try to add a file that already exists in the wheel
            with pytest.raises(WheelError, match="already exists"):
                patcher.add_file(temp_file, "requests/__init__.py")

    finally:
        temp_file.unlink()


def test_add_file_with_overwrite():
    """Test adding a file with overwrite flag."""
    if not TEST_WHEEL.exists():
        pytest.skip("Test wheel not found")

    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("new content")
        temp_file = Path(f.name)

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_wheel = Path(tmpdir) / "patched.whl"

            with WheelPatcher(TEST_WHEEL) as patcher:
                # Overwrite existing file
                patcher.add_file(temp_file, "requests/__init__.py", overwrite=True)
                patcher.save(output_wheel)

            # Verify the file was overwritten
            with zipfile.ZipFile(output_wheel, "r") as zf:
                content = zf.read("requests/__init__.py").decode("utf-8")
                assert content == "new content"

    finally:
        temp_file.unlink()


def test_save_without_files():
    """Test saving without adding any files."""
    if not TEST_WHEEL.exists():
        pytest.skip("Test wheel not found")

    with tempfile.TemporaryDirectory() as tmpdir:
        output_wheel = Path(tmpdir) / "patched.whl"

        with WheelPatcher(TEST_WHEEL) as patcher:
            with pytest.raises(WheelError, match="No files to add"):
                patcher.save(output_wheel)


def test_context_manager():
    """Test WheelPatcher as context manager."""
    if not TEST_WHEEL.exists():
        pytest.skip("Test wheel not found")

    with WheelPatcher(TEST_WHEEL) as patcher:
        assert patcher.get_dist_info_dir() == "requests-2.32.5.dist-info"
    # File should be closed after exiting context


def test_dist_info_prefix_resolution():
    """Test automatic .dist-info/ prefix resolution."""
    if not TEST_WHEEL.exists():
        pytest.skip("Test wheel not found")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write('{"type": "sbom"}')
        temp_file = Path(f.name)

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_wheel = Path(tmpdir) / "patched.whl"

            with WheelPatcher(TEST_WHEEL) as patcher:
                # Use .dist-info/ prefix - should be automatically resolved
                patcher.add_file(temp_file, ".dist-info/sboms/sbom.json")
                patcher.save(output_wheel)

            # Verify the file was added with the correct path
            expected_path = "requests-2.32.5.dist-info/sboms/sbom.json"
            with zipfile.ZipFile(output_wheel, "r") as zf:
                assert expected_path in zf.namelist()
                content = zf.read(expected_path).decode("utf-8")
                assert content == '{"type": "sbom"}'

                # Verify RECORD was updated with resolved path
                record_content = zf.read("requests-2.32.5.dist-info/RECORD").decode(
                    "utf-8"
                )
                assert expected_path in record_content

    finally:
        temp_file.unlink()


def test_dist_info_prefix_multiple_files():
    """Test .dist-info/ prefix resolution with multiple files."""
    if not TEST_WHEEL.exists():
        pytest.skip("Test wheel not found")

    # Create two temporary files
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write('{"sbom": "data"}')
        sbom_file = Path(f.name)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("License text")
        license_file = Path(f.name)

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_wheel = Path(tmpdir) / "patched.whl"

            with WheelPatcher(TEST_WHEEL) as patcher:
                # Add multiple files using .dist-info/ prefix
                patcher.add_file(sbom_file, ".dist-info/sbom.json")
                patcher.add_file(
                    license_file, ".dist-info/licenses/LICENSE-THIRD-PARTY"
                )
                patcher.save(output_wheel)

            # Verify both files were added with resolved paths
            with zipfile.ZipFile(output_wheel, "r") as zf:
                assert "requests-2.32.5.dist-info/sbom.json" in zf.namelist()
                assert (
                    "requests-2.32.5.dist-info/licenses/LICENSE-THIRD-PARTY"
                    in zf.namelist()
                )

    finally:
        sbom_file.unlink()
        license_file.unlink()


def test_dist_info_prefix_not_applied_when_absent():
    """Test that paths without .dist-info/ prefix are not modified."""
    if not TEST_WHEEL.exists():
        pytest.skip("Test wheel not found")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("Regular file")
        temp_file = Path(f.name)

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_wheel = Path(tmpdir) / "patched.whl"

            with WheelPatcher(TEST_WHEEL) as patcher:
                # Regular path without .dist-info/ prefix
                patcher.add_file(temp_file, "custom/path/file.txt")
                patcher.save(output_wheel)

            # Verify the file is at the exact path specified
            with zipfile.ZipFile(output_wheel, "r") as zf:
                assert "custom/path/file.txt" in zf.namelist()
                # Should NOT be in dist-info
                assert (
                    "requests-2.32.5.dist-info/custom/path/file.txt"
                    not in zf.namelist()
                )

    finally:
        temp_file.unlink()
