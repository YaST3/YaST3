"""Device panel component for Android module."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from mast.core.i18n import _


class DevicePanel(QWidget):
    """Component containing the device list and refresh button."""

    refresh_clicked = Signal()
    device_selection_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

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
        self.refresh_btn.clicked.connect(self.refresh_clicked)
        self.device_list.currentRowChanged.connect(self.device_selection_changed)