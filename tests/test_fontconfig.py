"""Unit tests for fontconfig core logic."""

import tempfile
import unittest
from pathlib import Path

from mast.core.fontconfig import FontConfig


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
