"""Device panel component for the GTK4 Android module."""

from __future__ import annotations

import threading

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import GLib, GObject, Gtk

from mast.core.android import DeviceInfo, list_devices
from mast.core.i18n import _


class DevicePanel(Gtk.Box):
    """Component containing the device list and refresh button."""

    __gsignals__ = {
        "selected-device-changed": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (GObject.TYPE_PYOBJECT,),
        ),
        "show-message": (GObject.SignalFlags.RUN_FIRST, None, (str, str, str)),
        "busy-changed": (GObject.SignalFlags.RUN_FIRST, None, (bool,)),
    }

    def __init__(self, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8, **kwargs)
        self._devices: list[DeviceInfo] = []
        self._loading = False
        self._external_busy = False
        self._build_ui()
        self.device_selection.connect("changed", self._on_selection_changed)

    def _build_ui(self) -> None:
        self.set_margin_start(8)
        self.set_margin_top(8)
        self.set_margin_bottom(8)

        device_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        device_header.append(Gtk.Label(label=_("Devices"), xalign=0))

        self.refresh_btn = Gtk.Button(label=_("Refresh"))
        device_header.append(self.refresh_btn)
        self.append(device_header)

        self.device_list_store = Gtk.ListStore(str, str)
        self.device_tree = Gtk.TreeView(model=self.device_list_store)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Name"), renderer, text=0)
        column.set_resizable(True)
        self.device_tree.append_column(column)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Status"), renderer, text=1)
        column.set_resizable(True)
        self.device_tree.append_column(column)

        self.device_selection = self.device_tree.get_selection()
        self.device_selection.set_mode(Gtk.SelectionMode.SINGLE)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(self.device_tree)
        self.append(scrolled)

        self.refresh_btn.connect("clicked", lambda _: self.load_devices())

    def set_external_busy(self, busy: bool) -> None:
        self._external_busy = busy
        self.refresh_btn.set_sensitive(not (self._loading or self._external_busy))

    def load_devices(self) -> None:
        if self._loading or self._external_busy:
            return

        self._loading = True
        self.refresh_btn.set_sensitive(False)
        self.emit("busy-changed", True)

        def worker() -> None:
            try:
                devices = list_devices()
                GLib.idle_add(self.set_devices, devices)
            except Exception as e:
                GLib.idle_add(
                    self.emit,
                    "show-message",
                    "error",
                    _("Error"),
                    str(e),
                )
                GLib.idle_add(self._finish_loading)

        threading.Thread(target=worker, daemon=True).start()

    def set_devices(self, devices: list[DeviceInfo]) -> None:
        self._devices = devices
        self.device_list_store.clear()

        for device in devices:
            status_text = device.status
            if device.status == "device":
                status_text = _("Connected")
            elif device.status == "offline":
                status_text = _("Offline")
            elif device.status == "unauthorized":
                status_text = _("Unauthorized")

            self.device_list_store.append([device.name, f"[{status_text}]"])

        # Release busy before auto-selection so package auto-load is not blocked
        # by window-level busy guards.
        self._finish_loading()

        if devices:
            path = Gtk.TreePath.new_from_string("0")
            if path:
                self.device_selection.select_path(path)
        else:
            self.emit("selected-device-changed", None)

        return False

    def _finish_loading(self) -> bool:
        self._loading = False
        self.refresh_btn.set_sensitive(not self._external_busy)
        self.emit("busy-changed", False)
        return False

    def _on_selection_changed(self, selection) -> None:
        model, tree_iter = selection.get_selected()
        if tree_iter is None:
            self.emit("selected-device-changed", None)
            return

        path = model.get_path(tree_iter)
        path_str = path.to_string() if path else None
        if not path_str:
            self.emit("selected-device-changed", None)
            return

        index = int(path_str)
        if index < 0 or index >= len(self._devices):
            self.emit("selected-device-changed", None)
            return

        self.emit("selected-device-changed", self._devices[index])

    def clear(self) -> None:
        self._devices = []
        self.device_list_store.clear()
        self.device_selection.unselect_all()