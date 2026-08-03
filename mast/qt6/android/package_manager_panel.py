"""Package manager panel component for Android module."""

from __future__ import annotations

import os
import tempfile
import threading
import urllib.request

import adbutils

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from mast.core.android import (
    DeviceInfo,
    PackageInfo,
    get_blacklist_info,
    is_dangerous,
    is_in_blacklist,
)
from mast.core.i18n import _


def _install_apk_with_adbutils(serial: str, apk_path: str) -> bool:
    try:
        adbutils.adb.device(serial=serial).install(apk_path, silent=True, flags=["-r"])
        return True
    except Exception:
        return False


def _uninstall_package_with_adbutils(
    serial: str, package_name: str, keep_data: bool = False
) -> bool:
    args = ["pm", "uninstall"]
    if keep_data:
        args.append("-k")
    args.append(package_name)

    try:
        output = str(adbutils.adb.device(serial=serial).shell(args, timeout=60)).strip()
        return "Success" in output
    except Exception:
        return False


class PackageManagerPanel(QWidget):
    """Component for managing and displaying package lists and filters."""

    refresh_clicked = Signal()
    show_message = Signal(str, str, str)
    busy_changed = Signal(bool)
    packages_refresh_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._packages: list[PackageInfo] = []
        self._device: DeviceInfo | None = None
        self._fdroid_installed: bool | None = None
        self._external_busy = False
        self._operation_in_progress = False
        self._init_ui()
        self._connect_signals()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)

        filter_layout = QHBoxLayout()

        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText(_("Search"))
        filter_layout.addWidget(self.search_entry)

        filter_layout.addStretch()

        self.blacklist_only = QCheckBox(_("Blacklist only"))
        filter_layout.addWidget(self.blacklist_only)

        self.system_only = QCheckBox(_("System apps"))
        filter_layout.addWidget(self.system_only)

        self.user_only = QCheckBox(_("User apps"))
        filter_layout.addWidget(self.user_only)

        layout.addLayout(filter_layout)

        action_layout = QHBoxLayout()

        self.uninstall_btn = QPushButton(_("Uninstall"))
        self.uninstall_btn.setEnabled(False)
        action_layout.addWidget(self.uninstall_btn)

        self.install_btn = QPushButton(_("Install APK"))
        action_layout.addWidget(self.install_btn)

        self.install_fdroid_btn = QPushButton(_("Install F-Droid"))
        self.install_fdroid_btn.setVisible(False)
        action_layout.addWidget(self.install_fdroid_btn)

        self.refresh_pkgs_btn = QPushButton(_("Refresh"))
        action_layout.addWidget(self.refresh_pkgs_btn)

        action_layout.addStretch()
        layout.addLayout(action_layout)

        self.package_table = QTableWidget()
        self.package_table.setColumnCount(3)
        self.package_table.setHorizontalHeaderLabels([_("ID"), _("Version"), _("Type")])
        self.package_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.package_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.package_table.setWordWrap(False)
        self.package_table.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.package_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.package_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.package_table)

    def _connect_signals(self) -> None:
        self.search_entry.textChanged.connect(self._apply_filters)
        self.blacklist_only.stateChanged.connect(self._apply_filters)
        self.system_only.stateChanged.connect(self._apply_filters)
        self.user_only.stateChanged.connect(self._apply_filters)
        self.uninstall_btn.clicked.connect(self._uninstall_selected)
        self.install_btn.clicked.connect(self._install_apk)
        self.install_fdroid_btn.clicked.connect(self._install_fdroid)
        self.refresh_pkgs_btn.clicked.connect(self.refresh_clicked)
        self.package_table.itemSelectionChanged.connect(self._update_selection_state)

    def set_selected_device(self, device: DeviceInfo | None) -> None:
        new_device = device if device and device.status == "device" else None
        prev_serial = self._device.serial if self._device is not None else None
        new_serial = new_device.serial if new_device is not None else None
        if prev_serial != new_serial:
            self._fdroid_installed = None
        self._device = new_device
        self._sync_controls()

    def set_packages(self, packages: list[PackageInfo]) -> None:
        self._packages = sorted(
            packages,
            key=lambda p: (not is_in_blacklist(p.package_name), p.package_name.lower()),
        )
        self._fdroid_installed = any(
            pkg.package_name == "org.fdroid.fdroid" for pkg in self._packages
        )
        self._apply_filters()
        self._sync_controls()

    def clear_packages(self) -> None:
        self._packages = []
        self._fdroid_installed = None
        self.package_table.setRowCount(0)
        self.uninstall_btn.setEnabled(False)
        self._sync_controls()

    def selected_package_name(self) -> str | None:
        selected = self.package_table.selectedItems()
        if not selected:
            return None

        row = selected[0].row()
        if row < 0 or row >= self.package_table.rowCount():
            return None

        item = self.package_table.item(row, 0)
        if item is None:
            return None
        return item.text()

    def set_busy_state(self, busy: bool, has_selected_device: bool) -> None:
        self._external_busy = busy
        if not has_selected_device:
            self._device = None
        self._sync_controls()

    def _apply_filters(self, *_args) -> None:
        search_text = self.search_entry.text().strip().lower()
        show_blacklist = self.blacklist_only.isChecked()
        show_system = self.system_only.isChecked()
        show_user = self.user_only.isChecked()

        self.package_table.setRowCount(0)

        for pkg in self._packages:
            if show_blacklist and not is_in_blacklist(pkg.package_name):
                continue

            if show_system and show_user:
                pass
            elif show_system and not pkg.is_system:
                continue
            elif show_user and pkg.is_system:
                continue

            if search_text and search_text not in pkg.package_name.lower():
                continue

            pkg_type = _("System") if pkg.is_system else _("User")
            if is_in_blacklist(pkg.package_name):
                pkg_type = _("Blacklist")

            row = self.package_table.rowCount()
            self.package_table.insertRow(row)

            pkg_id_item = QTableWidgetItem(pkg.package_name)
            pkg_id_item.setToolTip(pkg.package_name)
            self.package_table.setItem(row, 0, pkg_id_item)
            self.package_table.setItem(row, 1, QTableWidgetItem(pkg.version_name))
            self.package_table.setItem(row, 2, QTableWidgetItem(pkg_type))

        self.uninstall_btn.setEnabled(False)

    def _update_selection_state(self) -> None:
        self._sync_controls()

    def _sync_controls(self) -> None:
        busy = self._external_busy or self._operation_in_progress
        has_device = self._device is not None

        self.refresh_pkgs_btn.setEnabled(not busy)
        self.install_btn.setEnabled(not busy and has_device)
        should_show_fdroid = has_device and self._fdroid_installed is False
        self.install_fdroid_btn.setVisible(should_show_fdroid)
        self.install_fdroid_btn.setEnabled(not busy and should_show_fdroid)
        self.uninstall_btn.setEnabled(
            not busy and has_device and self.selected_package_name() is not None
        )

    def _install_fdroid(self) -> None:
        if self._device is None:
            return
        if self._operation_in_progress:
            return
        if self._fdroid_installed is True:
            return

        self._operation_in_progress = True
        self._sync_controls()
        self.busy_changed.emit(True)

        serial = self._device.serial

        def worker() -> None:
            apk_path = ""
            try:
                with tempfile.NamedTemporaryFile(
                    prefix="fdroid-", suffix=".apk", delete=False
                ) as tmp:
                    apk_path = tmp.name

                with urllib.request.urlopen("https://f-droid.org/F-Droid.apk", timeout=60) as response:
                    with open(apk_path, "wb") as out_file:
                        out_file.write(response.read())

                success = _install_apk_with_adbutils(serial, apk_path)
                if success:
                    self.show_message.emit(
                        "success",
                        _("Success"),
                        _("F-Droid installed successfully."),
                    )
                    self.packages_refresh_requested.emit()
                else:
                    self.show_message.emit(
                        "error",
                        _("Error"),
                        _("Failed to install F-Droid."),
                    )
            except Exception as e:
                self.show_message.emit("error", _("Error"), str(e))
            finally:
                if apk_path and os.path.exists(apk_path):
                    try:
                        os.remove(apk_path)
                    except OSError:
                        pass
                self._operation_in_progress = False
                self.busy_changed.emit(False)

    def _uninstall_selected(self) -> None:
        if self._device is None:
            return

        pkg_name = self.selected_package_name()
        if not pkg_name:
            return

        blacklist_info = get_blacklist_info(pkg_name)
        app_name = pkg_name
        if blacklist_info:
            if is_dangerous(pkg_name):
                msg = _(
                    'Are you sure you want to uninstall "{0}" ({1})?\n\nWARNING: This package is marked as dangerous. Uninstalling it may cause system instability or prevent the device from booting!'
                ).format(app_name, pkg_name)
            else:
                msg = _(
                    'Are you sure you want to uninstall "{0}" ({1})?\n\nThis is a known bloatware package and can be safely removed.'
                ).format(app_name, pkg_name)
        else:
            msg = _(
                'Are you sure you want to uninstall "{0}" ({1})?\n\nThis may affect system functionality.'
            ).format(app_name, pkg_name)

        reply = QMessageBox.question(
            self,
            _("Uninstall Package"),
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._do_uninstall(pkg_name)

    def _do_uninstall(self, pkg_name: str) -> None:
        if self._device is None:
            return
        if self._operation_in_progress:
            return

        self._operation_in_progress = True
        self._sync_controls()
        self.busy_changed.emit(True)

        serial = self._device.serial

        def worker() -> None:
            try:
                success = _uninstall_package_with_adbutils(serial, pkg_name)
                if success:
                    self.show_message.emit(
                        "success",
                        _("Success"),
                        _('Package "{0}" uninstalled successfully.').format(pkg_name),
                    )
                    self.packages_refresh_requested.emit()
                else:
                    self.show_message.emit(
                        "error",
                        _("Error"),
                        _('Failed to uninstall "{0}". Device may require root access.').format(
                            pkg_name
                        ),
                    )
            except Exception as e:
                self.show_message.emit("error", _("Error"), str(e))
            finally:
                self._operation_in_progress = False
                self.busy_changed.emit(False)

        threading.Thread(target=worker, daemon=True).start()

    def _install_apk(self) -> None:
        if self._device is None:
            return
        if self._operation_in_progress:
            return

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
        if self._device is None:
            return
        if self._operation_in_progress:
            return

        self._operation_in_progress = True
        self._sync_controls()
        self.busy_changed.emit(True)

        serial = self._device.serial

        def worker() -> None:
            try:
                success = _install_apk_with_adbutils(serial, apk_path)
                if success:
                    self.show_message.emit(
                        "success",
                        _("Success"),
                        _('APK "{0}" installed successfully.').format(
                            os.path.basename(apk_path)
                        ),
                    )
                    self.packages_refresh_requested.emit()
                else:
                    self.show_message.emit(
                        "error",
                        _("Error"),
                        _('Failed to install "{0}".').format(os.path.basename(apk_path)),
                    )
            except Exception as e:
                self.show_message.emit("error", _("Error"), str(e))
            finally:
                self._operation_in_progress = False
                self.busy_changed.emit(False)

        threading.Thread(target=worker, daemon=True).start()