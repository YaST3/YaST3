"""UI components for the Repositories module (TUI)."""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Checkbox, DataTable, Header, Input, Label, Select, Static

from mast.core.i18n import _
from mast.core.repositories import (
    RepoEntry,
    switch_mirror,
)
from mast.core.repositories.opensuse_mirrors import opensuse_mirrors
from mast.core.repositories.packman_mirrors import packman_mirrors
from mast.core.repositories.switch_mirror import switch_mirror_pkexec


class RepositoriesWindow(Screen):
    """TUI window for repositories configuration."""

    CSS = """
    Screen {
        height: 100%;
    }

    .button-bar {
        height: 3;
        margin-bottom: 1;
        padding-left: 1;
    }

    .button-row {
        align: left middle;
    }

    .message-area {
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
        ("a", "add", "Add"),
        ("e", "edit", "Edit"),
        ("d", "delete", "Delete"),
        ("m", "switch_mirror", "Switch Mirror"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.repo_entries: list[RepoEntry] = []

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(classes="button-bar"):
            yield Button(_("Add"), id="add-btn")
            yield Button(_("Edit"), id="edit-btn")
            yield Button(_("Delete"), id="delete-btn")
            yield Button(_("Switch Mirror"), id="switch-mirror-btn")
        yield DataTable(id="repos-table")
        yield Static("", id="message", classes="message-area")

    def on_mount(self) -> None:
        """Load repositories on mount."""
        table = self.query_one("#repos-table", DataTable)
        table.add_columns(_("Name"), _("URL"), _("Priority"), _("Enabled"), _("Auto Refresh"))
        self.load_repos()

    def load_repos(self) -> None:
        """Load repositories."""
        self.repo_entries.clear()
        table = self.query_one("#repos-table", DataTable)
        table.clear()

        try:
            self.repo_entries = RepoEntry.load_repos()
        except PermissionError:
            self.show_message(
                _("Error: Cannot read repository directory. Root permission required."),
                error=True,
            )
            return

        self.populate_table()

    def populate_table(self) -> None:
        """Populate the table with repo entries."""
        table = self.query_one("#repos-table", DataTable)
        table.clear()

        for entry in self.repo_entries:
            enabled = "✓" if entry.enabled else ""
            autorefresh = "✓" if entry.autorefresh else ""
            table.add_row(entry.name, entry.url, str(entry.priority), enabled, autorefresh)

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
        if event.button.id == "add-btn":
            self.action_add()
        elif event.button.id == "edit-btn":
            self.action_edit()
        elif event.button.id == "delete-btn":
            self.action_delete()
        elif event.button.id == "switch-mirror-btn":
            self.action_switch_mirror()

    def action_add(self) -> None:
        """Add a new repository."""
        self.app.push_screen(RepoEditScreen(self, _("Add Repository")))

    def action_edit(self) -> None:
        """Edit the selected repository."""
        table = self.query_one("#repos-table", DataTable)
        if table.cursor_row < 0 or table.cursor_row >= len(self.repo_entries):
            self.show_message(_("Please select a repository to edit."), error=True)
            return

        entry = self.repo_entries[table.cursor_row]
        self.app.push_screen(
            RepoEditScreen(
                self,
                _("Edit Repository"),
                entry,
                table.cursor_row,
            )
        )

    def action_delete(self) -> None:
        """Delete the selected repository."""
        table = self.query_one("#repos-table", DataTable)
        if table.cursor_row < 0 or table.cursor_row >= len(self.repo_entries):
            self.show_message(_("Please select a repository to delete."), error=True)
            return

        entry = self.repo_entries[table.cursor_row]
        result = entry.delete()
        if result == "ok":
            self.repo_entries.pop(table.cursor_row)
            self.populate_table()
            self.show_message(_("Repository deleted."), success=True)
        else:
            self.show_message(result, error=True)

    def action_switch_mirror(self) -> None:
        """Switch mirrors for openSUSE and Packman repositories."""
        self.app.push_screen(SwitchMirrorScreen(self))

    def switch_mirror(self, opensuse_url: str, packman_url: str) -> None:
        """Execute mirror switch operation."""
        status = switch_mirror_pkexec(opensuse_url, packman_url)
        if status == "ok":
            self.show_message(_("Mirror switching completed successfully."), success=True)
            self.load_repos()
        elif status == "permission_denied":
            self.show_message(_("Permission denied."), error=True)
        elif status == "pkexec_failed":
            self.show_message(_("Failed to obtain root privileges."), error=True)
        else:
            self.show_message(_("Failed to switch mirrors."), error=True)

    def add_repo(self, values: dict) -> None:
        """Add a new repository."""
        repo_id = values.get("id", "")
        url = values.get("baseurl") or values.get("mirrorlist")

        if not repo_id:
            self.show_message(_("Error: Repository ID is required."), error=True)
            return
        if not url:
            self.show_message(_("Error: URL is required."), error=True)
            return

        new_entry = RepoEntry(
            id=repo_id,
            name=values.get("name", repo_id),
            enabled=values.get("enabled", True),
            autorefresh=values.get("autorefresh", True),
            baseurl=values.get("baseurl", ""),
            mirrorlist=values.get("mirrorlist", ""),
            path=values.get("path", ""),
            type=values.get("type", ""),
            gpgcheck=values.get("gpgcheck", False),
            repo_gpgcheck=values.get("repo_gpgcheck", False),
            gpgkey=values.get("gpgkey", ""),
            priority=values.get("priority", 99),
            keep_packages=values.get("keep_packages", False),
        )

        result = new_entry.save()
        if result == "ok":
            self.repo_entries.append(new_entry)
            self.populate_table()
            self.show_message(_("Repository added."), success=True)
        else:
            self.show_message(result, error=True)

    def update_repo(self, row: int, values: dict) -> None:
        """Update an existing repository."""
        entry = self.repo_entries[row]
        repo_id = values.get("id", "")
        url = values.get("baseurl") or values.get("mirrorlist")

        if not repo_id:
            self.show_message(_("Error: Repository ID is required."), error=True)
            return
        if not url:
            self.show_message(_("Error: URL is required."), error=True)
            return

        updated_entry = RepoEntry(
            id=repo_id,
            name=values.get("name", repo_id),
            enabled=values.get("enabled", True),
            autorefresh=values.get("autorefresh", True),
            baseurl=values.get("baseurl", ""),
            mirrorlist=values.get("mirrorlist", ""),
            path=values.get("path", ""),
            type=values.get("type", ""),
            gpgcheck=values.get("gpgcheck", False),
            repo_gpgcheck=values.get("repo_gpgcheck", False),
            gpgkey=values.get("gpgkey", ""),
            priority=values.get("priority", 99),
            keep_packages=values.get("keep_packages", False),
        )

        result = updated_entry.save()
        if result == "ok":
            self.repo_entries[row] = updated_entry
            self.populate_table()
            self.show_message(_("Repository updated."), success=True)
        else:
            self.handle_save_error(result)

    def handle_save_error(self, result: str) -> None:
        """Handle save errors."""
        if result == "permission_denied":
            self.show_message(
                _("Error: Cannot write to repository directory. Root permission required."),
                error=True,
            )
        elif result == "pkexec_failed":
            self.show_message(
                _("Error: Authentication failed or pkexec not available."),
                error=True,
            )
        else:
            self.show_message(_("Error: Failed to save repository configuration."), error=True)


class RepoEditScreen(Screen):
    """Screen for adding/editing a repository."""

    CSS = """
    .container {
        width: 70;
        height: auto;
        max-height: 80%;
        padding: 2;
        border: solid green;
    }

    .input-row {
        height: 3;
        margin-bottom: 1;
    }

    .input-label {
        width: 14;
        content-align: right middle;
        padding-right: 1;
    }

    Checkbox {
        margin-bottom: 1;
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
        parent: RepositoriesWindow,
        title: str,
        entry: RepoEntry | None = None,
        row: int = -1,
    ) -> None:
        super().__init__()
        self.parent_window = parent
        self.screen_title = title
        self.edit_row = row
        self.initial_entry = entry

    def compose(self) -> ComposeResult:
        with Vertical(classes="container"):
            yield Label(self.screen_title, classes="title")
            with Horizontal():
                yield Label(_("Repository ID"), classes="input-label")
                yield Input(value=self._get_value("id"), id="id-input", placeholder=_("Unique repository ID"))
            with Horizontal():
                yield Label(_("Name"), classes="input-label")
                yield Input(value=self._get_value("name"), id="name-input", placeholder=_("Display name"))
            with Horizontal():
                yield Label(_("Base URL"), classes="input-label")
                yield Input(value=self._get_value("baseurl"), id="baseurl-input", placeholder=_("Base URL"))
            with Horizontal():
                yield Label(_("Mirror List"), classes="input-label")
                yield Input(value=self._get_value("mirrorlist"), id="mirrorlist-input", placeholder=_("Mirror list URL"))
            with Horizontal():
                yield Label(_("Priority"), classes="input-label")
                yield Input(value=self._get_value("priority"), id="priority-input", placeholder=_("Priority (default 99)"))
            with Horizontal():
                yield Label(_("Type"), classes="input-label")
                yield Select(
                    [("yast2", "yast2"), ("rpm-md", "rpm-md"), ("plaindir", "plaindir")],
                    id="type-select",
                    allow_blank=True,
                )
            with Horizontal():
                yield Label(_("GPG Key"), classes="input-label")
                yield Input(value=self._get_value("gpgkey"), id="gpgkey-input", placeholder=_("GPG key URL"))
            yield Checkbox(_("Enabled"), id="enabled-check", value=self._get_bool("enabled", True))
            yield Checkbox(_("Auto Refresh"), id="autorefresh-check", value=self._get_bool("autorefresh", True))
            yield Checkbox(_("Package GPG Check"), id="gpgcheck-check", value=self._get_bool("gpgcheck", False))
            yield Checkbox(_("Repository GPG Check"), id="repo-gpgcheck-check", value=self._get_bool("repo_gpgcheck", False))
            yield Checkbox(_("Keep Packages"), id="keep-packages-check", value=self._get_bool("keep_packages", False))
            with Horizontal(classes="button-row"):
                yield Button(_("OK"), id="ok-btn", variant="primary")
                yield Button(_("Cancel"), id="cancel-btn")

    def _get_value(self, key: str) -> str:
        """Get initial value from entry."""
        if self.initial_entry:
            val = getattr(self.initial_entry, key, "")
            if isinstance(val, int):
                return str(val)
            return val or ""
        return ""

    def _get_bool(self, key: str, default: bool) -> bool:
        """Get initial boolean value from entry."""
        if self.initial_entry:
            return getattr(self.initial_entry, key, default)
        return default

    def on_mount(self) -> None:
        """Set initial select value."""
        if self.initial_entry:
            try:
                type_select = self.query_one("#type-select", Select)
                if self.initial_entry.type:
                    type_select.value = self.initial_entry.type
            except Exception:
                pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "ok-btn":
            self.action_submit()
        elif event.button.id == "cancel-btn":
            self.app.pop_screen()

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Keep repository signature checking aligned with package checking."""
        if event.checkbox.id == "gpgcheck-check":
            self.query_one("#repo-gpgcheck-check", Checkbox).value = event.value

    def action_submit(self) -> None:
        """Submit the form."""
        values = {
            "id": self.query_one("#id-input", Input).value.strip(),
            "name": self.query_one("#name-input", Input).value.strip(),
            "baseurl": self.query_one("#baseurl-input", Input).value.strip(),
            "mirrorlist": self.query_one("#mirrorlist-input", Input).value.strip(),
            "priority": int(self.query_one("#priority-input", Input).value.strip() or "99"),
            "type": self._get_select_value("type-select"),
            "gpgkey": self.query_one("#gpgkey-input", Input).value.strip(),
            "enabled": self.query_one("#enabled-check", Checkbox).value,
            "autorefresh": self.query_one("#autorefresh-check", Checkbox).value,
            "gpgcheck": self.query_one("#gpgcheck-check", Checkbox).value,
            "repo_gpgcheck": self.query_one("#repo-gpgcheck-check", Checkbox).value,
            "keep_packages": self.query_one("#keep-packages-check", Checkbox).value,
        }

        if self.edit_row >= 0:
            self.parent_window.update_repo(self.edit_row, values)
        else:
            self.parent_window.add_repo(values)
        self.app.pop_screen()

    def _get_select_value(self, select_id: str) -> str:
        """Get select widget value."""
        try:
            select = self.query_one(f"#{select_id}", Select)
            value = select.value
            return str(value) if value != Select.BLANK else ""
        except Exception:
            return ""


class SwitchMirrorScreen(Screen):
    """Screen for switching mirrors."""

    CSS = """
    .container {
        width: 70;
        height: auto;
        max-height: 80%;
        padding: 2;
        border: solid green;
    }

    .input-row {
        height: 3;
        margin-bottom: 1;
    }

    .input-label {
        width: 16;
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

    def __init__(self, parent: RepositoriesWindow) -> None:
        super().__init__()
        self.parent_window = parent
        self.opensuse_mirrors_list = list(opensuse_mirrors)
        self.packman_mirrors_list = list(packman_mirrors)
        self.opensuse_protocols = []
        self.packman_protocols = []

    def compose(self) -> ComposeResult:
        opensuse_options = [(f"{m.organization} ({m.location})", i) for i, m in enumerate(self.opensuse_mirrors_list)]
        packman_options = [(f"{m.organization} ({m.location})", i) for i, m in enumerate(self.packman_mirrors_list)]

        self.opensuse_protocols = self.opensuse_mirrors_list[0].protocols
        self.packman_protocols = self.packman_mirrors_list[0].protocols

        opensuse_proto_options = [(p.upper(), p) for p in self.opensuse_protocols]
        packman_proto_options = [(p.upper(), p) for p in self.packman_protocols]

        with Vertical(classes="container"):
            yield Label(_("Switch Mirror"), classes="title")
            with Horizontal():
                yield Label(_("openSUSE"), classes="input-label")
                yield Select(opensuse_options, id="opensuse-select", allow_blank=False)
                yield Select(opensuse_proto_options, id="opensuse-proto-select", allow_blank=False)
            with Horizontal():
                yield Label(_("Packman"), classes="input-label")
                yield Select(packman_options, id="packman-select", allow_blank=False)
                yield Select(packman_proto_options, id="packman-proto-select", allow_blank=False)
            with Horizontal(classes="button-row"):
                yield Button(_("OK"), id="ok-btn", variant="primary")
                yield Button(_("Cancel"), id="cancel-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "ok-btn":
            self.action_submit()
        elif event.button.id == "cancel-btn":
            self.app.pop_screen()

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle select changes to update protocol options."""
        if event.select.id == "opensuse-select":
            mirror = self.opensuse_mirrors_list[event.select.value]
            self.opensuse_protocols = mirror.protocols
            proto_select = self.query_one("#opensuse-proto-select", Select)
            proto_select.set_options([(p.upper(), p) for p in self.opensuse_protocols])
        elif event.select.id == "packman-select":
            mirror = self.packman_mirrors_list[event.select.value]
            self.packman_protocols = mirror.protocols
            proto_select = self.query_one("#packman-proto-select", Select)
            proto_select.set_options([(p.upper(), p) for p in self.packman_protocols])

    def action_submit(self) -> None:
        """Submit the form."""
        opensuse_idx = self.query_one("#opensuse-select", Select).value
        packman_idx = self.query_one("#packman-select", Select).value
        opensuse_proto = self.query_one("#opensuse-proto-select", Select).value
        packman_proto = self.query_one("#packman-proto-select", Select).value

        opensuse_mirror = self.opensuse_mirrors_list[opensuse_idx]
        packman_mirror = self.packman_mirrors_list[packman_idx]

        opensuse_url = f"{opensuse_proto}://{opensuse_mirror.url}"
        packman_url = f"{packman_proto}://{packman_mirror.url}"

        self.parent_window.switch_mirror(opensuse_url, packman_url)
        self.app.pop_screen()