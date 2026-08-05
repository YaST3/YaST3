"""Qt6 Flatpak package management widget."""

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

from mast.core.flatpak import (
    FlatpakPackage,
    list_flatpak_packages,
    list_remote_flatpak_packages,
)
from mast.core.i18n import _
from mast.qt6.command.action import CommandAction


class _RemoteCatalogWorker(QObject):
    """Worker that loads remote package IDs outside the UI thread."""

    loaded = Signal(list)
    failed = Signal(str)

    def __init__(self, remote: str) -> None:
        super().__init__()
        self.remote = remote

    def run(self) -> None:
        try:
            packages = list_remote_flatpak_packages(self.remote)
        except Exception as e:
            self.failed.emit(str(e))
            return

        self.loaded.emit(packages)


class FlatpakPackageManager(QWidget):
    """Manage Flatpak packages in either search or installed mode."""

    DEFAULT_REMOTE = "flathub"
    DEFAULT_SCOPE: Literal["system", "user"] = "system"
    PAGE_SIZE = 100
    MODE_SEARCH: Literal["search"] = "search"
    MODE_INSTALLED: Literal["installed"] = "installed"

    def __init__(self, mode: Literal["search", "installed"], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.mode = mode

        self.remote_packages: list[FlatpakPackage] = []
        self.filtered_remote_packages: list[FlatpakPackage] = []
        self.installed_packages: list[FlatpakPackage] = []
        self.filtered_installed_packages: list[FlatpakPackage] = []
        self.installed_app_ids: set[str] = set()
        self.search_page = 0
        self.installed_page = 0
        self.remote_loading = False
        self.remote_loader_thread: QThread | None = None
        self.remote_loader: _RemoteCatalogWorker | None = None

        layout = QVBoxLayout(self)

        if self.mode == self.MODE_SEARCH:
            self.install_action = CommandAction(
                text=_("Install"),
                running_text=_("Installing package..."),
                dialog_title=_("Install Flatpak Package"),
                command=["true"],
                success_output=_("Package installed successfully."),
                auto_close_on_success=True,
                parent=self,
            )
            self.install_action.triggered.disconnect(self.install_action.start_action)
            self.install_action.triggered.connect(self._on_install_triggered)
            self.install_action.action_finished.connect(self._on_install_finished)
            self._build_search_layout(layout)
        else:
            self.uninstall_action = CommandAction(
                text=_("Uninstall"),
                running_text=_("Removing package..."),
                dialog_title=_("Remove Flatpak Package"),
                command=["true"],
                success_output=_("Package removed successfully."),
                auto_close_on_success=True,
                parent=self,
            )
            self.uninstall_action.triggered.disconnect(self.uninstall_action.start_action)
            self.uninstall_action.triggered.connect(self._on_uninstall_triggered)
            self.uninstall_action.action_finished.connect(self._on_uninstall_finished)
            self._build_installed_layout(layout)

        self._sync_action_buttons()
        self.refresh()

    def _build_search_layout(self, layout: QVBoxLayout) -> None:
        btn_layout = QHBoxLayout()

        self.install_btn = QPushButton(self.install_action.text(), self)
        self.install_btn.clicked.connect(self.install_action.trigger)
        self.install_action.changed.connect(self._sync_action_buttons)
        btn_layout.addWidget(self.install_btn)

        btn_layout.addStretch()

        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("org.example")
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
        self.search_table.setColumnCount(9)
        self.search_table.setHorizontalHeaderLabels(
            [
                _("ID"),
                _("Name"),
                _("Description"),
                _("Version"),
                _("Download Size"),
                _("Branch"),
                _("Remote"),
                _("Scope"),
                _("Installed"),
            ]
        )
        self.search_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.search_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.search_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.search_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.search_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.search_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.search_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.search_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        self.search_table.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeMode.ResizeToContents)
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

        self.uninstall_btn = QPushButton(self.uninstall_action.text(), self)
        self.uninstall_btn.clicked.connect(self.uninstall_action.trigger)
        self.uninstall_action.changed.connect(self._sync_action_buttons)
        btn_layout.addWidget(self.uninstall_btn)

        btn_layout.addStretch()

        self.installed_search_input = QLineEdit(self)
        self.installed_search_input.setPlaceholderText("org.example")
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
        self.installed_table.setColumnCount(8)
        self.installed_table.setHorizontalHeaderLabels(
            [
                _("ID"),
                _("Name"),
                _("Description"),
                _("Version"),
                _("Installed Size"),
                _("Branch"),
                _("Remote"),
                _("Scope"),
            ]
        )
        self.installed_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.installed_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.installed_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.installed_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.installed_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.installed_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.installed_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.installed_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
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
            self.install_btn.setText(self.install_action.text())
            self.install_btn.setEnabled(self.install_action.isEnabled() and not self.remote_loading)
            self.search_btn.setEnabled(not self.remote_loading)
            self.reset_btn.setEnabled(not self.remote_loading)
            self.refresh_catalog_btn.setEnabled(not self.remote_loading)
            return

        self.uninstall_btn.setText(self.uninstall_action.text())
        self.uninstall_btn.setEnabled(self.uninstall_action.isEnabled())

    def _set_remote_loading(self, loading: bool) -> None:
        if self.mode != self.MODE_SEARCH:
            return

        self.remote_loading = loading
        if loading:
            self.refresh_catalog_btn.setText(_("Loading..."))
        else:
            self.refresh_catalog_btn.setText(_("Refresh"))
        self._sync_action_buttons()

    def _selected_app_id(self) -> str:
        if self.mode != self.MODE_SEARCH:
            return ""
        row = self.search_table.currentRow()
        page_items = self._search_page_items()
        if row < 0 or row >= len(page_items):
            return ""
        return page_items[row].app_id

    def _selected_remote(self) -> str:
        if self.mode != self.MODE_SEARCH:
            return self.DEFAULT_REMOTE
        row = self.search_table.currentRow()
        page_items = self._search_page_items()
        if row < 0 or row >= len(page_items):
            return self.DEFAULT_REMOTE
        remote = page_items[row].remote.strip()
        return remote or self.DEFAULT_REMOTE

    def _selected_scope(self) -> Literal["system", "user"]:
        if self.mode != self.MODE_SEARCH:
            return self.DEFAULT_SCOPE
        row = self.search_table.currentRow()
        page_items = self._search_page_items()
        if row < 0 or row >= len(page_items):
            return self.DEFAULT_SCOPE
        return page_items[row].scope

    def _selected_installed_app_id(self) -> str:
        if self.mode != self.MODE_INSTALLED:
            return ""
        row = self.installed_table.currentRow()
        page_items = self._installed_page_items()
        if row < 0 or row >= len(page_items):
            return ""
        return page_items[row].app_id

    def _selected_installed_scope(self) -> Literal["system", "user"]:
        if self.mode != self.MODE_INSTALLED:
            return self.DEFAULT_SCOPE
        row = self.installed_table.currentRow()
        page_items = self._installed_page_items()
        if row < 0 or row >= len(page_items):
            return self.DEFAULT_SCOPE
        return page_items[row].scope

    def _build_install_command(self, app_id: str, remote: str, scope: Literal["system", "user"]) -> list[str]:
        base = ["flatpak", "install", "-y", f"--{scope}", remote, app_id]
        if scope == "system":
            return ["pkexec", *base]
        return base

    def _build_uninstall_command(self, app_id: str, scope: Literal["system", "user"]) -> list[str]:
        base = ["flatpak", "uninstall", "-y", f"--{scope}", app_id]
        if scope == "system":
            return ["pkexec", *base]
        return base

    def _on_install_triggered(self) -> None:
        if self.mode != self.MODE_SEARCH:
            return

        app_id = self._selected_app_id()
        remote = self._selected_remote()
        scope = self._selected_scope()

        if not app_id:
            QMessageBox.information(self, _("Information"), _("Please select a package from the list to install."))
            return

        if app_id in self.installed_app_ids:
            QMessageBox.information(self, _("Information"), _("The selected package is already installed."))
            return

        self.install_action.command = self._build_install_command(app_id, remote, scope)
        self.install_action.start_action()

    def _on_uninstall_triggered(self) -> None:
        if self.mode != self.MODE_INSTALLED:
            return

        app_id = self._selected_installed_app_id()
        scope = self._selected_installed_scope()
        if not app_id:
            QMessageBox.information(self, _("Information"), _("Please select an installed package from the list."))
            return

        reply = QMessageBox.question(
            self,
            _("Confirm"),
            _("Are you sure you want to remove package '{0}'?").format(app_id),
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.uninstall_action.command = self._build_uninstall_command(app_id, scope)
        self.uninstall_action.start_action()

    def _on_install_finished(self, success: bool, error: str, _stdout: str) -> None:
        if self.mode != self.MODE_SEARCH:
            return

        if success:
            self.refresh()
            return

        if error:
            QMessageBox.critical(self, _("Error"), _("Failed to install package: {0}").format(error))

    def _on_uninstall_finished(self, success: bool, error: str, _stdout: str) -> None:
        if self.mode != self.MODE_INSTALLED:
            return

        if success:
            self.refresh()
            return

        if error:
            QMessageBox.critical(self, _("Error"), _("Failed to remove package: {0}").format(error))

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
        if self.mode != self.MODE_SEARCH:
            return

        if self.remote_loader_thread is not None:
            return

        self._set_remote_loading(True)

        self.remote_loader_thread = QThread(self)
        self.remote_loader = _RemoteCatalogWorker(self.DEFAULT_REMOTE)
        self.remote_loader.moveToThread(self.remote_loader_thread)

        self.remote_loader_thread.started.connect(self.remote_loader.run)
        self.remote_loader.loaded.connect(self._on_remote_packages_loaded)
        self.remote_loader.failed.connect(self._on_remote_packages_failed)

        self.remote_loader.loaded.connect(self.remote_loader_thread.quit)
        self.remote_loader.failed.connect(self.remote_loader_thread.quit)
        self.remote_loader.loaded.connect(self.remote_loader.deleteLater)
        self.remote_loader.failed.connect(self.remote_loader.deleteLater)
        self.remote_loader_thread.finished.connect(self.remote_loader_thread.deleteLater)
        self.remote_loader_thread.finished.connect(self._on_remote_loader_finished)

        self.remote_loader_thread.start()

    def _on_remote_packages_loaded(self, packages: list[FlatpakPackage]) -> None:
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
        self.remote_loader_thread = None
        self.remote_loader = None
        self._set_remote_loading(False)

    def load_installed_packages(self, refresh_search_table: bool = True) -> None:
        try:
            self.installed_packages = list_flatpak_packages()
            self.installed_app_ids = {pkg.app_id for pkg in self.installed_packages}
        except Exception as e:
            QMessageBox.critical(self, _("Error"), _("Failed to load Flatpak packages: {0}").format(str(e)))
            self.installed_packages = []
            self.installed_app_ids = set()

        if self.mode == self.MODE_INSTALLED:
            self.filtered_installed_packages = self._filter_packages(
                self.installed_packages,
                self.installed_search_input.text().strip(),
            )
            self.installed_page = 0
            self._populate_installed_table()
            return

        if refresh_search_table:
            self._populate_search_table()

    def _populate_search_table(self) -> None:
        if self.mode != self.MODE_SEARCH:
            return

        page_items = self._search_page_items()
        self.search_table.setRowCount(len(page_items))
        for row, package in enumerate(page_items):
            self.search_table.setItem(row, 0, QTableWidgetItem(package.app_id))
            self.search_table.setItem(row, 1, QTableWidgetItem(package.name))
            self.search_table.setItem(row, 2, QTableWidgetItem(package.description))
            self.search_table.setItem(row, 3, QTableWidgetItem(package.version))
            self.search_table.setItem(row, 4, QTableWidgetItem(package.download_size))
            self.search_table.setItem(row, 5, QTableWidgetItem(package.branch))
            self.search_table.setItem(row, 6, QTableWidgetItem(package.remote))
            self.search_table.setItem(row, 7, QTableWidgetItem(package.scope))
            installed_text = _("Yes") if package.app_id in self.installed_app_ids else _("No")
            self.search_table.setItem(row, 8, QTableWidgetItem(installed_text))

        self._update_search_pager()

    def _populate_installed_table(self) -> None:
        if self.mode != self.MODE_INSTALLED:
            return

        page_items = self._installed_page_items()
        self.installed_table.setRowCount(len(page_items))
        for row, package in enumerate(page_items):
            self.installed_table.setItem(row, 0, QTableWidgetItem(package.app_id))
            self.installed_table.setItem(row, 1, QTableWidgetItem(package.name))
            self.installed_table.setItem(row, 2, QTableWidgetItem(package.description))
            self.installed_table.setItem(row, 3, QTableWidgetItem(package.version))
            self.installed_table.setItem(row, 4, QTableWidgetItem(package.installed_size))
            self.installed_table.setItem(row, 5, QTableWidgetItem(package.branch))
            self.installed_table.setItem(row, 6, QTableWidgetItem(package.remote))
            self.installed_table.setItem(row, 7, QTableWidgetItem(package.scope))

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

    def _search_page_items(self) -> list[FlatpakPackage]:
        start = self.search_page * self.PAGE_SIZE
        end = start + self.PAGE_SIZE
        return self.filtered_remote_packages[start:end]

    def _installed_page_items(self) -> list[FlatpakPackage]:
        start = self.installed_page * self.PAGE_SIZE
        end = start + self.PAGE_SIZE
        return self.filtered_installed_packages[start:end]

    def _update_search_pager(self) -> None:
        total = len(self.filtered_remote_packages)
        total_pages = self._total_pages(total)
        self.search_page = min(self.search_page, total_pages - 1)
        self.search_page_label.setText(f"{self.search_page + 1}/{total_pages}")
        self.search_prev_btn.setEnabled(self.search_page > 0)
        self.search_next_btn.setEnabled(self.search_page + 1 < total_pages)

    def _update_installed_pager(self) -> None:
        total = len(self.filtered_installed_packages)
        total_pages = self._total_pages(total)
        self.installed_page = min(self.installed_page, total_pages - 1)
        self.installed_page_label.setText(f"{self.installed_page + 1}/{total_pages}")
        self.installed_prev_btn.setEnabled(self.installed_page > 0)
        self.installed_next_btn.setEnabled(self.installed_page + 1 < total_pages)

    def _total_pages(self, total_rows: int) -> int:
        if total_rows <= 0:
            return 1
        return (total_rows + self.PAGE_SIZE - 1) // self.PAGE_SIZE

    def _filter_packages(self, packages: list[FlatpakPackage], query: str) -> list[FlatpakPackage]:
        normalized_query = query.strip().lower()
        if not normalized_query:
            return list(packages)

        return [
            package
            for package in packages
            if normalized_query in package.app_id.lower()
            or normalized_query in package.name.lower()
            or normalized_query in package.description.lower()
            or normalized_query in package.version.lower()
            or normalized_query in package.installed_size.lower()
            or normalized_query in package.download_size.lower()
            or normalized_query in package.branch.lower()
            or normalized_query in package.remote.lower()
        ]
