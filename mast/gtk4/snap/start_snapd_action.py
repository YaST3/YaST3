"""Start Snapd service action component."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk

from mast.core.i18n import _
from mast.core.snap import start_snapd_command
from mast.gtk4.command.action import CommandAction


class StartSnapdAction(CommandAction):
    """Reusable action for starting the snapd daemon."""

    def __init__(self, parent_window: Gtk.Window | None = None):
        super().__init__(
            text=_("Start Snapd"),
            running_text=_("Starting Snapd..."),
            dialog_title=_("Start Snapd"),
            command=start_snapd_command(),
            success_output=_("Snapd started successfully."),
            auto_close_on_success=True,
            parent_window=parent_window,
        )
