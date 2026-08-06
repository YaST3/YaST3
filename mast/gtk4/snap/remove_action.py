"""Uninstall Snap action component."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk

from mast.core.i18n import _
from mast.gtk4.command.action import CommandAction


class UninstallSnapAction(CommandAction):
    """Reusable action for triggering snapd uninstall."""

    def __init__(self, parent_window: Gtk.Window | None = None):
        super().__init__(
            text=_("Uninstall Snap"),
            running_text=_("Uninstalling Snap..."),
            dialog_title=_("Uninstall Snap"),
            command=["pkexec", "zypper", "--non-interactive", "remove", "-y", "snapd"],
            success_output=_("Snap uninstalled successfully."),
            auto_close_on_success=True,
            parent_window=parent_window,
        )

    def start_action(self) -> None:
        if self.is_running():
            return

        confirm_dialog = Gtk.MessageDialog(
            transient_for=self.parent_window,
            modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=_("Confirm"),
        )
        confirm_dialog.set_property("secondary-text", _("Are you sure you want to uninstall Snap?"))
        confirm_dialog.connect("response", self._on_confirm_response)
        confirm_dialog.present()

    def _on_confirm_response(self, dialog: Gtk.MessageDialog, response_id: Gtk.ResponseType) -> None:
        dialog.destroy()
        if response_id != Gtk.ResponseType.YES:
            return

        super().start_action()