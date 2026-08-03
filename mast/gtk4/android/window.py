"""UI components for the Android module (GTK4)."""

from __future__ import annotations

import os
import threading

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import GLib, Gtk

from mast.core.android import (
    DeviceInfo,
    PackageInfo,
    get_blacklist_info,
    install_apk,
    is_adb_available,
    is_dangerous,
    is_in_blacklist,
    list_devices,
    list_packages,
    uninstall_package,
)
from mast.core.i18n import _
from mast.gtk4.android.device_info_panel import DeviceInfoPanel
from mast.gtk4.android.device_panel import DevicePanel
from mast.gtk4.android.package_manager_panel import PackageManagerPanel


class AndroidWindow(Gtk.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.devices: list[DeviceInfo] = []
        self.packages: list[PackageInfo] = []
        self.selected_device: DeviceInfo | None = None
        self._busy = False

        self.set_default_size(1280, 720)

        if not is_adb_available():
            self._show_adb_not_found()
            return

        self._build_ui()
        self._connect_signals()
        self._load_devices()

    def _build_ui(self) -> None:
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_child(main_box)

        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_position(280)
        main_box.append(paned)

        self.device_panel = DevicePanel()
        paned.set_start_child(self.device_panel)

        self.notebook = Gtk.Notebook()
        paned.set_end_child(self.notebook)

        self.device_info_panel = DeviceInfoPanel()
        self.notebook.append_page(self.device_info_panel, Gtk.Label(label=_("Device Info")))

        self.packages_tab = PackageManagerPanel()
        self.notebook.append_page(self.packages_tab, Gtk.Label(label=_("Packages")))

    def _connect_signals(self) -> None:
        self.device_panel.refresh_btn.connect("clicked", lambda _: self._load_devices())
        self.device_panel.device_selection.connect("changed", self._on_device_selected)

        self.packages_tab.search_entry.connect("changed", self._on_search_changed)
        self.packages_tab.blacklist_only.connect("toggled", self._on_search_changed)
        self.packages_tab.system_only.connect("toggled", self._on_search_changed)
        self.packages_tab.user_only.connect("toggled", self._on_search_changed)
        self.packages_tab.uninstall_btn.connect("clicked", lambda _: self._uninstall_selected())
        self.packages_tab.install_btn.connect("clicked", lambda _: self._install_apk())
        self.packages_tab.refresh_pkgs_btn.connect("clicked", lambda _: self._load_packages())
        self.packages_tab.package_selection.connect("changed", self._on_package_selected)

    def _show_adb_not_found(self) -> None:
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content.set_margin_start(32)
        content.set_margin_end(32)
        content.set_margin_top(32)
        content.set_margin_bottom(32)

        icon = Gtk.Image.new_from_icon_name("dialog-error")
        icon.set_pixel_size(64)
        content.append(icon)

        label = Gtk.Label(label=_("ADB Not Found"))
        label.set_wrap(True)
        label.set_justify(Gtk.Justification.CENTER)
        content.append(label)

        desc = Gtk.Label(label=_("ADB (Android Debug Bridge) is not installed or not in PATH. Please install Android SDK platform tools."))
        desc.set_wrap(True)
        desc.set_justify(Gtk.Justification.CENTER)
        content.append(desc)

        self.set_child(content)

    def _load_devices(self) -> None:
        if self._busy:
            return
        self._busy = True
        self.device_panel.refresh_btn.set_sensitive(False)

        def worker():
            try:
                devices = list_devices()
                GLib.idle_add(self._set_busy, False)
                GLib.idle_add(self._on_devices_loaded, devices)
            except Exception as e:
                GLib.idle_add(self._show_error, str(e))
                GLib.idle_add(self._set_busy, False)

        threading.Thread(target=worker, daemon=True).start()

    def _on_devices_loaded(self, devices: list[DeviceInfo]) -> None:
        self.devices = devices
        self.device_panel.set_devices(devices)

        if not devices:
            self._clear_device_selection()

    def _clear_device_selection(self) -> None:
        self.selected_device = None
        self.device_info_panel.clear()
        self.packages_tab.clear_packages()

    def _on_device_selected(self, _selection) -> None:
        model, tree_iter = self.device_panel.device_selection.get_selected()
        if tree_iter is None:
            self._clear_device_selection()
            return

        path = model.get_path(tree_iter)
        path_str = path.to_string() if path else None
        if not path_str:
            self._clear_device_selection()
            return

        index = int(path_str)
        if index < 0 or index >= len(self.devices):
            self._clear_device_selection()
            return

        device = self.devices[index]
        self.selected_device = device
        self._update_device_info(device)

        if device.status == "device":
            self._load_packages()
        else:
            self.packages_tab.clear_packages()

    def _update_device_info(self, device: DeviceInfo) -> None:
        self.device_info_panel.set_device(device)

    def _load_packages(self) -> None:
        if not self.selected_device or self.selected_device.status != "device":
            return

        if self._busy:
            return
        self._busy = True
        self.packages_tab.refresh_pkgs_btn.set_sensitive(False)
        self.packages_tab.install_btn.set_sensitive(False)

        device = self.selected_device

        def worker():
            try:
                packages = list_packages(device.serial)
                packages.sort(
                    key=lambda p: (not is_in_blacklist(p.package_name), p.package_name.lower())
                )
                GLib.idle_add(self._on_packages_loaded, packages)
            except Exception as e:
                GLib.idle_add(self._show_error, str(e))
            finally:
                GLib.idle_add(self._set_busy, False)

        threading.Thread(target=worker, daemon=True).start()

    def _on_packages_loaded(self, packages: list[PackageInfo]) -> None:
        self.packages = packages
        self._apply_package_filters()

    def _on_search_changed(self, _widget) -> None:
        self._apply_package_filters()

    def _apply_package_filters(self) -> None:
        search_text = self.packages_tab.search_entry.get_text().strip().lower()
        show_blacklist = self.packages_tab.blacklist_only.get_active()
        show_system = self.packages_tab.system_only.get_active()
        show_user = self.packages_tab.user_only.get_active()

        self.packages_tab.package_list_store.clear()

        for pkg in self.packages:
            if show_blacklist and not is_in_blacklist(pkg.package_name):
                continue

            if show_system and show_user:
                pass
            elif show_system and not pkg.is_system:
                continue
            elif show_user and pkg.is_system:
                continue

            if search_text:
                haystack = pkg.package_name.lower()
                if search_text not in haystack:
                    continue

            pkg_type = _("System") if pkg.is_system else _("User")
            if is_in_blacklist(pkg.package_name):
                pkg_type = _("Blacklist")

            self.packages_tab.package_list_store.append([
                pkg.package_name,
                pkg.version_name,
                pkg_type,
                pkg.is_system,
                is_in_blacklist(pkg.package_name),
            ])

        self.packages_tab.uninstall_btn.set_sensitive(False)

    def _on_package_selected(self, _selection) -> None:
        model, tree_iter = self.packages_tab.package_selection.get_selected()
        if tree_iter is None:
            self.packages_tab.uninstall_btn.set_sensitive(False)
            return

        path = model.get_path(tree_iter)
        path_str = path.to_string() if path else None
        if not path_str:
            self.packages_tab.uninstall_btn.set_sensitive(False)
            return

        index = int(path_str)
        if index < 0 or index >= len(self.packages_tab.package_list_store):
            self.packages_tab.uninstall_btn.set_sensitive(False)
            return

        self.packages_tab.uninstall_btn.set_sensitive(True)

    def _uninstall_selected(self) -> None:
        model, tree_iter = self.packages_tab.package_selection.get_selected()
        if tree_iter is None:
            return

        path = model.get_path(tree_iter)
        path_str = path.to_string() if path else None
        if not path_str:
            return

        index = int(path_str)
        if index < 0 or index >= len(self.packages_tab.package_list_store):
            return

        pkg_name = self.packages_tab.package_list_store[path][0]
        app_name = pkg_name

        dialog = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=_("Uninstall Package"),
        )

        blacklist_info = get_blacklist_info(pkg_name)
        if blacklist_info:
            if is_dangerous(pkg_name):
                secondary = _('Are you sure you want to uninstall "{0}" ({1})?\n\nWARNING: This package is marked as dangerous. Uninstalling it may cause system instability or prevent the device from booting!').format(app_name, pkg_name)
            else:
                secondary = _('Are you sure you want to uninstall "{0}" ({1})?\n\nThis is a known bloatware package and can be safely removed.').format(app_name, pkg_name)
        else:
            secondary = _('Are you sure you want to uninstall "{0}" ({1})?\n\nThis may affect system functionality.').format(app_name, pkg_name)

        dialog.set_property("secondary-text", secondary)

        def on_response(d, response):
            if response == Gtk.ResponseType.YES:
                self._do_uninstall(pkg_name)
            d.destroy()

        dialog.connect("response", on_response)
        dialog.present()

    def _do_uninstall(self, pkg_name: str) -> None:
        device = self.selected_device
        if not device:
            return

        if self._busy:
            return
        self._busy = True

        def worker():
            try:
                success = uninstall_package(device.serial, pkg_name)
                GLib.idle_add(self._on_uninstall_done, success, pkg_name)
            except Exception as e:
                GLib.idle_add(self._show_error, str(e))
            finally:
                GLib.idle_add(self._set_busy, False)

        threading.Thread(target=worker, daemon=True).start()

    def _on_uninstall_done(self, success: bool, pkg_name: str) -> None:
        if success:
            self._show_message(Gtk.MessageType.INFO, _("Success"), _('Package "{0}" uninstalled successfully.').format(pkg_name))
            self._load_packages()
        else:
            self._show_message(Gtk.MessageType.ERROR, _("Error"), _('Failed to uninstall "{0}". Device may require root access.').format(pkg_name))

    def _install_apk(self) -> None:
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

        dialog.open(self, None, on_response)

    def _do_install(self, apk_path: str) -> None:
        device = self.selected_device
        if not device:
            return

        if self._busy:
            return
        self._busy = True

        def worker():
            try:
                success = install_apk(device.serial, apk_path)
                GLib.idle_add(self._on_install_done, success, apk_path)
            except Exception as e:
                GLib.idle_add(self._show_error, str(e))
            finally:
                GLib.idle_add(self._set_busy, False)

        threading.Thread(target=worker, daemon=True).start()

    def _on_install_done(self, success: bool, apk_path: str) -> None:
        if success:
            self._show_message(Gtk.MessageType.INFO, _("Success"), _('APK "{0}" installed successfully.').format(os.path.basename(apk_path)))
            self._load_packages()
        else:
            self._show_message(Gtk.MessageType.ERROR, _("Error"), _('Failed to install "{0}".').format(os.path.basename(apk_path)))

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.device_panel.refresh_btn.set_sensitive(not busy)
        self.packages_tab.refresh_pkgs_btn.set_sensitive(not busy)
        self.packages_tab.install_btn.set_sensitive(
            not busy and self.selected_device is not None and self.selected_device.status == "device"
        )

    def _show_error(self, message: str) -> None:
        self._show_message(Gtk.MessageType.ERROR, _("Error"), message)

    def _show_message(self, msg_type: Gtk.MessageType, title: str, message: str) -> None:
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
