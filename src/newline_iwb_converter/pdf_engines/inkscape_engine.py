#!/usr/bin/env python3

"""Inkscape PDF conversion engine."""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from newline_iwb_converter.pdf_engines.base import BasePDFEngine


class InkscapeEngine(BasePDFEngine):
    """PDF conversion engine using Inkscape."""

    def __init__(self):
        """Initialize the Inkscape engine."""
        self._inkscape_path = None

    def find_inkscape(self):
        """
        Find Inkscape executable in system PATH or common installation paths.

        Returns:
            Path to Inkscape executable if found, None otherwise
        """
        if self._inkscape_path:
            return self._inkscape_path

        # First, try to find in PATH
        inkscape_path = shutil.which("inkscape")
        if inkscape_path:
            self._inkscape_path = inkscape_path
            return inkscape_path

        # Common installation paths for different operating systems
        common_paths = []

        if sys.platform == "win32":
            # Windows common paths
            common_paths = [
                r"C:\Program Files\Inkscape\bin\inkscape.exe",
                r"C:\Program Files (x86)\Inkscape\bin\inkscape.exe",
                r"C:\Program Files\Inkscape\inkscape.exe",
                r"C:\Program Files (x86)\Inkscape\inkscape.exe",
            ]
        elif sys.platform == "darwin":
            # macOS common paths
            common_paths = [
                "/Applications/Inkscape.app/Contents/MacOS/inkscape",
                "/usr/local/bin/inkscape",
                "/opt/homebrew/bin/inkscape",
            ]
        elif sys.platform == "linux":
            # Linux common paths
            common_paths = [
                "/usr/bin/inkscape",
                "/usr/local/bin/inkscape",
                "/snap/bin/inkscape",
            ]

        # Check each common path
        for path in common_paths:
            if Path(path).exists():
                self._inkscape_path = path
                return path

        return None

    def is_available(self):
        """
        Check if Inkscape is available on the system.

        Returns:
            True if Inkscape is available, False otherwise
        """
        return self.find_inkscape() is not None

    def combine_svgs_to_pdf(self, svg_dir, output_pdf, **kwargs):
        """
        Combine multiple SVG files into a single PDF using Inkscape.

        Args:
            svg_dir: Directory containing SVG files
            output_pdf: Path to output PDF file
            **kwargs: Unused for Inkscape engine
        """
        # Get all SVG files, sorted by name
        svg_files = sorted(
            Path(svg_dir).glob("page_*.svg"),
            key=lambda x: int(x.stem.split("_")[1])
        )

        if not svg_files:
            print(f"No SVG files found in {svg_dir}", file=sys.stderr)
            sys.exit(1)

        inkscape_path = self.find_inkscape()
        pdf_files = []

        with tempfile.TemporaryDirectory() as temp_dir:
            # Convert each SVG to PDF using Inkscape
            for svg_file in svg_files:
                temp_pdf = Path(temp_dir) / f"page_{svg_file.stem.split('_')[1]}.pdf"

                try:
                    cmd = [
                        inkscape_path,
                        "--without-gui",
                        str(svg_file),
                        f"--export-filename={temp_pdf}",
                        f"--export-type=pdf",
                    ]

                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

                    if result.returncode == 0:
                        pdf_files.append(temp_pdf)
                        print(f"Converted: {svg_file.name} -> {temp_pdf.name}")
                    else:
                        print(f"Failed to convert {svg_file.name}: {result.stderr}", file=sys.stderr)
                        sys.exit(1)

                except subprocess.TimeoutExpired:
                    print(f"Inkscape conversion timed out for {svg_file.name}", file=sys.stderr)
                    sys.exit(1)
                except Exception as e:
                    print(f"Error converting {svg_file.name}: {e}", file=sys.stderr)
                    sys.exit(1)

            # Merge all PDFs into one
            try:
                from PyPDF2 import PdfMerger

                merger = PdfMerger()
                for pdf_file in pdf_files:
                    merger.append(str(pdf_file))
                merger.write(output_pdf)
                merger.close()
                print(f"Saved PDF: {output_pdf}")

            except ImportError:
                # Fallback: copy first PDF as a workaround
                print("PyPDF2 not available, using reportlab for PDF merging", file=sys.stderr)

                if pdf_files:
                    import shutil
                    shutil.copy(str(pdf_files[0]), output_pdf)
                    print(f"Warning: Only first page saved. Install PyPDF2 for full merging: pip install PyPDF2", file=sys.stderr)
                    print(f"Saved PDF: {output_pdf}")
