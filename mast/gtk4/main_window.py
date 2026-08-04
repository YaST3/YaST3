"""Main application window showing module buttons."""

from gi.repository import Gio, Gtk

from mast.core.i18n import _
from mast.gtk4 import (
    AndroidModule,
    CronModule,
    DateTimeModule,
    FlatpakModule,
    GitModule,
    HostnameModule,
    HostsModule,
    JournalModule,
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
            GitModule(),
            HostnameModule(),
            HostsModule(),
            JournalModule(),
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