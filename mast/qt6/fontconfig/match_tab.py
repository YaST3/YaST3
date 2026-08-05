"""Font match tab component for Font Config module (Qt6)."""

from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QLineEdit,
)

from mast.core.fontconfig import FontConfig, FontMatch
from mast.core.i18n import _


class FontMatchTab(QWidget):
    DEFAULT_MATCH_FAMILIES = ("sans-serif", "serif", "monospace")

    def __init__(
        self,
        config: FontConfig,
        system_fonts: list[str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.config = config
        self.system_fonts = system_fonts

        self._build_ui()

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)

        left_box = QVBoxLayout()
        left_box.addWidget(QLabel(_("Match List")))

        self.match_list = QListWidget()
        self.match_list.currentRowChanged.connect(self._on_match_row_changed)
        left_box.addWidget(self.match_list)

        match_buttons = QHBoxLayout()
        create_match_btn = QPushButton(_("Create"))
        create_match_btn.clicked.connect(self._on_create_match_clicked)
        match_buttons.addWidget(create_match_btn)

        delete_match_btn = QPushButton(_("Delete"))
        delete_match_btn.clicked.connect(self._on_delete_match_clicked)
        match_buttons.addWidget(delete_match_btn)
        left_box.addLayout(match_buttons)

        right_box = QVBoxLayout()
        right_box.addWidget(QLabel(_("Font List")))

        self.font_list = QListWidget()
        right_box.addWidget(self.font_list)

        font_buttons = QHBoxLayout()
        move_up_btn = QPushButton(_("Move Up"))
        move_up_btn.clicked.connect(self._on_move_font_up_clicked)
        font_buttons.addWidget(move_up_btn)

        move_down_btn = QPushButton(_("Move Down"))
        move_down_btn.clicked.connect(self._on_move_font_down_clicked)
        font_buttons.addWidget(move_down_btn)

        remove_font_btn = QPushButton(_("Remove"))
        remove_font_btn.clicked.connect(self._on_remove_font_clicked)
        font_buttons.addWidget(remove_font_btn)
        right_box.addLayout(font_buttons)

        add_layout = QHBoxLayout()
        self.font_add_combo = QComboBox()
        self.font_add_combo.addItems(self.system_fonts)
        add_layout.addWidget(self.font_add_combo)

        add_font_btn = QPushButton(_("Add"))
        add_font_btn.clicked.connect(self._on_add_font_clicked)
        add_layout.addWidget(add_font_btn)
        right_box.addLayout(add_layout)

        root.addLayout(left_box)
        root.addLayout(right_box)

    def refresh(self, selected_match_index: int | None = 0) -> None:
        self.match_list.clear()
        for match in self.config.match_list:
            self.match_list.addItem(self._format_match_label(match))

        if not self.config.match_list:
            self.font_list.clear()
            return

        if selected_match_index is None:
            selected_match_index = 0
        selected_match_index = max(0, min(selected_match_index, len(self.config.match_list) - 1))
        self.match_list.setCurrentRow(selected_match_index)
        self._refresh_font_list(selected_match_index)

    def _selected_match_index(self) -> int | None:
        index = self.match_list.currentRow()
        if index < 0 or index >= len(self.config.match_list):
            return None
        return index

    def _selected_font_index(self) -> int | None:
        match_index = self._selected_match_index()
        if match_index is None:
            return None
        index = self.font_list.currentRow()
        fonts = self.config.match_list[match_index].family_edit
        if index < 0 or index >= len(fonts):
            return None
        return index

    def _format_match_label(self, match: FontMatch) -> str:
        if match.lang_test:
            return f"{match.family_test} [{match.lang_test}]"
        return match.family_test

    def _refresh_font_list(self, match_index: int | None, selected_index: int | None = None) -> None:
        self.font_list.clear()

        if match_index is None or not (0 <= match_index < len(self.config.match_list)):
            return

        fonts = self.config.match_list[match_index].family_edit
        self.font_list.addItems(fonts)

        if not fonts:
            return

        if selected_index is None:
            selected_index = 0
        selected_index = max(0, min(selected_index, len(fonts) - 1))
        self.font_list.setCurrentRow(selected_index)

    def _show_create_match_dialog(self) -> tuple[str, str | None] | None:
        dialog = QDialog(self)
        dialog.setWindowTitle(_("Create"))

        layout = QVBoxLayout(dialog)

        family_row = QHBoxLayout()
        family_row.addWidget(QLabel(_("Font family")))
        family_combo = QComboBox()
        family_combo.addItems(list(self.DEFAULT_MATCH_FAMILIES))
        family_row.addWidget(family_combo)
        layout.addLayout(family_row)

        lang_row = QHBoxLayout()
        lang_row.addWidget(QLabel(_("Language")))
        language_edit = QLineEdit()
        language_edit.setPlaceholderText(_("Language"))
        lang_row.addWidget(language_edit)
        layout.addLayout(lang_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() != QDialog.Accepted:
            return None

        family = family_combo.currentText() or "sans-serif"
        language_raw = language_edit.text().strip()
        language = language_raw if language_raw else None
        return family, language

    def _on_match_row_changed(self, row: int) -> None:
        if row < 0:
            self._refresh_font_list(None)
            return
        self._refresh_font_list(row)

    def _on_create_match_clicked(self) -> None:
        result = self._show_create_match_dialog()
        if result is None:
            return
        family, language = result
        self.config.match_list.append(
            FontMatch(family_test=family, lang_test=language, family_edit=[])
        )
        self.refresh(len(self.config.match_list) - 1)

    def _on_delete_match_clicked(self) -> None:
        match_index = self._selected_match_index()
        if match_index is None:
            return
        self.config.match_list.pop(match_index)
        self.refresh(match_index)

    def _on_add_font_clicked(self) -> None:
        match_index = self._selected_match_index()
        if match_index is None:
            return
        font = self.font_add_combo.currentText()
        if not font:
            return
        self.config.match_list[match_index].family_edit.append(font)
        self._refresh_font_list(
            match_index,
            len(self.config.match_list[match_index].family_edit) - 1,
        )

    def _on_remove_font_clicked(self) -> None:
        match_index = self._selected_match_index()
        font_index = self._selected_font_index()
        if match_index is None or font_index is None:
            return

        fonts = self.config.match_list[match_index].family_edit
        fonts.pop(font_index)
        self._refresh_font_list(match_index, font_index)

    def _on_move_font_up_clicked(self) -> None:
        match_index = self._selected_match_index()
        font_index = self._selected_font_index()
        if match_index is None or font_index is None or font_index <= 0:
            return

        fonts = self.config.match_list[match_index].family_edit
        fonts[font_index - 1], fonts[font_index] = fonts[font_index], fonts[font_index - 1]
        self._refresh_font_list(match_index, font_index - 1)

    def _on_move_font_down_clicked(self) -> None:
        match_index = self._selected_match_index()
        font_index = self._selected_font_index()
        if match_index is None or font_index is None:
            return

        fonts = self.config.match_list[match_index].family_edit
        if font_index >= len(fonts) - 1:
            return
        fonts[font_index + 1], fonts[font_index] = fonts[font_index], fonts[font_index + 1]
        self._refresh_font_list(match_index, font_index + 1)
