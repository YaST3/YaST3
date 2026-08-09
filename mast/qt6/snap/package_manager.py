"""Qt6 Snap package management widget."""

from __future__ import annotations

from typing import Literal

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
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

from mast.core.i18n import _
from mast.core.snap import SnapPackage, list_snap_packages, search_snap_packages
from mast.qt6.command.action import CommandAction
from mast.qt6.snap.settings import SnapSettingsDialog


FILTER_ALL: Literal["all"] = "all"
FILTER_INSTALLED: Literal["installed"] = "installed"


def _make_transparent_icon(size: int = 16) -> QIcon:
    """Create a transparent placeholder icon for consistent column alignment."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    return QIcon(pixmap)


class _CatalogWorker(QObject):
    """Worker that loads snap package search results outside the UI thread."""

    loaded = Signal(list)
    failed = Signal(str)

    def __init__(self, query: str) -> None:
        super().__init__()
        self.query = query

    def run(self) -> None:
        try:
            packages = search_snap_packages(self.query)
        except Exception as e:
            self.failed.emit(str(e))
            return

        self.loaded.emit(packages)


class _InstalledCatalogWorker(QObject):
    """Worker that loads installed snap packages outside the UI thread."""

    loaded = Signal(list)
    failed = Signal(str)

    def run(self) -> None:
        try:
            packages = list_snap_packages()
        except Exception as e:
            self.failed.emit(str(e))
            return

        self.loaded.emit(packages)


class SnapPackageManager(QWidget):
    """Manage snap packages with an All/Installed filter."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.remote_packages: list[SnapPackage] = []
        self.filtered_remote_packages: list[SnapPackage] = []
        self.installed_packages: list[SnapPackage] = []
        self.filtered_installed_packages: list[SnapPackage] = []
        self.installed_names: set[str] = set()
        self.current_filter: Literal["all", "installed"] = FILTER_ALL
        self.remote_loading = False
        self.catalog_thread: QThread | None = None
        self.catalog_loader: _CatalogWorker | None = None
        self.installed_loading = False
        self.installed_thread: QThread | None = None
        self.installed_loader: _InstalledCatalogWorker | None = None
        self.action: CommandAction | None = None

        layout = QVBoxLayout(self)
        self._build_layout(layout)

        self._sync_action_buttons()
        self.refresh()

    def _build_layout(self, layout: QVBoxLayout) -> None:
        btn_layout = QHBoxLayout()

        self.primary_btn = QPushButton(_("Install"), self)
        self.primary_btn.setEnabled(False)
        self.primary_btn.clicked.connect(self._on_primary_triggered)
        btn_layout.addWidget(self.primary_btn)

        self.update_btn = QPushButton(_("Update"), self)
        self.update_btn.setEnabled(False)
        self.update_btn.clicked.connect(self._on_update_triggered)
        btn_layout.addWidget(self.update_btn)

        self.update_all_btn = QPushButton(_("Update All"), self)
        self.update_all_btn.setEnabled(False)
        self.update_all_btn.clicked.connect(self._on_update_all_triggered)
        btn_layout.addWidget(self.update_all_btn)

        btn_layout.addStretch()

        self.filter_combo = QComboBox(self)
        self.filter_combo.addItem(_("All"), FILTER_ALL)
        self.filter_combo.addItem(_("Installed"), FILTER_INSTALLED)
        self.filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        btn_layout.addWidget(self.filter_combo)

        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText(_("Search"))
        self.search_input.setClearButtonEnabled(True)
        self.search_input.returnPressed.connect(self._on_search_triggered)
        btn_layout.addWidget(self.search_input)

        self.search_btn = QPushButton(_("Search"), self)
        self.search_btn.clicked.connect(self._on_search_triggered)
        btn_layout.addWidget(self.search_btn)

        self.settings_btn = QPushButton(_("Settings"), self)
        self.settings_btn.clicked.connect(self._on_settings_clicked)
        btn_layout.addWidget(self.settings_btn)

        layout.addLayout(btn_layout)

        self.table = QTableWidget(self)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            [_("Name"), _("Version"), _("Size"), _("Publisher"), _("Summary"), _("Installed")]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setColumnWidth(1, 80)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.table)

    def refresh(self) -> None:
        self.load_remote_packages()
        self.load_installed_packages()

    def _is_busy(self) -> bool:
        return self.remote_loading or self.installed_loading or (self.action is not None and self.action.is_running())

    def _updatable_names(self) -> set[str]:
        installed_versions = {p.name: p.version for p in self.installed_packages}
        remote_versions = {p.name: p.version for p in self.remote_packages}
        updatable: set[str] = set()
        for name, v in installed_versions.items():
            if name in remote_versions and remote_versions[name] != v:
                updatable.add(name)
        return updatable

    def _selected_status(self) -> str:
        package = self._selected_package()
        if package is None:
            return "not_installed"
        installed_versions = {p.name: p.version for p in self.installed_packages}
        remote_versions = {p.name: p.version for p in self.remote_packages}
        return self._compute_status(package.name, installed_versions, remote_versions)

    def _sync_action_buttons(self) -> None:
        is_loading = self.remote_loading or self.installed_loading
        is_busy = self._is_busy()

        status = self._selected_status()
        if status == "not_installed":
            self.primary_btn.setText(_("Install"))
            self.primary_btn.setEnabled(not is_busy and self._selected_package() is not None)
        else:
            self.primary_btn.setText(_("Uninstall"))
            self.primary_btn.setEnabled(not is_busy)

        self.update_btn.setEnabled(not is_busy and status == "updatable")

        updatable_count = len(self._updatable_names())
        self.update_all_btn.setEnabled(not is_busy and updatable_count > 0)
        self.update_all_btn.setText(
            _("Update All ({0})").format(updatable_count) if updatable_count > 0 else _("Update All")
        )

        self.search_btn.setEnabled(not is_busy)
        self.settings_btn.setEnabled(not is_busy)
        self.filter_combo.setEnabled(not is_busy)
        self.search_btn.setText(_("Loading...") if is_loading else _("Search"))

    def _on_selection_changed(self) -> None:
        self._sync_action_buttons()

    def _selected_package(self) -> SnapPackage | None:
        row = self.table.currentRow()
        items = self._current_items()
        if row < 0 or row >= len(items):
            return None
        return items[row]

    def _current_items(self) -> list[SnapPackage]:
        if self.current_filter == FILTER_ALL:
            return self.filtered_remote_packages
        return self.filtered_installed_packages

    def _start_action(self, action: str, name: str = "") -> None:
        if self.action is not None and self.action.is_running():
            return

        if action == "refresh":
            cmd: list[str]
            if name:
                cmd = ["pkexec", "snap", "refresh", name]
                success_text = _("Package updated successfully.")
                title = _("Update Package")
            else:
                cmd = ["pkexec", "snap", "refresh"]
                success_text = _("All packages updated successfully.")
                title = _("Update All Packages")
            self.action = CommandAction(
                text=_("Update"),
                running_text=_("Updating..."),
                dialog_title=title,
                command=cmd,
                success_output=success_text,
                auto_close_on_success=True,
                parent=self,
            )
        else:
            is_install = action == "install"
            self.action = CommandAction(
                text=_("Install") if is_install else _("Uninstall"),
                running_text=_("Installing...") if is_install else _("Uninstalling..."),
                dialog_title=_("Install Package") if is_install else _("Uninstall Package"),
                command=["pkexec", "snap", "install" if is_install else "remove", name],
                success_output=_("Package installed successfully.") if is_install else _("Package uninstalled successfully."),
                auto_close_on_success=True,
                parent=self,
            )
        self.action.action_finished.connect(self._on_action_finished)
        self.action.trigger()
        self._sync_action_buttons()

    def _on_action_finished(self, success: bool, error: str, _stdout: str) -> None:
        self.action = None
        if success:
            self.refresh()
            return

        package = self._selected_package()
        is_uninstall_error = package is not None and package.name in self.installed_names
        if is_uninstall_error:
            QMessageBox.critical(self, _("Error"), _("Failed to uninstall package: {0}").format(error))
        else:
            QMessageBox.critical(self, _("Error"), _("Failed to install package: {0}").format(error))
        self._sync_action_buttons()

    def _on_primary_triggered(self) -> None:
        package = self._selected_package()
        if package is None:
            QMessageBox.information(self, _("Information"), _("Please select a package from the list."))
            return

        is_installed = package.name in self.installed_names
        if is_installed:
            reply = QMessageBox.question(
                self,
                _("Confirm"),
                _("Are you sure you want to uninstall package '{0}'?").format(package.name),
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            self._start_action("uninstall", package.name)
        else:
            self._start_action("install", package.name)

    def _on_update_triggered(self) -> None:
        package = self._selected_package()
        if package is None:
            return
        if self._selected_status() != "updatable":
            return
        self._start_action("refresh", package.name)

    def _on_update_all_triggered(self) -> None:
        if not self._updatable_names():
            return
        self._start_action("refresh")

    def _on_filter_changed(self, _index: int) -> None:
        data = self.filter_combo.currentData()
        if data in (FILTER_ALL, FILTER_INSTALLED):
            self.current_filter = data  # type: ignore[assignment]
        self._populate_table()
        self._sync_action_buttons()

    def _on_search_triggered(self) -> None:
        self.refresh()

    def _on_settings_clicked(self) -> None:
        dialog = SnapSettingsDialog(self.window())
        dialog.exec()

    def load_remote_packages(self) -> None:
        if self.catalog_thread is not None:
            return

        self.remote_loading = True
        self._sync_action_buttons()

        self.catalog_thread = QThread(self)
        self.catalog_loader = _CatalogWorker(self.search_input.text().strip())
        self.catalog_loader.moveToThread(self.catalog_thread)

        self.catalog_thread.started.connect(self.catalog_loader.run)
        self.catalog_loader.loaded.connect(self._on_remote_packages_loaded)
        self.catalog_loader.failed.connect(self._on_remote_packages_failed)

        self.catalog_loader.loaded.connect(self.catalog_thread.quit)
        self.catalog_loader.failed.connect(self.catalog_thread.quit)
        self.catalog_loader.loaded.connect(self.catalog_loader.deleteLater)
        self.catalog_loader.failed.connect(self.catalog_loader.deleteLater)
        self.catalog_thread.finished.connect(self.catalog_thread.deleteLater)
        self.catalog_thread.finished.connect(self._on_remote_loader_finished)

        self.catalog_thread.start()

    def _on_remote_packages_loaded(self, packages: list[SnapPackage]) -> None:
        self.remote_packages = packages
        self.filtered_remote_packages = self._filter_packages(self.remote_packages, self.search_input.text().strip())
        self._populate_table()

    def _on_remote_packages_failed(self, error: str) -> None:
        QMessageBox.critical(self, _("Error"), _("Failed to load package catalog: {0}").format(error))
        self.remote_packages = []
        self.filtered_remote_packages = []
        self._populate_table()

    def _on_remote_loader_finished(self) -> None:
        self.catalog_thread = None
        self.catalog_loader = None
        self.remote_loading = False
        self._sync_action_buttons()

    def load_installed_packages(self) -> None:
        if self.installed_thread is not None:
            return

        self.installed_loading = True
        self._sync_action_buttons()

        self.installed_thread = QThread(self)
        self.installed_loader = _InstalledCatalogWorker()
        self.installed_loader.moveToThread(self.installed_thread)

        self.installed_thread.started.connect(self.installed_loader.run)
        self.installed_loader.loaded.connect(self._on_installed_packages_loaded)
        self.installed_loader.failed.connect(self._on_installed_packages_failed)

        self.installed_loader.loaded.connect(self.installed_thread.quit)
        self.installed_loader.failed.connect(self.installed_thread.quit)
        self.installed_loader.loaded.connect(self.installed_loader.deleteLater)
        self.installed_loader.failed.connect(self.installed_loader.deleteLater)
        self.installed_thread.finished.connect(self.installed_thread.deleteLater)
        self.installed_thread.finished.connect(self._on_installed_loader_finished)

        self.installed_thread.start()

    def _on_installed_packages_loaded(self, packages: list[SnapPackage]) -> None:
        self.installed_packages = packages
        self.installed_names = {pkg.name for pkg in self.installed_packages}
        self.filtered_installed_packages = self._filter_packages(
            self.installed_packages,
            self.search_input.text().strip(),
        )
        self._populate_table()

    def _on_installed_packages_failed(self, error: str) -> None:
        QMessageBox.critical(self, _("Error"), _("Failed to load packages: {0}").format(error))
        self.installed_packages = []
        self.installed_names = set()
        self.filtered_installed_packages = []
        self._populate_table()

    def _on_installed_loader_finished(self) -> None:
        self.installed_thread = None
        self.installed_loader = None
        self.installed_loading = False
        self._sync_action_buttons()

    def _populate_table(self) -> None:
        items = self._current_items()
        self.table.setRowCount(len(items))
        installed_versions = {p.name: p.version for p in self.installed_packages}
        remote_versions = {p.name: p.version for p in self.remote_packages}
        for row, package in enumerate(items):
            self.table.setItem(row, 0, QTableWidgetItem(package.name))
            self.table.setItem(row, 1, QTableWidgetItem(package.version))
            self.table.setItem(row, 2, QTableWidgetItem(package.size))
            self.table.setItem(row, 3, self._make_publisher_item(package))
            self.table.setItem(row, 4, QTableWidgetItem(package.summary))
            self.table.setItem(row, 5, self._make_installed_item(
                package.name, installed_versions, remote_versions
            ))
        self._sync_action_buttons()

    @staticmethod
    def _compute_status(name: str, installed_versions: dict[str, str], remote_versions: dict[str, str]) -> str:
        """Compute install status: 'installed', 'updatable', or 'not_installed'."""
        if name not in installed_versions:
            return "not_installed"
        if name in remote_versions and remote_versions[name] != installed_versions[name]:
            return "updatable"
        return "installed"

    @classmethod
    def _make_installed_item(cls, name, installed_versions, remote_versions) -> QTableWidgetItem:
        """Build the Installed cell with status text and color."""
        status = cls._compute_status(name, installed_versions, remote_versions)
        if status == "installed":
            item = QTableWidgetItem(_("Yes"))
            item.setForeground(QColor("#22c55e"))
        elif status == "updatable":
            item = QTableWidgetItem(_("Update"))
            item.setForeground(QColor("#f97316"))
        else:
            item = QTableWidgetItem(_("No"))
        return item

    @staticmethod
    def _make_publisher_item(package: SnapPackage) -> QTableWidgetItem:
        """Build the Publisher cell, showing a verified/star marker when applicable."""
        validation = package.publisher_validation
        if validation == "verified":
            item = QTableWidgetItem(package.publisher)
            item.setIcon(QIcon.fromTheme("data-success"))
            item.setToolTip(_("Verified Account"))
            return item
        if validation == "starred":
            item = QTableWidgetItem(package.publisher)
            item.setIcon(QIcon.fromTheme("preferences-desktop-default-applications"))
            item.setToolTip(_("Star Developer"))
            return item
        item = QTableWidgetItem(package.publisher)
        item.setIcon(_make_transparent_icon())
        return item

    def _filter_packages(self, packages: list[SnapPackage], query: str) -> list[SnapPackage]:
        normalized_query = query.strip().lower()
        if not normalized_query:
            return list(packages)

        return [
            package
            for package in packages
            if normalized_query in package.name.lower()
            or normalized_query in package.version.lower()
            or normalized_query in package.publisher.lower()
            or normalized_query in package.summary.lower()
            or normalized_query in package.revision.lower()
            or normalized_query in package.tracking.lower()
        ]
