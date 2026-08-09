"""Settings dialog for Snap module."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from mast.core.i18n import _
from mast.core.snap import clear_snap_cache_command, get_snap_cache_size
from mast.qt6.command.action import CommandAction
from mast.qt6.snap.remove_action import UninstallSnapAction


class ClearSnapCacheAction(CommandAction):
    """Reusable action for clearing snap cache."""

    def __init__(self, parent=None):
        super().__init__(
            text=_("Clear Cache"),
            running_text=_("Clearing Cache..."),
            dialog_title=_("Clear Snap Cache"),
            command=clear_snap_cache_command(),
            success_output=_("Snap cache cleared successfully."),
            auto_close_on_success=True,
            parent=parent,
        )


class SnapSettingsDialog(QDialog):
    """Modal settings dialog for dangerous Snap operations."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(_("Settings"))
        self.setMinimumSize(400, 220)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Cache group
        cache_group = QGroupBox(_("Cache Management"), self)
        cache_layout = QVBoxLayout(cache_group)

        cache_size_row = QHBoxLayout()
        cache_size_label = QLabel(_("Cache Size:"), cache_group)
        self.cache_size_value = QLabel(get_snap_cache_size(), cache_group)
        cache_size_row.addWidget(cache_size_label)
        cache_size_row.addWidget(self.cache_size_value)
        cache_size_row.addStretch()
        cache_layout.addLayout(cache_size_row)

        self.clear_cache_action = ClearSnapCacheAction(self)
        self.clear_cache_action.action_finished.connect(self._on_clear_cache_finished)
        self.clear_cache_button = QPushButton(self.clear_cache_action.text(), cache_group)
        self.clear_cache_button.clicked.connect(self.clear_cache_action.trigger)
        self.clear_cache_action.changed.connect(self._sync_clear_cache_action_state)
        cache_layout.addWidget(self.clear_cache_button)

        layout.addWidget(cache_group)

        # Uninstall section
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
        self._sync_clear_cache_action_state()

    def _sync_uninstall_action_state(self) -> None:
        self.uninstall_button.setText(self.uninstall_action.text())
        self.uninstall_button.setEnabled(self.uninstall_action.isEnabled())

    def _sync_clear_cache_action_state(self) -> None:
        self.clear_cache_button.setText(self.clear_cache_action.text())
        self.clear_cache_button.setEnabled(self.clear_cache_action.isEnabled())

    def _on_clear_cache_finished(self, success: bool, error: str, _stdout: str) -> None:
        if success:
            self.cache_size_value.setText(get_snap_cache_size())
            QMessageBox.information(self, _("Success"), _("Snap cache cleared successfully."))
        else:
            QMessageBox.critical(
                self,
                _("Error"),
                _("Failed to clear Snap cache: {0}").format(error or _("Unknown error")),
            )

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
