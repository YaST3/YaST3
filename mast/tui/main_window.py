"""Main application window showing module buttons."""

from textual.app import App, ComposeResult
from textual.containers import Grid, Horizontal, ScrollableContainer, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static

from mast.core import GITHUB_URL, LICENSE_NAME, __version__, get_license_text
from mast.core.i18n import _
from mast.tui.module import Module
from mast.tui import (
    CronModule,
    DateTimeModule,
    GitModule,
    HostnameModule,
    HostsModule,
    KeyboardModule,
    LanguagesModule,
    PackagesModule,
    ProxyModule,
    RepositoriesModule,
    ServicesModule,
    SnapshotsModule,
    SSHClientModule,
    UsersModule,
)


class AboutScreen(Screen):
    CSS = """
    Vertical {
        height: 100%;
        width: 100%;
        align: center middle;
        padding: 2;
    }

    .title {
        text-align: center;
        text-style: bold;
        margin-bottom: 2;
    }

    .info {
        text-align: center;
        margin-bottom: 1;
    }

    .license-text {
        width: 100%;
        height: 40;
        overflow: auto;
        border: solid green;
        padding: 1;
    }

    Button {
        width: 20;
        margin-top: 2;
    }
    """

    def compose(self) -> ComposeResult:
        license_text = get_license_text()
        license_content = license_text if license_text else _("License file not found.")

        yield Header(title=_("About MaST"))
        with Vertical():
            yield Static("MaST", classes="title")
            yield Static(_("Version: {}").format(__version__), classes="info")
            yield Static(_("License: {}").format(LICENSE_NAME), classes="info")
            yield Static(GITHUB_URL, classes="info")
            yield Static(_("License Text:"))
            yield Static(license_content, classes="license-text")
            with Horizontal():
                yield Button(_("OK"), id="ok-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok-btn":
            self.app.pop_screen()


class ModuleButton(Button):
    """A button for launching a module."""

    CSS = """
    ModuleButton {
        width: 100%;
    }
    """

    def __init__(self, module: Module) -> None:
        safe_id = module.__class__.__name__.lower().replace("module", "")
        label = f"{module.emoji} {module.name}"
        super().__init__(label, id=f"module-{safe_id}")
        self.module = module


class MainWindow(App):
    """Main MaST TUI application."""

    CSS = """
    .module-grid {
        grid-size: 4;
        grid-columns: 1fr 1fr 1fr 1fr;
        grid-rows: auto;
        grid-gutter: 2;
        padding: 2;
        width: 100%;
    }

    .title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
        padding: 1;
    }

    ScrollableContainer {
        align: center top;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("escape", "quit", "Quit"),
        ("a", "about", _("About")),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.modules: list[Module] = [
            HostnameModule(),
            GitModule(),
            HostsModule(),
            CronModule(),
            DateTimeModule(),
            KeyboardModule(),
            LanguagesModule(),
            RepositoriesModule(),
            ProxyModule(),
            ServicesModule(),
            SnapshotsModule(),
            SSHClientModule(),
            PackagesModule(),
            UsersModule(),
        ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        with ScrollableContainer():
            yield Static("MaST", classes="title")
            with Grid(classes="module-grid"):
                for module in self.modules:
                    yield ModuleButton(module)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle module button press."""
        if isinstance(event.button, ModuleButton):
            screen = event.button.module.create_window()
            if screen:
                self.push_screen(screen)

    def action_about(self) -> None:
        """Show about screen."""
        self.push_screen(AboutScreen())