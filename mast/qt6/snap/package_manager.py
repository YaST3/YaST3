"""Qt6 Snap package management widget."""

from __future__ import annotations

from typing import Literal

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
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


FILTER_ALL: Literal["all"] = "all"
FILTER_INSTALLED: Literal["installed"] = "installed"


def _resolve_icon(names: tuple[str, ...]) -> QIcon | None:
    """Return the first available themed icon from *names*, or ``None``."""
    for name in names:
        icon = QIcon.fromTheme(name)
        if not icon.isNull():
            return icon
    return None


def _make_verified_icon(size: int = 16) -> QIcon:
    """Render a green checkmark icon for verified publishers."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor("#22c55e"))
    pen.setWidth(2)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    painter.drawLine(3, 8, 6, 11)
    painter.drawLine(6, 11, 13, 4)
    painter.end()
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

        btn_layout.addStretch()

        self.filter_combo = QComboBox(self)
        self.filter_combo.addItem(_("All"), FILTER_ALL)
        self.filter_combo.addItem(_("Installed"), FILTER_INSTALLED)
        self.filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        btn_layout.addWidget(self.filter_combo)

        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("firefox")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.returnPressed.connect(self._on_search_triggered)
        btn_layout.addWidget(self.search_input)

        self.search_btn = QPushButton(_("Search"), self)
        self.search_btn.clicked.connect(self._on_search_triggered)
        btn_layout.addWidget(self.search_btn)

        layout.addLayout(btn_layout)

        self.table = QTableWidget(self)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            [_("Name"), _("Version"), _("Publisher"), _("Summary"), _("Installed")]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.table)

    def refresh(self) -> None:
        self.load_remote_packages()
        self.load_installed_packages()

    def _is_busy(self) -> bool:
        return self.remote_loading or self.installed_loading or (self.action is not None and self.action.is_running())

    def _sync_action_buttons(self) -> None:
        is_loading = self.remote_loading or self.installed_loading
        is_busy = self._is_busy()

        package = self._selected_package()
        if package is None:
            self.primary_btn.setText(_("Install"))
            self.primary_btn.setEnabled(False)
        else:
            is_installed = package.name in self.installed_names
            self.primary_btn.setText(_("Uninstall") if is_installed else _("Install"))
            self.primary_btn.setEnabled(not is_busy)

        self.search_btn.setEnabled(not is_busy)
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

    def _start_action(self, action: str, name: str) -> None:
        if self.action is not None and self.action.is_running():
            return

        is_install = action == "install"
        self.action = CommandAction(
            text=_("Install") if is_install else _("Uninstall"),
            running_text=_("Installing...") if is_install else _("Uninstalling..."),
            dialog_title=_("Install Snap Package") if is_install else _("Uninstall Snap Package"),
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

    def _on_filter_changed(self, _index: int) -> None:
        data = self.filter_combo.currentData()
        if data in (FILTER_ALL, FILTER_INSTALLED):
            self.current_filter = data  # type: ignore[assignment]
        self._populate_table()
        self._sync_action_buttons()

    def _on_search_triggered(self) -> None:
        self.refresh()

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
        QMessageBox.critical(self, _("Error"), _("Failed to load Snap packages: {0}").format(error))
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
        for row, package in enumerate(items):
            self.table.setItem(row, 0, QTableWidgetItem(package.name))
            self.table.setItem(row, 1, QTableWidgetItem(package.version))
            self.table.setItem(row, 2, self._make_publisher_item(package))
            self.table.setItem(row, 3, QTableWidgetItem(package.summary))
            installed_text = _("Yes") if package.name in self.installed_names else _("No")
            self.table.setItem(row, 4, QTableWidgetItem(installed_text))
        self._sync_action_buttons()

    @staticmethod
    def _make_publisher_item(package: SnapPackage) -> QTableWidgetItem:
        """Build the Publisher cell, showing a verified/star marker when applicable."""
        validation = package.publisher_validation
        if validation == "verified":
            item = QTableWidgetItem(package.publisher)
            item.setIcon(_make_verified_icon())
            item.setToolTip(_("Verified Account"))
            return item
        if validation == "star-developer":
            icon = _resolve_icon(("starred", "star", "emblem-favorite"))
            text = package.publisher if icon is not None else f"★ {package.publisher}"
            item = QTableWidgetItem(text)
            if icon is not None:
                item.setIcon(icon)
            item.setToolTip(_("Star Developer"))
            return item
        return QTableWidgetItem(package.publisher)

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
