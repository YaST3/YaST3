"""UI components for the Font Config module (Qt6)."""

from __future__ import annotations

import subprocess

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from mast.core.fontconfig import FontConfig
from mast.core.i18n import _
from mast.qt6.fontconfig.alias_tab import FontAliasTab
from mast.qt6.fontconfig.match_tab import FontMatchTab
from mast.qt6.fontconfig.option_tab import FontOptionTab


class FontConfigWindow(QMainWindow):
    closed = Signal()

    def __init__(self):
        super().__init__()
        self.resize(760, 480)

        self.config = FontConfig()
        self.system_fonts = self._load_system_fonts()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        self.tab_widget = QTabWidget()

        self.match_tab = FontMatchTab(self.config, self.system_fonts, self)
        self.tab_widget.addTab(self.match_tab, _("Font Match"))

        self.alias_tab = FontAliasTab(self.config, self.system_fonts, self._show_error_message, self)
        self.tab_widget.addTab(self.alias_tab, _("Font Alias"))

        self.option_tab = FontOptionTab(self)
        self.tab_widget.addTab(self.option_tab, _("Font Option"))

        layout.addWidget(self.tab_widget)

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

    def _load_system_fonts(self) -> list[str]:
        default_fonts = ["Sans", "Serif", "Monospace"]

        try:
            proc = subprocess.run(
                ["fc-list", ":", "family"],
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError:
            return default_fonts

        if proc.returncode != 0 or not proc.stdout:
            return default_fonts

        seen: set[str] = set()
        fonts: list[str] = []
        for line in proc.stdout.splitlines():
            for item in line.split(","):
                name = item.strip()
                if not name:
                    continue
                if name in seen:
                    continue
                seen.add(name)
                fonts.append(name)

        return sorted(fonts, key=str.casefold) if fonts else default_fonts

    def _show_error_message(self, message: str) -> None:
        QMessageBox.critical(self, _("Error"), message)

    def load_config(self) -> None:
        try:
            self.config.reload()
            self.match_tab.refresh(0)
            self.alias_tab.refresh(0)
            self.option_tab.load_from_config(self.config)
        except Exception as e:
            QMessageBox.critical(
                self,
                _("Error"),
                _("Failed to load font config: {0}").format(str(e)),
            )

    def save_config(self) -> None:
        self.option_tab.apply_to_config(self.config)

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
