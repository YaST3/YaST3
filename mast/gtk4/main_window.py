"""Main application window showing module buttons."""

from gi.repository import Gio, Gtk

from mast.core.i18n import _
from mast.core.telemetry import (
    get_telemetry_consent,
    set_telemetry_consent,
)
from mast.gtk4.telemetry import track_app_started
from mast.gtk4 import (
    AndroidModule,
    CronModule,
    DateTimeModule,
    FlatpakModule,
    FontConfigModule,
    GitModule,
    HostnameModule,
    HostsModule,
    JournalModule,
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
from mast.gtk4.about_dialog import show_about_dialog
from mast.gtk4.module_button import ModuleButton


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.modules = (
            AndroidModule(),
            CronModule(),
            DateTimeModule(),
            FlatpakModule(),
            FontConfigModule(),
            GitModule(),
            HostnameModule(),
            HostsModule(),
            JournalModule(),
            KeyboardModule(),
            LanguagesModule(),
            PackagesModule(),
            ProxyModule(),
            RepositoriesModule(),
            ServicesModule(),
            SnapshotsModule(),
            SSHClientModule(),
            UsersModule(),
        )

        self.windows = {}  # Keep track of open module windows

        self.set_title("MaST")
        self.set_default_size(960, 640)

        self._setup_header_bar()

        # Create scrolled window
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        # Create main container
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        scrolled.set_child(self.main_box)

        # Create grid for module buttons
        self.grid = Gtk.Grid()
        self.grid.set_margin_top(32)
        self.grid.set_margin_bottom(32)
        self.grid.set_margin_start(32)
        self.grid.set_margin_end(32)
        self.grid.set_row_spacing(24)
        self.grid.set_column_spacing(24)
        self.grid.set_halign(Gtk.Align.CENTER)
        self.grid.set_valign(Gtk.Align.START)

        # Add module buttons
        for index, module in enumerate(self.modules):
            button = ModuleButton(module, self)
            row, column = divmod(index, 4)
            self.grid.attach(button, column, row, 1, 1)

        self.main_box.append(self.grid)
        self.set_child(scrolled)

        self._setup_telemetry()

    def _setup_header_bar(self) -> None:
        header_bar = Gtk.HeaderBar()
        self.set_titlebar(header_bar)

        about_action = Gio.SimpleAction(name="about")
        about_action.connect("activate", self._show_about)
        self.add_action(about_action)

        menu = Gio.Menu()
        menu.append(_("About"), "win.about")

        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name("open-menu-symbolic")
        menu_button.set_menu_model(menu)
        header_bar.pack_end(menu_button)

    def _show_about(self, action, param) -> None:
        show_about_dialog(self)

    def _setup_telemetry(self) -> None:
        consent = get_telemetry_consent()
        if consent is None:
            self._ask_telemetry_consent()
            return

        if consent:
            track_app_started()

    def _ask_telemetry_consent(self) -> None:
        dialog = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=_("Enable anonymous usage analytics?"),
        )
        dialog.set_property(
            "secondary-text",
            _(
                "MaST only collects fully anonymous, minimal usage data, and never shares it with third parties."
            ),
        )
        dialog.connect("response", self._on_telemetry_consent_response)
        dialog.present()

    def _on_telemetry_consent_response(self, dialog: Gtk.MessageDialog, response: int) -> None:
        enabled = response == Gtk.ResponseType.YES
        set_telemetry_consent(enabled)
        if enabled:
            track_app_started()
        dialog.destroy()