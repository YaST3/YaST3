"""UI components for the Snap module."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QMainWindow, QMessageBox, QPushButton, QVBoxLayout, QWidget

from mast.core.i18n import _
from mast.core.snap import is_snap_installed, is_snapd_running
from mast.qt6.snap.install_action import InstallSnapAction
from mast.qt6.snap.package_manager import SnapPackageManager
from mast.qt6.snap.start_snapd_action import StartSnapdAction


class SnapWindow(QMainWindow):
    closed = Signal()

    def __init__(self):
        super().__init__()
        self.resize(960, 640)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.install_box = QWidget()
        install_layout = QVBoxLayout(self.install_box)
        self.install_action = InstallSnapAction(self)
        self.install_action.action_finished.connect(self._on_install_finished)
        self.install_button = QPushButton(self.install_action.text(), self.install_box)
        self.install_button.clicked.connect(self.install_action.trigger)
        self.install_action.changed.connect(self._sync_install_action_state)
        install_layout.addWidget(self.install_button)
        layout.addWidget(self.install_box)

        self.start_snapd_box = QWidget()
        start_snapd_layout = QVBoxLayout(self.start_snapd_box)
        self.start_snapd_action = StartSnapdAction(self)
        self.start_snapd_action.action_finished.connect(self._on_start_snapd_finished)
        self.start_snapd_button = QPushButton(self.start_snapd_action.text(), self.start_snapd_box)
        self.start_snapd_button.clicked.connect(self.start_snapd_action.trigger)
        self.start_snapd_action.changed.connect(self._sync_start_snapd_action_state)
        start_snapd_layout.addWidget(self.start_snapd_button)
        layout.addWidget(self.start_snapd_box)

        self.manage_box = QWidget()
        manage_layout = QVBoxLayout(self.manage_box)

        self.package_manager = SnapPackageManager(self.manage_box)
        manage_layout.addWidget(self.package_manager)

        layout.addWidget(self.manage_box)

        self._sync_install_action_state()
        self._sync_start_snapd_action_state()
        self.refresh_state()

    def _sync_install_action_state(self) -> None:
        self.install_button.setText(self.install_action.text())
        self.install_button.setEnabled(self.install_action.isEnabled())

    def _sync_start_snapd_action_state(self) -> None:
        self.start_snapd_button.setText(self.start_snapd_action.text())
        self.start_snapd_button.setEnabled(self.start_snapd_action.isEnabled())

    def refresh_state(self) -> None:
        if not is_snap_installed():
            self.install_box.show()
            self.start_snapd_box.hide()
            self.manage_box.hide()
            return

        if not is_snapd_running():
            self.install_box.hide()
            self.start_snapd_box.show()
            self.manage_box.hide()
            return

        self.install_box.hide()
        self.start_snapd_box.hide()
        self.manage_box.show()
        self.package_manager.refresh()

    def _on_install_finished(self, success: bool, error: str, _stdout: str) -> None:
        if success:
            QMessageBox.information(self, _("Success"), _("Snap installed successfully."))
            self.refresh_state()
        else:
            QMessageBox.critical(
                self,
                _("Error"),
                _("Failed to install Snap: {0}").format(error or _("Unknown error")),
            )

    def _on_start_snapd_finished(self, success: bool, error: str, _stdout: str) -> None:
        if success:
            QMessageBox.information(self, _("Success"), _("Snapd started successfully."))
            self.refresh_state()
        else:
            QMessageBox.critical(
                self,
                _("Error"),
                _("Failed to start Snapd: {0}").format(error or _("Unknown error")),
            )

    def closeEvent(self, event) -> None:
        if (
            self.install_action.is_running()
            or self.start_snapd_action.is_running()
        ):
            QMessageBox.warning(
                self,
                _("Please wait"),
                _("A Snap operation is still running. Please wait for it to finish."),
            )
            event.ignore()
            return

        self.closed.emit()
        self.deleteLater()
