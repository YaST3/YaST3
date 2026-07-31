"""Packages tab component for Android module."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from mast.core.i18n import _


class PackagesTab(QWidget):
    """Component for managing and displaying package lists and filters."""

    search_changed = Signal(str)
    filter_changed = Signal(int)  # state change for checkboxes
    uninstall_clicked = Signal()
    install_clicked = Signal()
    refresh_clicked = Signal()
    selection_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._connect_signals()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)

        filter_layout = QHBoxLayout()

        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText(_("Search packages"))
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

        self.refresh_pkgs_btn = QPushButton(_("Refresh"))
        action_layout.addWidget(self.refresh_pkgs_btn)

        action_layout.addStretch()
        layout.addLayout(action_layout)

        self.package_table = QTableWidget()
        self.package_table.setColumnCount(4)
        self.package_table.setHorizontalHeaderLabels([
            _("Package"),
            _("Name"),
            _("Version"),
            _("Type"),
        ])
        self.package_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.package_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.package_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.package_table)

    def _connect_signals(self) -> None:
        self.search_entry.textChanged.connect(self.search_changed)
        self.blacklist_only.stateChanged.connect(self.filter_changed)
        self.system_only.stateChanged.connect(self.filter_changed)
        self.user_only.stateChanged.connect(self.filter_changed)
        self.uninstall_btn.clicked.connect(self.uninstall_clicked)
        self.install_btn.clicked.connect(self.install_clicked)
        self.refresh_pkgs_btn.clicked.connect(self.refresh_clicked)
        self.package_table.itemSelectionChanged.connect(self.selection_changed)