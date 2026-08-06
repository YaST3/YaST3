"""Main application window showing module buttons."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QMainWindow,
    QMenu,
    QMessageBox,
    QScrollArea,
    QWidget,
)

from mast.core.i18n import _
from mast.core.telemetry import (
    get_telemetry_consent,
    set_telemetry_consent,
    track_app_started,
)
from mast.qt6 import (
    AndroidModule,
    CronModule,
    DateTimeModule,
    FlatpakModule,
    FontConfigModule,
    GitModule,
    HostnameModule,
    HostsModule,
    JournalModule,
    KeyboardModule,
    LanguagesModule,
    PackagesModule,
    ProxyModule,
    RepositoriesModule,
    ServicesModule,
    SnapshotsModule,
    SSHClientModule,
    UsersModule,
)
from mast.qt6.about_dialog import show_about_dialog
from mast.qt6.module_button import ModuleButton


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.modules = (
            AndroidModule(),
            CronModule(),
            DateTimeModule(),
            FlatpakModule(),
            FontConfigModule(),
            GitModule(),
            HostnameModule(),
            HostsModule(),
            JournalModule(),
            KeyboardModule(),
            LanguagesModule(),
            PackagesModule(),
            ProxyModule(),
            RepositoriesModule(),
            ServicesModule(),
            SnapshotsModule(),
            SSHClientModule(),
            UsersModule(),
        )

        self.setWindowTitle("MaST")  # DO NOT TRANSLATE
        self.resize(960, 640)

        menubar = self.menuBar()
        help_menu = QMenu(_("Help"), self)
        about_action = help_menu.addAction(_("About"))
        about_action.triggered.connect(self._show_about)
        menubar.addMenu(help_menu)

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget(scroll_area)
        grid = QGridLayout(container)
        grid.setContentsMargins(32, 32, 32, 32)
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(24)

        for index, module in enumerate(self.modules):
            button = ModuleButton(module)
            row, column = divmod(index, 4)
            grid.addWidget(button, row, column)

        scroll_area.setWidget(container)
        self.setCentralWidget(scroll_area)

        self._setup_telemetry()

    def _show_about(self) -> None:
        show_about_dialog(self)

    def _setup_telemetry(self) -> None:
        consent = get_telemetry_consent()
        if consent is None:
            self._ask_telemetry_consent()
            return

        if consent:
            track_app_started("qt6")

    def _ask_telemetry_consent(self) -> None:
        title = _("Anonymous Usage Analytics")
        text = _(
            "Enable anonymous usage analytics?\n\n"
            "MaST only collects fully anonymous, minimal usage data, and never shares it with third parties."
        )
        result = QMessageBox.question(
            self,
            title,
            text,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        enabled = result == QMessageBox.StandardButton.Yes
        set_telemetry_consent(enabled)
        if enabled:
            track_app_started("qt6")