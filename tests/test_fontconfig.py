"""Unit tests for fontconfig core logic."""

import tempfile
import unittest
from pathlib import Path

from mast.core.fontconfig import FontAlias, FontConfig, FontMatch


class TestFontConfig(unittest.TestCase):
    def test_defaults_when_file_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "missing-fonts.conf"
            cfg = FontConfig(str(config_path))

            self.assertTrue(cfg.antialias)
            self.assertTrue(cfg.hinting)
            self.assertEqual(cfg.hintstyle, "hintfull")
            self.assertEqual(cfg.rgba, "none")
            self.assertEqual(cfg.lcdfilter, "lcddefault")
            self.assertTrue(cfg.embeddedbitmap)
            self.assertEqual(len(cfg.match_list), 3)
            self.assertEqual([m.family_test for m in cfg.match_list], ["sans-serif", "serif", "monospace"])
            self.assertEqual(cfg.alias_list, [])

    def test_reload_reads_options(self) -> None:
        content = """<?xml version=\"1.0\"?>
<fontconfig>
  <match target=\"font\">
    <edit name=\"antialias\" mode=\"assign\"><bool>false</bool></edit>
  </match>
  <match target=\"font\">
    <edit name=\"hinting\" mode=\"assign\"><bool>true</bool></edit>
  </match>
  <match target=\"font\">
    <edit name=\"hintstyle\" mode=\"assign\"><const>hintslight</const></edit>
  </match>
  <match target=\"font\">
    <edit name=\"rgba\" mode=\"assign\"><const>rgb</const></edit>
  </match>
  <match target=\"font\">
    <edit name=\"lcdfilter\" mode=\"assign\"><const>lcdlight</const></edit>
  </match>
  <match target=\"font\">
    <edit name=\"embeddedbitmap\" mode=\"assign\"><bool>false</bool></edit>
  </match>
</fontconfig>
"""
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "fonts.conf"
            config_path.write_text(content, encoding="utf-8")

            cfg = FontConfig(str(config_path))

            self.assertFalse(cfg.antialias)
            self.assertTrue(cfg.hinting)
            self.assertEqual(cfg.hintstyle, "hintslight")
            self.assertEqual(cfg.rgba, "rgb")
            self.assertEqual(cfg.lcdfilter, "lcdlight")
            self.assertFalse(cfg.embeddedbitmap)

    def test_reload_reads_matches_and_aliases(self) -> None:
        content = """<?xml version=\"1.0\"?>
<fontconfig>
  <match>
    <test name=\"family\"><string>sans-serif</string></test>
    <edit name=\"family\" binding=\"strong\" mode=\"prepend\">
      <string>Noto Sans</string>
      <string>DejaVu Sans</string>
    </edit>
  </match>
  <match>
    <test name=\"family\"><string>serif</string></test>
    <test name=\"lang\"><string>ja</string></test>
    <edit name=\"family\" binding=\"strong\" mode=\"prepend\">
      <string>Noto Serif CJK JP</string>
    </edit>
  </match>
  <alias>
    <family>Arial</family>
    <prefer><family>Liberation Sans</family></prefer>
  </alias>
</fontconfig>
"""
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "fonts.conf"
            config_path.write_text(content, encoding="utf-8")

            cfg = FontConfig(str(config_path))

            self.assertEqual(cfg.match_list[0].family_test, "sans-serif")
            self.assertEqual(cfg.match_list[0].family_edit, ["Noto Sans", "DejaVu Sans"])
            self.assertEqual(cfg.match_list[1].family_test, "serif")
            self.assertEqual(cfg.match_list[1].lang_test, "ja")
            self.assertEqual(cfg.match_list[1].family_edit, ["Noto Serif CJK JP"])
            self.assertEqual(len(cfg.alias_list), 1)
            self.assertEqual(cfg.alias_list[0].family, "Arial")
            self.assertEqual(cfg.alias_list[0].prefer, "Liberation Sans")

    def test_write_replaces_matches_aliases_and_options(self) -> None:
        content = """<?xml version=\"1.0\"?>
<fontconfig>
  <match>
    <test name=\"family\"><string>sans-serif</string></test>
    <edit name=\"family\" binding=\"strong\" mode=\"prepend\"><string>Old Sans</string></edit>
  </match>
  <alias>
    <family>Arial</family>
    <prefer><family>Old Prefer</family></prefer>
  </alias>
</fontconfig>
"""
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "fonts.conf"
            config_path.write_text(content, encoding="utf-8")

            cfg = FontConfig(str(config_path))
            cfg.match_list = [
                FontMatch(family_test="sans-serif", family_edit=["Noto Sans", "DejaVu Sans"]),
                FontMatch(family_test="serif", lang_test="ja", family_edit=["Noto Serif CJK JP"]),
                FontMatch(family_test="monospace", family_edit=["JetBrains Mono"]),
            ]
            cfg.alias_list = [
                FontAlias(family="Arial", prefer="Liberation Sans"),
                FontAlias(family="Helvetica", prefer="Noto Sans"),
            ]
            cfg.antialias = True
            cfg.hinting = False
            cfg.hintstyle = "hintmedium"
            cfg.rgba = "bgr"
            cfg.lcdfilter = "lcdlegacy"
            cfg.embeddedbitmap = False

            cfg.write()

            written = config_path.read_text(encoding="utf-8")
            self.assertIn('<test name="family">', written)
            self.assertIn("<string>Noto Sans</string>", written)
            self.assertIn("<string>DejaVu Sans</string>", written)
            self.assertIn('<test name="lang">', written)
            self.assertIn("<string>ja</string>", written)
            self.assertIn("<alias>", written)
            self.assertIn("<family>Arial</family>", written)
            self.assertIn("<family>Liberation Sans</family>", written)
            self.assertIn("<family>Helvetica</family>", written)
            self.assertIn('<edit name="hintstyle" mode="assign">', written)
            self.assertIn("<const>hintmedium</const>", written)

    def test_write_replaces_existing_option_nodes(self) -> None:
        content = """<?xml version=\"1.0\"?>
<fontconfig>
  <match target=\"font\">
    <edit name=\"antialias\" mode=\"assign\"><bool>false</bool></edit>
  </match>
  <match target=\"pattern\">
    <edit name=\"family\" mode=\"assign\"><string>Serif</string></edit>
  </match>
</fontconfig>
"""
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "fonts.conf"
            config_path.write_text(content, encoding="utf-8")

            cfg = FontConfig(str(config_path))
            cfg.antialias = True
            cfg.hinting = False
            cfg.hintstyle = "hintmedium"
            cfg.rgba = "bgr"
            cfg.lcdfilter = "lcdlegacy"
            cfg.embeddedbitmap = False
            cfg.write()

            written = config_path.read_text(encoding="utf-8")
            self.assertIn('<edit name="antialias" mode="assign">', written)
            self.assertIn("<bool>true</bool>", written)
            self.assertIn('<edit name="hintstyle" mode="assign">', written)
            self.assertIn("<const>hintmedium</const>", written)
            self.assertIn('<edit name="rgba" mode="assign">', written)
            self.assertIn("<const>bgr</const>", written)
            self.assertIn('<edit name="lcdfilter" mode="assign">', written)
            self.assertIn("<const>lcdlegacy</const>", written)
            self.assertIn('<edit name="embeddedbitmap" mode="assign">', written)
            self.assertIn("<bool>false</bool>", written)
            self.assertIn('<match target="pattern">', written)


if __name__ == "__main__":
    unittest.main()
