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
    get_device_info,
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


class AndroidWindow(Gtk.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.devices: list[DeviceInfo] = []
        self.packages: list[PackageInfo] = []
        self.selected_device: DeviceInfo | None = None
        self._busy = False

        self.info_labels: list[Gtk.Label] = []
        for _ in range(7):
            label = Gtk.Label(label="", xalign=0)
            self.info_labels.append(label)

        self.set_default_size(1280, 720)

        if not is_adb_available():
            self._show_adb_not_found()
            return

        self._build_ui()
        self._load_devices()

    def _build_ui(self) -> None:
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_child(main_box)

        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_position(280)
        main_box.append(paned)

        left_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        left_panel.set_margin_start(8)
        left_panel.set_margin_top(8)
        left_panel.set_margin_bottom(8)
        paned.set_start_child(left_panel)

        device_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        device_header.append(Gtk.Label(label=_("Devices"), xalign=0))
        self.refresh_btn = Gtk.Button(label=_("Refresh"))
        self.refresh_btn.connect("clicked", lambda _: self._load_devices())
        device_header.append(self.refresh_btn)
        left_panel.append(device_header)

        self.device_list_store = Gtk.ListStore(str, str, str)
        self.device_tree = Gtk.TreeView(model=self.device_list_store)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Name"), renderer, text=0)
        column.set_resizable(True)
        self.device_tree.append_column(column)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Model"), renderer, text=1)
        column.set_resizable(True)
        self.device_tree.append_column(column)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Status"), renderer, text=2)
        column.set_resizable(True)
        self.device_tree.append_column(column)

        self.device_selection = self.device_tree.get_selection()
        self.device_selection.set_mode(Gtk.SelectionMode.SINGLE)
        self.device_selection.connect("changed", self._on_device_selected)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(self.device_tree)
        left_panel.append(scrolled)

        self.notebook = Gtk.Notebook()
        paned.set_end_child(self.notebook)

        self.info_tab = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.info_tab.set_margin_start(16)
        self.info_tab.set_margin_end(16)
        self.info_tab.set_margin_top(16)
        self.info_tab.set_margin_bottom(16)
        self.notebook.append_page(self.info_tab, Gtk.Label(label=_("Device Info")))

        self._build_info_tab()

        self.packages_tab = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.packages_tab.set_margin_start(8)
        self.packages_tab.set_margin_end(8)
        self.packages_tab.set_margin_top(8)
        self.packages_tab.set_margin_bottom(8)
        self.notebook.append_page(self.packages_tab, Gtk.Label(label=_("Packages")))

        self._build_packages_tab()

    def _build_info_tab(self) -> None:
        grid = Gtk.Grid(column_spacing=16, row_spacing=8)

        labels = [
            (_("Serial"), 0),
            (_("Name"), 1),
            (_("Model"), 2),
            (_("Manufacturer"), 3),
            (_("Android Version"), 4),
            (_("API Level"), 5),
            (_("Status"), 6),
        ]

        for i, (label_text, row) in enumerate(labels):
            label = Gtk.Label(label=label_text + ":", xalign=0)
            grid.attach(label, 0, row, 1, 1)
            value_label = self.info_labels[i]
            value_label.set_hexpand(True)
            grid.attach(value_label, 1, row, 1, 1)

        self.info_tab.append(grid)
        self.info_tab.append(Gtk.Box(vexpand=True))

    def _build_packages_tab(self) -> None:
        filter_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        self.search_entry = Gtk.Entry()
        self.search_entry.set_placeholder_text(_("Search packages"))
        self.search_entry.set_hexpand(True)
        self.search_entry.connect("changed", self._on_search_changed)
        filter_box.append(self.search_entry)

        self.blacklist_only = Gtk.CheckButton(label=_("Blacklist only"))
        self.blacklist_only.connect("toggled", self._on_search_changed)
        filter_box.append(self.blacklist_only)

        self.system_only = Gtk.CheckButton(label=_("System apps"))
        self.system_only.connect("toggled", self._on_search_changed)
        filter_box.append(self.system_only)

        self.user_only = Gtk.CheckButton(label=_("User apps"))
        self.user_only.connect("toggled", self._on_search_changed)
        filter_box.append(self.user_only)

        self.packages_tab.append(filter_box)

        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        self.uninstall_btn = Gtk.Button(label=_("Uninstall"))
        self.uninstall_btn.connect("clicked", lambda _: self._uninstall_selected())
        self.uninstall_btn.set_sensitive(False)
        action_box.append(self.uninstall_btn)

        self.install_btn = Gtk.Button(label=_("Install APK"))
        self.install_btn.connect("clicked", lambda _: self._install_apk())
        action_box.append(self.install_btn)

        self.refresh_pkgs_btn = Gtk.Button(label=_("Refresh"))
        self.refresh_pkgs_btn.connect("clicked", lambda _: self._load_packages())
        action_box.append(self.refresh_pkgs_btn)

        action_box.append(Gtk.Box(hexpand=True))
        self.packages_tab.append(action_box)

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
        self.package_selection.connect("changed", self._on_package_selected)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(self.package_tree)
        self.packages_tab.append(scrolled)

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
        self.refresh_btn.set_sensitive(False)

        def worker():
            try:
                devices = list_devices()
                # Release busy first so auto-selection can trigger package load.
                GLib.idle_add(self._set_busy, False)
                GLib.idle_add(self._on_devices_loaded, devices)
            except Exception as e:
                GLib.idle_add(self._show_error, str(e))
                GLib.idle_add(self._set_busy, False)

        threading.Thread(target=worker, daemon=True).start()

    def _on_devices_loaded(self, devices: list[DeviceInfo]) -> None:
        self.devices = devices
        self.device_list_store.clear()

        for device in devices:
            status_text = device.status
            if device.status == "device":
                status_text = _("Connected")
            elif device.status == "offline":
                status_text = _("Offline")
            elif device.status == "unauthorized":
                status_text = _("Unauthorized")

            self.device_list_store.append([device.name, device.model, status_text])

        if devices:
            path = Gtk.TreePath.new_from_string("0")
            if path:
                self.device_selection.select_path(path)
        else:
            self._clear_device_selection()

    def _clear_device_selection(self) -> None:
        self.selected_device = None
        for label in self.info_labels:
            label.set_label("")
        self.package_list_store.clear()
        self.uninstall_btn.set_sensitive(False)

    def _on_device_selected(self, _selection) -> None:
        model, tree_iter = self.device_selection.get_selected()
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
        if device.status != "device":
            self.selected_device = device
            self._update_device_info(device)
            self.package_list_store.clear()
            self.uninstall_btn.set_sensitive(False)
            return

        self.selected_device = device
        self._update_device_info(device)
        self._load_packages()

    def _update_device_info(self, device: DeviceInfo) -> None:
        self.info_labels[0].set_label(device.serial)
        self.info_labels[1].set_label(device.name)
        self.info_labels[2].set_label(device.model)
        self.info_labels[3].set_label(device.manufacturer)
        self.info_labels[4].set_label(device.android_version)
        self.info_labels[5].set_label(device.api_level)

        status_text = device.status
        if device.status == "device":
            status_text = _("Connected")
        elif device.status == "offline":
            status_text = _("Offline")
        elif device.status == "unauthorized":
            status_text = _("Unauthorized")
        self.info_labels[6].set_label(status_text)

    def _load_packages(self) -> None:
        if not self.selected_device or self.selected_device.status != "device":
            return

        if self._busy:
            return
        self._busy = True
        self.refresh_pkgs_btn.set_sensitive(False)
        self.install_btn.set_sensitive(False)

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
        search_text = self.search_entry.get_text().strip().lower()
        show_blacklist = self.blacklist_only.get_active()
        show_system = self.system_only.get_active()
        show_user = self.user_only.get_active()

        self.package_list_store.clear()

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

            self.package_list_store.append([
                pkg.package_name,
                pkg.version_name,
                pkg_type,
                pkg.is_system,
                is_in_blacklist(pkg.package_name),
            ])

        self.uninstall_btn.set_sensitive(False)

    def _on_package_selected(self, _selection) -> None:
        model, tree_iter = self.package_selection.get_selected()
        if tree_iter is None:
            self.uninstall_btn.set_sensitive(False)
            return

        path = model.get_path(tree_iter)
        path_str = path.to_string() if path else None
        if not path_str:
            self.uninstall_btn.set_sensitive(False)
            return
        index = int(path_str)

        if index < 0 or index >= len(self.package_list_store):
            self.uninstall_btn.set_sensitive(False)
            return

        self.uninstall_btn.set_sensitive(True)

    def _uninstall_selected(self) -> None:
        model, tree_iter = self.package_selection.get_selected()
        if tree_iter is None:
            return

        path = model.get_path(tree_iter)
        path_str = path.to_string() if path else None
        if not path_str:
            return
        index = int(path_str)

        if index < 0 or index >= len(self.package_list_store):
            return

        pkg_name = self.package_list_store[path][0]
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
        self.refresh_btn.set_sensitive(not busy)
        self.refresh_pkgs_btn.set_sensitive(not busy)
        self.install_btn.set_sensitive(not busy and self.selected_device is not None and self.selected_device.status == "device")

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