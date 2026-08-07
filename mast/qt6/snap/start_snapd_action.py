"""Start Snapd service action component."""

from __future__ import annotations

from PySide6.QtCore import QObject

from mast.core.i18n import _
from mast.core.snap import start_snapd_command
from mast.qt6.command.action import CommandAction


class StartSnapdAction(CommandAction):
    """Reusable action for starting the snapd daemon."""

    def __init__(self, parent: QObject | None = None):
        super().__init__(
            text=_("Start Snapd"),
            running_text=_("Starting Snapd..."),
            dialog_title=_("Start Snapd"),
            command=start_snapd_command(),
            success_output=_("Snapd started successfully."),
            auto_close_on_success=True,
            parent=parent,
        )
