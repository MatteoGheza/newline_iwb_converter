# Newline IWB Converter

A converter utility for extracting SVG pages from Newline whiteboard IWB files, with optional PDF conversion.

## Features

- **Extract SVG pages** from Newline IWB (`.iwb`) files
- **Convert IWB to PDF** - create multi-page PDFs with independent or uniform page sizing
- **Flexible image handling**:
  - Embed images as base64 data URIs (default)
  - Copy images directory alongside SVGs
  - Keep external image references
- **Optional fill removal** from shape elements (Inkscape-style)
- **Zero external dependencies for iwb2svg** - uses only Python standard library for SVG extraction

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

### iwb2svg - Extract SVG Pages

#### Basic Usage

```bash
iwb2svg input.iwb -o output_directory
```

This will extract all SVG pages from the IWB file and embed images as base64 data URIs (default behavior).

#### Command Line Options

```
usage: iwb2svg [-h] [-o OUTPUT] [--fix-fills | --no-fix-fills] [--fix-size | --no-fix-size] [--images {nothing,copy_directory,data_uri}] [--delete-background] iwb_file

Extract SVG pages from an IWB file, with optional fill→stroke repair.

positional arguments:
  iwb_file              Path to input .iwb file

options:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        Output directory (default: svg_output)
  --fix-fills           Remove fill from shapes (default)
  --no-fix-fills        Do NOT modify fill behavior
  --fix-size            Fix SVG size if content extends beyond dimensions (default)
  --no-fix-size         Do NOT fix SVG size
  --images {nothing,copy_directory,data_uri}
                        How to handle images (default: data_uri)
  --delete-background   Remove background image elements
```

#### Examples

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

**Remove background images:**
```bash
iwb2svg input.iwb -o output_dir --delete-background
```

**Using uv run (without virtual environment activation):**
```bash
uv run iwb2svg input.iwb -o output_dir
```

### iwb2pdf - Convert to PDF

#### Basic Usage

```bash
iwb2pdf input.iwb -o output.pdf
```

This will extract all SVG pages and convert them to a multi-page PDF with independent page sizing.

#### Command Line Options

```
usage: iwb2pdf [-h] [-o OUTPUT] [--fix-fills | --no-fix-fills] [--fix-size | --no-fix-size] [--delete-background] [--uniform-size | --independent-size] iwb_file

Convert IWB files to PDF format.

positional arguments:
  iwb_file              Path to input .iwb file

options:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        Output PDF file (default: output.pdf)
  --fix-fills           Remove fill from shapes (default)
  --no-fix-fills        Do NOT modify fill behavior
  --fix-size            Fix SVG size if content extends beyond dimensions (default)
  --no-fix-size         Do NOT fix SVG size
  --delete-background   Remove background image elements
  --uniform-size        Make all pages the same size (size of the largest page)
  --independent-size    Each page size is independent based on its content (default)
```

#### Examples

**Create PDF with independent page sizing (default):**
```bash
iwb2pdf input.iwb -o output.pdf
```

**Make all pages the same size:**
```bash
iwb2pdf input.iwb -o output.pdf --uniform-size
```

**Remove background images:**
```bash
iwb2pdf input.iwb -o output.pdf --delete-background
```

**Using uv run:**
```bash
uv run iwb2pdf input.iwb -o output.pdf
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

To create standalone executables:

```bash
# Install dev dependencies (if not already installed)
uv sync --group dev

# Build all executables (iwb2svg and iwb2pdf)
uv run python scripts/build_exec.py

# Or build a specific tool
uv run python scripts/build_exec.py iwb2svg
uv run python scripts/build_exec.py iwb2pdf
```

The executables will be created in the `dist/` folder:
- `iwb2svg.exe` / `iwb2svg` (Linux/macOS)
- `iwb2pdf.exe` / `iwb2pdf` (Linux/macOS)

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
│       ├── iwb2svg.py          # SVG extraction utility
│       └── iwb2pdf.py          # PDF conversion utility
├── scripts/
│   └── build_exec.py                # PyInstaller build script
├── pyproject.toml               # Project configuration
├── README.md                    # This file
└── .python-version              # Python version lock
```

## How It Works

### iwb2svg
1. **Extract IWB**: Opens the `.iwb` file (which is a ZIP archive)
2. **Parse content.xml**: Extracts and parses the embedded XML containing SVG pages
3. **Process Images**: Handles image references according to the selected mode
4. **Fix Fills (optional)**: Removes fill attributes from shape elements
5. **Fix Size (optional)**: Adjusts SVG dimensions if content extends beyond them
6. **Export SVG**: Writes each page as a separate SVG file

### iwb2pdf
1. **Extract SVGs**: Uses `iwb2svg` to extract all SVG pages from the IWB file
2. **Convert SVGs**: Converts each SVG to a ReportLab drawing
3. **Create PDF**: Combines all drawings into a multi-page PDF
4. **Page Sizing**: Each page is sized independently (or uniformly) based on content

## Requirements

- Python 3.10+
- `iwb2svg`: No external dependencies (uses only Python standard library)
- `iwb2pdf`: Requires `reportlab` and `svglib` (installed via `uv sync`)

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

You are free to use, modify, and distribute this software under the terms of the GPL v3.0.

