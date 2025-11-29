#!/usr/bin/env python3

"""SVGlib PDF conversion engine."""

import sys
from pathlib import Path

from reportlab.pdfgen import canvas
from reportlab.graphics import renderPDF
from svglib.svglib import svg2rlg

from newline_iwb_converter.pdf_engines.base import BasePDFEngine


class SvglibEngine(BasePDFEngine):
    """PDF conversion engine using svglib."""

    def is_available(self):
        """
        Check if svglib is available.

        Returns:
            True (svglib is always available as a dependency)
        """
        return True

    def svg_to_pdf_page(self, svg_path):
        """
        Convert an SVG file to a ReportLab drawing.

        Args:
            svg_path: Path to the SVG file

        Returns:
            ReportLab drawing object or None if conversion failed
        """
        try:
            drawing = svg2rlg(svg_path)
            return drawing
        except Exception as e:
            print(f"Warning: Could not convert {svg_path} to drawing: {e}", file=sys.stderr)
            return None

    def combine_svgs_to_pdf(self, svg_dir, output_pdf, uniform_size=False, **kwargs):
        """
        Combine multiple SVG files from a directory into a single PDF using svglib.

        Args:
            svg_dir: Directory containing SVG files
            output_pdf: Path to output PDF file
            uniform_size: If True, all pages have the size of the largest page.
                          If False, each page is sized independently (default).
            **kwargs: Additional options (unused)
        """
        # Get all SVG files, sorted by name
        svg_files = sorted(
            Path(svg_dir).glob("page_*.svg"),
            key=lambda x: int(x.stem.split("_")[1])
        )

        if not svg_files:
            print(f"No SVG files found in {svg_dir}", file=sys.stderr)
            sys.exit(1)

        # If uniform size is requested, first pass to find max dimensions
        max_width = 0
        max_height = 0
        drawings = []

        for svg_file in svg_files:
            drawing = self.svg_to_pdf_page(str(svg_file))
            if drawing is None:
                print(f"Skipping {svg_file}", file=sys.stderr)
                drawings.append(None)
                continue
            drawings.append(drawing)
            if uniform_size:
                max_width = max(max_width, drawing.width)
                max_height = max(max_height, drawing.height)

        if uniform_size:
            padding = 10
            uniform_page_width = max_width + padding * 2
            uniform_page_height = max_height + padding * 2

        # Create PDF
        pdf_canvas = canvas.Canvas(output_pdf)

        for idx, (svg_file, drawing) in enumerate(zip(svg_files, drawings)):
            if drawing is None:
                continue

            # Get SVG dimensions
            svg_width = drawing.width
            svg_height = drawing.height

            if uniform_size:
                page_width = uniform_page_width
                page_height = uniform_page_height
                padding = 10
            else:
                # Set page size to match SVG dimensions (with small padding)
                padding = 10
                page_width = svg_width + padding * 2
                page_height = svg_height + padding * 2

            pdf_canvas.setPageSize((page_width, page_height))

            # Draw SVG on the page
            if uniform_size:
                # Center SVG on the page
                x_offset = (page_width - svg_width) / 2
                y_offset = (page_height - svg_height) / 2
                pdf_canvas.saveState()
                pdf_canvas.translate(x_offset, y_offset)
            else:
                # Just add padding
                pdf_canvas.saveState()
                pdf_canvas.translate(padding, padding)

            renderPDF.draw(drawing, pdf_canvas, 0, 0)
            pdf_canvas.restoreState()

            # Add new page for next SVG (except for the last one)
            if idx < len(drawings) - 1:
                pdf_canvas.showPage()

            if uniform_size:
                print(f"Added to PDF: {svg_file.name} (centered on {page_width}x{page_height})")
            else:
                print(f"Added to PDF: {svg_file.name} ({page_width}x{page_height})")

        pdf_canvas.save()
        print(f"Saved PDF: {output_pdf}")
