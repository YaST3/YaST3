"""UI components for the Services module."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from mast.core.i18n import _
from mast.core.services import (
    ServiceEntry,
    build_service_action_command,
    build_service_logs_command,
    list_services,
)
from mast.qt6.command.action import CommandAction


class ServicesWindow(QMainWindow):
    """Qt6 window for managing systemd services."""

    closed = Signal()

    def __init__(self):
        super().__init__()
        self.resize(1280, 720)

        self.services: list[ServiceEntry] = []
        self.filtered_services: list[ServiceEntry] = []
        self.current_action: CommandAction | None = None
        self.log_action: CommandAction | None = None

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        filters_layout = QHBoxLayout()
        filters_layout.setSpacing(12)

        filters_layout.addWidget(QLabel(_("Status")))
        self.status_filter = QComboBox()
        self.status_filter.addItem(_("All"), "all")
        self.status_filter.addItem(_("Active"), "active")
        self.status_filter.addItem(_("Inactive"), "inactive")
        self.status_filter.addItem(_("Failed"), "failed")
        self.status_filter.addItem(_("Activating"), "activating")
        self.status_filter.currentIndexChanged.connect(self.apply_filters)
        filters_layout.addWidget(self.status_filter)

        filters_layout.addWidget(QLabel(_("Scope")))
        self.scope_filter = QComboBox()
        self.scope_filter.addItem(_("All"), "all")
        self.scope_filter.addItem(_("System"), "system")
        self.scope_filter.addItem(_("User"), "user")
        self.scope_filter.currentIndexChanged.connect(self.apply_filters)
        filters_layout.addWidget(self.scope_filter)

        filters_layout.addWidget(QLabel(_("Search")))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(_("Service name or description"))
        self.search_edit.textChanged.connect(self.apply_filters)
        filters_layout.addWidget(self.search_edit, 1)

        self.refresh_btn = QPushButton(_("Refresh"))
        self.refresh_btn.clicked.connect(self.load_services)
        filters_layout.addWidget(self.refresh_btn)

        layout.addLayout(filters_layout)

        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(12)

        self.start_btn = QPushButton(_("Start"))
        self.start_btn.clicked.connect(lambda: self.run_selected_action("start"))
        actions_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton(_("Stop"))
        self.stop_btn.clicked.connect(lambda: self.run_selected_action("stop"))
        actions_layout.addWidget(self.stop_btn)

        self.enable_btn = QPushButton(_("Enable"))
        self.enable_btn.clicked.connect(lambda: self.run_selected_action("enable"))
        actions_layout.addWidget(self.enable_btn)

        self.disable_btn = QPushButton(_("Disable"))
        self.disable_btn.clicked.connect(lambda: self.run_selected_action("disable"))
        actions_layout.addWidget(self.disable_btn)

        self.logs_btn = QPushButton(_("Logs"))
        self.logs_btn.clicked.connect(self.show_selected_logs)
        actions_layout.addWidget(self.logs_btn)

        actions_layout.addStretch()
        layout.addLayout(actions_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            [_("Name"), _("Scope"), _("Status"), _("Enabled"), _("Description")]
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
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        self.load_services()

    def load_services(self) -> None:
        try:
            self.services = list_services()
            self.apply_filters()
        except Exception as error:
            QMessageBox.critical(
                self,
                _("Error"),
                _("Failed to load services: {0}").format(str(error)),
            )

    def apply_filters(self) -> None:
        status_filter = self.status_filter.currentData()
        scope_filter = self.scope_filter.currentData()
        search_text = self.search_edit.text().strip().lower()

        self.filtered_services = []
        for service in self.services:
            if status_filter not in (None, "all") and service.active_state != status_filter:
                continue
            if scope_filter not in (None, "all") and service.scope != scope_filter:
                continue
            if search_text:
                haystack = f"{service.name} {service.description}".lower()
                if search_text not in haystack:
                    continue
            self.filtered_services.append(service)

        self.populate_table()

    def populate_table(self) -> None:
        self.table.setRowCount(len(self.filtered_services))
        for row, service in enumerate(self.filtered_services):
            self._set_text_item(row, 0, service.name)
            self._set_text_item(row, 1, self._display_scope(service.scope))
            self._set_status_item(row, 2, service)
            self._set_text_item(row, 3, service.enabled_text)
            self._set_text_item(row, 4, service.description)

        if self.filtered_services:
            self.table.selectRow(0)
        self.update_action_buttons()

    def _set_text_item(self, row: int, column: int, text: str) -> None:
        item = QTableWidgetItem(text)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, column, item)

    def _set_status_item(self, row: int, column: int, service: ServiceEntry) -> None:
        item = QTableWidgetItem(service.status_text)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        item.setForeground(QColor(self._status_color(service.active_state)))
        self.table.setItem(row, column, item)

    def _display_scope(self, scope: str) -> str:
        return _("System") if scope == "system" else _("User")

    def _status_color(self, status: str) -> str:
        return {
            "active": "#188038",
            "inactive": "#5f6368",
            "failed": "#c5221f",
            "activating": "#b06000",
            "deactivating": "#b06000",
            "reloading": "#1a73e8",
        }.get(status, "#202124")

    def selected_service(self) -> ServiceEntry | None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self.filtered_services):
            return None
        return self.filtered_services[row]

    def update_action_buttons(self) -> None:
        service = self.selected_service()
        has_selection = service is not None

        self.start_btn.setEnabled(has_selection)
        self.stop_btn.setEnabled(has_selection)
        self.enable_btn.setEnabled(has_selection)
        self.disable_btn.setEnabled(has_selection)
        self.logs_btn.setEnabled(has_selection)

        if service is None:
            return

        self.start_btn.setEnabled(service.active_state != "active")
        self.stop_btn.setEnabled(service.active_state == "active")
        self.enable_btn.setEnabled(service.enabled_state not in {"enabled", "static", "alias"})
        self.disable_btn.setEnabled(service.enabled_state == "enabled")

    def run_selected_action(self, action_name: str) -> None:
        service = self.selected_service()
        if service is None:
            QMessageBox.information(self, _("Information"), _("Please select a service."))
            return

        action_text = {
            "start": _("Start"),
            "stop": _("Stop"),
            "enable": _("Enable"),
            "disable": _("Disable"),
        }[action_name]
        action_result = {
            "start": _("Started"),
            "stop": _("Stopped"),
            "enable": _("Enabled"),
            "disable": _("Disabled"),
        }[action_name]

        self.current_action = self._create_action(
            text=action_text,
            running_text=_("Working..."),
            dialog_title=_("{0} Service").format(action_text),
            command=build_service_action_command(service, action_name),
            success_output=_("Service '{0}' {1} successfully.").format(service.name, action_result),
            on_finished=self._reload_after_action,
        )
        self.current_action.start_action()

    def show_selected_logs(self) -> None:
        service = self.selected_service()
        if service is None:
            QMessageBox.information(self, _("Information"), _("Please select a service."))
            return

        self.log_action = self._create_action(
            text=_("Logs"),
            running_text=_("Loading logs..."),
            dialog_title=_("Journal Logs: {0}").format(service.name),
            command=build_service_logs_command(service),
            success_output=_("End of journal output."),
            on_finished=None,
        )
        self.log_action.start_action()

    def _reload_after_action(self, success: bool, _error: str, _stdout: str) -> None:
        if success:
            self.load_services()

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

    def closeEvent(self, _event) -> None:
        self.closed.emit()
        self.deleteLater()