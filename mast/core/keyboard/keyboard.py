"""Keyboard layout management logic."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

VCONSOLE_FILE = "/etc/vconsole.conf"


@dataclass
class KeyboardLayout:
    code: str
    name: str


def get_current_keyboard_layout() -> str:
    """Get the current keyboard layout from vconsole.conf.

    Returns:
        The current keyboard layout code (e.g., "us", "de", "cn").
    """
    if Path(VCONSOLE_FILE).exists():
        try:
            with open(VCONSOLE_FILE, "r") as f:
                for line in f:
                    if line.startswith("KEYMAP="):
                        return line.strip().split("=", 1)[1]
        except (PermissionError, IOError):
            pass

    try:
        result = subprocess.run(
            ["localectl", "status"], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            for line in result.stdout.split("\n"):
                if "VC Keymap" in line:
                    parts = line.split(":", 1)
                    if len(parts) > 1:
                        return parts[1].strip()
    except (subprocess.CalledProcessError, FileNotFoundError, TimeoutError):
        pass

    return "us"


def get_all_keyboard_layouts() -> list[KeyboardLayout]:
    """Get all available keyboard layouts.

    Returns:
        List of KeyboardLayout objects with code and name.
    """
    layouts = []

    try:
        result = subprocess.run(
            ["localectl", "list-keymaps"], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            for line in result.stdout.split("\n"):
                code = line.strip()
                if code:
                    layouts.append(KeyboardLayout(code=code, name=code))
    except (subprocess.CalledProcessError, FileNotFoundError, TimeoutError):
        pass

    layouts.sort(key=lambda x: x.code)
    return layouts


def get_layout_name(code: str) -> str:
    """Get human-readable name for a keyboard layout code."""
    layout_names = {
        "us": "English (US)",
        "uk": "English (UK)",
        "de": "German",
        "de-latin1": "German (Latin1)",
        "de-latin1-nodeadkeys": "German (Latin1, no dead keys)",
        "at": "Austrian",
        "ch": "Swiss",
        "fr": "French",
        "fr-latin1": "French (Latin1)",
        "es": "Spanish",
        "es-latin1": "Spanish (Latin1)",
        "it": "Italian",
        "it-ibm": "Italian (IBM)",
        "nl": "Dutch",
        "be": "Belgian",
        "pt": "Portuguese",
        "br": "Brazilian",
        "ru": "Russian",
        "ru-cp1251": "Russian (CP1251)",
        "ru-ms": "Russian (Microsoft)",
        "pl": "Polish",
        "pl2": "Polish (Programmer)",
        "pl-latin2": "Polish (Latin2)",
        "cz": "Czech",
        "cz-lat2": "Czech (Latin2)",
        "sk": "Slovak",
        "hu": "Hungarian",
        "hr": "Croatian",
        "sr": "Serbian",
        "bg": "Bulgarian",
        "ro": "Romanian",
        "el": "Greek",
        "tr": "Turkish",
        "trq": "Turkish (Q)",
        "fi": "Finnish",
        "se": "Swedish",
        "no": "Norwegian",
        "dk": "Danish",
        "is": "Icelandic",
        "lt": "Lithuanian",
        "lv": "Latvian",
        "ee": "Estonian",
        "et": "Estonian",
        "hu101": "Hungarian (101-key)",
        "jp": "Japanese",
        "kr": "Korean",
        "cn": "Chinese",
        "tw": "Taiwanese",
        "hk": "Hong Kong",
        "th": "Thai",
        "vn": "Vietnamese",
        "ara": "Arabic",
        "il": "Hebrew",
        "in": "Indian",
        "pk": "Pakistani",
        "bd": "Bangla",
        "np": "Nepali",
        "am": "Armenian",
        "ge": "Georgian",
        "uz": "Uzbek",
        "kz": "Kazakh",
        "kg": "Kyrgyz",
        "mn": "Mongolian",
        "id": "Indonesian",
        "my": "Malay",
        "ph": "Philippine",
        "sg": "Singapore",
        "ma": "Moroccan",
        "dz": "Algerian",
        "eg": "Egyptian",
        "iq": "Iraqi",
        "ir": "Iranian",
        "kw": "Kuwaiti",
        "sa": "Saudi",
        "sy": "Syrian",
        "tn": "Tunisian",
        "ye": "Yemeni",
        "af": "Afghan",
        "pk-urdu": "Pakistani (Urdu)",
        "in-dev": "Indian (Devanagari)",
        "in-guj": "Indian (Gujarati)",
        "in-pun": "Indian (Punjabi)",
        "in-tam": "Indian (Tamil)",
        "in-tel": "Indian (Telugu)",
        "in-kan": "Indian (Kannada)",
        "in-mal": "Indian (Malayalam)",
        "in-ben": "Indian (Bengali)",
        "in-ass": "Indian (Assamese)",
        "in-ori": "Indian (Oriya)",
        "in-gujr": "Indian (Gujarati)",
        "in-panj": "Indian (Punjabi)",
        "in-tamil": "Indian (Tamil)",
        "in-telugu": "Indian (Telugu)",
        "in-kannada": "Indian (Kannada)",
        "in-malayalam": "Indian (Malayalam)",
        "in-bengali": "Indian (Bengali)",
        "in-assamese": "Indian (Assamese)",
        "in-odia": "Indian (Oriya)",
        "latam": "Latin American",
        "mx": "Mexican",
        "co": "Colombian",
        "pe": "Peruvian",
        "ve": "Venezuelan",
        "cl": "Chilean",
        "ar": "Argentine",
        "ec": "Ecuadorian",
        "bo": "Bolivian",
        "uy": "Uruguayan",
        "py": "Paraguayan",
        "cr": "Costa Rican",
        "sv": "Salvadoran",
        "hn": "Honduran",
        "ni": "Nicaraguan",
        "pa": "Panamanian",
        "do": "Dominican",
        "pr": "Puerto Rican",
        "au": "Australian",
        "nz": "New Zealand",
        "za": "South African",
        "gb": "United Kingdom",
        "ca": "Canadian",
        "ca-fr": "Canadian French",
        "ie": "Irish",
        "mt": "Maltese",
        "lu": "Luxembourgish",
        "li": "Liechtenstein",
        "mc": "Monaco",
        "fr-ch": "French (Swiss)",
        "de-ch": "German (Swiss)",
        "it-ch": "Italian (Swiss)",
        "at-nodeadkeys": "Austrian (no dead keys)",
        "be-latin1": "Belgian (Latin1)",
        "dk-latin1": "Danish (Latin1)",
        "fi-latin1": "Finnish (Latin1)",
        "no-latin1": "Norwegian (Latin1)",
        "se-latin1": "Swedish (Latin1)",
        "gb-dvorak": "UK Dvorak",
        "us-dvorak": "US Dvorak",
        "us-dvorak-l": "US Dvorak Left",
        "us-dvorak-r": "US Dvorak Right",
        "us-colemak": "US Colemak",
        "us-workman": "US Workman",
    }
    return layout_names.get(code, code)


def set_keyboard_layout(
    layout_code: str, use_pkexec: bool = True
) -> tuple[Literal["ok", "permission_denied", "pkexec_failed", "error"], str]:
    """Set the keyboard layout for both console and X11.

    Args:
        layout_code: The keyboard layout code (e.g., "us", "de").
        use_pkexec: If True, use pkexec for privilege escalation.

    Returns:
        Tuple of (status, message).
        status can be "ok", "permission_denied", "pkexec_failed", or "error".
    """
    if not use_pkexec:
        result = subprocess.run(
            ["/usr/bin/localectl", "set-keymap", layout_code],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            if result.returncode == 6:
                return ("permission_denied", "Permission denied")
            else:
                return ("error", result.stderr.strip() or "Failed to set console keymap")

        result = subprocess.run(
            ["/usr/bin/localectl", "set-x11-keymap", layout_code],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return ("ok", "Keyboard layout updated successfully")
        elif result.returncode == 6:
            return ("permission_denied", "Permission denied")
        else:
            return ("error", result.stderr.strip() or "Failed to set X11 keyboard layout")

    result = subprocess.run(
        ["pkexec", "/usr/bin/localectl", "set-keymap", layout_code],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        if result.returncode == 126 or result.returncode == 127:
            return ("pkexec_failed", "Authentication failed")
        elif result.returncode == 6:
            return ("permission_denied", "Permission denied")
        else:
            return ("error", result.stderr.strip() or "Failed to set console keymap")

    result = subprocess.run(
        ["pkexec", "/usr/bin/localectl", "set-x11-keymap", layout_code],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        return ("ok", "Keyboard layout updated successfully")
    elif result.returncode == 126 or result.returncode == 127:
        return ("pkexec_failed", "Authentication failed")
    elif result.returncode == 6:
        return ("permission_denied", "Permission denied")
    else:
        return ("error", result.stderr.strip() or "Failed to set X11 keyboard layout")