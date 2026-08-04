"""UI components for the Font Config module (Qt6)."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from mast.core.fontconfig import FontConfig
from mast.core.i18n import _


class FontConfigWindow(QMainWindow):
    closed = Signal()

    def __init__(self):
        super().__init__()
        self.resize(560, 360)

        self.config = FontConfig()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        form = QFormLayout()
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

        layout.addLayout(form)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        reload_btn = QPushButton(_("Reload"))
        reload_btn.clicked.connect(self.load_config)
        button_layout.addWidget(reload_btn)

        save_btn = QPushButton(_("Save"))
        save_btn.clicked.connect(self.save_config)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

        self.load_config()

    def _set_combo_value(self, combo: QComboBox, value: str) -> None:
        index = combo.findText(value)
        combo.setCurrentIndex(index if index >= 0 else 0)

    def load_config(self) -> None:
        try:
            self.config.reload()
            self.antialias_check.setChecked(self.config.antialias)
            self.hinting_check.setChecked(self.config.hinting)
            self._set_combo_value(self.hintstyle_combo, self.config.hintstyle)
            self._set_combo_value(self.rgba_combo, self.config.rgba)
            self._set_combo_value(self.lcdfilter_combo, self.config.lcdfilter)
            self.embeddedbitmap_check.setChecked(self.config.embeddedbitmap)
        except Exception as e:
            QMessageBox.critical(
                self,
                _("Error"),
                _("Failed to load font config: {0}").format(str(e)),
            )

    def save_config(self) -> None:
        self.config.antialias = self.antialias_check.isChecked()
        self.config.hinting = self.hinting_check.isChecked()
        self.config.hintstyle = self.hintstyle_combo.currentText()
        self.config.rgba = self.rgba_combo.currentText()
        self.config.lcdfilter = self.lcdfilter_combo.currentText()
        self.config.embeddedbitmap = self.embeddedbitmap_check.isChecked()

        try:
            self.config.write()
            QMessageBox.information(
                self,
                _("Success"),
                _("Font configuration saved successfully."),
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                _("Error"),
                _("Failed to save font config: {0}").format(str(e)),
            )

    def closeEvent(self, _event) -> None:
        self.closed.emit()
        self.deleteLater()
