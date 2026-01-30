"""Command-line interface for wheel-patcher."""

import argparse
import json
import sys
import zipfile
from pathlib import Path
from typing import Dict

from . import __version__
from .patcher import WheelPatcher
from .utils import (
    WheelError,
    generate_output_path,
    is_valid_wheel,
    list_wheel_contents,
)

__all__ = ["main"]


def _validate_wheel_file(wheel_path: Path) -> int:
    """
    Validate that a wheel file exists and is valid.

    Args:
        wheel_path: Path to wheel file

    Returns:
        0 if valid, 1 if invalid (with error printed to stderr)
    """
    if not wheel_path.exists():
        print(f"Error: Wheel file not found: {wheel_path}", file=sys.stderr)
        return 1

    if not is_valid_wheel(wheel_path):
        print(f"Error: Invalid wheel file: {wheel_path}", file=sys.stderr)
        return 1

    return 0


def _determine_output_path(args, wheel_path: Path) -> Path:
    """
    Determine the output path for a patched wheel based on arguments.

    Args:
        args: Parsed command-line arguments
        wheel_path: Path to the original wheel file

    Returns:
        Path where the patched wheel should be saved
    """
    if args.output:
        return Path(args.output)
    elif args.in_place:
        return wheel_path
    else:
        return generate_output_path(wheel_path)


def cmd_add(args):
    """Handle 'add' command - add a file to a wheel."""
    wheel_path = Path(args.wheel)
    source_path = Path(args.file)

    if (result := _validate_wheel_file(wheel_path)) != 0:
        return result

    if not source_path.exists():
        print(f"Error: Source file not found: {source_path}", file=sys.stderr)
        return 1

    output_path = _determine_output_path(args, wheel_path)

    try:
        with WheelPatcher(wheel_path) as patcher:
            dest = args.dest
            patcher.add_file(source_path, dest, overwrite=args.force)
            patcher.save(output_path)

        print(f"Successfully patched wheel: {output_path}")
        if args.dest:
            print(f"  Added: {source_path.name} -> {args.dest}")
        else:
            print(f"  Added: {source_path.name}")
        return 0

    except WheelError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


def cmd_apply(args):
    """Handle 'apply' command - apply changes from manifest."""
    wheel_path = Path(args.wheel)
    manifest_path = Path(args.manifest)

    if (result := _validate_wheel_file(wheel_path)) != 0:
        return result

    if not manifest_path.exists():
        print(f"Error: Manifest file not found: {manifest_path}", file=sys.stderr)
        return 1

    try:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in manifest: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error reading manifest: {e}", file=sys.stderr)
        return 1

    if 'files' not in manifest:
        print("Error: Manifest must contain 'files' array", file=sys.stderr)
        return 1

    output_path = _determine_output_path(args, wheel_path)

    try:
        with WheelPatcher(wheel_path) as patcher:
            for file_spec in manifest['files']:
                if 'source' not in file_spec or 'dest' not in file_spec:
                    print("Error: Each file entry must have 'source' and 'dest'", file=sys.stderr)
                    return 1

                source = Path(file_spec['source'])
                dest = file_spec['dest']

                if not source.exists():
                    print(f"Error: Source file not found: {source}", file=sys.stderr)
                    return 1

                patcher.add_file(source, dest, overwrite=args.force)
                print(f"  Queued: {source.name} -> {dest}")

            patcher.save(output_path)

        print(f"\nSuccessfully patched wheel: {output_path}")
        print(f"  Added {len(manifest['files'])} file(s)")
        return 0

    except WheelError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


def cmd_list(args):
    """Handle 'list' command - list wheel contents."""
    wheel_path = Path(args.wheel)

    if (result := _validate_wheel_file(wheel_path)) != 0:
        return result

    try:
        contents = list_wheel_contents(wheel_path)
        print(f"Contents of {wheel_path.name}:")
        print(f"  {len(contents)} files")
        print()
        for item in sorted(contents):
            print(f"  {item}")
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_extract(args):
    """Handle 'extract' command - extract wheel to directory."""
    wheel_path = Path(args.wheel)

    if (result := _validate_wheel_file(wheel_path)) != 0:
        return result

    # Determine output directory
    if args.output:
        output_dir = Path(args.output)
    else:
        output_dir = Path.cwd() / wheel_path.stem

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(wheel_path, 'r') as zf:
            zf.extractall(output_dir)
        print(f"Extracted wheel to: {output_dir}")
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        prog='wheel-patcher',
        description='A tool for patching Python wheel files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Add an SBOM file to a wheel
  wheel-patcher add mypackage-1.0-py3-none-any.whl sbom.json \\
    --dest .dist-info/sbom.json

  # Apply changes from a manifest
  wheel-patcher apply mypackage-1.0-py3-none-any.whl --manifest changes.json

  # List wheel contents
  wheel-patcher list mypackage-1.0-py3-none-any.whl

  # Extract wheel to directory
  wheel-patcher extract mypackage-1.0-py3-none-any.whl --output extracted/

Note: Use .dist-info/ prefix for auto-resolution (e.g., .dist-info/sbom.json).
'''
    )

    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {__version__}'
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Add command
    add_parser = subparsers.add_parser(
        'add',
        help='Add a file to a wheel'
    )
    add_parser.add_argument('wheel', help='Path to wheel file')
    add_parser.add_argument('file', help='Path to file to add')
    add_parser.add_argument(
        '--dest', '-d',
        help='Destination path within wheel (default: filename). Use .dist-info/ prefix for auto-resolution.'
    )
    add_parser.add_argument(
        '--output', '-o',
        help='Output path for patched wheel (default: adds -patched suffix)'
    )
    add_parser.add_argument(
        '--in-place',
        action='store_true',
        help='Modify wheel in-place (default: create new file)'
    )
    add_parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Overwrite existing files in wheel'
    )

    # Apply command
    apply_parser = subparsers.add_parser(
        'apply',
        help='Apply changes from a manifest file'
    )
    apply_parser.add_argument('wheel', help='Path to wheel file')
    apply_parser.add_argument(
        '--manifest', '-m',
        required=True,
        help='Path to manifest JSON file'
    )
    apply_parser.add_argument(
        '--output', '-o',
        help='Output path for patched wheel (default: adds -patched suffix)'
    )
    apply_parser.add_argument(
        '--in-place',
        action='store_true',
        help='Modify wheel in-place (default: create new file)'
    )
    apply_parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Overwrite existing files in wheel'
    )

    # List command
    list_parser = subparsers.add_parser(
        'list',
        help='List contents of a wheel'
    )
    list_parser.add_argument('wheel', help='Path to wheel file')

    # Extract command
    extract_parser = subparsers.add_parser(
        'extract',
        help='Extract wheel to directory'
    )
    extract_parser.add_argument('wheel', help='Path to wheel file')
    extract_parser.add_argument(
        '--output', '-o',
        help='Output directory (default: wheel name)'
    )

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    if args.command == 'add':
        return cmd_add(args)
    elif args.command == 'apply':
        return cmd_apply(args)
    elif args.command == 'list':
        return cmd_list(args)
    elif args.command == 'extract':
        return cmd_extract(args)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())
