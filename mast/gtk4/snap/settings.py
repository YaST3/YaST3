"""GTK4 settings dialog for Snap module."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk

from mast.core.i18n import _
from mast.core.snap import (
    clear_snap_cache_command,
    clear_snap_old_versions_command,
    get_snap_cache_size,
    get_snap_old_versions_size,
    get_snap_retain_count,
    set_snap_retain_command,
)
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


class ClearOldVersionsAction(CommandAction):
    """Reusable action for removing old snap revisions."""

    def __init__(self, parent_window: Gtk.Window | None = None):
        super().__init__(
            text=_("Clean Old Versions"),
            running_text=_("Cleaning Old Versions..."),
            dialog_title=_("Clean Old Snap Versions"),
            command=clear_snap_old_versions_command(),
            success_output=_("Old snap versions cleaned successfully."),
            auto_close_on_success=True,
            parent_window=parent_window,
        )


class SetRetainCountAction(CommandAction):
    """Action for setting the snap revision retain count."""

    def __init__(self, count: int, parent_window: Gtk.Window | None = None):
        super().__init__(
            text=_("Apply"),
            running_text=_("Applying..."),
            dialog_title=_("Set Retain Count"),
            command=set_snap_retain_command(count),
            success_output=_("Retain count updated successfully."),
            auto_close_on_success=True,
            parent_window=parent_window,
        )


class SnapSettingsDialog(Gtk.Window):
    """Modal settings dialog for dangerous Snap operations."""

    def __init__(self, parent_window: Gtk.ApplicationWindow):
        super().__init__(transient_for=parent_window, modal=True, title=_("Settings"))
        self.parent_window = parent_window
        self.set_default_size(400, 480)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)

        # --- Package Versions group ---
        versions_group = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        versions_frame = Gtk.Frame(label=_("Package Versions"))
        versions_frame.set_child(versions_group)
        versions_group.set_margin_top(8)
        versions_group.set_margin_bottom(8)
        versions_group.set_margin_start(8)
        versions_group.set_margin_end(8)

        retain_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        retain_label = Gtk.Label(label=_("Max Versions to Keep:"))
        retain_label.set_halign(Gtk.Align.START)
        self.retain_spin = Gtk.SpinButton.new_with_range(1, 20, 1)
        self.retain_spin.set_value(get_snap_retain_count())
        self.retain_apply_btn = Gtk.Button(label=_("Apply"))
        self.retain_apply_btn.connect("clicked", lambda *_: self._apply_retain_count())
        retain_row.append(retain_label)
        retain_row.append(self.retain_spin)
        retain_row.append(self.retain_apply_btn)
        versions_group.append(retain_row)

        old_size_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        old_size_label = Gtk.Label(label=_("Old Versions Size:"))
        old_size_label.set_halign(Gtk.Align.START)
        self.old_versions_size_value = Gtk.Label(label=get_snap_old_versions_size())
        self.old_versions_size_value.set_halign(Gtk.Align.START)
        old_size_row.append(old_size_label)
        old_size_row.append(self.old_versions_size_value)
        versions_group.append(old_size_row)

        self.clear_old_versions_action = ClearOldVersionsAction(parent_window)
        self.clear_old_versions_action.connect_changed(self._sync_clear_old_versions_state)
        self.clear_old_versions_action.connect_finished(self._on_clear_old_versions_finished)

        self.clear_old_versions_btn = Gtk.Button(label=self.clear_old_versions_action.text())
        self.clear_old_versions_btn.connect("clicked", self.clear_old_versions_action.trigger)
        versions_group.append(self.clear_old_versions_btn)

        box.append(versions_frame)

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
        cache_group.append(self.clear_cache_btn)

        box.append(cache_frame)

        # --- Uninstall section ---
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
        self._sync_clear_old_versions_state()

    def _apply_retain_count(self) -> None:
        count = int(self.retain_spin.get_value())
        self._retain_action = SetRetainCountAction(count, self.parent_window)
        self._retain_action.connect_finished(self._on_retain_finished)
        self.retain_apply_btn.set_sensitive(False)
        self._retain_action.start_action()

    def _on_retain_finished(self, success: bool, error: str, _stdout: str) -> None:
        self.retain_apply_btn.set_sensitive(True)
        if success:
            self._show_message_dialog(
                Gtk.MessageType.INFO, _("Success"), _("Retain count updated successfully.")
            )
        else:
            self._show_message_dialog(
                Gtk.MessageType.ERROR,
                _("Error"),
                _("Failed to set retain count: {0}").format(error or _("Unknown error")),
            )

    def _sync_uninstall_action_state(self) -> None:
        self.uninstall_btn.set_label(self.uninstall_action.text())
        self.uninstall_btn.set_sensitive(self.uninstall_action.is_enabled())

    def _sync_clear_cache_action_state(self) -> None:
        self.clear_cache_btn.set_label(self.clear_cache_action.text())
        self.clear_cache_btn.set_sensitive(self.clear_cache_action.is_enabled())

    def _sync_clear_old_versions_state(self) -> None:
        self.clear_old_versions_btn.set_label(self.clear_old_versions_action.text())
        self.clear_old_versions_btn.set_sensitive(self.clear_old_versions_action.is_enabled())

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

    def _on_clear_old_versions_finished(self, success: bool, error: str, _stdout: str) -> None:
        if success:
            self.old_versions_size_value.set_label(get_snap_old_versions_size())
            self._show_message_dialog(
                Gtk.MessageType.INFO, _("Success"), _("Old snap versions cleaned successfully.")
            )
        else:
            self._show_message_dialog(
                Gtk.MessageType.ERROR,
                _("Error"),
                _("Failed to clean old versions: {0}").format(error or _("Unknown error")),
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
