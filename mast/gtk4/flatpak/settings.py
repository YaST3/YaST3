"""GTK4 settings tab for Flatpak module."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk

from mast.core.flatpak import (
    clear_flatpak_cache_command,
    get_flatpak_cache_size,
)
from mast.core.i18n import _
from mast.gtk4.command.action import CommandAction
from mast.gtk4.flatpak.remove_action import UninstallFlatpakAction


class ClearFlatpakCacheAction(CommandAction):
    """Reusable action for clearing flatpak cache."""

    def __init__(self, parent_window: Gtk.Window | None = None):
        super().__init__(
            text=_("Clear Cache"),
            running_text=_("Clearing Cache..."),
            dialog_title=_("Clear Flatpak Cache"),
            command=clear_flatpak_cache_command(),
            success_output=_("Flatpak cache cleared successfully."),
            auto_close_on_success=True,
            parent_window=parent_window,
        )


class FlatpakSettingsTab(Gtk.Box):
    """Settings UI for dangerous Flatpak operations."""

    def __init__(self, parent_window: Gtk.ApplicationWindow, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8, **kwargs)
        self.parent_window = parent_window

        # --- Cache group ---
        cache_group = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        cache_frame = Gtk.Frame(label=_("Cache Management"))
        cache_frame.set_child(cache_group)
        cache_group.set_margin_top(8)
        cache_group.set_margin_bottom(8)
        cache_group.set_margin_start(8)
        cache_group.set_margin_end(8)

        cache_size_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        cache_size_label = Gtk.Label(label=_("Cache Size:"))
        cache_size_label.set_halign(Gtk.Align.START)
        self.cache_size_value = Gtk.Label(label=get_flatpak_cache_size())
        self.cache_size_value.set_halign(Gtk.Align.START)
        cache_size_row.append(cache_size_label)
        cache_size_row.append(self.cache_size_value)
        cache_group.append(cache_size_row)

        self.clear_cache_action = ClearFlatpakCacheAction(parent_window)
        self.clear_cache_action.connect_changed(self._sync_clear_cache_action_state)
        self.clear_cache_action.connect_finished(self._on_clear_cache_finished)

        self.clear_cache_btn = Gtk.Button(label=self.clear_cache_action.text())
        self.clear_cache_btn.connect("clicked", self.clear_cache_action.trigger)
        cache_group.append(self.clear_cache_btn)

        self.append(cache_frame)

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
        self._sync_clear_cache_action_state()

    def _sync_uninstall_action_state(self) -> None:
        self.uninstall_btn.set_label(self.uninstall_action.text())
        self.uninstall_btn.set_sensitive(self.uninstall_action.is_enabled())

    def _sync_clear_cache_action_state(self) -> None:
        self.clear_cache_btn.set_label(self.clear_cache_action.text())
        self.clear_cache_btn.set_sensitive(self.clear_cache_action.is_enabled())

    def _on_clear_cache_finished(self, success: bool, error: str, _stdout: str) -> None:
        if success:
            self.cache_size_value.set_label(get_flatpak_cache_size())
            self._show_message_dialog(
                Gtk.MessageType.INFO, _("Success"), _("Flatpak cache cleared successfully.")
            )
        else:
            self._show_message_dialog(
                Gtk.MessageType.ERROR,
                _("Error"),
                _("Failed to clear Flatpak cache: {0}").format(error or _("Unknown error")),
            )

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
