# Newline IWB Converter

A converter utility for handling newline formats in IWB files. Extracts SVG pages from Newline whiteboard IWB files.

## Features

- **Extract SVG pages** from Newline IWB (`.iwb`) files
- **Flexible image handling**:
  - Embed images as base64 data URIs (default)
  - Copy images directory alongside SVGs
  - Keep external image references
- **Optional fill removal** from shape elements (Inkscape-style)
- **Zero external dependencies** - uses only Python standard library

## Getting Started

### Prerequisites

- Python 3.10 or later
- [UV](https://github.com/astral-sh/uv) package manager

### Installation

```bash
uv sync
```

### Activate Virtual Environment

```bash
.venv\Scripts\Activate.ps1
```

## Usage

### Basic Usage

```bash
iwb2svg input.iwb -o output_directory
```

This will extract all SVG pages from the IWB file and embed images as base64 data URIs (default behavior).

### Command Line Options

```
usage: iwb2svg [-h] [-o OUTPUT] [--fix-fills | --no-fix-fills] [--images {nothing,copy_directory,data_uri}] iwb_file

Extract SVG pages from an IWB file, with optional fill→stroke repair.

positional arguments:
  iwb_file              Path to input .iwb file

options:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        Output directory (default: svg_output)
  --fix-fills           Remove fill from shapes (default)
  --no-fix-fills        Do NOT modify fill behavior
  --images {nothing,copy_directory,data_uri}
                        How to handle images:
                        - nothing: keep xlink:href references (default behavior)
                        - copy_directory: copy images/ to output directory
                        - data_uri: embed as base64 (default)
```

### Examples

**Embed images as data URIs (default):**
```bash
iwb2svg input.iwb -o output_dir
```

**Keep external image references:**
```bash
iwb2svg input.iwb -o output_dir --images nothing
```

**Copy images directory alongside SVGs:**
```bash
iwb2svg input.iwb -o output_dir --images copy_directory
```

**Don't remove fills from shapes:**
```bash
iwb2svg input.iwb -o output_dir --no-fix-fills
```

**Using uv run (without virtual environment activation):**
```bash
uv run iwb2svg input.iwb -o output_dir
```

## Development

### Add Dependencies

```bash
uv add <package-name>
```

### Install Dev Dependencies

```bash
uv sync --group dev
```

### Package with PyInstaller

To create a standalone executable of the `iwb2svg` utility:

```bash
# Install dev dependencies (if not already installed)
uv sync --group dev

# Build standalone executable using the spec file
uv run pyinstaller iwb2svg.spec
```

The executable will be created in the `dist/` folder as `iwb2svg.exe` (Windows) or `iwb2svg` (Linux/macOS).

To customize the build, edit `iwb2svg.spec` before running PyInstaller.

### Run Tests

```bash
uv run pytest
```

### Project Structure

```
newline_iwb_converter/
├── src/
│   └── newline_iwb_converter/
│       ├── __init__.py
│       └── iwb2svg.py          # Main converter utility
├── pyproject.toml               # Project configuration
├── README.md                    # This file
└── .python-version              # Python version lock
```

## How It Works

1. **Extract IWB**: Opens the `.iwb` file (which is a ZIP archive)
2. **Parse content.xml**: Extracts and parses the embedded XML containing SVG pages
3. **Process Images**: Handles image references according to the selected mode
4. **Fix Fills (optional)**: Removes fill attributes from shape elements
5. **Export SVG**: Writes each page as a separate SVG file

## Requirements

- Python 3.10+
- No external dependencies (uses only Python standard library)

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

You are free to use, modify, and distribute this software under the terms of the GPL v3.0.

