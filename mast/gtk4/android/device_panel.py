"""Device panel component for the GTK4 Android module."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk

from mast.core.android import DeviceInfo
from mast.core.i18n import _


class DevicePanel(Gtk.Box):
    """Component containing the device list and refresh button."""

    def __init__(self, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8, **kwargs)
        self._build_ui()

    def _build_ui(self) -> None:
        self.set_margin_start(8)
        self.set_margin_top(8)
        self.set_margin_bottom(8)

        device_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        device_header.append(Gtk.Label(label=_("Devices"), xalign=0))

        self.refresh_btn = Gtk.Button(label=_("Refresh"))
        device_header.append(self.refresh_btn)
        self.append(device_header)

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

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(self.device_tree)
        self.append(scrolled)

    def set_devices(self, devices: list[DeviceInfo]) -> None:
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
            self.device_selection.unselect_all()

    def clear(self) -> None:
        self.device_list_store.clear()
        self.device_selection.unselect_all()