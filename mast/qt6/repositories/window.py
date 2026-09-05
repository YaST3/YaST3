"""UI components for the Repositories module."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QHeaderView,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from mast.core.i18n import _
from mast.core.repositories import (
    RepoEntry,
    delete_repo_entry,
    load_repos,
    save_repo_entry,
    switch_mirror_pkexec,
)
from mast.qt6.repositories.import_repo_button import ImportRepoButton
from mast.qt6.repositories.repo_edit_dialog import RepoEditDialog
from mast.qt6.repositories.switch_mirror_dialog import SwitchMirrorDialog


class RepositoriesWindow(QMainWindow):
    closed = Signal()

    def __init__(self):
        super().__init__()
        self.resize(1200, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        button_layout = QHBoxLayout()
        self.add_btn = QPushButton(_("Add"))
        self.add_btn.clicked.connect(self.add_repo)
        button_layout.addWidget(self.add_btn)

        self.import_btn = ImportRepoButton(self)
        self.import_btn.repo_selected.connect(self.import_third_party_repo)
        button_layout.addWidget(self.import_btn)

        self.edit_btn = QPushButton(_("Edit"))
        self.edit_btn.clicked.connect(self.edit_repo)
        button_layout.addWidget(self.edit_btn)

        self.delete_btn = QPushButton(_("Delete"))
        self.delete_btn.clicked.connect(self.delete_repo)
        button_layout.addWidget(self.delete_btn)

        self.switch_mirror_btn = QPushButton(_("Switch Mirror"))
        self.switch_mirror_btn.clicked.connect(self.switch_mirror_action)
        button_layout.addWidget(self.switch_mirror_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            [_("Name"), _("URL"), _("Priority"), _("Enabled"), _("Auto Refresh")]
        )

        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Fixed
        )
        self.table.setColumnWidth(
            0, self.table.fontMetrics().horizontalAdvance("M") * 32
        )
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Fixed
        )
        self.table.setColumnWidth(2, 60)
        self.table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.Fixed
        )
        self.table.setColumnWidth(3, 60)
        self.table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.ResizeMode.Fixed
        )
        self.table.setColumnWidth(4, 80)

        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        layout.addWidget(self.table)

        self.repo_entries: list[RepoEntry] = []
        self.load_repos()

    def import_third_party_repo(self, entry: RepoEntry) -> None:
        if any(entry.id == existing_entry.id for existing_entry in self.repo_entries):
            QMessageBox.information(
                self,
                _("Information"),
                _("Repository '{}' already exists.").format(entry.name),
            )
            return

        result = save_repo_entry(entry)
        if result != "ok":
            QMessageBox.critical(
                self, _("Error"), _("Failed to import repository: %s") % result
            )
            return

        QMessageBox.information(
            self,
            _("Success"),
            _("Repository '{}' imported successfully.").format(entry.name),
        )
        self.load_repos()

    def load_repos(self) -> None:
        self.repo_entries.clear()
        self.table.setRowCount(0)

        try:
            self.repo_entries = load_repos()
        except PermissionError:
            QMessageBox.warning(
                self,
                _("Error"),
                _("Cannot read repository directory. Root permission required."),
            )
            return

        self.populate_table()

    def closeEvent(self, event) -> None:
        self.closed.emit()
        self.deleteLater()

    def populate_table(self) -> None:
        self.table.setRowCount(len(self.repo_entries))

        for row, entry in enumerate(self.repo_entries):
            self.table.setItem(row, 0, QTableWidgetItem(entry.name))
            self.table.setItem(row, 1, QTableWidgetItem(entry.url))
            self.table.setItem(row, 2, QTableWidgetItem(str(entry.priority)))
            self._set_checkbox_cell(row, 3, entry.enabled, self.toggle_enabled)
            self._set_checkbox_cell(row, 4, entry.autorefresh, self.toggle_autorefresh)

    def _set_checkbox_cell(self, row: int, col: int, checked: bool, callback) -> None:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        checkbox = QCheckBox()
        checkbox.setChecked(checked)
        checkbox.stateChanged.connect(lambda s, r=row: callback(r, s))
        layout.addWidget(checkbox)
        self.table.setCellWidget(row, col, widget)

    def toggle_enabled(self, row: int, state: int) -> None:
        if 0 <= row < len(self.repo_entries):
            self.repo_entries[row].enabled = state == Qt.CheckState.Checked.value
            self.save_single_entry(row)

    def toggle_autorefresh(self, row: int, state: int) -> None:
        if 0 <= row < len(self.repo_entries):
            self.repo_entries[row].autorefresh = state == Qt.CheckState.Checked.value
            self.save_single_entry(row)

    def add_repo(self) -> None:
        dialog = RepoEditDialog(self)
        if dialog.exec():
            values = dialog.get_values()
            repo_id = values["id"]
            url = values["baseurl"] or values["mirrorlist"]

            if not repo_id:
                QMessageBox.warning(self, _("Error"), _("Repository ID is required."))
                return
            if not url:
                QMessageBox.warning(self, _("Error"), _("URL is required."))
                return

            new_entry = RepoEntry(
                id=repo_id,
                name=values["name"],
                enabled=values["enabled"],
                autorefresh=values["autorefresh"],
                baseurl=values["baseurl"],
                mirrorlist=values["mirrorlist"],
                path=values["path"],
                type=values["type"],
                gpgcheck=values["gpgcheck"],
                gpgkey=values["gpgkey"],
                priority=values["priority"],
                keep_packages=values["keep_packages"],
            )
            self.repo_entries.append(new_entry)
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.populate_row(row)

            result = save_repo_entry(new_entry)
            if result != "ok":
                QMessageBox.critical(self, _("Error"), _("Failed to save repository: %s") % result)

    def edit_repo(self) -> None:
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.information(
                self, _("Information"), _("Please select a repository to edit.")
            )
            return

        entry = self.repo_entries[current_row]
        dialog = RepoEditDialog(self, entry)
        if dialog.exec():
            values = dialog.get_values()
            repo_id = values["id"]
            url = values["baseurl"] or values["mirrorlist"]

            if not repo_id:
                QMessageBox.warning(self, _("Error"), _("Repository ID is required."))
                return
            if not url:
                QMessageBox.warning(self, _("Error"), _("URL is required."))
                return

            self.repo_entries[current_row] = RepoEntry(
                id=repo_id,
                name=values["name"],
                enabled=values["enabled"],
                autorefresh=values["autorefresh"],
                baseurl=values["baseurl"],
                mirrorlist=values["mirrorlist"],
                path=values["path"],
                type=values["type"],
                gpgcheck=values["gpgcheck"],
                gpgkey=values["gpgkey"],
                priority=values["priority"],
                keep_packages=values["keep_packages"],
            )
            self.populate_row(current_row)

            result = save_repo_entry(self.repo_entries[current_row])
            if result != "ok":
                QMessageBox.critical(self, _("Error"), _("Failed to save repository: %s") % result)

    def delete_repo(self) -> None:
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.information(
                self, _("Information"), _("Please select a repository to delete.")
            )
            return

        entry = self.repo_entries[current_row]
        reply = QMessageBox.question(
            self,
            _("Confirm"),
            _("Are you sure you want to delete repository '{}'?").format(entry.name),
        )
        if reply == QMessageBox.StandardButton.Yes:
            result = delete_repo_entry(entry)
            if result == "ok":
                self.repo_entries.pop(current_row)
                self.table.removeRow(current_row)
            else:
                QMessageBox.critical(self, _("Error"), _("Failed to delete repository: %s") % result)

    def switch_mirror_action(self) -> None:
        dialog = SwitchMirrorDialog(self)
        if dialog.exec():
            values = dialog.get_values()
            opensuse_url = values["opensuse_mirror"]
            packman_url = values["packman_mirror"]

            reply = QMessageBox.question(
                self,
                _("Confirm"),
                _("Are you sure you want to switch mirrors?\n\nopenSUSE mirror: {}\nPackman mirror: {}").format(
                    opensuse_url, packman_url
                ),
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

            status = switch_mirror_pkexec(opensuse_url, packman_url)
            if status == "ok":
                QMessageBox.information(
                    self,
                    _("Success"),
                    _("Mirror switching completed successfully."),
                )
                self.load_repos()
            elif status == "permission_denied":
                QMessageBox.critical(self, _("Error"), _("Permission denied."))
            elif status == "pkexec_failed":
                QMessageBox.critical(self, _("Error"), _("Failed to obtain root privileges."))
            else:
                QMessageBox.critical(self, _("Error"), _("Failed to switch mirrors."))

    def populate_row(self, row: int) -> None:
        entry = self.repo_entries[row]

        self.table.setItem(row, 0, QTableWidgetItem(entry.name))
        self.table.setItem(row, 1, QTableWidgetItem(entry.url))
        self.table.setItem(row, 2, QTableWidgetItem(str(entry.priority)))
        self._set_checkbox_cell(row, 3, entry.enabled, self.toggle_enabled)
        self._set_checkbox_cell(row, 4, entry.autorefresh, self.toggle_autorefresh)

    def save_single_entry(self, row: int) -> None:
        entry = self.repo_entries[row]
        result = save_repo_entry(entry)
        if result != "ok":
            QMessageBox.critical(self, _("Error"), _("Failed to save repository: %s") % result)
            entry.enabled = not entry.enabled
            self.populate_row(row)
