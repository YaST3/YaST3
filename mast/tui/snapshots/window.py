"""UI components for the Snapshots module (TUI)."""

from __future__ import annotations

import subprocess

from bytesize import Size
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import Button, DataTable, Header, Input, Static

from mast.core.i18n import _
from mast.core.snapshots import (
    SnapshotEntry,
    build_snapshot_create_command,
    build_snapshot_delete_command,
    build_snapshot_list_command,
    parse_snapshots_from_json,
)
from mast.tui.snapshots.config_screen import SnapperConfigScreen


class SnapshotsWindow(Screen):
    """TUI window for managing snapper snapshots."""

    CSS = """
    Screen {
        height: 100%;
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
        ("c", "create_snapshot", "Create"),
        ("d", "delete_snapshot", "Delete"),
        ("g", "configure", "Configure"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.snapshots: list[SnapshotEntry] = []
        self._loading = False

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(classes="action-row"):
            yield Input(placeholder=_("Description"), id="description-input")
            yield Button(_("Create"), id="create-btn")
            yield Button(_("Delete"), id="delete-btn")
            yield Button(_("Refresh"), id="refresh-btn")
            yield Button(_("Configure"), id="config-btn")

        yield DataTable(id="snapshots-table")
        yield Static("", id="message", classes="message")

    def on_mount(self) -> None:
        table = self.query_one("#snapshots-table", DataTable)
        table.cursor_type = "row"
        table.add_columns(
            _("ID"),
            _("Type"),
            _("Date"),
            _("User"),
            _("Size"),
            _("Description"),
            _("Cleanup"),
        )

        self.load_snapshots()

    def show_message(self, message: str, error: bool = False, success: bool = False) -> None:
        msg_widget = self.query_one("#message", Static)
        msg_widget.update(message)
        msg_widget.remove_class("error", "success")
        if error:
            msg_widget.add_class("error")
        elif success:
            msg_widget.add_class("success")

    def load_snapshots(self) -> None:
        if self._loading:
            return

        self._loading = True
        refresh_btn = self.query_one("#refresh-btn", Button)
        refresh_btn.disabled = True
        refresh_btn.label = _("Loading...")

        command = build_snapshot_list_command()

        def _worker():
            try:
                result = subprocess.run(command, capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    snapshots = parse_snapshots_from_json(result.stdout)
                    self.app.call_later(self._update_snapshots_ui, True, snapshots)
                else:
                    error_text = (result.stdout or result.stderr or _("Unknown error")).strip()
                    self.app.call_later(self._update_snapshots_ui, False, error_text)
            except subprocess.TimeoutExpired:
                self.app.call_later(self._update_snapshots_ui, False, _("Timeout waiting for snapshots"))
            except Exception as error:
                self.app.call_later(self._update_snapshots_ui, False, str(error))

        import threading

        threading.Thread(target=_worker, daemon=True).start()

    def _update_snapshots_ui(self, success: bool, result) -> None:
        self._loading = False
        refresh_btn = self.query_one("#refresh-btn", Button)
        refresh_btn.disabled = False
        refresh_btn.label = _("Refresh")

        if success:
            self.snapshots = result
            self.populate_table()
        else:
            self.show_message(
                _("Error: Failed to load snapshots: {0}").format(str(result)),
                error=True,
            )

    def populate_table(self) -> None:
        table = self.query_one("#snapshots-table", DataTable)
        table.clear()

        for snapshot in self.snapshots:
            table.add_row(
                str(snapshot.number),
                snapshot.snapshot_type,
                snapshot.date,
                snapshot.user,
                self._format_size(snapshot.used_space),
                snapshot.description,
                snapshot.cleanup,
            )

        self.update_action_buttons()

    @staticmethod
    def _format_size(used_space: int | None) -> str:
        if used_space is None:
            return "-"
        return Size(used_space).human_readable()

    def selected_snapshot(self) -> SnapshotEntry | None:
        table = self.query_one("#snapshots-table", DataTable)
        row = table.cursor_row
        if row < 0 or row >= len(self.snapshots):
            return None
        return self.snapshots[row]

    def update_action_buttons(self) -> None:
        self.query_one("#delete-btn", Button).disabled = self.selected_snapshot() is None

    def on_data_table_row_highlighted(self, _event: DataTable.RowHighlighted) -> None:
        self.update_action_buttons()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "create-btn":
            self.action_create_snapshot()
        elif button_id == "delete-btn":
            self.action_delete_snapshot()
        elif button_id == "refresh-btn":
            self.action_reload()
        elif button_id == "config-btn":
            self.action_configure()

    def action_reload(self) -> None:
        self.load_snapshots()

    def action_create_snapshot(self) -> None:
        description_input = self.query_one("#description-input", Input)
        description = description_input.value.strip()
        if not description:
            self.show_message(_("Description cannot be empty."), error=True)
            return

        command = build_snapshot_create_command(description)
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=False)
        except Exception as error:
            self.show_message(
                _("Error: Failed to execute command: {0}").format(str(error)),
                error=True,
            )
            return

        if result.returncode == 0:
            description_input.value = ""
            self.show_message(_("Snapshot created successfully."), success=True)
            self.load_snapshots()
            return

        error_text = (result.stdout or result.stderr or _("Unknown error")).strip()
        self.show_message(error_text, error=True)

    def action_delete_snapshot(self) -> None:
        snapshot = self.selected_snapshot()
        if snapshot is None:
            self.show_message(_("Please select a snapshot."), error=True)
            return

        command = build_snapshot_delete_command(snapshot.number)
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
                _("Snapshot #{0} deleted successfully.").format(snapshot.number),
                success=True,
            )
            self.load_snapshots()
            return

        error_text = (result.stdout or result.stderr or _("Unknown error")).strip()
        self.show_message(error_text, error=True)

    def action_configure(self) -> None:
        def on_config_result(result: bool) -> None:
            if result:
                self.show_message(_("Configuration saved successfully."), success=True)

        self.app.push_screen(SnapperConfigScreen(on_config_result))