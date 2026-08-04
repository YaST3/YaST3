"""Fontconfig options reader and writer.

This module manages a subset of fontconfig options inspired by fontweak:
- antialias
- hinting
- hintstyle
- rgba
- lcdfilter
- embeddedbitmap
"""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from pathlib import Path

OPTION_NAMES = {
    "antialias",
    "hinting",
    "hintstyle",
    "rgba",
    "lcdfilter",
    "embeddedbitmap",
}


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class FontConfig:
    """Represents user fontconfig options stored in fonts.conf."""

    HINTSTYLE_OPTIONS = ("hintnone", "hintslight", "hintmedium", "hintfull")
    RGBA_OPTIONS = ("none", "rgb", "bgr", "vrgb", "vbgr")
    LCDFILTER_OPTIONS = ("lcdnone", "lcddefault", "lcdlight", "lcdlegacy")

    antialias: bool
    hinting: bool
    hintstyle: str
    rgba: str
    lcdfilter: str
    embeddedbitmap: bool

    def __init__(self, file_path: str | None = None) -> None:
        self.file_path = Path(file_path) if file_path else self._resolve_file_path()
        self._set_defaults()
        self.reload()

    @staticmethod
    def _resolve_file_path() -> Path:
        xdg_config_home = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        modern = xdg_config_home / "fontconfig" / "fonts.conf"
        legacy = Path.home() / ".fonts.conf"

        if modern.exists():
            return modern
        if legacy.exists():
            return legacy
        return modern

    def _set_defaults(self) -> None:
        self.antialias = True
        self.hinting = True
        self.hintstyle = "hintfull"
        self.rgba = "none"
        self.lcdfilter = "lcddefault"
        self.embeddedbitmap = True

    def reload(self) -> None:
        """Reload options from fonts.conf if it exists."""
        self._set_defaults()

        if not self.file_path.exists():
            return

        tree = ET.parse(self.file_path)
        root = tree.getroot()

        for match in root.findall("match"):
            if match.get("target") != "font":
                continue

            edit = match.find("edit")
            if edit is None:
                continue

            name = edit.get("name")
            if name not in OPTION_NAMES:
                continue

            bool_node = edit.find("bool")
            const_node = edit.find("const")
            value = None
            if bool_node is not None:
                value = bool_node.text
            elif const_node is not None:
                value = const_node.text

            if name == "antialias":
                self.antialias = _parse_bool(value, self.antialias)
            elif name == "hinting":
                self.hinting = _parse_bool(value, self.hinting)
            elif name == "hintstyle" and value:
                self.hintstyle = value.strip()
            elif name == "rgba" and value:
                self.rgba = value.strip()
            elif name == "lcdfilter" and value:
                self.lcdfilter = value.strip()
            elif name == "embeddedbitmap":
                self.embeddedbitmap = _parse_bool(value, self.embeddedbitmap)

    def write(self) -> None:
        """Write current options into fonts.conf."""
        root: ET.Element

        if self.file_path.exists():
            tree = ET.parse(self.file_path)
            root = tree.getroot()
            if root.tag != "fontconfig":
                raise ValueError(f"Invalid root element in {self.file_path}: {root.tag}")
        else:
            root = ET.Element("fontconfig")
            tree = ET.ElementTree(root)

        for match in list(root.findall("match")):
            if match.get("target") != "font":
                continue
            edit = match.find("edit")
            if edit is None:
                continue
            if edit.get("name") in OPTION_NAMES:
                root.remove(match)

        self._append_option(root, "antialias", "bool", "true" if self.antialias else "false")
        self._append_option(root, "hinting", "bool", "true" if self.hinting else "false")
        self._append_option(root, "hintstyle", "const", self.hintstyle)
        self._append_option(root, "rgba", "const", self.rgba)
        self._append_option(root, "lcdfilter", "const", self.lcdfilter)
        self._append_option(
            root,
            "embeddedbitmap",
            "bool",
            "true" if self.embeddedbitmap else "false",
        )

        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        ET.indent(tree, space="  ")
        tree.write(self.file_path, encoding="utf-8", xml_declaration=True)

    @staticmethod
    def _append_option(root: ET.Element, name: str, value_tag: str, value: str) -> None:
        match = ET.SubElement(root, "match", {"target": "font"})
        edit = ET.SubElement(match, "edit", {"name": name, "mode": "assign"})
        node = ET.SubElement(edit, value_tag)
        node.text = value
