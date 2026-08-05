"""Settings tab for Flatpak module."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from mast.qt6.flatpak.remove_action import UninstallFlatpakAction


class FlatpakSettingsTab(QWidget):
    """Settings UI for dangerous or advanced Flatpak operations."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.addStretch()

        danger_layout = QHBoxLayout()
        danger_layout.addStretch()

        self.uninstall_action = UninstallFlatpakAction(self)
        self.uninstall_button = QPushButton(self.uninstall_action.text(), self)
        self.uninstall_button.clicked.connect(self.uninstall_action.trigger)
        self.uninstall_action.changed.connect(self._sync_uninstall_action_state)
        danger_layout.addWidget(self.uninstall_button)

        layout.addLayout(danger_layout)
        self._sync_uninstall_action_state()

    def _sync_uninstall_action_state(self) -> None:
        self.uninstall_button.setText(self.uninstall_action.text())
        self.uninstall_button.setEnabled(self.uninstall_action.isEnabled())
