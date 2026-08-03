"""Main Android window component for the Android module (Qt6)."""

from __future__ import annotations

import threading

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from mast.core.android import (
    DeviceInfo,
    is_adb_available,
    list_devices,
    list_packages,
)
from mast.core.i18n import _

from mast.qt6.android.device_panel import DevicePanel
from mast.qt6.android.device_info_panel import DeviceInfoPanel
from mast.qt6.android.package_manager_panel import PackageManagerPanel


class AndroidWindow(QMainWindow):
    devices_loaded = Signal(list)
    packages_loaded = Signal(list)
    show_message = Signal(str, str, str)
    update_busy = Signal(bool)

    def __init__(self):
        super().__init__()

        self.devices: list[DeviceInfo] = []
        self.selected_device: DeviceInfo | None = None
        self._busy = False

        self.setMinimumSize(960, 640)

        if not is_adb_available():
            self._show_adb_not_found()
            return

        self._build_ui()
        self._connect_signals()
        self._load_devices()

    def _build_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setHandleWidth(10)
        main_layout.addWidget(splitter)

        # 实例化左侧设备面板组件
        self.device_panel = DevicePanel()
        splitter.addWidget(self.device_panel)

        self.tab_widget = QTabWidget()
        splitter.addWidget(self.tab_widget)

        # 设备信息组件
        self.device_info_panel = DeviceInfoPanel()
        self.tab_widget.addTab(self.device_info_panel, _("Device Info"))

        # 软件包管理组件
        self.packages_tab = PackageManagerPanel()
        self.tab_widget.addTab(self.packages_tab, _("Packages"))

    def _connect_signals(self) -> None:
        # 绑定子组件信号
        self.device_panel.refresh_clicked.connect(self._load_devices)
        self.device_panel.device_selection_changed.connect(self._on_device_selected)

        self.packages_tab.refresh_clicked.connect(self._load_packages)
        self.packages_tab.packages_refresh_requested.connect(self._load_packages)
        self.packages_tab.show_message.connect(self._show_message_dialog)
        self.packages_tab.busy_changed.connect(self._set_busy)

        # 绑定内部异步/跨线程信号
        self.devices_loaded.connect(self._on_devices_loaded)
        self.packages_loaded.connect(self._on_packages_loaded)
        self.show_message.connect(self._show_message_dialog)
        self.update_busy.connect(self._set_busy)

    def _show_adb_not_found(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(16)
        layout.setContentsMargins(32, 32, 32, 32)

        label = QLabel(_("ADB Not Found"))
        label.setStyleSheet("font-size: 18pt; font-weight: bold;")
        layout.addWidget(label)

        desc = QLabel(_("ADB (Android Debug Bridge) is not installed or not in PATH. Please install Android SDK platform tools."))
        desc.setWordWrap(True)
        layout.addWidget(desc)

    def _load_devices(self) -> None:
        if self._busy:
            return
        self._busy = True
        self.device_panel.refresh_btn.setEnabled(False)

        def worker():
            try:
                devices = list_devices()
                # Release busy first so auto-selection can trigger package load.
                self.update_busy.emit(False)
                self.devices_loaded.emit(devices)
            except Exception as e:
                self.show_message.emit("error", _("Error"), str(e))
                self.update_busy.emit(False)

        threading.Thread(target=worker, daemon=True).start()

    @Slot(list)
    def _on_devices_loaded(self, devices: list[DeviceInfo]) -> None:
        self.devices = devices
        self.device_panel.device_list.clear()

        for device in devices:
            status_text = device.status
            if device.status == "device":
                status_text = _("Connected")
            elif device.status == "offline":
                status_text = _("Offline")
            elif device.status == "unauthorized":
                status_text = _("Unauthorized")

            item_text = f"{device.name} ({device.model}) - {status_text}"
            item = QListWidgetItem(item_text)
            self.device_panel.device_list.addItem(item)

        if devices:
            self.device_panel.device_list.setCurrentRow(0)
        else:
            self._clear_device_selection()

    def _clear_device_selection(self) -> None:
        self.selected_device = None
        self.device_info_panel.clear()
        self.packages_tab.set_selected_device(None)
        self.packages_tab.clear_packages()

    @Slot(int)
    def _on_device_selected(self, row: int) -> None:
        if row < 0 or row >= len(self.devices):
            self._clear_device_selection()
            return

        device = self.devices[row]
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
        self.packages_tab.refresh_pkgs_btn.setEnabled(False)
        self.packages_tab.install_btn.setEnabled(False)

        device = self.selected_device

        def worker():
            try:
                packages = list_packages(device.serial)
                self.packages_loaded.emit(packages)
            except Exception as e:
                self.show_message.emit("error", _("Error"), str(e))
            finally:
                self.update_busy.emit(False)

        threading.Thread(target=worker, daemon=True).start()

    @Slot(list)
    def _on_packages_loaded(self, packages: list) -> None:
        self.packages_tab.set_packages(packages)

    @Slot(bool)
    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.device_panel.refresh_btn.setEnabled(not busy)
        has_selected_device = (
            self.selected_device is not None and self.selected_device.status == "device"
        )
        self.packages_tab.set_busy_state(busy, has_selected_device)

    @Slot(str, str, str)
    def _show_message_dialog(self, msg_type: str, title: str, message: str) -> None:
        if msg_type == "error":
            QMessageBox.critical(self, title, message)
        else:
            QMessageBox.information(self, title, message)

    def closeEvent(self, _event) -> None:
        self.deleteLater()