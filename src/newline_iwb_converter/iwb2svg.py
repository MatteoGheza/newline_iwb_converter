#!/usr/bin/env python3

"""Convert Newline IWB files to SVG format."""

import zipfile
import os
import sys
import argparse
import xml.etree.ElementTree as ET
import base64
import re
from pathlib import Path
from newline_iwb_converter import __version__

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"

ET.register_namespace("svg", SVG_NS)
ET.register_namespace("xlink", XLINK_NS)
ET.register_namespace("", "http://www.imsglobal.org/xsd/iwb_v1p0")


def remove_fills(svg_root):
    # Set fill="none" or rewrite style fill to none for all shape elements.
    # Skip elements with id starting with "Autoshape" or "Word"
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

        # Skip elements with id starting with "Autoshape" or "Word"
        elem_id = elem.get("id", "")
        if elem_id.startswith("Autoshape") or elem_id.startswith("Word"):
            continue

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


def convert_textarea_to_text(svg_root):
    """
    Convert textarea elements to text elements, preserving all attributes and children.
    Replace tbreak elements with tspan elements that have proper line spacing (dy="1.2em").
    """
    # Find all textarea elements
    textareas = []
    for elem in svg_root.iter():
        tag = elem.tag
        if isinstance(tag, str) and tag.endswith("textarea"):
            textareas.append(elem)
    
    # Convert each textarea to text
    for textarea in textareas:
        # Create new text element with same attributes
        text_elem = ET.Element(f"{{{SVG_NS}}}text", attrib=textarea.attrib)
        
        # Get the x coordinate for line breaks (from parent text element)
        text_x = textarea.attrib.get("x", "0")
        
        # Process children, replacing tbreak elements with properly spaced tspan elements
        for child in textarea:
            tag = child.tag
            if isinstance(tag, str) and tag.endswith("tbreak"):
                # Skip tbreak elements - they will be handled by the following tspan
                continue
            
            # Check if this tspan is preceded by a tbreak
            child_index = list(textarea).index(child)
            has_preceding_tbreak = False
            if child_index > 0:
                prev_sibling = textarea[child_index - 1]
                prev_tag = prev_sibling.tag
                if isinstance(prev_tag, str) and prev_tag.endswith("tbreak"):
                    has_preceding_tbreak = True
            
            # Copy the child element
            new_child = child
            if has_preceding_tbreak:
                # Add line break attributes to tspan that follows tbreak
                if isinstance(tag, str) and tag.endswith("tspan"):
                    # Create a copy to modify
                    new_child = ET.Element(tag, attrib=child.attrib)
                    # Add x coordinate and line spacing
                    new_child.set("x", text_x)
                    new_child.set("dy", "1.2em")
                    # Copy text and tail
                    new_child.text = child.text
                    new_child.tail = child.tail
                    # Copy all children
                    for grandchild in child:
                        new_child.append(grandchild)
            
            text_elem.append(new_child)
        
        # Copy text content from textarea
        if textarea.text:
            text_elem.text = textarea.text
        if textarea.tail:
            text_elem.tail = textarea.tail
        
        # Replace textarea with text in parent
        parent = svg_root.find(".//" + textarea.tag + "/..")
        if parent is not None:
            index = list(parent).index(textarea)
            parent[index] = text_elem
        else:
            # If not found as child, search more thoroughly
            for elem in svg_root.iter():
                if textarea in list(elem):
                    index = list(elem).index(textarea)
                    elem[index] = text_elem
                    break


def parse_transform_translate(transform_str):
    """Extract translate(x, y) from a transform attribute string."""
    if not transform_str:
        return 0.0, 0.0
    
    # Look for translate(...) pattern
    match = re.search(r'translate\s*\(\s*([+-]?\d+\.?\d*)\s*[,\s]\s*([+-]?\d+\.?\d*)\s*\)', transform_str)
    if match:
        try:
            tx = float(match.group(1))
            ty = float(match.group(2))
            return tx, ty
        except (ValueError, IndexError):
            pass
    
    return 0.0, 0.0


def fix_svg_size(svg_root, margin=100):
    """
    Fix SVG size if width or height are smaller than the actual content.
    Calculate bounding box of all elements and expand SVG if needed.
    Takes into account transform attributes (especially translate).
    
    Args:
        svg_root: The SVG root element
        margin: Safety margin to add around content (default: 100)
    """
    try:
        # Get current SVG dimensions
        width_str = svg_root.get("width", "100%")
        height_str = svg_root.get("height", "100%")
        
        # Parse numeric values (ignore percentages)
        width = float(width_str) if width_str and width_str.replace(".", "").isdigit() else None
        height = float(height_str) if height_str and height_str.replace(".", "").isdigit() else None
        
        if width is None or height is None:
            return  # Can't fix if dimensions are percentages or invalid
        
        # Find bounding box of all elements with position/size attributes
        max_x = 0.0
        max_y = 0.0
        
        for elem in svg_root.iter():
            tag = elem.tag
            if not isinstance(tag, str):
                continue
            local = tag.split("}")[-1]
            
            # Get transform offset if present
            transform = elem.get("transform", "")
            tx, ty = parse_transform_translate(transform)
            
            # For rect elements
            if local == "rect":
                try:
                    x = float(elem.get("x", 0)) + tx
                    y = float(elem.get("y", 0)) + ty
                    w = float(elem.get("width", 0))
                    h = float(elem.get("height", 0))
                    max_x = max(max_x, x + w)
                    max_y = max(max_y, y + h)
                except (ValueError, TypeError):
                    pass
            
            # For circle elements
            elif local == "circle":
                try:
                    cx = float(elem.get("cx", 0)) + tx
                    cy = float(elem.get("cy", 0)) + ty
                    r = float(elem.get("r", 0))
                    max_x = max(max_x, cx + r)
                    max_y = max(max_y, cy + r)
                except (ValueError, TypeError):
                    pass
            
            # For ellipse elements
            elif local == "ellipse":
                try:
                    cx = float(elem.get("cx", 0)) + tx
                    cy = float(elem.get("cy", 0)) + ty
                    rx = float(elem.get("rx", 0))
                    ry = float(elem.get("ry", 0))
                    max_x = max(max_x, cx + rx)
                    max_y = max(max_y, cy + ry)
                except (ValueError, TypeError):
                    pass
            
            # For polyline and polygon - parse points attribute
            elif local in ("polyline", "polygon"):
                try:
                    points_str = elem.get("points", "")
                    if points_str:
                        # Points format: "x1,y1 x2,y2 x3,y3 ..."
                        points = points_str.replace(",", " ").split()
                        for i in range(0, len(points), 2):
                            if i + 1 < len(points):
                                x = float(points[i]) + tx
                                y = float(points[i + 1]) + ty
                                max_x = max(max_x, x)
                                max_y = max(max_y, y)
                except (ValueError, TypeError, IndexError):
                    pass
            
            # For image elements
            elif local == "image":
                try:
                    x = float(elem.get("x", 0)) + tx
                    y = float(elem.get("y", 0)) + ty
                    w = float(elem.get("width", 0))
                    h = float(elem.get("height", 0))
                    max_x = max(max_x, x + w)
                    max_y = max(max_y, y + h)
                except (ValueError, TypeError):
                    pass
            
            # For path elements - extract coordinates from d attribute (basic parsing)
            elif local == "path":
                try:
                    d_str = elem.get("d", "")
                    if d_str:
                        # Simple extraction of all numbers from path data
                        numbers = re.findall(r"-?\d+\.?\d*", d_str)
                        for i in range(0, len(numbers), 2):
                            if i + 1 < len(numbers):
                                x = float(numbers[i]) + tx
                                y = float(numbers[i + 1]) + ty
                                max_x = max(max_x, x)
                                max_y = max(max_y, y)
                except (ValueError, TypeError, IndexError):
                    pass
        
        # If content extends beyond current size, expand SVG with safety margin
        if max_x > width or max_y > height:
            new_width = max(width, max_x + margin)
            new_height = max(height, max_y + margin)
            svg_root.set("width", str(new_width))
            svg_root.set("height", str(new_height))
            print(f"Fixed SVG size: {width}x{height} → {new_width}x{new_height} (margin: {margin})")
    
    except Exception as e:
        print(f"Warning: Could not fix SVG size: {e}", file=sys.stderr)


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


def fix_compressed_unexistent_images(svg_root, zip_file):
    """Fix xlink:href for compressed images that do not exist in the zip."""
    for img_elem in svg_root.findall(".//svg:image", {"svg": SVG_NS}):
        href = img_elem.get(f"{{{XLINK_NS}}}href")
        if href and href.startswith("images/") and href.endswith(".png"):
            try:
                zip_file.getinfo(href)
            except KeyError:
                # Image does not exist, try compressed version
                compressed_href = href.replace("images/", "images/compressed_")
                print(f"Fixing missing image href: {href} → {compressed_href}")
                try:
                    zip_file.getinfo(compressed_href)
                    img_elem.set(f"{{{XLINK_NS}}}href", compressed_href)
                except KeyError:
                    pass  # Neither original nor compressed exists


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


def extract_iwb_to_svg(iwb_path, output_dir, fix_fills=True, fix_size=True, images_mode="data_uri", delete_background=False):
    """
    Extract SVG pages from an IWB file.
    
    Args:
        iwb_path: Path to input .iwb file
        output_dir: Output directory for SVG files
        fix_fills: Whether to remove fills from shapes
        fix_size: Whether to fix SVG size if content extends beyond dimensions
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
            fix_compressed_unexistent_images(svg_root, z)
            if images_mode == "data_uri":
                process_images_data_uri(svg_root, z)
            # For "nothing" mode, leave href as-is
            # For "copy_directory" mode, leave href as-is (already copied)

            # ---- DELETE BACKGROUND IMAGES ----
            if delete_background:
                delete_background_images(svg_root)

            # ---- CONVERT TEXTAREA TO TEXT ----
            convert_textarea_to_text(svg_root)

            # ---- APPLY FIX OPTIONS ----
            if fix_fills:
                remove_fills(svg_root)
            
            if fix_size:
                fix_svg_size(svg_root)

            out_path = os.path.join(output_dir, f"page_{idx}.svg")
            ET.ElementTree(svg_root).write(
                out_path, encoding="utf-8", xml_declaration=True
            )
            print(f"Saved: {out_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Extract SVG pages from an IWB file, with optional fill→stroke repair."
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
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

    size_group = parser.add_mutually_exclusive_group()
    size_group.add_argument(
        "--fix-size",
        dest="fix_size",
        action="store_true",
        help="Fix SVG size if content extends beyond dimensions (default)",
    )
    size_group.add_argument(
        "--no-fix-size",
        dest="fix_size",
        action="store_false",
        help="Do NOT fix SVG size",
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

    parser.set_defaults(fix_fills=True, fix_size=True, delete_background=False)
    args = parser.parse_args()

    extract_iwb_to_svg(
        args.iwb_file,
        args.output,
        fix_fills=args.fix_fills,
        fix_size=args.fix_size,
        images_mode=args.images_mode,
        delete_background=args.delete_background,
    )


if __name__ == "__main__":
    main()
