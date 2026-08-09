"""GTK4 settings dialog for Snap module."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk

from mast.core.i18n import _
from mast.core.snap import clear_snap_cache_command, get_snap_cache_size
from mast.gtk4.command.action import CommandAction
from mast.gtk4.snap.remove_action import UninstallSnapAction


class ClearSnapCacheAction(CommandAction):
    """Reusable action for clearing snap cache."""

    def __init__(self, parent_window: Gtk.Window | None = None):
        super().__init__(
            text=_("Clear Cache"),
            running_text=_("Clearing Cache..."),
            dialog_title=_("Clear Snap Cache"),
            command=clear_snap_cache_command(),
            success_output=_("Snap cache cleared successfully."),
            auto_close_on_success=True,
            parent_window=parent_window,
        )


class SnapSettingsDialog(Gtk.Window):
    """Modal settings dialog for dangerous Snap operations."""

    def __init__(self, parent_window: Gtk.ApplicationWindow):
        super().__init__(transient_for=parent_window, modal=True, title=_("Settings"))
        self.parent_window = parent_window
        self.set_default_size(400, 260)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)

        # Cache group
        cache_group = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        cache_frame = Gtk.Frame(label=_("Cache Management"))
        cache_frame.set_child(cache_group)

        cache_size_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        cache_size_row.set_margin_top(8)
        cache_size_row.set_margin_bottom(8)
        cache_size_row.set_margin_start(8)
        cache_size_row.set_margin_end(8)
        cache_size_label = Gtk.Label(label=_("Cache Size:"))
        cache_size_label.set_halign(Gtk.Align.START)
        self.cache_size_value = Gtk.Label(label=get_snap_cache_size())
        self.cache_size_value.set_halign(Gtk.Align.START)
        cache_size_row.append(cache_size_label)
        cache_size_row.append(self.cache_size_value)
        cache_group.append(cache_size_row)

        self.clear_cache_action = ClearSnapCacheAction(parent_window)
        self.clear_cache_action.connect_changed(self._sync_clear_cache_action_state)
        self.clear_cache_action.connect_finished(self._on_clear_cache_finished)

        self.clear_cache_btn = Gtk.Button(label=self.clear_cache_action.text())
        self.clear_cache_btn.connect("clicked", self.clear_cache_action.trigger)
        self.clear_cache_btn.set_margin_start(8)
        self.clear_cache_btn.set_margin_end(8)
        self.clear_cache_btn.set_margin_bottom(8)
        cache_group.append(self.clear_cache_btn)

        box.append(cache_frame)

        # Uninstall section
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
        self._sync_clear_cache_action_state()

    def _sync_uninstall_action_state(self) -> None:
        self.uninstall_btn.set_label(self.uninstall_action.text())
        self.uninstall_btn.set_sensitive(self.uninstall_action.is_enabled())

    def _sync_clear_cache_action_state(self) -> None:
        self.clear_cache_btn.set_label(self.clear_cache_action.text())
        self.clear_cache_btn.set_sensitive(self.clear_cache_action.is_enabled())

    def _on_clear_cache_finished(self, success: bool, error: str, _stdout: str) -> None:
        if success:
            self.cache_size_value.set_label(get_snap_cache_size())
            self._show_message_dialog(
                Gtk.MessageType.INFO, _("Success"), _("Snap cache cleared successfully.")
            )
        else:
            self._show_message_dialog(
                Gtk.MessageType.ERROR,
                _("Error"),
                _("Failed to clear Snap cache: {0}").format(error or _("Unknown error")),
            )

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
