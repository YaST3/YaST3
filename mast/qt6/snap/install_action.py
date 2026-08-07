"""Install Snap action component."""

from __future__ import annotations

from PySide6.QtCore import QObject

from mast.core.i18n import _
from mast.core.snap import install_snap_command

from mast.qt6.command.action import CommandAction


class InstallSnapAction(CommandAction):
    """Reusable action for triggering snapd installation."""

    def __init__(self, parent: QObject | None = None):
        super().__init__(
            text=_("Install Snap"),
            running_text=_("Installing Snap..."),
            dialog_title=_("Install Snap"),
            command=install_snap_command(),
            success_output=_("Snap installed successfully."),
            auto_close_on_success=True,
            parent=parent,
        )