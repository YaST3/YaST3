"""UI components for the Android module (GTK4)."""

from __future__ import annotations

import threading

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import GLib, Gtk

from mast.core.android import (
    DeviceInfo,
    PackageInfo,
    is_adb_available,
    is_in_blacklist,
    list_devices,
    list_packages,
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
        self.packages_tab.connect("refresh-clicked", lambda _x: self._load_packages())
        self.packages_tab.connect("packages-refresh-requested", lambda _x: self._load_packages())
        self.packages_tab.connect("show-message", self._on_panel_show_message)
        self.packages_tab.connect("busy-changed", self._on_panel_busy_changed)
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
        self.packages_tab.set_selected_device(None)
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
        self.packages_tab.set_selected_device(device)
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
        self.packages_tab.set_busy_state(
            self._busy,
            self.selected_device is not None and self.selected_device.status == "device",
        )

    def _on_panel_show_message(self, _panel, msg_type: str, title: str, message: str) -> None:
        if msg_type == "error":
            self._show_message(Gtk.MessageType.ERROR, title, message)
        else:
            self._show_message(Gtk.MessageType.INFO, title, message)

    def _on_panel_busy_changed(self, _panel, busy: bool) -> None:
        self._set_busy(busy)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.device_panel.refresh_btn.set_sensitive(not busy)
        self.packages_tab.set_busy_state(
            busy,
            self.selected_device is not None and self.selected_device.status == "device",
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
