#!/usr/bin/env python3

"""Convert Newline IWB files to SVG format."""

import zipfile
import os
import sys
import argparse
import xml.etree.ElementTree as ET
import base64
from pathlib import Path

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"

ET.register_namespace("svg", SVG_NS)
ET.register_namespace("xlink", XLINK_NS)
ET.register_namespace("", "http://www.imsglobal.org/xsd/iwb_v1p0")


def remove_fills(svg_root):
    """
    Mimic Inkscape: "Select All" -> Fill -> None.
    Set fill="none" or rewrite style fill to none for all shape elements.
    """
    shape_tags = {
        "path",
        "rect",
        "circle",
        "ellipse",
        "polygon",
        "polyline",
        "line",
        "text",
    }
    for elem in svg_root.iter():
        # ensure we work with local tag name (ignore namespace)
        tag = elem.tag
        if not isinstance(tag, str):
            continue
        local = tag.split("}")[-1]

        # If explicit presentation attribute exists, set it to none
        if "fill" in elem.attrib:
            elem.set("fill", "none")

        # Handle style attribute (e.g. "style:fill:#000000;stroke:...")
        style = elem.get("style")
        if style:
            parts = [p for p in style.split(";") if p.strip()]
            out_parts = []
            has_fill = False
            for p in parts:
                if ":" not in p:
                    continue
                k, v = p.split(":", 1)
                k = k.strip()
                v = v.strip()
                if k == "fill":
                    out_parts.append("fill:none")
                    has_fill = True
                else:
                    out_parts.append(f"{k}:{v}")
            # If there was no fill declaration but the element is a shape, add fill:none
            if not has_fill and local in shape_tags:
                out_parts.append("fill:none")
            if out_parts:
                elem.set("style", ";".join(out_parts))

        # If there was neither a fill attribute nor a style and this is a shape, set fill attribute
        if "fill" not in elem.attrib and not elem.get("style") and local in shape_tags:
            elem.set("fill", "none")


def delete_background_images(svg_root):
    """Remove image elements with id starting with 'backgroundImage'."""
    for img_elem in svg_root.findall(".//svg:image", {"svg": SVG_NS}):
        elem_id = img_elem.get("id")
        if elem_id and elem_id.startswith("backgroundImage"):
            # Find parent and remove the image element
            for parent in svg_root.iter():
                if img_elem in list(parent):
                    parent.remove(img_elem)
                    break


def process_images_data_uri(svg_root, zip_file):
    """Convert image xlink:href to data URIs from the zip file."""
    for img_elem in svg_root.findall(".//svg:image", {"svg": SVG_NS}):
        href = img_elem.get(f"{{{XLINK_NS}}}href")
        if href and href.startswith("images/"):
            try:
                image_data = zip_file.read(href)
                # Determine MIME type from file extension
                ext = Path(href).suffix.lower()
                mime_types = {
                    ".png": "image/png",
                    ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg",
                    ".gif": "image/gif",
                    ".svg": "image/svg+xml",
                }
                mime_type = mime_types.get(ext, "application/octet-stream")
                
                # Create data URI
                b64_data = base64.b64encode(image_data).decode("utf-8")
                data_uri = f"data:{mime_type};base64,{b64_data}"
                img_elem.set(f"{{{XLINK_NS}}}href", data_uri)
            except KeyError:
                print(f"Warning: Image file not found in IWB: {href}", file=sys.stderr)


def process_images_copy_directory(svg_root, zip_file, output_dir):
    """Copy the images directory from the IWB file to the output directory."""
    # Extract all images from the zip
    for name in zip_file.namelist():
        if name.startswith("images/"):
            target_path = os.path.join(output_dir, name)
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            with zip_file.open(name) as source:
                with open(target_path, "wb") as target:
                    target.write(source.read())


def extract_iwb_to_svg(iwb_path, output_dir, fix_fills=True, images_mode="data_uri", delete_background=False):
    """
    Extract SVG pages from an IWB file.
    
    Args:
        iwb_path: Path to input .iwb file
        output_dir: Output directory for SVG files
        fix_fills: Whether to remove fills from shapes
        images_mode: How to handle images - "nothing", "copy_directory", or "data_uri"
        delete_background: Whether to remove background image elements
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with zipfile.ZipFile(iwb_path, "r") as z:
        xml_name = None
        for name in z.namelist():
            if name.lower().endswith(".xml"):
                xml_name = name
                break

        if xml_name is None:
            print("No XML file found in IWB.", file=sys.stderr)
            sys.exit(1)

        xml_data = z.read(xml_name)
        root = ET.fromstring(xml_data)

        ns = {"svg": SVG_NS}
        pages = root.findall(".//svg:page", ns)

        if not pages:
            print("No <svg:page> elements found.", file=sys.stderr)
            sys.exit(1)

        # Handle images directory copy first if needed
        if images_mode == "copy_directory":
            process_images_copy_directory(root, z, output_dir)

        for idx, page in enumerate(pages):
            attribs = {
                "version": "1.1",
                "width": page.attrib.get("width", "100%"),
                "height": page.attrib.get("height", "100%"),
            }

            svg_root = ET.Element(f"{{{SVG_NS}}}svg", attrib=attribs)

            # Copy page content
            for child in list(page):
                svg_root.append(child)

            # ---- PROCESS IMAGES ----
            if images_mode == "data_uri":
                process_images_data_uri(svg_root, z)
            # For "nothing" mode, leave href as-is
            # For "copy_directory" mode, leave href as-is (already copied)

            # ---- DELETE BACKGROUND IMAGES ----
            if delete_background:
                delete_background_images(svg_root)

            # ---- APPLY FIX OPTION ----
            if fix_fills:
                remove_fills(svg_root)

            out_path = os.path.join(output_dir, f"page_{idx}.svg")
            ET.ElementTree(svg_root).write(
                out_path, encoding="utf-8", xml_declaration=True
            )
            print(f"Saved: {out_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Extract SVG pages from an IWB file, with optional fill→stroke repair."
    )
    parser.add_argument("iwb_file", help="Path to input .iwb file")
    parser.add_argument("-o", "--output", default="svg_output", help="Output directory")

    fix_group = parser.add_mutually_exclusive_group()
    fix_group.add_argument(
        "--fix-fills",
        dest="fix_fills",
        action="store_true",
        help="Remove fill from shapes (default)",
    )
    fix_group.add_argument(
        "--no-fix-fills",
        dest="fix_fills",
        action="store_false",
        help="Do NOT modify fill behavior",
    )

    parser.add_argument(
        "--images",
        dest="images_mode",
        choices=["nothing", "copy_directory", "data_uri"],
        default="data_uri",
        help="How to handle images: nothing (keep xlink:href), copy_directory (copy images/ to output), data_uri (embed as base64, default)",
    )

    parser.add_argument(
        "--delete-background",
        dest="delete_background",
        action="store_true",
        help="Remove background image elements (id starting with 'backgroundImage')",
    )

    parser.set_defaults(fix_fills=True, delete_background=False)
    args = parser.parse_args()

    extract_iwb_to_svg(
        args.iwb_file,
        args.output,
        fix_fills=args.fix_fills,
        images_mode=args.images_mode,
        delete_background=args.delete_background,
    )


if __name__ == "__main__":
    main()
