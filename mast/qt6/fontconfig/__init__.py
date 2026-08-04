"""Font Config module package - Qt6 GUI."""

from mast.core.i18n import _
from mast.qt6.fontconfig.window import FontConfigWindow
from mast.qt6.module import Module


class FontConfigModule(Module):
    def __init__(self):
        super().__init__(_("Font Config"), ("preferences-desktop-font", "preferences-desktop"))

    def _create_window(self):
        return FontConfigWindow()


__all__ = ["FontConfigModule"]
