"""Qt6 Flatpak runtime management widget."""

from __future__ import annotations

from typing import Literal

from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from mast.core.flatpak import FlatpakRuntime, list_flatpak_runtimes
from mast.core.i18n import _
from mast.qt6.command.action import CommandAction


class FlatpakRuntimeManager(QWidget):
    """Manage installed Flatpak runtimes."""
    DEFAULT_SCOPE: Literal["system", "user"] = "system"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.runtimes: list[FlatpakRuntime] = []
        self.filtered_runtimes: list[FlatpakRuntime] = []

        self.uninstall_action = CommandAction(
            text=_("Uninstall"),
            running_text=_("Removing runtime..."),
            dialog_title=_("Remove Flatpak Runtime"),
            command=["true"],
            success_output=_("Runtime removed successfully."),
            auto_close_on_success=True,
            parent=self,
        )
        self.uninstall_action.triggered.disconnect(self.uninstall_action.start_action)
        self.uninstall_action.triggered.connect(self._on_uninstall_triggered)
        self.uninstall_action.action_finished.connect(self._on_uninstall_finished)

        layout = QVBoxLayout(self)

        btn_layout = QHBoxLayout()

        self.uninstall_btn = QPushButton(self.uninstall_action.text(), self)
        self.uninstall_btn.clicked.connect(self.uninstall_action.trigger)
        self.uninstall_action.changed.connect(self._sync_action_buttons)
        btn_layout.addWidget(self.uninstall_btn)

        btn_layout.addStretch()

        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("org.example.Platform")
        self.search_input.returnPressed.connect(self.search_runtimes)
        btn_layout.addWidget(self.search_input)

        self.search_btn = QPushButton(_("Search"), self)
        self.search_btn.clicked.connect(self.search_runtimes)
        btn_layout.addWidget(self.search_btn)

        self.reset_btn = QPushButton(_("Reset"), self)
        self.reset_btn.clicked.connect(self.reset_search)
        btn_layout.addWidget(self.reset_btn)

        self.refresh_btn = QPushButton(_("Refresh"), self)
        self.refresh_btn.clicked.connect(self.load_runtimes)
        btn_layout.addWidget(self.refresh_btn)

        layout.addLayout(btn_layout)

        self.table = QTableWidget(self)
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(
            [
                _("ID"),
                _("Name"),
                _("Description"),
                _("Version"),
                _("Branch"),
                _("Installed Size"),
                _("Remote"),
                _("Scope"),
            ]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(7, 90)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        layout.addWidget(self.table)

        self._sync_action_buttons()
        self.load_runtimes()

    def _sync_action_buttons(self) -> None:
        self.uninstall_btn.setText(self.uninstall_action.text())
        self.uninstall_btn.setEnabled(self.uninstall_action.isEnabled())

    def _selected_runtime_id(self) -> str:
        row = self.table.currentRow()
        if row < 0 or row >= len(self.filtered_runtimes):
            return ""
        return self.filtered_runtimes[row].runtime_id

    def _selected_runtime_scope(self) -> Literal["system", "user"]:
        row = self.table.currentRow()
        if row < 0 or row >= len(self.filtered_runtimes):
            return self.DEFAULT_SCOPE
        return self.filtered_runtimes[row].scope

    def _build_uninstall_command(self, runtime_id: str, scope: Literal["system", "user"]) -> list[str]:
        base = ["flatpak", "uninstall", "-y", f"--{scope}", runtime_id]
        if scope == "system":
            return ["pkexec", *base]
        return base

    def _on_uninstall_triggered(self) -> None:
        runtime_id = self._selected_runtime_id()
        scope = self._selected_runtime_scope()
        if not runtime_id:
            QMessageBox.information(self, _("Information"), _("Please select an installed runtime from the list."))
            return

        reply = QMessageBox.question(
            self,
            _("Confirm"),
            _("Are you sure you want to remove runtime '{0}'?").format(runtime_id),
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.uninstall_action.command = self._build_uninstall_command(runtime_id, scope)
        self.uninstall_action.start_action()

    def _on_uninstall_finished(self, success: bool, error: str) -> None:
        if success:
            self.load_runtimes()
            return

        if error:
            QMessageBox.critical(self, _("Error"), _("Failed to remove runtime: {0}").format(error))

    def load_runtimes(self) -> None:
        try:
            self.runtimes = list_flatpak_runtimes()
        except Exception as e:
            QMessageBox.critical(self, _("Error"), _("Failed to load Flatpak runtimes: {0}").format(str(e)))
            self.runtimes = []

        self.filtered_runtimes = self._filter_runtimes(self.runtimes, self.search_input.text().strip())
        self._populate_table()

    def search_runtimes(self) -> None:
        query = self.search_input.text().strip()
        self.filtered_runtimes = self._filter_runtimes(self.runtimes, query)
        self._populate_table()

    def reset_search(self) -> None:
        self.search_input.clear()
        self.filtered_runtimes = list(self.runtimes)
        self._populate_table()

    def _populate_table(self) -> None:
        self.table.setRowCount(len(self.filtered_runtimes))
        for row, runtime in enumerate(self.filtered_runtimes):
            self.table.setItem(row, 0, QTableWidgetItem(runtime.runtime_id))
            self.table.setItem(row, 1, QTableWidgetItem(runtime.name))
            self.table.setItem(row, 2, QTableWidgetItem(runtime.description))
            self.table.setItem(row, 3, QTableWidgetItem(runtime.version))
            self.table.setItem(row, 4, QTableWidgetItem(runtime.branch))
            self.table.setItem(row, 5, QTableWidgetItem(runtime.installed_size))
            self.table.setItem(row, 6, QTableWidgetItem(runtime.remote))
            self.table.setItem(row, 7, QTableWidgetItem(runtime.scope))

    def _filter_runtimes(self, runtimes: list[FlatpakRuntime], query: str) -> list[FlatpakRuntime]:
        normalized_query = query.strip().lower()
        if not normalized_query:
            return list(runtimes)

        return [
            runtime
            for runtime in runtimes
            if normalized_query in runtime.runtime_id.lower()
            or normalized_query in runtime.name.lower()
            or normalized_query in runtime.description.lower()
            or normalized_query in runtime.version.lower()
            or normalized_query in runtime.branch.lower()
            or normalized_query in runtime.remote.lower()
            or normalized_query in runtime.installed_size.lower()
        ]
