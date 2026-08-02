"""Device information panel for Android module."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from mast.core.android import DeviceInfo
from mast.core.i18n import _


class DeviceInfoPanel(QWidget):
    """Component for displaying selected device information."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._info_labels: list[QLabel] = []
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 16, 16, 16)

        labels = [
            _("Serial"),
            _("Name"),
            _("Model"),
            _("Manufacturer"),
            _("Android Version"),
            _("API Level"),
            _("Status"),
        ]

        for label_text in labels:
            row_layout = QHBoxLayout()
            label = QLabel(label_text + ":")
            label.setFixedWidth(120)
            row_layout.addWidget(label)

            value_label = QLabel("")
            value_label.setWordWrap(True)
            row_layout.addWidget(value_label)
            self._info_labels.append(value_label)

            layout.addLayout(row_layout)

        layout.addStretch()

    def clear(self) -> None:
        for label in self._info_labels:
            label.setText("")

    def set_device(self, device: DeviceInfo) -> None:
        self._info_labels[0].setText(device.serial)
        self._info_labels[1].setText(device.name)
        self._info_labels[2].setText(device.model)
        self._info_labels[3].setText(device.manufacturer)
        self._info_labels[4].setText(device.android_version)
        self._info_labels[5].setText(device.api_level)

        status_text = device.status
        if device.status == "device":
            status_text = _("Connected")
        elif device.status == "offline":
            status_text = _("Offline")
        elif device.status == "unauthorized":
            status_text = _("Unauthorized")

        self._info_labels[6].setText(status_text)