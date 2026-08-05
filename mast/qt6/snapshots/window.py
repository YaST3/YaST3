"""UI components for the Snapshots module."""

from __future__ import annotations

from collections.abc import Callable

from bytesize import Size
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QHeaderView,
    QHBoxLayout,
    QInputDialog,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from mast.core.i18n import _
from mast.core.snapshots import (
    SnapshotEntry,
    build_snapshot_create_command,
    build_snapshot_delete_command,
    build_snapshot_list_command,
    parse_snapshots_from_json,
)
from mast.qt6.snapshots.config_dialog import SnapperConfigDialog
from mast.qt6.command.action import CommandAction


class SnapshotsWindow(QMainWindow):
    """Qt6 window for managing snapper snapshots."""

    closed = Signal()

    def __init__(self):
        super().__init__()
        self.resize(1280, 720)

        self.snapshots: list[SnapshotEntry] = []
        self.current_action: CommandAction | None = None
        self._list_action: CommandAction | None = None

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(12)

        self.refresh_btn = QPushButton(_("Refresh"))
        self.refresh_btn.clicked.connect(self.load_snapshots)
        actions_layout.addWidget(self.refresh_btn)

        self.create_btn = QPushButton(_("Create"))
        self.create_btn.clicked.connect(self.create_snapshot)
        actions_layout.addWidget(self.create_btn)

        self.delete_btn = QPushButton(_("Delete"))
        self.delete_btn.clicked.connect(self.delete_snapshot)
        actions_layout.addWidget(self.delete_btn)

        self.config_btn = QPushButton(_("Configure"))
        self.config_btn.clicked.connect(self.show_config_dialog)
        actions_layout.addWidget(self.config_btn)

        actions_layout.addStretch()
        layout.addLayout(actions_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            [_("ID"), _("Type"), _("Date"), _("User"), _("Size"), _("Description"), _("Cleanup")]
        )
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.itemSelectionChanged.connect(self.update_action_buttons)

        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self.table)

    def load_snapshots(self) -> None:
        if self._list_action is not None and self._list_action.is_running():
            return

        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText(_("Loading..."))

        self._list_action = CommandAction(
            text=_("Refresh"),
            running_text=_("Loading..."),
            dialog_title=_("Load Snapshots"),
            command=build_snapshot_list_command(),
            success_output=_("Snapshots loaded successfully."),
            auto_close_on_success=True,
            auto_close_delay_ms=200,
            parent=self,
        )
        self._list_action.action_finished.connect(self._on_snapshots_loaded)
        self._list_action.start_action()

    def _on_snapshots_loaded(self, success: bool, error: str, stdout: str) -> None:
        self._list_action = None
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText(_("Refresh"))

        if success:
            try:
                self.snapshots = parse_snapshots_from_json(stdout)
                self.populate_table()
            except Exception as parse_error:
                QMessageBox.critical(
                    self,
                    _("Error"),
                    _("Failed to parse snapshot data: {0}").format(str(parse_error)),
                )
        else:
            QMessageBox.critical(
                self,
                _("Error"),
                _("Failed to load snapshots: {0}").format(error or _("Unknown error")),
            )

    def populate_table(self) -> None:
        self.table.setRowCount(len(self.snapshots))
        for row, snapshot in enumerate(self.snapshots):
            self._set_text_item(row, 0, str(snapshot.number))
            self._set_text_item(row, 1, snapshot.snapshot_type)
            self._set_text_item(row, 2, snapshot.date)
            self._set_text_item(row, 3, snapshot.user)
            self._set_text_item(row, 4, self._format_size(snapshot.used_space))
            self._set_text_item(row, 5, snapshot.description)
            self._set_text_item(row, 6, snapshot.cleanup)

        if self.snapshots:
            self.table.selectRow(0)
        self.update_action_buttons()

    def _set_text_item(self, row: int, column: int, text: str) -> None:
        item = QTableWidgetItem(text)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, column, item)

    @staticmethod
    def _format_size(used_space: int | None) -> str:
        if used_space is None:
            return "-"
        return Size(used_space).human_readable()

    def selected_snapshot(self) -> SnapshotEntry | None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self.snapshots):
            return None
        return self.snapshots[row]

    def update_action_buttons(self) -> None:
        self.delete_btn.setEnabled(self.selected_snapshot() is not None)

    def create_snapshot(self) -> None:
        description, ok = QInputDialog.getText(
            self,
            _("Create Snapshot"),
            _("Description"),
        )
        if not ok:
            return

        clean_description = description.strip()
        if not clean_description:
            QMessageBox.information(self, _("Information"), _("Description cannot be empty."))
            return

        self.current_action = self._create_action(
            text=_("Create"),
            running_text=_("Creating..."),
            dialog_title=_("Create Snapshot"),
            command=build_snapshot_create_command(clean_description),
            success_output=_("Snapshot created successfully."),
            on_finished=self._reload_after_action,
        )
        self.current_action.start_action()

    def delete_snapshot(self) -> None:
        snapshot = self.selected_snapshot()
        if snapshot is None:
            QMessageBox.information(self, _("Information"), _("Please select a snapshot."))
            return

        answer = QMessageBox.question(
            self,
            _("Delete Snapshot"),
            _("Delete snapshot #{0}? This action cannot be undone.").format(snapshot.number),
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self.current_action = self._create_action(
            text=_("Delete"),
            running_text=_("Deleting..."),
            dialog_title=_("Delete Snapshot"),
            command=build_snapshot_delete_command(snapshot.number),
            success_output=_("Snapshot #{0} deleted successfully.").format(snapshot.number),
            on_finished=self._reload_after_action,
        )
        self.current_action.start_action()

    def _reload_after_action(self, success: bool, _error: str, _stdout: str) -> None:
        if success:
            self.load_snapshots()

    def _create_action(
        self,
        text: str,
        running_text: str,
        dialog_title: str,
        command: list[str],
        success_output: str,
        on_finished: Callable[[bool, str, str], None] | None,
    ) -> CommandAction:
        action = CommandAction(
            text=text,
            running_text=running_text,
            dialog_title=dialog_title,
            command=command,
            success_output=success_output,
            parent=self,
        )
        if on_finished is not None:
            action.action_finished.connect(on_finished)
        return action

    def show_config_dialog(self) -> None:
        dialog = SnapperConfigDialog(self)
        dialog.exec()

    def showEvent(self, _event) -> None:
        super().showEvent(_event)
        QTimer.singleShot(1000, self.load_snapshots)

    def closeEvent(self, _event) -> None:
        self.closed.emit()
        self.deleteLater()
