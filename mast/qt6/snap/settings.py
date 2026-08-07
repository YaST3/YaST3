"""Settings dialog for Snap module."""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QMessageBox, QPushButton, QVBoxLayout

from mast.core.i18n import _
from mast.qt6.snap.remove_action import UninstallSnapAction


class SnapSettingsDialog(QDialog):
    """Modal settings dialog for dangerous Snap operations."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(_("Settings"))
        self.setMinimumSize(360, 120)

        layout = QVBoxLayout(self)

        self.uninstall_action = UninstallSnapAction(self)
        self.uninstall_action.action_finished.connect(self._on_uninstall_finished)
        self.uninstall_button = QPushButton(self.uninstall_action.text(), self)
        self.uninstall_button.clicked.connect(self.uninstall_action.trigger)
        self.uninstall_action.changed.connect(self._sync_uninstall_action_state)
        layout.addWidget(self.uninstall_button)

        close_button = QPushButton(_("Close"), self)
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

        self._sync_uninstall_action_state()

    def _sync_uninstall_action_state(self) -> None:
        self.uninstall_button.setText(self.uninstall_action.text())
        self.uninstall_button.setEnabled(self.uninstall_action.isEnabled())

    def _on_uninstall_finished(self, success: bool, error: str, _stdout: str) -> None:
        if success:
            QMessageBox.information(self, _("Success"), _("Snap uninstalled successfully."))
            parent_window = self.parent()
            if parent_window and hasattr(parent_window, "refresh_state"):
                parent_window.refresh_state()
            self.accept()
        else:
            QMessageBox.critical(
                self,
                _("Error"),
                _("Failed to uninstall Snap: {0}").format(error or _("Unknown error")),
            )
