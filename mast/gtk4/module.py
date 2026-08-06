"""Base module class for MaST GTK4 modules."""

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk

from mast.core.i18n import _
from mast.gtk4.telemetry import track_module_started


class Module:
    """Base class for MaST GTK4 modules."""

    name: str
    icon_names: tuple[str, ...]
    experimental: bool = False
    window: Gtk.Window | None = None

    def __init__(self, name: str, icon_names: tuple[str, ...], experimental: bool = False) -> None:
        self.name = name
        self.icon_names = icon_names
        self.experimental = experimental

    def _create_window(self) -> Gtk.Window:
        """Create the module window. Must be implemented by subclass."""
        raise NotImplementedError("Module window creation not implemented.")

    def launch(self, parent: Gtk.ApplicationWindow | None = None) -> None:
        """Launch the module window."""
        track_module_started(self.__class__.__name__)
        if self.window is None:
            self.window = self._create_window()
            self.window.set_title(_("{name} — MaST").format(name=self.name))
            self.window.connect("close-request", self._on_window_closed)
        self.window.present()

    def _on_window_closed(self, window) -> None:
        """Handle window closed signal."""
        self.window = None
