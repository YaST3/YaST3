"""Main Android window component for the Android module (Qt6)."""

from __future__ import annotations

import os
import threading

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QTabWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

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

from mast.qt6.android.device_panel import DevicePanel
from mast.qt6.android.packages_tab import PackagesTab


class AndroidWindow(QMainWindow):
    devices_loaded = Signal(list)
    packages_loaded = Signal(list)
    show_message = Signal(str, str, str)
    update_busy = Signal(bool)

    def __init__(self):
        super().__init__()

        self.devices: list[DeviceInfo] = []
        self.packages: list[PackageInfo] = []
        self.selected_device: DeviceInfo | None = None
        self._busy = False

        self.setWindowTitle(_("Android Device Manager"))
        self.setMinimumSize(1280, 720)

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

        # 设备信息 Tab
        self.info_tab = QWidget()
        self.tab_widget.addTab(self.info_tab, _("Device Info"))
        self._build_info_tab()

        # 实例化应用列表 Tab 组件
        self.packages_tab = PackagesTab()
        self.tab_widget.addTab(self.packages_tab, _("Packages"))

    def _build_info_tab(self) -> None:
        layout = QVBoxLayout(self.info_tab)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 16, 16, 16)

        labels = [
            (_("Serial"), 0),
            (_("Name"), 1),
            (_("Model"), 2),
            (_("Manufacturer"), 3),
            (_("Android Version"), 4),
            (_("API Level"), 5),
            (_("Status"), 6),
        ]

        self.info_labels: list[QLabel] = []

        for i, (label_text, _row) in enumerate(labels):
            row_layout = QHBoxLayout()
            label = QLabel(label_text + ":")
            label.setFixedWidth(120)
            row_layout.addWidget(label)
            value_label = QLabel("")
            value_label.setWordWrap(True)
            row_layout.addWidget(value_label)
            self.info_labels.append(value_label)
            layout.addLayout(row_layout)

        layout.addStretch()

    def _connect_signals(self) -> None:
        # 绑定子组件信号
        self.device_panel.refresh_clicked.connect(self._load_devices)
        self.device_panel.device_selection_changed.connect(self._on_device_selected)

        self.packages_tab.search_changed.connect(self._apply_package_filters)
        self.packages_tab.filter_changed.connect(self._apply_package_filters)
        self.packages_tab.uninstall_clicked.connect(self._uninstall_selected)
        self.packages_tab.install_clicked.connect(self._install_apk)
        self.packages_tab.refresh_clicked.connect(self._load_packages)
        self.packages_tab.selection_changed.connect(self._on_package_selected)

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
        for label in self.info_labels:
            label.setText("")
        self.packages_tab.package_table.setRowCount(0)
        self.packages_tab.uninstall_btn.setEnabled(False)

    @Slot(int)
    def _on_device_selected(self, row: int) -> None:
        if row < 0 or row >= len(self.devices):
            self._clear_device_selection()
            return

        device = self.devices[row]
        self.selected_device = device
        self._update_device_info(device)

        if device.status == "device":
            self._load_packages()
        else:
            self.packages_tab.package_table.setRowCount(0)
            self.packages_tab.uninstall_btn.setEnabled(False)

    def _update_device_info(self, device: DeviceInfo) -> None:
        self.info_labels[0].setText(device.serial)
        self.info_labels[1].setText(device.name)
        self.info_labels[2].setText(device.model)
        self.info_labels[3].setText(device.manufacturer)
        self.info_labels[4].setText(device.android_version)
        self.info_labels[5].setText(device.api_level)

        status_text = device.status
        if device.status == "device":
            status_text = _("Connected")
        elif device.status == "offline":
            status_text = _("Offline")
        elif device.status == "unauthorized":
            status_text = _("Unauthorized")
        self.info_labels[6].setText(status_text)

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
                packages.sort(
                    key=lambda p: (not is_in_blacklist(p.package_name), p.package_name.lower())
                )
                self.packages_loaded.emit(packages)
            except Exception as e:
                self.show_message.emit("error", _("Error"), str(e))
            finally:
                self.update_busy.emit(False)

        threading.Thread(target=worker, daemon=True).start()

    @Slot(list)
    def _on_packages_loaded(self, packages: list[PackageInfo]) -> None:
        self.packages = packages
        self._apply_package_filters()

    def _apply_package_filters(self, *_x) -> None:
        search_text = self.packages_tab.search_entry.text().strip().lower()
        show_blacklist = self.packages_tab.blacklist_only.isChecked()
        show_system = self.packages_tab.system_only.isChecked()
        show_user = self.packages_tab.user_only.isChecked()

        table = self.packages_tab.package_table
        table.setRowCount(0)

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

            row = table.rowCount()
            table.insertRow(row)

            pkg_id_item = QTableWidgetItem(pkg.package_name)
            pkg_id_item.setToolTip(pkg.package_name)
            table.setItem(row, 0, pkg_id_item)
            table.setItem(row, 1, QTableWidgetItem(pkg.version_name))
            table.setItem(row, 2, QTableWidgetItem(pkg_type))

        self.packages_tab.uninstall_btn.setEnabled(False)

    def _on_package_selected(self) -> None:
        selected = self.packages_tab.package_table.selectedItems()
        self.packages_tab.uninstall_btn.setEnabled(len(selected) > 0)

    def _uninstall_selected(self) -> None:
        table = self.packages_tab.package_table
        selected = table.selectedItems()
        if not selected:
            return

        row = selected[0].row()
        if row < 0 or row >= table.rowCount():
            return

        pkg_item = table.item(row, 0)
        if pkg_item is None:
            return
        pkg_name = pkg_item.text()
        app_name = pkg_name

        blacklist_info = get_blacklist_info(pkg_name)
        if blacklist_info:
            if is_dangerous(pkg_name):
                msg = _('Are you sure you want to uninstall "{0}" ({1})?\n\nWARNING: This package is marked as dangerous. Uninstalling it may cause system instability or prevent the device from booting!').format(app_name, pkg_name)
            else:
                msg = _('Are you sure you want to uninstall "{0}" ({1})?\n\nThis is a known bloatware package and can be safely removed.').format(app_name, pkg_name)
        else:
            msg = _('Are you sure you want to uninstall "{0}" ({1})?\n\nThis may affect system functionality.').format(app_name, pkg_name)

        reply = QMessageBox.question(
            self,
            _("Uninstall Package"),
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._do_uninstall(pkg_name)

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
                if success:
                    self.show_message.emit("success", _("Success"), _('Package "{0}" uninstalled successfully.').format(pkg_name))
                    self._load_packages()
                else:
                    self.show_message.emit("error", _("Error"), _('Failed to uninstall "{0}". Device may require root access.').format(pkg_name))
            except Exception as e:
                self.show_message.emit("error", _("Error"), str(e))
            finally:
                self.update_busy.emit(False)

        threading.Thread(target=worker, daemon=True).start()

    def _install_apk(self) -> None:
        file_path, _filter = QFileDialog.getOpenFileName(
            self,
            _("Select APK File"),
            "",
            _("APK Files (*.apk);;All Files (*)"),
        )

        if not file_path or not os.path.exists(file_path):
            return

        self._do_install(file_path)

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
                if success:
                    self.show_message.emit("success", _("Success"), _('APK "{0}" installed successfully.').format(os.path.basename(apk_path)))
                    self._load_packages()
                else:
                    self.show_message.emit("error", _("Error"), _('Failed to install "{0}".').format(os.path.basename(apk_path)))
            except Exception as e:
                self.show_message.emit("error", _("Error"), str(e))
            finally:
                self.update_busy.emit(False)

        threading.Thread(target=worker, daemon=True).start()

    @Slot(bool)
    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.device_panel.refresh_btn.setEnabled(not busy)
        self.packages_tab.refresh_pkgs_btn.setEnabled(not busy)
        self.packages_tab.install_btn.setEnabled(not busy and self.selected_device is not None and self.selected_device.status == "device")

    @Slot(str, str, str)
    def _show_message_dialog(self, msg_type: str, title: str, message: str) -> None:
        if msg_type == "error":
            QMessageBox.critical(self, title, message)
        else:
            QMessageBox.information(self, title, message)

    def closeEvent(self, _event) -> None:
        self.deleteLater()