"""Device information panel for the GTK4 Android module."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk

from mast.core.android import DeviceInfo
from mast.core.i18n import _


class DeviceInfoPanel(Gtk.Box):
    """Component for displaying selected device information."""

    def __init__(self, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=16, **kwargs)
        self.info_labels: list[Gtk.Label] = []
        self._build_ui()

    def _build_ui(self) -> None:
        self.set_margin_start(16)
        self.set_margin_end(16)
        self.set_margin_top(16)
        self.set_margin_bottom(16)

        grid = Gtk.Grid(column_spacing=16, row_spacing=8)

        labels = [
            _("Serial"),
            _("Name"),
            _("Code Name"),
            _("Model"),
            _("Manufacturer"),
            _("Android Version"),
            _("API Level"),
            _("Status"),
        ]

        for i, label_text in enumerate(labels):
            label = Gtk.Label(label=label_text + ":", xalign=0)
            grid.attach(label, 0, i, 1, 1)

            value_label = Gtk.Label(label="", xalign=0)
            value_label.set_hexpand(True)
            grid.attach(value_label, 1, i, 1, 1)
            self.info_labels.append(value_label)

        self.append(grid)
        self.append(Gtk.Box(vexpand=True))

    def clear(self) -> None:
        for label in self.info_labels:
            label.set_label("")

    def set_device(self, device: DeviceInfo) -> None:
        self.info_labels[0].set_label(device.serial)
        self.info_labels[1].set_label(device.name)
        self.info_labels[2].set_label(device.code_name)
        self.info_labels[3].set_label(device.model)
        self.info_labels[4].set_label(device.manufacturer)
        self.info_labels[5].set_label(device.android_version)
        self.info_labels[6].set_label(device.api_level)

        status_text = device.status
        if device.status == "device":
            status_text = _("Connected")
        elif device.status == "offline":
            status_text = _("Offline")
        elif device.status == "unauthorized":
            status_text = _("Unauthorized")

        self.info_labels[7].set_label(status_text)