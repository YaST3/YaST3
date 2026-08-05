"""UI components for the Keyboard module (TUI)."""

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Button, Header, Label, ListItem, ListView, Static

from mast.core.i18n import _
from mast.core.keyboard import (
    get_current_keyboard_layout,
    get_all_keyboard_layouts,
    set_keyboard_layout,
    get_layout_name,
)


class KeyboardWindow(Screen):
    """TUI window for keyboard layout configuration."""

    CSS = """
    Screen {
        align: center middle;
    }

    .container {
        width: 80;
        height: 30;
        padding: 2;
        border: solid green;
    }

    .button-row {
        align: right middle;
        margin-top: 1;
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

    ListView {
        height: 20;
    }
    """

    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("q", "app.pop_screen", "Back"),
        ("enter", "save", "Save"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="container"):
            yield Label(_("Keyboard Layout Configuration"), classes="title")
            yield ListView(id="layout-list")
            with Vertical(classes="button-row"):
                yield Button(_("Save"), id="save-btn", variant="primary")
                yield Button(_("Cancel"), id="cancel-btn")
            yield Static("", id="message", classes="message")

    def on_mount(self) -> None:
        """Load current keyboard layout on mount."""
        self._current_layout = get_current_keyboard_layout()
        self._layout_codes = []
        self._load_layouts()

    def _load_layouts(self) -> None:
        list_view = self.query_one("#layout-list", ListView)
        list_view.clear()
        self._layout_codes.clear()

        layouts = get_all_keyboard_layouts()
        selected_index = 0

        for i, layout in enumerate(layouts):
            name = get_layout_name(layout.code)
            label = f"{name} ({layout.code})"
            item = ListItem(Label(label))
            list_view.append(item)
            self._layout_codes.append(layout.code)
            if layout.code == self._current_layout:
                selected_index = i

        list_view.index = selected_index

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
        if event.button.id == "save-btn":
            self.action_save()
        elif event.button.id == "cancel-btn":
            self.app.pop_screen()

    def action_save(self) -> None:
        """Save the keyboard layout."""
        list_view = self.query_one("#layout-list", ListView)
        selected_index = list_view.index

        if selected_index is None or selected_index < 0:
            return

        selected_layout = self._layout_codes[selected_index]

        if selected_layout == self._current_layout:
            self.show_message(_("Info: No changes to save."))
            return

        status, message = set_keyboard_layout(selected_layout)

        if status == "ok":
            self.show_message(
                _("Success: Keyboard layout changed successfully to '{0}'.").format(
                    get_layout_name(selected_layout)
                ),
                success=True,
            )
            self.set_timer(1.5, self.app.pop_screen)
        elif status == "permission_denied":
            self.show_message(
                _("Error: Permission denied. Root permission required."),
                error=True,
            )
        elif status == "pkexec_failed":
            self.show_message(
                _("Error: Authentication failed or pkexec not available."),
                error=True,
            )
        else:
            self.show_message(_("Error: {0}").format(message), error=True)