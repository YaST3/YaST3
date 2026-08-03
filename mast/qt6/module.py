"""Base module class for MaST Qt6 modules."""

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMainWindow

from mast.core.i18n import _


class Module(QObject):
    """Base class for MaST Qt6 modules."""

    name: str
    icon_names: tuple[str, ...]
    experimental: bool = False
    window: QMainWindow | None = None

    def __init__(self, name: str, icon_names: tuple[str, ...], experimental: bool = False) -> None:
        super().__init__()
        self.name = name
        self.icon_names = icon_names
        self.experimental = experimental

    def _create_window(self) -> QMainWindow:
        """Create the module window. Must be implemented by subclass."""
        raise NotImplementedError("Module window creation not implemented.")

    def launch(self, parent: QMainWindow | None = None) -> None:
        """Launch the module window."""
        if self.window is None:
            self.window = self._create_window()
            self.window.setWindowTitle(_("{name} — MaST").format(name=self.name))
            self.window.destroyed.connect(self._on_window_closed)
        self.window.show()
        self.window.activateWindow()

    def _on_window_closed(self) -> None:
        """Handle window closed signal."""
        self.window = None
        print(f"Module '{self.name}' window closed.")
