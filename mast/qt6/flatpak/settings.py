"""Settings tab for Flatpak module."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from mast.core.flatpak import (
    clear_flatpak_cache_command,
    get_flatpak_cache_size,
)
from mast.core.i18n import _
from mast.qt6.command.action import CommandAction
from mast.qt6.flatpak.remove_action import UninstallFlatpakAction


class ClearFlatpakCacheAction(CommandAction):
    """Reusable action for clearing flatpak cache."""

    def __init__(self, parent=None):
        super().__init__(
            text=_("Clear Cache"),
            running_text=_("Clearing Cache..."),
            dialog_title=_("Clear Flatpak Cache"),
            command=clear_flatpak_cache_command(),
            success_output=_("Flatpak cache cleared successfully."),
            auto_close_on_success=True,
            parent=parent,
        )


class FlatpakSettingsTab(QWidget):
    """Settings UI for dangerous or advanced Flatpak operations."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)

        # --- Cache group ---
        cache_group = QGroupBox(_("Cache Management"), self)
        cache_layout = QVBoxLayout(cache_group)

        cache_size_row = QHBoxLayout()
        cache_size_label = QLabel(_("Cache Size:"), cache_group)
        self.cache_size_value = QLabel(get_flatpak_cache_size(), cache_group)
        cache_size_row.addWidget(cache_size_label)
        cache_size_row.addWidget(self.cache_size_value)
        cache_size_row.addStretch()
        cache_layout.addLayout(cache_size_row)

        self.clear_cache_action = ClearFlatpakCacheAction(self)
        self.clear_cache_action.action_finished.connect(self._on_clear_cache_finished)
        self.clear_cache_button = QPushButton(self.clear_cache_action.text(), cache_group)
        self.clear_cache_button.clicked.connect(self.clear_cache_action.trigger)
        self.clear_cache_action.changed.connect(self._sync_clear_cache_action_state)
        cache_layout.addWidget(self.clear_cache_button)

        layout.addWidget(cache_group)

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
        self._sync_clear_cache_action_state()

    def _sync_uninstall_action_state(self) -> None:
        self.uninstall_button.setText(self.uninstall_action.text())
        self.uninstall_button.setEnabled(self.uninstall_action.isEnabled())

    def _sync_clear_cache_action_state(self) -> None:
        self.clear_cache_button.setText(self.clear_cache_action.text())
        self.clear_cache_button.setEnabled(self.clear_cache_action.isEnabled())

    def _on_clear_cache_finished(self, success: bool, error: str, _stdout: str) -> None:
        if success:
            self.cache_size_value.setText(get_flatpak_cache_size())
            QMessageBox.information(self, _("Success"), _("Flatpak cache cleared successfully."))
        else:
            QMessageBox.critical(
                self,
                _("Error"),
                _("Failed to clear Flatpak cache: {0}").format(error or _("Unknown error")),
            )
