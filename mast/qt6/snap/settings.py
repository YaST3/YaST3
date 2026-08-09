"""Settings dialog for Snap module."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from mast.core.i18n import _
from mast.core.snap import (
    clear_snap_cache_command,
    clear_snap_old_versions_command,
    get_snap_cache_size,
    get_snap_old_versions_size,
    get_snap_retain_count,
    set_snap_retain_command,
)
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


class ClearOldVersionsAction(CommandAction):
    """Reusable action for removing old snap revisions."""

    def __init__(self, parent=None):
        super().__init__(
            text=_("Clean Old Versions"),
            running_text=_("Cleaning Old Versions..."),
            dialog_title=_("Clean Old Snap Versions"),
            command=clear_snap_old_versions_command(),
            success_output=_("Old snap versions cleaned successfully."),
            auto_close_on_success=True,
            parent=parent,
        )


class SetRetainCountAction(CommandAction):
    """Action for setting the snap revision retain count."""

    def __init__(self, count: int, parent=None):
        super().__init__(
            text=_("Apply"),
            running_text=_("Applying..."),
            dialog_title=_("Set Retain Count"),
            command=set_snap_retain_command(count),
            success_output=_("Retain count updated successfully."),
            auto_close_on_success=True,
            parent=parent,
        )


class SnapSettingsDialog(QDialog):
    """Modal settings dialog for dangerous Snap operations."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(_("Settings"))
        self.setMinimumSize(400, 400)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # --- Package Versions group ---
        versions_group = QGroupBox(_("Package Versions"), self)
        versions_layout = QVBoxLayout(versions_group)

        retain_row = QHBoxLayout()
        retain_label = QLabel(_("Max Versions to Keep:"), versions_group)
        self.retain_spin = QSpinBox(versions_group)
        self.retain_spin.setRange(1, 20)
        self.retain_spin.setValue(get_snap_retain_count())
        self.retain_apply_btn = QPushButton(_("Apply"), versions_group)
        self.retain_apply_btn.clicked.connect(self._apply_retain_count)
        retain_row.addWidget(retain_label)
        retain_row.addWidget(self.retain_spin)
        retain_row.addWidget(self.retain_apply_btn)
        versions_layout.addLayout(retain_row)

        old_size_row = QHBoxLayout()
        old_size_label = QLabel(_("Old Versions Size:"), versions_group)
        self.old_versions_size_value = QLabel(get_snap_old_versions_size(), versions_group)
        old_size_row.addWidget(old_size_label)
        old_size_row.addWidget(self.old_versions_size_value)
        old_size_row.addStretch()
        versions_layout.addLayout(old_size_row)

        self.clear_old_versions_action = ClearOldVersionsAction(self)
        self.clear_old_versions_action.action_finished.connect(self._on_clear_old_versions_finished)
        self.clear_old_versions_btn = QPushButton(self.clear_old_versions_action.text(), versions_group)
        self.clear_old_versions_btn.clicked.connect(self.clear_old_versions_action.trigger)
        self.clear_old_versions_action.changed.connect(self._sync_clear_old_versions_state)
        versions_layout.addWidget(self.clear_old_versions_btn)

        layout.addWidget(versions_group)

        # --- Cache group ---
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

        # --- Uninstall section ---
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
        self._sync_clear_old_versions_state()

    def _apply_retain_count(self) -> None:
        count = self.retain_spin.value()
        self._retain_action = SetRetainCountAction(count, self)
        self._retain_action.action_finished.connect(self._on_retain_finished)
        self.retain_apply_btn.setEnabled(False)
        self._retain_action.start_action()

    def _on_retain_finished(self, success: bool, error: str, _stdout: str) -> None:
        self.retain_apply_btn.setEnabled(True)
        if success:
            QMessageBox.information(self, _("Success"), _("Retain count updated successfully."))
        else:
            QMessageBox.critical(
                self,
                _("Error"),
                _("Failed to set retain count: {0}").format(error or _("Unknown error")),
            )

    def _sync_uninstall_action_state(self) -> None:
        self.uninstall_button.setText(self.uninstall_action.text())
        self.uninstall_button.setEnabled(self.uninstall_action.isEnabled())

    def _sync_clear_cache_action_state(self) -> None:
        self.clear_cache_button.setText(self.clear_cache_action.text())
        self.clear_cache_button.setEnabled(self.clear_cache_action.isEnabled())

    def _sync_clear_old_versions_state(self) -> None:
        self.clear_old_versions_btn.setText(self.clear_old_versions_action.text())
        self.clear_old_versions_btn.setEnabled(self.clear_old_versions_action.isEnabled())

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

    def _on_clear_old_versions_finished(self, success: bool, error: str, _stdout: str) -> None:
        if success:
            self.old_versions_size_value.setText(get_snap_old_versions_size())
            QMessageBox.information(self, _("Success"), _("Old snap versions cleaned successfully."))
        else:
            QMessageBox.critical(
                self,
                _("Error"),
                _("Failed to clean old versions: {0}").format(error or _("Unknown error")),
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
