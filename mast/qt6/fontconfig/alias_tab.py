"""Font alias tab component for Font Config module (Qt6)."""

from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from mast.core.fontconfig import FontAlias, FontConfig
from mast.core.i18n import _


class FontAliasTab(QWidget):
    def __init__(
        self,
        config: FontConfig,
        system_fonts: list[str],
        show_error_message: Callable[[str], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.config = config
        self.system_fonts = system_fonts
        self.show_error_message = show_error_message

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel(_("Original Font")))
        header_layout.addWidget(QLabel(_("Preferred Font")))
        layout.addLayout(header_layout)

        self.alias_list = QListWidget()
        layout.addWidget(self.alias_list)

        control_layout = QHBoxLayout()
        self.alias_family_edit = QLineEdit()
        self.alias_family_edit.setPlaceholderText(_("Font family"))
        control_layout.addWidget(self.alias_family_edit)

        self.alias_prefer_combo = QComboBox()
        self.alias_prefer_combo.addItems(self.system_fonts)
        control_layout.addWidget(self.alias_prefer_combo)

        add_button = QPushButton(_("Add"))
        add_button.clicked.connect(self._on_add_alias_clicked)
        control_layout.addWidget(add_button)

        remove_button = QPushButton(_("Remove"))
        remove_button.clicked.connect(self._on_remove_alias_clicked)
        control_layout.addWidget(remove_button)
        layout.addLayout(control_layout)

    def refresh(self, selected_index: int | None = 0) -> None:
        self.alias_list.clear()
        for alias in self.config.alias_list:
            self.alias_list.addItem(f"{alias.family}\t{alias.prefer}")

        if not self.config.alias_list:
            return

        if selected_index is None:
            selected_index = len(self.config.alias_list) - 1
        selected_index = max(0, min(selected_index, len(self.config.alias_list) - 1))
        self.alias_list.setCurrentRow(selected_index)

    def _selected_alias_index(self) -> int | None:
        index = self.alias_list.currentRow()
        if index < 0 or index >= len(self.config.alias_list):
            return None
        return index

    def _on_add_alias_clicked(self) -> None:
        family = self.alias_family_edit.text().strip()
        prefer = self.alias_prefer_combo.currentText()

        if not family:
            self.show_error_message(_("Font family is required."))
            return
        if not prefer:
            return

        self.config.alias_list.append(FontAlias(family=family, prefer=prefer))
        self.alias_family_edit.clear()
        self.refresh(len(self.config.alias_list) - 1)

    def _on_remove_alias_clicked(self) -> None:
        alias_index = self._selected_alias_index()
        if alias_index is None:
            return
        self.config.alias_list.pop(alias_index)
        self.refresh(alias_index)
