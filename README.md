# wheel-patcher

A simple, zero-dependency tool for patching Python wheel files.

## Overview

`wheel-patcher` allows you to add files to existing Python wheel (.whl) files while maintaining wheel integrity and PEP 427 compliance. The primary use case is adding SBOM (Software Bill of Materials) files to wheels, but the tool is generic and can add any files.

## Features

- Add files to existing wheels
- Batch operations via manifest files
- PEP 427 compliant RECORD file handling
- Zero runtime dependencies (stdlib only)
- Safe by default (creates new wheel, preserves original)
- Simple CLI interface

## Installation

### From source

```bash
pip install .
```

### Development installation

```bash
pip install -e .
```

## Usage

### Add a single file

Add a file to a wheel:

```bash
wheel-patcher add mypackage-1.0-py3-none-any.whl sbom.json \
  --dest .dist-info/sbom.json
```

By default, this creates `mypackage-1.0-py3-none-any-patched.whl`.

**Note:** The `.dist-info/` prefix is automatically resolved to the actual dist-info directory name (e.g., `mypackage-1.0.dist-info/`), so you don't need to know the exact package name and version. This works in both commands and manifest files.

### Specify output path

```bash
wheel-patcher add mypackage-1.0-py3-none-any.whl sbom.json \
  --dest .dist-info/sbom.json \
  --output mypackage-1.0-py3-none-any-with-sbom.whl
```

### Modify in-place

```bash
wheel-patcher add mypackage-1.0-py3-none-any.whl sbom.json \
  --dest .dist-info/sbom.json \
  --in-place
```

### Add multiple files with manifest

Create a manifest file (`manifest.json`):

```json
{
  "files": [
    {
      "source": "sbom.json",
      "dest": ".dist-info/sbom.json"
    },
    {
      "source": "LICENSE-THIRD-PARTY",
      "dest": ".dist-info/licenses/LICENSE-THIRD-PARTY"
    }
  ]
}
```

Apply the manifest:

```bash
wheel-patcher apply mypackage-1.0-py3-none-any.whl --manifest manifest.json
```

### List wheel contents

```bash
wheel-patcher list mypackage-1.0-py3-none-any.whl
```

### Extract wheel

```bash
wheel-patcher extract mypackage-1.0-py3-none-any.whl --output extracted/
```

## CLI Reference

### `wheel-patcher add`

Add a single file to a wheel.

```text
wheel-patcher add <wheel-file> <file-to-add> [options]
```

Options:

- `--dest`, `-d`: Destination path within wheel (default: filename)
- `--output`, `-o`: Output path for patched wheel (default: adds -patched suffix)
- `--in-place`: Modify wheel in-place
- `--force`, `-f`: Overwrite existing files in wheel

### `wheel-patcher apply`

Apply batch changes from a manifest file.

```text
wheel-patcher apply <wheel-file> --manifest <manifest.json> [options]
```

Options:

- `--manifest`, `-m`: Path to manifest JSON file (required)
- `--output`, `-o`: Output path for patched wheel
- `--in-place`: Modify wheel in-place
- `--force`, `-f`: Overwrite existing files in wheel

### `wheel-patcher list`

List contents of a wheel.

```text
wheel-patcher list <wheel-file>
```

### `wheel-patcher extract`

Extract wheel to a directory.

```text
wheel-patcher extract <wheel-file> [--output <directory>]
```

Options:

- `--output`, `-o`: Output directory (default: wheel name)

## Manifest File Format

Manifest files are JSON with the following structure:

```json
{
  "files": [
    {
      "source": "path/to/source/file",
      "dest": "path/in/wheel"
    }
  ]
}
```

Each file entry must have:

- `source`: Path to the source file on disk
- `dest`: Destination path within the wheel (use `.dist-info/` prefix for auto-resolution)

## Common Use Cases

### Adding SBOM to a wheel

```bash
# Generate SBOM (example using cyclonedx)
cyclonedx-py -o sbom.json

# Add to wheel
wheel-patcher add mypackage-1.0-py3-none-any.whl sbom.json \
  --dest .dist-info/sbom.json
```

### Adding license files

```bash
wheel-patcher add mypackage-1.0-py3-none-any.whl LICENSE-THIRD-PARTY \
  --dest .dist-info/licenses/LICENSE-THIRD-PARTY
```

### Adding metadata files

```bash
wheel-patcher add mypackage-1.0-py3-none-any.whl SECURITY.md \
  --dest .dist-info/SECURITY.md
```

## How It Works

1. Opens the wheel file (which is a ZIP archive)
2. Reads and parses the RECORD file (PEP 427)
3. Adds new files to the wheel
4. Calculates SHA256 hashes for new files
5. Updates the RECORD file with new entries
6. Writes the patched wheel

The tool ensures:

- Proper SHA256 hash format (urlsafe base64, no padding)
- RECORD file compliance (itself listed with empty hash)
- Path validation (prevents path traversal)
- Wheel integrity (maintains ZIP structure)

## Technical Details

### RECORD File Format

Per PEP 427, the RECORD file is CSV format:

```text
path/to/file,sha256=base64hash,size
another/file,sha256=anotherhash,1234
package.dist-info/RECORD,,
```

The RECORD entry itself must have empty hash and size.

### Hash Calculation

Hashes are calculated as:

```python
digest = hashlib.sha256(content).digest()
hash_str = "sha256=" + base64.urlsafe_b64encode(digest).rstrip(b'=').decode()
```

This matches the PEP 427 specification exactly.

## Requirements

- Python 3.9 or higher
- No external dependencies (uses stdlib only)

## Development

### Running tests

This project uses [nox](https://nox.thea.codes/) for test automation and [uv](https://github.com/astral-sh/uv) for fast package installation.

Install nox:

```bash
pip install nox
```

Run all tests across all supported Python versions:

```bash
nox
```

Run tests on a specific Python version:

```bash
nox -s tests-3.12
```

Other available sessions:

```bash
# Run linting
nox -s lint

# Check code formatting
nox -s format_check

# Auto-format code
nox -s format

# Run type checking
nox -s type_check
```

For faster iteration during development, reuse virtual environments:

```bash
nox -s tests-3.12 -R
```

Alternatively, run tests directly with pytest:

```bash
pip install pytest
pytest tests/ -v
```

## License

MIT License

## Contributing

Contributions welcome! Please ensure:

- Tests pass
- Code follows existing style
- RECORD format compliance is maintained
