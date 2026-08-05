"""Font option tab component for Font Config module (Qt6)."""

from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QComboBox, QFormLayout, QWidget

from mast.core.fontconfig import FontConfig
from mast.core.i18n import _


class FontOptionTab(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        form = QFormLayout(self)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(12)

        self.antialias_check = QCheckBox()
        form.addRow(_("Antialias"), self.antialias_check)

        self.hinting_check = QCheckBox()
        form.addRow(_("Hinting"), self.hinting_check)

        self.hintstyle_combo = QComboBox()
        self.hintstyle_combo.addItems(FontConfig.HINTSTYLE_OPTIONS)
        form.addRow(_("Hint Style"), self.hintstyle_combo)

        self.rgba_combo = QComboBox()
        self.rgba_combo.addItems(FontConfig.RGBA_OPTIONS)
        form.addRow(_("Subpixel Render"), self.rgba_combo)

        self.lcdfilter_combo = QComboBox()
        self.lcdfilter_combo.addItems(FontConfig.LCDFILTER_OPTIONS)
        form.addRow(_("LCD Filter"), self.lcdfilter_combo)

        self.embeddedbitmap_check = QCheckBox()
        form.addRow(_("Embedded Bitmap"), self.embeddedbitmap_check)

    def load_from_config(self, config: FontConfig) -> None:
        self.antialias_check.setChecked(config.antialias)
        self.hinting_check.setChecked(config.hinting)
        self._set_combo_value(self.hintstyle_combo, config.hintstyle)
        self._set_combo_value(self.rgba_combo, config.rgba)
        self._set_combo_value(self.lcdfilter_combo, config.lcdfilter)
        self.embeddedbitmap_check.setChecked(config.embeddedbitmap)

    def apply_to_config(self, config: FontConfig) -> None:
        config.antialias = self.antialias_check.isChecked()
        config.hinting = self.hinting_check.isChecked()
        config.hintstyle = self.hintstyle_combo.currentText()
        config.rgba = self.rgba_combo.currentText()
        config.lcdfilter = self.lcdfilter_combo.currentText()
        config.embeddedbitmap = self.embeddedbitmap_check.isChecked()

    def _set_combo_value(self, combo: QComboBox, value: str) -> None:
        index = combo.findText(value)
        combo.setCurrentIndex(index if index >= 0 else 0)
