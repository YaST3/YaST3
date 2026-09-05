"""TUI Build Service search screen."""

from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Header, Input, Static
from textual.worker import Worker, WorkerState

from mast.core.buildservice import BuildServicePackage, build_install_command, search_packages
from mast.core.i18n import _


class BuildServiceWindow(Screen):
    BINDINGS = [("escape", "app.pop_screen", "Back"), ("q", "app.pop_screen", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            with Horizontal():
                yield Input(placeholder=_("Package name"), id="query")
                yield Button(_("Search"), id="search")
                yield Button(_("Install"), id="install", disabled=True)
            yield Static(_("Search packages published by build.opensuse.org."), id="status")
            yield DataTable(id="results")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#results", DataTable)
        for column in [_('Name'), _('Version'), _('Architecture'), _('Project')]:
            table.add_column(column)
        self.packages: list[BuildServicePackage] = []

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "query":
            self.search()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "search":
            self.search()
        elif event.button.id == "install":
            self.install_selected()

    def search(self) -> None:
        query = self.query_one("#query", Input).value.strip()
        if query:
            self.query_one("#search", Button).disabled = True
            self.run_worker(lambda: search_packages(query), thread=True, name="buildservice-search")

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.worker.name != "buildservice-search":
            return
        if event.state == WorkerState.SUCCESS:
            self._show_results(event.worker.result)
        elif event.state == WorkerState.ERROR:
            self.query_one("#status", Static).update(_("Build Service search failed: {0}").format(event.worker.error))
        if event.state in (WorkerState.SUCCESS, WorkerState.ERROR):
            self.query_one("#search", Button).disabled = False

    def _show_results(self, packages: list[BuildServicePackage]) -> None:
        self.packages = packages
        table = self.query_one("#results", DataTable)
        table.clear()
        for package in packages:
            table.add_row(
                package.name,
                f"{package.version}-{package.release}",
                package.arch,
                Text(package.project, style=self._project_color(package.project)),
            )
        self.query_one("#status", Static).update(_("Found {0} packages.").format(len(packages)))

    @staticmethod
    def _project_color(project: str) -> str:
        if project.startswith("openSUSE:"):
            return "green"
        if project.startswith(("home:", "isv:")):
            return "red"
        return "orange"

    def on_data_table_row_selected(self, _event: DataTable.RowSelected) -> None:
        self.query_one("#install", Button).disabled = False

    def install_selected(self) -> None:
        table = self.query_one("#results", DataTable)
        if table.cursor_row < 0 or table.cursor_row >= len(self.packages):
            return
        package = self.packages[table.cursor_row]
        self.app.push_screen(InstallScreen(package))


class InstallScreen(Screen):
    def __init__(self, package: BuildServicePackage) -> None:
        super().__init__()
        self.package = package

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(_("Installing {0}...").format(self.package.name), id="status")
        yield Footer()

    def on_mount(self) -> None:
        self.run_worker(self._install, thread=True, name="buildservice-install")

    def _install(self) -> None:
        import subprocess

        result = subprocess.run(build_install_command(self.package), capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip() or _("Unknown error"))

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.worker.name != "buildservice-install" or event.state not in (WorkerState.SUCCESS, WorkerState.ERROR):
            return
        status = self.query_one("#status", Static)
        if event.state == WorkerState.SUCCESS:
            status.update(_("Package installed successfully."))
        else:
            status.update(_("Installation failed: {0}").format(event.worker.error))
