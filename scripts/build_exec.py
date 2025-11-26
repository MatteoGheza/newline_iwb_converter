#!/usr/bin/env python3
"""
Build script for creating PyInstaller executables.
Usage: python scripts/build_exec.py [iwb2svg|iwb2pdf|all]
"""

import sys
import PyInstaller.__main__


def build_iwb2svg():
    """Build iwb2svg executable."""
    print("Building iwb2svg executable...")
    try:
        PyInstaller.__main__.run([
            "src/newline_iwb_converter/iwb2svg.py",
            "--onefile",
            "--console",
            "--name", "iwb2svg",
        ])
        return True
    except Exception as e:
        print(f"Error building iwb2svg: {e}")
        return False


def build_iwb2pdf():
    """Build iwb2pdf executable."""
    print("Building iwb2pdf executable...")
    try:
        PyInstaller.__main__.run([
            "src/newline_iwb_converter/iwb2pdf.py",
            "--onefile",
            "--console",
            "--name", "iwb2pdf",
            "--hidden-import=reportlab",
            "--hidden-import=svglib",
            "--hidden-import=PIL",
            "--hidden-import=lxml",
        ])
        return True
    except Exception as e:
        print(f"Error building iwb2pdf: {e}")
        return False


def main():
    """Main entry point."""
    targets = sys.argv[1:] if sys.argv[1:] else ["all"]
    
    success = True
    for target in targets:
        if target == "iwb2svg":
            success = build_iwb2svg() and success
        elif target == "iwb2pdf":
            success = build_iwb2pdf() and success
        elif target == "all":
            success = build_iwb2svg() and success
            success = build_iwb2pdf() and success
        else:
            print(f"Unknown target: {target}")
            print("Available targets: iwb2svg, iwb2pdf, all")
            sys.exit(1)
    
    if success:
        print("\nBuild complete! Executables are in the 'dist' directory.")
        sys.exit(0)
    else:
        print("\nBuild failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
