"""Uninstall Snap action component."""

from __future__ import annotations

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMessageBox, QWidget

from mast.core.i18n import _
from mast.core.snap import remove_snap_command
from mast.qt6.command.action import CommandAction


class UninstallSnapAction(CommandAction):
    """Reusable action for triggering snapd uninstall."""

    def __init__(self, parent: QObject | None = None):
        super().__init__(
            text=_("Uninstall Snap"),
            running_text=_("Uninstalling Snap..."),
            dialog_title=_("Uninstall Snap"),
            command=remove_snap_command(),
            success_output=_("Snap uninstalled successfully."),
            auto_close_on_success=True,
            parent=parent,
        )

    def start_action(self) -> None:
        if self.is_running():
            return

        parent_widget: QWidget | None = None
        parent = self.parent()
        if isinstance(parent, QWidget):
            parent_widget = parent

        reply = QMessageBox.question(
            parent_widget,
            _("Confirm"),
            _("Are you sure you want to uninstall Snap?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        super().start_action()