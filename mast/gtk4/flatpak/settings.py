"""GTK4 settings tab for Flatpak module."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk

from mast.core.i18n import _
from mast.gtk4.flatpak.remove_action import UninstallFlatpakAction


class FlatpakSettingsTab(Gtk.Box):
    """Settings UI for dangerous Flatpak operations."""

    def __init__(self, parent_window: Gtk.ApplicationWindow, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8, **kwargs)
        self.parent_window = parent_window

        self.append(Gtk.Box(vexpand=True))

        bottom_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        bottom_row.set_halign(Gtk.Align.END)

        self.uninstall_action = UninstallFlatpakAction(parent_window)
        self.uninstall_action.connect_changed(self._sync_uninstall_action_state)
        self.uninstall_action.connect_finished(self._on_uninstall_finished)

        self.uninstall_btn = Gtk.Button(label=self.uninstall_action.text())
        self.uninstall_btn.connect("clicked", self.uninstall_action.trigger)
        bottom_row.append(self.uninstall_btn)

        self.append(bottom_row)
        self._sync_uninstall_action_state()

    def _sync_uninstall_action_state(self) -> None:
        self.uninstall_btn.set_label(self.uninstall_action.text())
        self.uninstall_btn.set_sensitive(self.uninstall_action.is_enabled())

    def _on_uninstall_finished(self, success: bool, error: str, _stdout: str) -> None:
        if success:
            self._show_message_dialog(Gtk.MessageType.INFO, _("Success"), _("Flatpak uninstalled successfully."))
            if hasattr(self.parent_window, "_refresh_state"):
                self.parent_window._refresh_state()
        else:
            self._show_message_dialog(
                Gtk.MessageType.ERROR,
                _("Error"),
                _("Failed to uninstall Flatpak: {0}").format(error or _("Unknown error")),
            )

    def _show_message_dialog(self, msg_type: Gtk.MessageType, title: str, message: str) -> None:
        dialog = Gtk.MessageDialog(
            transient_for=self.parent_window,
            modal=True,
            message_type=msg_type,
            buttons=Gtk.ButtonsType.OK,
            text=title,
        )
        dialog.set_property("secondary-text", message)
        dialog.connect("response", lambda d, _r: d.destroy())
        dialog.present()
