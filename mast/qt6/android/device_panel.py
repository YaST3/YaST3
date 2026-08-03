"""Device panel component for Android module."""

from __future__ import annotations

import threading

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from mast.core.android import DeviceInfo, list_devices
from mast.core.i18n import _


class DevicePanel(QWidget):
    """Component containing the device list and refresh button."""

    devices_loaded = Signal(list)
    selected_device_changed = Signal(object)
    show_message = Signal(str, str, str)
    busy_changed = Signal(bool)
    device_selection_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._devices: list[DeviceInfo] = []
        self._loading = False
        self._external_busy = False
        self._init_ui()
        self.devices_loaded.connect(self.set_devices)

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)

        header_layout = QHBoxLayout()
        device_label = QLabel(_("Devices"))
        header_layout.addWidget(device_label)
        header_layout.addStretch()

        self.refresh_btn = QPushButton(_("Refresh"))
        header_layout.addWidget(self.refresh_btn)
        layout.addLayout(header_layout)

        self.device_list = QListWidget()
        self.device_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        layout.addWidget(self.device_list)

        # 连接内部信号到自定义信号
        self.refresh_btn.clicked.connect(self.load_devices)
        self.device_list.currentRowChanged.connect(self.device_selection_changed)
        self.device_list.currentRowChanged.connect(self._on_row_changed)

    def set_external_busy(self, busy: bool) -> None:
        self._external_busy = busy
        self.refresh_btn.setEnabled(not (self._loading or self._external_busy))

    def load_devices(self) -> None:
        if self._loading or self._external_busy:
            return

        self._loading = True
        self.refresh_btn.setEnabled(False)
        self.busy_changed.emit(True)

        def worker() -> None:
            try:
                devices = list_devices()
                self.devices_loaded.emit(devices)
            except Exception as e:
                self.show_message.emit("error", _("Error"), str(e))
                self.busy_changed.emit(False)

        threading.Thread(target=worker, daemon=True).start()

    def set_devices(self, devices: list[DeviceInfo]) -> None:
        self._devices = devices
        self.device_list.clear()

        for device in devices:
            status_text = device.status
            if device.status == "device":
                status_text = _("Connected")
            elif device.status == "offline":
                status_text = _("Offline")
            elif device.status == "unauthorized":
                status_text = _("Unauthorized")

            item_text = f"{device.name} [{status_text}]"
            item = QListWidgetItem(item_text)
            self.device_list.addItem(item)

        # Release busy before auto-selection so package auto-load is not blocked
        # by window-level busy guards.
        self._loading = False
        self.refresh_btn.setEnabled(not self._external_busy)
        self.busy_changed.emit(False)

        if devices:
            self.device_list.setCurrentRow(0)
        else:
            self.selected_device_changed.emit(None)

    def _on_row_changed(self, row: int) -> None:
        if row < 0 or row >= len(self._devices):
            self.selected_device_changed.emit(None)
            return
        self.selected_device_changed.emit(self._devices[row])