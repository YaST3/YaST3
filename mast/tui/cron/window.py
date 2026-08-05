"""UI components for the Cron module (TUI)."""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Header, Input, Label, Static, TabbedContent, TabPane

from crontab import CronItem, CronTab

from mast.core.i18n import _
from mast.core.cron import load_root_cron, save_root_cron


class CronWindow(Screen):
    """TUI window for cron configuration."""

    CSS = """
    Screen {
        align: center middle;
    }

    .container {
        width: 100%;
        height: auto;
        max-height: 80%;
        padding: 1;
    }

    DataTable {
        height: 1fr;
    }

    .button-row {
        align: left middle;
        margin-bottom: 1;
    }

    .message {
        margin-top: 1;
        color: yellow;
    }

    .error {
        color: red;
    }

    .success {
        color: green;
    }

    TabbedContent {
        height: 1fr;
    }
    """

    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("q", "app.pop_screen", "Back"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.user_cron: CronTab | None = None
        self.root_cron: CronTab | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="container"):
            with TabbedContent(id="tabs"):
                with TabPane(_("User"), id="user-tab"):
                    yield from self._compose_manager("user")
                with TabPane(_("System"), id="root-tab"):
                    yield from self._compose_manager("root")
            yield Static("", id="message", classes="message")

    def _compose_manager(self, mode: str) -> ComposeResult:
        with Vertical():
            with Horizontal(classes="button-row"):
                yield Button(_("Add"), id=f"add-{mode}-btn")
                yield Button(_("Edit"), id=f"edit-{mode}-btn", disabled=True)
                yield Button(_("Delete"), id=f"delete-{mode}-btn", disabled=True)
                yield Button(_("Save"), id=f"save-{mode}-btn", variant="primary")
            yield DataTable(id=f"{mode}-table")

    def on_mount(self) -> None:
        """Setup tables on mount."""
        self._setup_table("user")
        self._setup_table("root")
        self._load_cron("user")

    def _load_cron(self, mode: str) -> None:
        """Load cron jobs for specified mode."""
        if mode == "user" and self.user_cron is None:
            self.user_cron = CronTab(user=True)
            self._populate_table("user")
        elif mode == "root" and self.root_cron is None:
            self.root_cron = load_root_cron()
            self._populate_table("root")

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Handle row highlighted in data table."""
        table_id = event.data_table.id
        if table_id is not None and "-table" in table_id:
            mode = table_id.replace("-table", "")
            table = event.data_table
            jobs = self._get_jobs(mode)
            selected = table.cursor_row >= 0 and table.cursor_row < len(jobs)

            edit_btn = self.query_one(f"#edit-{mode}-btn", Button)
            delete_btn = self.query_one(f"#delete-{mode}-btn", Button)
            edit_btn.disabled = not selected
            delete_btn.disabled = not selected

    def _setup_table(self, mode: str) -> None:
        """Setup table columns."""
        table = self.query_one(f"#{mode}-table", DataTable)
        table.add_columns(_("Enabled"), _("Minute"), _("Hour"), _("Day"), _("Month"), _("Weekday"), _("Command"), _("Comment"))

    def populate_tables(self) -> None:
        """Populate both tables."""
        self._populate_table("user")
        self._populate_table("root")

    def _populate_table(self, mode: str) -> None:
        """Populate a single table."""
        table = self.query_one(f"#{mode}-table", DataTable)
        table.clear()

        jobs = self._get_jobs(mode)
        for job in jobs:
            enabled = "✓" if job.is_enabled() else ""
            table.add_row(enabled, str(job.minute), str(job.hour), str(job.day), str(job.month), str(job.dow), job.command, job.comment)

    def show_message(self, message: str, error: bool = False, success: bool = False) -> None:
        """Display a message to the user."""
        msg_widget = self.query_one("#message", Static)
        msg_widget.update(message)
        msg_widget.remove_class("error", "success")
        if error:
            msg_widget.add_class("error")
        elif success:
            msg_widget.add_class("success")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        button_id = event.button.id
        if button_id and "-btn" in button_id:
            parts = button_id.replace("-btn", "").split("-")
            action = parts[0]
            mode = parts[1]

            if action == "add":
                self._add_job(mode)
            elif action == "edit":
                self._edit_job(mode)
            elif action == "delete":
                self._delete_job(mode)
            elif action == "save":
                self._save_jobs(mode)

    def _get_cron(self, mode: str) -> CronTab | None:
        """Get CronTab for mode."""
        return self.user_cron if mode == "user" else self.root_cron

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        """Load cron jobs when switching tabs."""
        tab_id = event.tab.id
        if tab_id == "user-tab":
            self._load_cron("user")
        elif tab_id == "root-tab":
            self._load_cron("root")

    def _get_jobs(self, mode: str) -> list[CronItem]:
        """Get jobs list for mode."""
        cron = self._get_cron(mode)
        return list(cron.crons) if cron and cron.crons else []

    def _add_job(self, mode: str) -> None:
        """Add a new cron job."""
        self.app.push_screen(CronEditScreen(self, _("Add Cron Job"), mode))

    def _edit_job(self, mode: str) -> None:
        """Edit the selected cron job."""
        table = self.query_one(f"#{mode}-table", DataTable)
        jobs = self._get_jobs(mode)
        if table.cursor_row < 0 or table.cursor_row >= len(jobs):
            self.show_message(_("Please select a cron job to edit."), error=True)
            return

        job = jobs[table.cursor_row]
        self.app.push_screen(
            CronEditScreen(
                self,
                _("Edit Cron Job"),
                mode,
                job,
                table.cursor_row,
            )
        )

    def _delete_job(self, mode: str) -> None:
        """Delete the selected cron job."""
        table = self.query_one(f"#{mode}-table", DataTable)
        jobs = self._get_jobs(mode)
        if table.cursor_row < 0 or table.cursor_row >= len(jobs):
            self.show_message(_("Please select a cron job to delete."), error=True)
            return

        cron = self._get_cron(mode)
        if cron:
            cron.remove(jobs[table.cursor_row])
            self._populate_table(mode)
            self.show_message(_("Cron job deleted."), success=True)

    def _save_jobs(self, mode: str) -> None:
        """Save cron jobs."""
        try:
            cron = self._get_cron(mode)
            if cron is None:
                raise Exception("Cron not loaded")
            if mode == "user":
                cron.write()
            else:
                if not save_root_cron(cron):
                    raise Exception("Failed to save")
            self.show_message(_("Success: Cron jobs saved successfully."), success=True)
        except Exception:
            self.show_message(_("Error: Permission denied. Root permission required."), error=True)

    def add_job(self, mode: str, job_data: tuple) -> None:
        """Add a new job."""
        minute, hour, day, month, weekday, command, comment = job_data
        cron = self._get_cron(mode)
        if cron:
            new_job = cron.new(command=command, comment=comment)
            new_job.setall(minute, hour, day, month, weekday)
            new_job.enable(True)
            self._populate_table(mode)
            self.show_message(_("Cron job added."), success=True)

    def update_job(self, mode: str, row: int, job_data: tuple) -> None:
        """Update an existing job."""
        minute, hour, day, month, weekday, command, comment = job_data
        cron = self._get_cron(mode)
        jobs = self._get_jobs(mode)
        job = jobs[row]
        job.setall(minute, hour, day, month, weekday)
        job.command = command
        job.comment = comment
        self._populate_table(mode)
        self.show_message(_("Cron job updated."), success=True)


class CronEditScreen(Screen):
    """Screen for adding/editing a cron job."""

    CSS = """
    .container {
        width: 70;
        height: auto;
        padding: 2;
        border: solid green;
    }

    .input-label {
        width: 10;
        content-align: right middle;
        padding-right: 1;
    }

    .button-row {
        align: right middle;
        margin-top: 1;
    }
    """

    BINDINGS = [
        ("escape", "app.pop_screen", "Cancel"),
    ]

    def __init__(
        self,
        parent: CronWindow,
        title: str,
        mode: str,
        job: CronItem | None = None,
        row: int = -1,
    ) -> None:
        super().__init__()
        self.parent_window = parent
        self.screen_title = title
        self.mode = mode
        self.edit_row = row
        self.initial_job = job

    def compose(self) -> ComposeResult:
        with Vertical(classes="container"):
            yield Label(self.screen_title, classes="title")
            with Horizontal():
                yield Label(_("Minute"), classes="input-label")
                default_minute = str(self.initial_job.minute) if self.initial_job else "*"
                yield Input(value=default_minute, id="minute-input", placeholder="0-59 or *")
            with Horizontal():
                yield Label(_("Hour"), classes="input-label")
                default_hour = str(self.initial_job.hour) if self.initial_job else "*"
                yield Input(value=default_hour, id="hour-input", placeholder="0-23 or *")
            with Horizontal():
                yield Label(_("Day"), classes="input-label")
                default_day = str(self.initial_job.day) if self.initial_job else "*"
                yield Input(value=default_day, id="day-input", placeholder="1-31 or *")
            with Horizontal():
                yield Label(_("Month"), classes="input-label")
                default_month = str(self.initial_job.month) if self.initial_job else "*"
                yield Input(value=default_month, id="month-input", placeholder="1-12 or *")
            with Horizontal():
                yield Label(_("Weekday"), classes="input-label")
                default_weekday = str(self.initial_job.dow) if self.initial_job else "*"
                yield Input(value=default_weekday, id="weekday-input", placeholder="0-7 or *")
            with Horizontal():
                yield Label(_("Command"), classes="input-label")
                default_command = self.initial_job.command if self.initial_job else ""
                yield Input(value=default_command, id="command-input", placeholder=_("Command to execute"))
            with Horizontal():
                yield Label(_("Comment"), classes="input-label")
                default_comment = self.initial_job.comment if self.initial_job else ""
                yield Input(value=default_comment, id="comment-input", placeholder=_("Optional comment"))
            with Horizontal(classes="button-row"):
                yield Button(_("OK"), id="ok-btn", variant="primary")
                yield Button(_("Cancel"), id="cancel-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "ok-btn":
            self.action_submit()
        elif event.button.id == "cancel-btn":
            self.app.pop_screen()

    def action_submit(self) -> None:
        """Submit the form."""
        minute = self.query_one("#minute-input", Input).value.strip() or "*"
        hour = self.query_one("#hour-input", Input).value.strip() or "*"
        day = self.query_one("#day-input", Input).value.strip() or "*"
        month = self.query_one("#month-input", Input).value.strip() or "*"
        weekday = self.query_one("#weekday-input", Input).value.strip() or "*"
        command = self.query_one("#command-input", Input).value.strip()
        comment = self.query_one("#comment-input", Input).value.strip()

        if not command:
            self.parent_window.show_message(_("Error: Command is required."), error=True)
            self.app.pop_screen()
            return

        job_data = (minute, hour, day, month, weekday, command, comment)

        if self.edit_row >= 0:
            self.parent_window.update_job(self.mode, self.edit_row, job_data)
        else:
            self.parent_window.add_job(self.mode, job_data)
        self.app.pop_screen()
