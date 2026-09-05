"""Qt6 Build Service search window."""

from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QHBoxLayout, QHeaderView, QLineEdit, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from mast.core.buildservice import BuildServicePackage, build_install_command, search_packages
from mast.core.i18n import _
from mast.qt6.command.action import CommandAction


class _SearchWorker(QObject):
    loaded = Signal(list)
    failed = Signal(str)

    def __init__(self, query: str) -> None:
        super().__init__()
        self.query = query

    def run(self) -> None:
        try:
            self.loaded.emit(search_packages(self.query))
        except Exception as error:
            self.failed.emit(str(error))


class BuildServiceWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.resize(1200, 720)
        self.packages: list[BuildServicePackage] = []
        self.search_thread: QThread | None = None
        self.worker: _SearchWorker | None = None
        self.install_action: CommandAction | None = None

        layout = QVBoxLayout(self)
        controls = QHBoxLayout()
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText(_("Package name"))
        self.search_input.returnPressed.connect(self.search)
        controls.addWidget(self.search_input)
        self.search_btn = QPushButton(_("Search"), self)
        self.search_btn.clicked.connect(self.search)
        controls.addWidget(self.search_btn)
        self.install_btn = QPushButton(_("Install"), self)
        self.install_btn.setEnabled(False)
        self.install_btn.clicked.connect(self.install_selected)
        controls.addWidget(self.install_btn)
        layout.addLayout(controls)

        self.table = QTableWidget(self)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([_("Name"), _("Version"), _("Architecture"), _("Project")])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.itemSelectionChanged.connect(lambda: self.install_btn.setEnabled(self.table.currentRow() >= 0))
        layout.addWidget(self.table)

    def search(self) -> None:
        query = self.search_input.text().strip()
        if not query or self.search_thread is not None:
            return
        self.search_btn.setEnabled(False)
        self.install_btn.setEnabled(False)
        self.table.setRowCount(0)
        self.search_thread = QThread(self)
        self.worker = _SearchWorker(query)
        self.worker.moveToThread(self.search_thread)
        self.search_thread.started.connect(self.worker.run)
        self.worker.loaded.connect(self._show_results)
        self.worker.failed.connect(self._show_error)
        self.worker.loaded.connect(self._finish_search)
        self.worker.failed.connect(self._finish_search)
        self.search_thread.finished.connect(self.search_thread.deleteLater)
        self.search_thread.start()

    def _finish_search(self, *_args) -> None:
        if self.search_thread is not None:
            self.search_thread.quit()
        self.search_thread = None
        self.worker = None
        self.search_btn.setEnabled(True)

    def _show_results(self, packages: list[BuildServicePackage]) -> None:
        self.packages = packages
        self.table.setRowCount(len(packages))
        for row, package in enumerate(packages):
            values = [package.name, f"{package.version}-{package.release}", package.arch, package.project]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 3:
                    item.setForeground(QColor(self._project_color(package.project)))
                self.table.setItem(row, column, item)

    @staticmethod
    def _project_color(project: str) -> str:
        if project.startswith("openSUSE:"):
            return "green"
        if project.startswith(("home:", "isv:")):
            return "red"
        return "orange"

    def _show_error(self, message: str) -> None:
        QMessageBox.critical(self, _("Error"), _("Build Service search failed: {0}").format(message))

    def install_selected(self) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self.packages) or self.install_action is not None:
            return
        package = self.packages[row]
        self.install_action = CommandAction(
            text=_("Install"), running_text=_("Installing..."), dialog_title=_("Install Package"),
            command=build_install_command(package), success_output=_("Package installed successfully."),
            auto_close_on_success=True, parent=self,
        )
        self.install_action.action_finished.connect(lambda *_args: self._clear_install_action())
        self.install_action.trigger()

    def _clear_install_action(self) -> None:
        self.install_action = None
