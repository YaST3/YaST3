"""UI components for the Services module (TUI)."""

from __future__ import annotations

import subprocess

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Header, Input, Select, Static

from mast.core.i18n import _
from mast.core.services import (
    ServiceEntry,
    build_service_action_command,
    build_service_logs_command,
    list_services,
)


class ServicesWindow(Screen):
    """TUI window for managing systemd services."""

    CSS = """
    Screen {
        height: 100%;
    }

    .filter-row {
        height: 3;
        padding-left: 1;
        padding-right: 1;
        margin-bottom: 1;
    }

    .action-row {
        height: 3;
        padding-left: 1;
        padding-right: 1;
        margin-bottom: 1;
    }

    .message {
        height: 3;
        padding-left: 1;
        color: yellow;
    }

    .error {
        color: red;
    }

    .success {
        color: green;
    }
    """

    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("q", "app.pop_screen", "Back"),
        ("r", "reload", "Refresh"),
        ("s", "start_service", "Start"),
        ("t", "stop_service", "Stop"),
        ("e", "enable_service", "Enable"),
        ("d", "disable_service", "Disable"),
        ("l", "view_logs", "Logs"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.services: list[ServiceEntry] = []
        self.filtered_services: list[ServiceEntry] = []

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(classes="filter-row"):
            yield Static(_("Status"))
            yield Select(
                [
                    (_("All"), "all"),
                    (_("Active"), "active"),
                    (_("Inactive"), "inactive"),
                    (_("Failed"), "failed"),
                    (_("Activating"), "activating"),
                ],
                id="status-filter",
                allow_blank=False,
            )
            yield Static(_("Scope"))
            yield Select(
                [
                    (_("All"), "all"),
                    (_("System"), "system"),
                    (_("User"), "user"),
                ],
                id="scope-filter",
                allow_blank=False,
            )
            yield Static(_("Search"))
            yield Input(placeholder=_("Service name or description"), id="search-input")
            yield Button(_("Refresh"), id="refresh-btn")

        with Horizontal(classes="action-row"):
            yield Button(_("Start"), id="start-btn")
            yield Button(_("Stop"), id="stop-btn")
            yield Button(_("Enable"), id="enable-btn")
            yield Button(_("Disable"), id="disable-btn")
            yield Button(_("Logs"), id="logs-btn")

        yield DataTable(id="services-table")
        yield Static("", id="message", classes="message")

    def on_mount(self) -> None:
        status_filter = self.query_one("#status-filter", Select)
        scope_filter = self.query_one("#scope-filter", Select)
        status_filter.value = "all"
        scope_filter.value = "all"

        table = self.query_one("#services-table", DataTable)
        table.cursor_type = "row"
        table.add_columns(
            _("Name"),
            _("Scope"),
            _("Status"),
            _("Enabled"),
            _("Description"),
        )

        self.load_services()

    def show_message(self, message: str, error: bool = False, success: bool = False) -> None:
        msg_widget = self.query_one("#message", Static)
        msg_widget.update(message)
        msg_widget.remove_class("error", "success")
        if error:
            msg_widget.add_class("error")
        elif success:
            msg_widget.add_class("success")

    def _status_style(self, status: str) -> str:
        return {
            "active": "green",
            "inactive": "bright_black",
            "failed": "red",
            "activating": "yellow",
            "deactivating": "yellow",
            "reloading": "cyan",
        }.get(status, "white")

    def load_services(self) -> None:
        try:
            self.services = list_services()
            self.apply_filters()
        except Exception as error:
            self.show_message(
                _("Error: Failed to load services: {0}").format(str(error)),
                error=True,
            )

    def apply_filters(self) -> None:
        status_filter = self._select_value("status-filter")
        scope_filter = self._select_value("scope-filter")
        search_text = self.query_one("#search-input", Input).value.strip().lower()

        self.filtered_services = []
        for service in self.services:
            if status_filter != "all" and service.active_state != status_filter:
                continue
            if scope_filter != "all" and service.scope != scope_filter:
                continue
            if search_text:
                haystack = f"{service.name} {service.description}".lower()
                if search_text not in haystack:
                    continue
            self.filtered_services.append(service)

        self.populate_table()

    def populate_table(self) -> None:
        table = self.query_one("#services-table", DataTable)
        table.clear()

        for service in self.filtered_services:
            status = Text(service.status_text, style=self._status_style(service.active_state))
            table.add_row(
                service.name,
                _("System") if service.scope == "system" else _("User"),
                status,
                service.enabled_text,
                service.description,
            )

        self.update_action_buttons()

    def selected_service(self) -> ServiceEntry | None:
        table = self.query_one("#services-table", DataTable)
        row = table.cursor_row
        if row < 0 or row >= len(self.filtered_services):
            return None
        return self.filtered_services[row]

    def update_action_buttons(self) -> None:
        service = self.selected_service()
        has_selection = service is not None

        self.query_one("#start-btn", Button).disabled = not has_selection
        self.query_one("#stop-btn", Button).disabled = not has_selection
        self.query_one("#enable-btn", Button).disabled = not has_selection
        self.query_one("#disable-btn", Button).disabled = not has_selection
        self.query_one("#logs-btn", Button).disabled = not has_selection

        if service is None:
            return

        self.query_one("#start-btn", Button).disabled = service.active_state == "active"
        self.query_one("#stop-btn", Button).disabled = service.active_state != "active"
        self.query_one("#enable-btn", Button).disabled = service.enabled_state in {
            "enabled",
            "static",
            "alias",
        }
        self.query_one("#disable-btn", Button).disabled = service.enabled_state != "enabled"

    def _select_value(self, select_id: str) -> str:
        select = self.query_one(f"#{select_id}", Select)
        value = select.value
        if value == Select.BLANK:
            return "all"
        return str(value)

    def on_select_changed(self, _event: Select.Changed) -> None:
        self.apply_filters()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search-input":
            self.apply_filters()

    def on_data_table_row_highlighted(self, _event: DataTable.RowHighlighted) -> None:
        self.update_action_buttons()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "refresh-btn":
            self.action_reload()
        elif button_id == "start-btn":
            self.action_start_service()
        elif button_id == "stop-btn":
            self.action_stop_service()
        elif button_id == "enable-btn":
            self.action_enable_service()
        elif button_id == "disable-btn":
            self.action_disable_service()
        elif button_id == "logs-btn":
            self.action_view_logs()

    def action_reload(self) -> None:
        self.load_services()

    def _run_service_action(self, action_name: str, success_text: str) -> None:
        service = self.selected_service()
        if service is None:
            self.show_message(_("Please select a service."), error=True)
            return

        command = build_service_action_command(service, action_name)
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=False)
        except Exception as error:
            self.show_message(
                _("Error: Failed to execute command: {0}").format(str(error)),
                error=True,
            )
            return

        if result.returncode == 0:
            self.show_message(
                _("Service '{0}' {1}.").format(service.name, success_text),
                success=True,
            )
            self.load_services()
            return

        error_text = (result.stdout or result.stderr or _("Unknown error")).strip()
        self.show_message(error_text, error=True)

    def action_start_service(self) -> None:
        self._run_service_action("start", _("Started"))

    def action_stop_service(self) -> None:
        self._run_service_action("stop", _("Stopped"))

    def action_enable_service(self) -> None:
        self._run_service_action("enable", _("Enabled"))

    def action_disable_service(self) -> None:
        self._run_service_action("disable", _("Disabled"))

    def action_view_logs(self) -> None:
        service = self.selected_service()
        if service is None:
            self.show_message(_("Please select a service."), error=True)
            return

        command = build_service_logs_command(service)
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=False)
        except Exception as error:
            self.show_message(
                _("Error: Failed to load logs: {0}").format(str(error)),
                error=True,
            )
            return

        output = (result.stdout or result.stderr or _("No logs available.")).strip()
        self.app.push_screen(ServiceLogsScreen(service.name, output))


class ServiceLogsScreen(Screen):
    """Read-only log screen for service journal output."""

    CSS = """
    .container {
        width: 100%;
        height: 100%;
        padding: 1;
    }

    .title {
        text-style: bold;
        margin-bottom: 1;
    }

    .log-view {
        height: 1fr;
        border: solid gray;
        padding: 1;
    }

    .button-row {
        align: right middle;
        margin-top: 1;
    }
    """

    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("q", "app.pop_screen", "Back"),
    ]

    def __init__(self, service_name: str, logs: str) -> None:
        super().__init__()
        self.service_name = service_name
        self.logs = logs

    def compose(self) -> ComposeResult:
        with Vertical(classes="container"):
            yield Label(_("Journal Logs: {0}").format(self.service_name), classes="title")
            with ScrollableContainer(classes="log-view"):
                yield Static(self.logs)
            with Horizontal(classes="button-row"):
                yield Button(_("Close"), id="close-btn", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-btn":
            self.app.pop_screen()
