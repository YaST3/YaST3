"""Qt6 Snap package management widget."""

from __future__ import annotations

from typing import Literal

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from mast.core.i18n import _
from mast.core.snap import (
    SnapPackage,
    install_snap_package,
    list_snap_packages,
    search_snap_packages,
    uninstall_snap_package,
)


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


class _SnapActionWorker(QObject):
    """Worker that installs or uninstalls a snap package outside the UI thread."""

    finished = Signal(bool, str)

    def __init__(self, action: str, name: str) -> None:
        super().__init__()
        self.action = action
        self.name = name

    def run(self) -> None:
        try:
            if self.action == "install":
                install_snap_package(self.name)
            else:
                uninstall_snap_package(self.name)
            self.finished.emit(True, "")
        except Exception as e:
            self.finished.emit(False, str(e))


class SnapPackageManager(QWidget):
    """Manage snap packages in either search or installed mode."""

    PAGE_SIZE = 100
    MODE_SEARCH: Literal["search"] = "search"
    MODE_INSTALLED: Literal["installed"] = "installed"

    def __init__(self, mode: Literal["search", "installed"], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.mode = mode

        self.remote_packages: list[SnapPackage] = []
        self.filtered_remote_packages: list[SnapPackage] = []
        self.installed_packages: list[SnapPackage] = []
        self.filtered_installed_packages: list[SnapPackage] = []
        self.installed_names: set[str] = set()
        self.search_page = 0
        self.installed_page = 0
        self.remote_loading = False
        self.catalog_thread: QThread | None = None
        self.catalog_loader: _CatalogWorker | None = None
        self.installed_loading = False
        self.installed_thread: QThread | None = None
        self.installed_loader: _InstalledCatalogWorker | None = None
        self.action_running = False
        self.action_thread: QThread | None = None
        self.action_worker: _SnapActionWorker | None = None

        layout = QVBoxLayout(self)

        if self.mode == self.MODE_SEARCH:
            self._build_search_layout(layout)
        else:
            self._build_installed_layout(layout)

        self._sync_action_buttons()
        self.refresh()

    def _build_search_layout(self, layout: QVBoxLayout) -> None:
        btn_layout = QHBoxLayout()

        self.install_btn = QPushButton(_("Install"), self)
        self.install_btn.clicked.connect(self._on_install_triggered)
        btn_layout.addWidget(self.install_btn)

        btn_layout.addStretch()

        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("firefox")
        self.search_input.returnPressed.connect(self.search_remote)
        btn_layout.addWidget(self.search_input)

        self.search_btn = QPushButton(_("Search"), self)
        self.search_btn.clicked.connect(self.search_remote)
        btn_layout.addWidget(self.search_btn)

        self.reset_btn = QPushButton(_("Reset"), self)
        self.reset_btn.clicked.connect(self.reset_remote_search)
        btn_layout.addWidget(self.reset_btn)

        self.refresh_catalog_btn = QPushButton(_("Refresh"), self)
        self.refresh_catalog_btn.clicked.connect(self.load_remote_packages)
        btn_layout.addWidget(self.refresh_catalog_btn)

        layout.addLayout(btn_layout)

        self.search_table = QTableWidget(self)
        self.search_table.setColumnCount(5)
        self.search_table.setHorizontalHeaderLabels(
            [_("Name"), _("Version"), _("Publisher"), _("Summary"), _("Installed")]
        )
        self.search_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.search_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.search_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.search_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.search_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.search_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.search_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        layout.addWidget(self.search_table)

        pager_row = QHBoxLayout()
        self.search_prev_btn = QPushButton(_("Prev"), self)
        self.search_prev_btn.clicked.connect(self.prev_search_page)
        pager_row.addWidget(self.search_prev_btn)

        self.search_page_label = QLabel(self)
        self.search_page_label.setText("1/1")
        pager_row.addWidget(self.search_page_label)

        self.search_next_btn = QPushButton(_("Next"), self)
        self.search_next_btn.clicked.connect(self.next_search_page)
        pager_row.addWidget(self.search_next_btn)
        pager_row.addStretch()
        layout.addLayout(pager_row)

    def _build_installed_layout(self, layout: QVBoxLayout) -> None:
        btn_layout = QHBoxLayout()

        self.uninstall_btn = QPushButton(_("Uninstall"), self)
        self.uninstall_btn.clicked.connect(self._on_uninstall_triggered)
        btn_layout.addWidget(self.uninstall_btn)

        btn_layout.addStretch()

        self.installed_search_input = QLineEdit(self)
        self.installed_search_input.setPlaceholderText("firefox")
        self.installed_search_input.returnPressed.connect(self.search_installed)
        btn_layout.addWidget(self.installed_search_input)

        self.installed_search_btn = QPushButton(_("Search"), self)
        self.installed_search_btn.clicked.connect(self.search_installed)
        btn_layout.addWidget(self.installed_search_btn)

        self.installed_reset_btn = QPushButton(_("Reset"), self)
        self.installed_reset_btn.clicked.connect(self.reset_installed_search)
        btn_layout.addWidget(self.installed_reset_btn)

        self.refresh_installed_btn = QPushButton(_("Refresh"), self)
        self.refresh_installed_btn.clicked.connect(self.load_installed_packages)
        btn_layout.addWidget(self.refresh_installed_btn)

        layout.addLayout(btn_layout)

        self.installed_table = QTableWidget(self)
        self.installed_table.setColumnCount(5)
        self.installed_table.setHorizontalHeaderLabels(
            [_("Name"), _("Version"), _("Revision"), _("Tracking"), _("Publisher")]
        )
        self.installed_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.installed_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.installed_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.installed_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.installed_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.installed_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.installed_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        layout.addWidget(self.installed_table)

        pager_row = QHBoxLayout()
        self.installed_prev_btn = QPushButton(_("Prev"), self)
        self.installed_prev_btn.clicked.connect(self.prev_installed_page)
        pager_row.addWidget(self.installed_prev_btn)

        self.installed_page_label = QLabel(self)
        self.installed_page_label.setText("1/1")
        pager_row.addWidget(self.installed_page_label)

        self.installed_next_btn = QPushButton(_("Next"), self)
        self.installed_next_btn.clicked.connect(self.next_installed_page)
        pager_row.addWidget(self.installed_next_btn)
        pager_row.addStretch()
        layout.addLayout(pager_row)

    def refresh(self) -> None:
        if self.mode == self.MODE_SEARCH:
            self.load_remote_packages()
            self.load_installed_packages(refresh_search_table=False)
        else:
            self.load_installed_packages(refresh_search_table=False)

    def _sync_action_buttons(self) -> None:
        if self.mode == self.MODE_SEARCH:
            if self.action_running:
                self.install_btn.setText(_("Installing..."))
                self.install_btn.setEnabled(False)
            else:
                self.install_btn.setText(_("Install"))
                self.install_btn.setEnabled(not self.remote_loading and not self.installed_loading)
            self.search_btn.setEnabled(not self.remote_loading and not self.installed_loading and not self.action_running)
            self.reset_btn.setEnabled(not self.remote_loading and not self.installed_loading and not self.action_running)
            self.refresh_catalog_btn.setEnabled(not self.remote_loading and not self.installed_loading and not self.action_running)
            return

        if self.action_running:
            self.uninstall_btn.setText(_("Uninstalling..."))
            self.uninstall_btn.setEnabled(False)
        else:
            self.uninstall_btn.setText(_("Uninstall"))
            self.uninstall_btn.setEnabled(not self.installed_loading)

    def _set_remote_loading(self, loading: bool) -> None:
        if self.mode != self.MODE_SEARCH:
            return

        self.remote_loading = loading
        self.refresh_catalog_btn.setText(_("Loading...") if loading or self.installed_loading else _("Refresh"))
        self._sync_action_buttons()

    def _selected_package_name(self) -> str:
        if self.mode != self.MODE_SEARCH:
            return ""
        row = self.search_table.currentRow()
        page_items = self._search_page_items()
        if row < 0 or row >= len(page_items):
            return ""
        return page_items[row].name

    def _selected_installed_name(self) -> str:
        if self.mode != self.MODE_INSTALLED:
            return ""
        row = self.installed_table.currentRow()
        page_items = self._installed_page_items()
        if row < 0 or row >= len(page_items):
            return ""
        return page_items[row].name

    def _start_action(self, action: str, name: str) -> None:
        if self.action_thread is not None:
            return

        self.action_running = True
        self._sync_action_buttons()

        self.action_thread = QThread(self)
        self.action_worker = _SnapActionWorker(action, name)
        self.action_worker.moveToThread(self.action_thread)

        self.action_thread.started.connect(self.action_worker.run)
        self.action_worker.finished.connect(self._on_action_finished)

        self.action_worker.finished.connect(self.action_thread.quit)
        self.action_worker.finished.connect(self.action_worker.deleteLater)
        self.action_thread.finished.connect(self.action_thread.deleteLater)
        self.action_thread.finished.connect(self._on_action_thread_finished)

        self.action_thread.start()

    def _on_action_finished(self, success: bool, error: str) -> None:
        if success:
            self.refresh()
            return

        if self.mode == self.MODE_SEARCH:
            QMessageBox.critical(self, _("Error"), _("Failed to install package: {0}").format(error))
        else:
            QMessageBox.critical(self, _("Error"), _("Failed to uninstall package: {0}").format(error))

    def _on_action_thread_finished(self) -> None:
        self.action_thread = None
        self.action_worker = None
        self.action_running = False
        self._sync_action_buttons()

    def _on_install_triggered(self) -> None:
        if self.mode != self.MODE_SEARCH:
            return

        name = self._selected_package_name()
        if not name:
            QMessageBox.information(self, _("Information"), _("Please select a package from the list to install."))
            return

        if name in self.installed_names:
            QMessageBox.information(self, _("Information"), _("The selected package is already installed."))
            return

        self._start_action("install", name)

    def _on_uninstall_triggered(self) -> None:
        if self.mode != self.MODE_INSTALLED:
            return

        name = self._selected_installed_name()
        if not name:
            QMessageBox.information(self, _("Information"), _("Please select an installed package from the list."))
            return

        reply = QMessageBox.question(
            self,
            _("Confirm"),
            _("Are you sure you want to uninstall package '{0}'?").format(name),
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._start_action("uninstall", name)

    def search_remote(self) -> None:
        if self.mode != self.MODE_SEARCH:
            return

        query = self.search_input.text().strip()
        self.filtered_remote_packages = self._filter_packages(self.remote_packages, query)
        self.search_page = 0
        self._populate_search_table()

    def reset_remote_search(self) -> None:
        if self.mode != self.MODE_SEARCH:
            return

        self.search_input.clear()
        self.filtered_remote_packages = list(self.remote_packages)
        self.search_page = 0
        self._populate_search_table()

    def search_installed(self) -> None:
        if self.mode != self.MODE_INSTALLED:
            return

        query = self.installed_search_input.text().strip()
        self.filtered_installed_packages = self._filter_packages(self.installed_packages, query)
        self.installed_page = 0
        self._populate_installed_table()

    def reset_installed_search(self) -> None:
        if self.mode != self.MODE_INSTALLED:
            return

        self.installed_search_input.clear()
        self.filtered_installed_packages = list(self.installed_packages)
        self.installed_page = 0
        self._populate_installed_table()

    def load_remote_packages(self) -> None:
        if self.mode != self.MODE_SEARCH or self.catalog_thread is not None:
            return

        self._set_remote_loading(True)

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
        if self.mode != self.MODE_SEARCH:
            return

        self.remote_packages = packages
        self.filtered_remote_packages = self._filter_packages(self.remote_packages, self.search_input.text().strip())
        self.search_page = 0
        self._populate_search_table()

    def _on_remote_packages_failed(self, error: str) -> None:
        if self.mode != self.MODE_SEARCH:
            return

        QMessageBox.critical(self, _("Error"), _("Failed to load package catalog: {0}").format(error))
        self.remote_packages = []
        self.filtered_remote_packages = []
        self.search_page = 0
        self._populate_search_table()

    def _on_remote_loader_finished(self) -> None:
        self.catalog_thread = None
        self.catalog_loader = None
        self._set_remote_loading(False)

    def load_installed_packages(self, refresh_search_table: bool = True) -> None:
        if self.installed_thread is not None:
            return

        self._set_installed_loading(True)

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

    def _set_installed_loading(self, loading: bool) -> None:
        self.installed_loading = loading
        if self.mode == self.MODE_INSTALLED:
            self.refresh_installed_btn.setText(_("Loading...") if loading else _("Refresh"))
        else:
            self.refresh_catalog_btn.setText(_("Loading...") if loading or self.remote_loading else _("Refresh"))
        self._sync_action_buttons()

    def _on_installed_packages_loaded(self, packages: list[SnapPackage]) -> None:
        self.installed_packages = packages
        self.installed_names = {pkg.name for pkg in self.installed_packages}

        if self.mode == self.MODE_INSTALLED:
            self.filtered_installed_packages = self._filter_packages(
                self.installed_packages,
                self.installed_search_input.text().strip(),
            )
            self.installed_page = 0
            self._populate_installed_table()
        else:
            self._populate_search_table()

    def _on_installed_packages_failed(self, error: str) -> None:
        QMessageBox.critical(self, _("Error"), _("Failed to load Snap packages: {0}").format(error))
        self.installed_packages = []
        self.installed_names = set()

        if self.mode == self.MODE_INSTALLED:
            self.filtered_installed_packages = []
            self.installed_page = 0
            self._populate_installed_table()
        else:
            self._populate_search_table()

    def _on_installed_loader_finished(self) -> None:
        self.installed_thread = None
        self.installed_loader = None
        self._set_installed_loading(False)

    def _populate_search_table(self) -> None:
        if self.mode != self.MODE_SEARCH:
            return

        page_items = self._search_page_items()
        self.search_table.setRowCount(len(page_items))
        for row, package in enumerate(page_items):
            self.search_table.setItem(row, 0, QTableWidgetItem(package.name))
            self.search_table.setItem(row, 1, QTableWidgetItem(package.version))
            self.search_table.setItem(row, 2, QTableWidgetItem(package.publisher))
            self.search_table.setItem(row, 3, QTableWidgetItem(package.summary))
            installed_text = _("Yes") if package.name in self.installed_names else _("No")
            self.search_table.setItem(row, 4, QTableWidgetItem(installed_text))

        self._update_search_pager()

    def _populate_installed_table(self) -> None:
        if self.mode != self.MODE_INSTALLED:
            return

        page_items = self._installed_page_items()
        self.installed_table.setRowCount(len(page_items))
        for row, package in enumerate(page_items):
            self.installed_table.setItem(row, 0, QTableWidgetItem(package.name))
            self.installed_table.setItem(row, 1, QTableWidgetItem(package.version))
            self.installed_table.setItem(row, 2, QTableWidgetItem(package.revision))
            self.installed_table.setItem(row, 3, QTableWidgetItem(package.tracking))
            self.installed_table.setItem(row, 4, QTableWidgetItem(package.publisher))

        self._update_installed_pager()

    def prev_search_page(self) -> None:
        if self.search_page <= 0:
            return
        self.search_page -= 1
        self._populate_search_table()

    def next_search_page(self) -> None:
        total_pages = self._total_pages(len(self.filtered_remote_packages))
        if self.search_page + 1 >= total_pages:
            return
        self.search_page += 1
        self._populate_search_table()

    def prev_installed_page(self) -> None:
        if self.installed_page <= 0:
            return
        self.installed_page -= 1
        self._populate_installed_table()

    def next_installed_page(self) -> None:
        total_pages = self._total_pages(len(self.filtered_installed_packages))
        if self.installed_page + 1 >= total_pages:
            return
        self.installed_page += 1
        self._populate_installed_table()

    def _search_page_items(self) -> list[SnapPackage]:
        start = self.search_page * self.PAGE_SIZE
        end = start + self.PAGE_SIZE
        return self.filtered_remote_packages[start:end]

    def _installed_page_items(self) -> list[SnapPackage]:
        start = self.installed_page * self.PAGE_SIZE
        end = start + self.PAGE_SIZE
        return self.filtered_installed_packages[start:end]

    def _update_search_pager(self) -> None:
        total_pages = self._total_pages(len(self.filtered_remote_packages))
        self.search_page = min(self.search_page, total_pages - 1)
        self.search_page_label.setText(f"{self.search_page + 1}/{total_pages}")
        self.search_prev_btn.setEnabled(self.search_page > 0)
        self.search_next_btn.setEnabled(self.search_page + 1 < total_pages)

    def _update_installed_pager(self) -> None:
        total_pages = self._total_pages(len(self.filtered_installed_packages))
        self.installed_page = min(self.installed_page, total_pages - 1)
        self.installed_page_label.setText(f"{self.installed_page + 1}/{total_pages}")
        self.installed_prev_btn.setEnabled(self.installed_page > 0)
        self.installed_next_btn.setEnabled(self.installed_page + 1 < total_pages)

    def _total_pages(self, total_rows: int) -> int:
        if total_rows <= 0:
            return 1
        return (total_rows + self.PAGE_SIZE - 1) // self.PAGE_SIZE

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