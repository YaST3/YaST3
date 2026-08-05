"""Remove Flatpak action component."""

from __future__ import annotations

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMessageBox, QWidget

from mast.core.i18n import _
from mast.qt6.command.action import CommandAction


class RemoveFlatpakAction(CommandAction):
    """Reusable action for triggering Flatpak removal."""

    def __init__(self, parent: QObject | None = None):
        super().__init__(
            text=_("Remove Flatpak"),
            running_text=_("Removing Flatpak..."),
            dialog_title=_("Remove Flatpak"),
            command=["pkexec", "zypper", "--non-interactive", "remove", "-y", "flatpak"],
            success_output=_("Flatpak removed successfully."),
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
            _("Are you sure you want to remove Flatpak?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        super().start_action()
