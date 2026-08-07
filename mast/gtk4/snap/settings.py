"""GTK4 settings dialog for Snap module."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk

from mast.core.i18n import _
from mast.gtk4.snap.remove_action import UninstallSnapAction


class SnapSettingsDialog(Gtk.Window):
    """Modal settings dialog for dangerous Snap operations."""

    def __init__(self, parent_window: Gtk.ApplicationWindow):
        super().__init__(transient_for=parent_window, modal=True, title=_("Settings"))
        self.parent_window = parent_window
        self.set_default_size(360, 160)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)

        self.uninstall_action = UninstallSnapAction(parent_window)
        self.uninstall_action.connect_changed(self._sync_uninstall_action_state)
        self.uninstall_action.connect_finished(self._on_uninstall_finished)

        self.uninstall_btn = Gtk.Button(label=self.uninstall_action.text())
        self.uninstall_btn.connect("clicked", self.uninstall_action.trigger)
        box.append(self.uninstall_btn)

        close_btn = Gtk.Button(label=_("Close"))
        close_btn.connect("clicked", lambda *_: self.destroy())
        box.append(close_btn)

        self.set_child(box)
        self._sync_uninstall_action_state()

    def _sync_uninstall_action_state(self) -> None:
        self.uninstall_btn.set_label(self.uninstall_action.text())
        self.uninstall_btn.set_sensitive(self.uninstall_action.is_enabled())

    def _on_uninstall_finished(self, success: bool, error: str, _stdout: str) -> None:
        if success:
            self._show_message_dialog(Gtk.MessageType.INFO, _("Success"), _("Snap uninstalled successfully."))
            if hasattr(self.parent_window, "_refresh_state"):
                self.parent_window._refresh_state()
            self.destroy()
        else:
            self._show_message_dialog(
                Gtk.MessageType.ERROR,
                _("Error"),
                _("Failed to uninstall Snap: {0}").format(error or _("Unknown error")),
            )

    def _show_message_dialog(self, msg_type: Gtk.MessageType, title: str, message: str) -> None:
        dialog = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            message_type=msg_type,
            buttons=Gtk.ButtonsType.OK,
            text=title,
        )
        dialog.set_property("secondary-text", message)
        dialog.connect("response", lambda d, _r: d.destroy())
        dialog.present()
