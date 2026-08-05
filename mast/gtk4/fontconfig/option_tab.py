"""Font option tab component for Font Config module (GTK4)."""

from __future__ import annotations

import gi



gi.require_version("Gtk", "4.0")

from gi.repository import Gtk

from mast.core.fontconfig import FontConfig
from mast.core.i18n import _


class FontOptionTab(Gtk.Box):
    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_top(8)
        self.set_margin_bottom(8)
        self.set_margin_start(8)
        self.set_margin_end(8)

        self._build_ui()

    def _build_ui(self) -> None:
        grid = Gtk.Grid()
        grid.set_row_spacing(12)
        grid.set_column_spacing(16)

        row = 0

        self.antialias_switch = Gtk.Switch()
        self.antialias_switch.set_halign(Gtk.Align.START)
        grid.attach(Gtk.Label(label=_("Antialias"), halign=Gtk.Align.START), 0, row, 1, 1)
        grid.attach(self.antialias_switch, 1, row, 1, 1)
        row += 1

        self.hinting_switch = Gtk.Switch()
        self.hinting_switch.set_halign(Gtk.Align.START)
        grid.attach(Gtk.Label(label=_("Hinting"), halign=Gtk.Align.START), 0, row, 1, 1)
        grid.attach(self.hinting_switch, 1, row, 1, 1)
        row += 1

        self.hintstyle_combo = Gtk.ComboBoxText()
        for option in FontConfig.HINTSTYLE_OPTIONS:
            self.hintstyle_combo.append_text(option)
        grid.attach(Gtk.Label(label=_("Hint Style"), halign=Gtk.Align.START), 0, row, 1, 1)
        grid.attach(self.hintstyle_combo, 1, row, 1, 1)
        row += 1

        self.rgba_combo = Gtk.ComboBoxText()
        for option in FontConfig.RGBA_OPTIONS:
            self.rgba_combo.append_text(option)
        grid.attach(Gtk.Label(label=_("Subpixel Render"), halign=Gtk.Align.START), 0, row, 1, 1)
        grid.attach(self.rgba_combo, 1, row, 1, 1)
        row += 1

        self.lcdfilter_combo = Gtk.ComboBoxText()
        for option in FontConfig.LCDFILTER_OPTIONS:
            self.lcdfilter_combo.append_text(option)
        grid.attach(Gtk.Label(label=_("LCD Filter"), halign=Gtk.Align.START), 0, row, 1, 1)
        grid.attach(self.lcdfilter_combo, 1, row, 1, 1)
        row += 1

        self.embeddedbitmap_switch = Gtk.Switch()
        self.embeddedbitmap_switch.set_halign(Gtk.Align.START)
        grid.attach(Gtk.Label(label=_("Embedded Bitmap"), halign=Gtk.Align.START), 0, row, 1, 1)
        grid.attach(self.embeddedbitmap_switch, 1, row, 1, 1)

        self.append(grid)

    def load_from_config(self, config: FontConfig) -> None:
        self.antialias_switch.set_active(config.antialias)
        self.hinting_switch.set_active(config.hinting)
        self._set_combo_value(self.hintstyle_combo, config.hintstyle)
        self._set_combo_value(self.rgba_combo, config.rgba)
        self._set_combo_value(self.lcdfilter_combo, config.lcdfilter)
        self.embeddedbitmap_switch.set_active(config.embeddedbitmap)

    def apply_to_config(self, config: FontConfig) -> None:
        config.antialias = self.antialias_switch.get_active()
        config.hinting = self.hinting_switch.get_active()
        config.hintstyle = self._get_combo_value(self.hintstyle_combo, "hintfull")
        config.rgba = self._get_combo_value(self.rgba_combo, "none")
        config.lcdfilter = self._get_combo_value(self.lcdfilter_combo, "lcddefault")
        config.embeddedbitmap = self.embeddedbitmap_switch.get_active()

    def _set_combo_value(self, combo: Gtk.ComboBoxText, value: str) -> None:
        model = combo.get_model()
        if model is None:
            return

        active_index = 0
        tree_iter = model.get_iter_first()
        index = 0
        while tree_iter is not None:
            if model.get_value(tree_iter, 0) == value:
                active_index = index
                break
            tree_iter = model.iter_next(tree_iter)
            index += 1

        combo.set_active(active_index)

    def _get_combo_value(self, combo: Gtk.ComboBoxText, fallback: str) -> str:
        text = combo.get_active_text()
        return text if text else fallback
