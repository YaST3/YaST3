"""Install Snap action component."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk

from mast.core.i18n import _
from mast.gtk4.command.action import CommandAction


class InstallSnapAction(CommandAction):
    """Reusable action for triggering snapd installation."""

    def __init__(self, parent_window: Gtk.Window | None = None):
        super().__init__(
            text=_("Install Snap"),
            running_text=_("Installing Snap..."),
            dialog_title=_("Install Snap"),
            command=["pkexec", "zypper", "--non-interactive", "install", "-y", "snapd"],
            success_output=_("Snap installed successfully."),
            auto_close_on_success=True,
            parent_window=parent_window,
        )