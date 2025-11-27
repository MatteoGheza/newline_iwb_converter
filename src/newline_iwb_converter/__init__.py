"""Newline IWB Converter - A utility for converting Newline IWB files."""

import importlib.metadata

try:
    __version__ = importlib.metadata.version("newline-iwb-converter")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.1.0"
