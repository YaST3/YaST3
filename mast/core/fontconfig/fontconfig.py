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
from dataclasses import dataclass, field
from pathlib import Path

OPTION_NAMES = {
    "antialias",
    "hinting",
    "hintstyle",
    "rgba",
    "lcdfilter",
    "embeddedbitmap",
}

DEFAULT_MATCH_FAMILIES = ("sans-serif", "serif", "monospace")


@dataclass(slots=True)
class FontMatch:
    """A fontconfig match rule for replacing a family by preferred families."""

    family_test: str
    lang_test: str | None = None
    family_edit: list[str] = field(default_factory=list)


@dataclass(slots=True)
class FontAlias:
    """A fontconfig alias rule mapping one family to another preferred family."""

    family: str
    prefer: str


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
    match_list: list[FontMatch]
    alias_list: list[FontAlias]

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
        self.match_list = [FontMatch(family_test=family) for family in DEFAULT_MATCH_FAMILIES]
        self.alias_list = []

    @staticmethod
    def _first_text(parent: ET.Element, path: str) -> str | None:
        node = parent.find(path)
        if node is None or node.text is None:
            return None
        text = node.text.strip()
        return text if text else None

    def _parse_option_match(self, match: ET.Element) -> bool:
        if match.get("target") != "font":
            return False

        edit = match.find("edit")
        if edit is None:
            return False

        name = edit.get("name")
        if name not in OPTION_NAMES:
            return False

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

        return True

    def _parse_family_match(self, match: ET.Element) -> FontMatch | None:
        family_test = self._first_text(match, "./test[@name='family']/string")
        if not family_test:
            return None

        family_edit = [
            node.text.strip()
            for node in match.findall("./edit[@name='family']/string")
            if node.text and node.text.strip()
        ]
        if not family_edit:
            return None

        lang_test = self._first_text(match, "./test[@name='lang']/string")
        return FontMatch(family_test=family_test, lang_test=lang_test, family_edit=family_edit)

    @staticmethod
    def _is_family_match_node(match: ET.Element) -> bool:
        return (
            match.find("./test[@name='family']/string") is not None
            and match.find("./edit[@name='family']/string") is not None
        )

    @staticmethod
    def _is_option_match_node(match: ET.Element) -> bool:
        if match.get("target") != "font":
            return False
        edit = match.find("edit")
        return edit is not None and edit.get("name") in OPTION_NAMES

    def _append_family_match(self, root: ET.Element, match_rule: FontMatch) -> None:
        match = ET.SubElement(root, "match")

        family_test = ET.SubElement(match, "test", {"name": "family"})
        family_test_text = ET.SubElement(family_test, "string")
        family_test_text.text = match_rule.family_test

        if match_rule.lang_test and match_rule.lang_test.lower() != "en":
            lang_test = ET.SubElement(match, "test", {"name": "lang"})
            lang_test_text = ET.SubElement(lang_test, "string")
            lang_test_text.text = match_rule.lang_test

        family_edit = ET.SubElement(
            match,
            "edit",
            {"name": "family", "binding": "strong", "mode": "prepend"},
        )
        for family in match_rule.family_edit:
            family_text = ET.SubElement(family_edit, "string")
            family_text.text = family

    def _append_alias(self, root: ET.Element, alias_rule: FontAlias) -> None:
        alias = ET.SubElement(root, "alias")
        family = ET.SubElement(alias, "family")
        family.text = alias_rule.family

        prefer = ET.SubElement(alias, "prefer")
        prefer_family = ET.SubElement(prefer, "family")
        prefer_family.text = alias_rule.prefer

    def reload(self) -> None:
        """Reload options from fonts.conf if it exists."""
        self._set_defaults()

        if not self.file_path.exists():
            return

        tree = ET.parse(self.file_path)
        root = tree.getroot()

        parsed_matches: list[FontMatch] = []

        for match in root.findall("match"):
            if self._parse_option_match(match):
                continue

            parsed_match = self._parse_family_match(match)
            if parsed_match is not None:
                parsed_matches.append(parsed_match)

        if parsed_matches:
            self.match_list = parsed_matches
            for family in DEFAULT_MATCH_FAMILIES:
                has_default = any(
                    match.family_test.lower() == family and match.lang_test is None
                    for match in self.match_list
                )
                if not has_default:
                    self.match_list.append(FontMatch(family_test=family))

        self.alias_list = []
        for alias in root.findall("alias"):
            family = self._first_text(alias, "./family")
            prefer = self._first_text(alias, "./prefer/family")
            if family and prefer:
                self.alias_list.append(FontAlias(family=family, prefer=prefer))

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
            if self._is_option_match_node(match) or self._is_family_match_node(match):
                root.remove(match)

        for alias in list(root.findall("alias")):
            root.remove(alias)

        for match_rule in self.match_list:
            if not match_rule.family_test or not match_rule.family_edit:
                continue
            self._append_family_match(root, match_rule)

        for alias_rule in self.alias_list:
            if not alias_rule.family or not alias_rule.prefer:
                continue
            self._append_alias(root, alias_rule)

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
