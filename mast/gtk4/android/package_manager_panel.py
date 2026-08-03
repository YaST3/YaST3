"""Package manager panel for the GTK4 Android module."""

from __future__ import annotations

import os
import tempfile
import threading
import urllib.request

import adbutils

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import GLib, GObject, Gtk

from mast.core.android import (
    DeviceInfo,
    get_blacklist_info,
    is_dangerous,
    uninstall_package,
)
from mast.core.i18n import _


def _install_apk_with_adbutils(serial: str, apk_path: str) -> bool:
    try:
        adbutils.adb.device(serial=serial).install(apk_path, silent=True, flags=["-r"])
        return True
    except Exception:
        return False


class PackageManagerPanel(Gtk.Box):
    """Component for managing and displaying package lists and filters."""

    __gsignals__ = {
        "refresh-clicked": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "show-message": (GObject.SignalFlags.RUN_FIRST, None, (str, str, str)),
        "busy-changed": (GObject.SignalFlags.RUN_FIRST, None, (bool,)),
        "packages-refresh-requested": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8, **kwargs)
        self._device: DeviceInfo | None = None
        self._fdroid_installed: bool | None = None
        self._external_busy = False
        self._operation_in_progress = False
        self._build_ui()

    def _build_ui(self) -> None:
        self.set_margin_start(8)
        self.set_margin_end(8)
        self.set_margin_top(8)
        self.set_margin_bottom(8)

        filter_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        self.search_entry = Gtk.Entry()
        self.search_entry.set_placeholder_text(_("Search"))
        self.search_entry.set_hexpand(True)
        filter_box.append(self.search_entry)

        self.blacklist_only = Gtk.CheckButton(label=_("Blacklist only"))
        filter_box.append(self.blacklist_only)

        self.system_only = Gtk.CheckButton(label=_("System apps"))
        filter_box.append(self.system_only)

        self.user_only = Gtk.CheckButton(label=_("User apps"))
        filter_box.append(self.user_only)

        self.append(filter_box)

        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        self.uninstall_btn = Gtk.Button(label=_("Uninstall"))
        self.uninstall_btn.set_sensitive(False)
        self.uninstall_btn.connect("clicked", lambda _: self._uninstall_selected())
        action_box.append(self.uninstall_btn)

        self.install_btn = Gtk.Button(label=_("Install APK"))
        self.install_btn.connect("clicked", lambda _: self._install_apk())
        action_box.append(self.install_btn)

        self.install_fdroid_btn = Gtk.Button(label=_("Install F-Droid"))
        self.install_fdroid_btn.connect("clicked", lambda _: self._install_fdroid())
        self.install_fdroid_btn.set_visible(False)
        action_box.append(self.install_fdroid_btn)

        self.refresh_pkgs_btn = Gtk.Button(label=_("Refresh"))
        self.refresh_pkgs_btn.connect("clicked", lambda _: self.emit("refresh-clicked"))
        action_box.append(self.refresh_pkgs_btn)

        action_box.append(Gtk.Box(hexpand=True))
        self.append(action_box)

        self.package_list_store = Gtk.ListStore(str, str, str, bool, bool)
        self.package_tree = Gtk.TreeView(model=self.package_list_store)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("ID"), renderer, text=0)
        column.set_resizable(True)
        column.set_min_width(280)
        column.set_expand(True)
        self.package_tree.append_column(column)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Version"), renderer, text=1)
        column.set_resizable(True)
        column.set_min_width(120)
        self.package_tree.append_column(column)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Type"), renderer, text=2)
        column.set_resizable(True)
        column.set_min_width(80)
        self.package_tree.append_column(column)

        self.package_selection = self.package_tree.get_selection()
        self.package_selection.set_mode(Gtk.SelectionMode.SINGLE)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(self.package_tree)
        self.append(scrolled)

    def clear_packages(self) -> None:
        self._fdroid_installed = None
        self.package_list_store.clear()
        self.uninstall_btn.set_sensitive(False)
        self._sync_controls()

    def set_selected_device(self, device: DeviceInfo | None) -> None:
        new_device = device if device and device.status == "device" else None
        prev_serial = self._device.serial if self._device is not None else None
        new_serial = new_device.serial if new_device is not None else None
        if prev_serial != new_serial:
            self._fdroid_installed = None
        self._device = new_device
        self._sync_controls()

    def set_fdroid_installed(self, installed: bool) -> None:
        self._fdroid_installed = installed
        self._sync_controls()

    def set_busy_state(self, busy: bool, has_selected_device: bool) -> None:
        self._external_busy = busy
        if not has_selected_device:
            self._device = None
        self._sync_controls()

    def _sync_controls(self) -> None:
        busy = self._external_busy or self._operation_in_progress
        has_device = self._device is not None

        self.refresh_pkgs_btn.set_sensitive(not busy)
        self.install_btn.set_sensitive(not busy and has_device)
        should_show_fdroid = has_device and self._fdroid_installed is False
        self.install_fdroid_btn.set_visible(should_show_fdroid)
        self.install_fdroid_btn.set_sensitive(not busy and should_show_fdroid)

        model, tree_iter = self.package_selection.get_selected()
        has_selection = tree_iter is not None
        self.uninstall_btn.set_sensitive(not busy and has_device and has_selection)

    def _get_selected_package_name(self) -> str | None:
        model, tree_iter = self.package_selection.get_selected()
        if tree_iter is None:
            return None

        path = model.get_path(tree_iter)
        path_str = path.to_string() if path else None
        if not path_str:
            return None

        index = int(path_str)
        if index < 0 or index >= len(self.package_list_store):
            return None

        return self.package_list_store[path][0]

    def _uninstall_selected(self) -> None:
        if self._device is None:
            return

        pkg_name = self._get_selected_package_name()
        if not pkg_name:
            return

        root = self.get_root()
        parent_window = root if isinstance(root, Gtk.Window) else None

        app_name = pkg_name
        dialog = Gtk.MessageDialog(
            transient_for=parent_window,
            modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=_("Uninstall Package"),
        )

        blacklist_info = get_blacklist_info(pkg_name)
        if blacklist_info:
            if is_dangerous(pkg_name):
                secondary = _(
                    'Are you sure you want to uninstall "{0}" ({1})?\n\nWARNING: This package is marked as dangerous. Uninstalling it may cause system instability or prevent the device from booting!'
                ).format(app_name, pkg_name)
            else:
                secondary = _(
                    'Are you sure you want to uninstall "{0}" ({1})?\n\nThis is a known bloatware package and can be safely removed.'
                ).format(app_name, pkg_name)
        else:
            secondary = _(
                'Are you sure you want to uninstall "{0}" ({1})?\n\nThis may affect system functionality.'
            ).format(app_name, pkg_name)

        dialog.set_property("secondary-text", secondary)

        def on_response(dlg, response):
            if response == Gtk.ResponseType.YES:
                self._do_uninstall(pkg_name)
            dlg.destroy()

        dialog.connect("response", on_response)
        dialog.present()

    def _do_uninstall(self, pkg_name: str) -> None:
        if self._device is None:
            return
        if self._operation_in_progress:
            return

        self._operation_in_progress = True
        self._sync_controls()
        self.emit("busy-changed", True)

        serial = self._device.serial

        def worker() -> None:
            try:
                success = uninstall_package(serial, pkg_name)
                GLib.idle_add(self._on_uninstall_finished, success, pkg_name)
            except Exception as e:
                GLib.idle_add(self.emit, "show-message", "error", _("Error"), str(e))
                GLib.idle_add(self._finish_operation)

        threading.Thread(target=worker, daemon=True).start()

    def _on_uninstall_finished(self, success: bool, pkg_name: str) -> bool:
        if success:
            self.emit(
                "show-message",
                "success",
                _("Success"),
                _('Package "{0}" uninstalled successfully.').format(pkg_name),
            )
            self.emit("packages-refresh-requested")
        else:
            self.emit(
                "show-message",
                "error",
                _("Error"),
                _('Failed to uninstall "{0}". Device may require root access.').format(
                    pkg_name
                ),
            )
        self._finish_operation()
        return False

    def _install_apk(self) -> None:
        if self._device is None:
            return
        if self._operation_in_progress:
            return

        root = self.get_root()
        parent_window = root if isinstance(root, Gtk.Window) else None

        dialog = Gtk.FileDialog(title=_("Select APK File"))
        filter_apk = Gtk.FileFilter()
        filter_apk.set_name(_("APK Files"))
        filter_apk.add_pattern("*.apk")
        dialog.set_default_filter(filter_apk)

        def on_response(d, result):
            try:
                file = d.open_finish(result)
                if file is None:
                    return

                apk_path = file.get_path()
                if apk_path and os.path.exists(apk_path):
                    self._do_install(apk_path)
            except Exception:
                pass

        dialog.open(parent_window, None, on_response)

    def _do_install(self, apk_path: str) -> None:
        if self._device is None:
            return
        if self._operation_in_progress:
            return

        self._operation_in_progress = True
        self._sync_controls()
        self.emit("busy-changed", True)

        serial = self._device.serial

        def worker() -> None:
            try:
                success = _install_apk_with_adbutils(serial, apk_path)
                GLib.idle_add(self._on_install_finished, success, apk_path)
            except Exception as e:
                GLib.idle_add(self.emit, "show-message", "error", _("Error"), str(e))
                GLib.idle_add(self._finish_operation)

        threading.Thread(target=worker, daemon=True).start()

    def _install_fdroid(self) -> None:
        if self._device is None:
            return
        if self._operation_in_progress:
            return
        if self._fdroid_installed is True:
            return

        self._operation_in_progress = True
        self._sync_controls()
        self.emit("busy-changed", True)

        serial = self._device.serial

        def worker() -> None:
            apk_path = ""
            try:
                with tempfile.NamedTemporaryFile(
                    prefix="fdroid-", suffix=".apk", delete=False
                ) as tmp:
                    apk_path = tmp.name

                with urllib.request.urlopen("https://f-droid.org/F-Droid.apk", timeout=60) as response:
                    with open(apk_path, "wb") as out_file:
                        out_file.write(response.read())

                success = _install_apk_with_adbutils(serial, apk_path)
                GLib.idle_add(self._on_fdroid_install_finished, success)
            except Exception as e:
                GLib.idle_add(self.emit, "show-message", "error", _("Error"), str(e))
                GLib.idle_add(self._finish_operation)
            finally:
                if apk_path and os.path.exists(apk_path):
                    try:
                        os.remove(apk_path)
                    except OSError:
                        pass

        threading.Thread(target=worker, daemon=True).start()

    def _on_fdroid_install_finished(self, success: bool) -> bool:
        if success:
            self.emit(
                "show-message",
                "success",
                _("Success"),
                _("F-Droid installed successfully."),
            )
            self.emit("packages-refresh-requested")
        else:
            self.emit(
                "show-message",
                "error",
                _("Error"),
                _("Failed to install F-Droid."),
            )
        self._finish_operation()
        return False

    def _on_install_finished(self, success: bool, apk_path: str) -> bool:
        if success:
            self.emit(
                "show-message",
                "success",
                _("Success"),
                _('APK "{0}" installed successfully.').format(os.path.basename(apk_path)),
            )
            self.emit("packages-refresh-requested")
        else:
            self.emit(
                "show-message",
                "error",
                _("Error"),
                _('Failed to install "{0}".').format(os.path.basename(apk_path)),
            )
        self._finish_operation()
        return False

    def _finish_operation(self) -> bool:
        self._operation_in_progress = False
        self.emit("busy-changed", False)
        self._sync_controls()
        return False