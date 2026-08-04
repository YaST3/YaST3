"""Entry point for the Qt6 GUI application."""

from PySide6.QtWidgets import QApplication

from mast.core.i18n import init_i18n
from mast.qt6.main_window import MainWindow


def main() -> int:
    app = QApplication([])
    app.setApplicationName("MaST Qt6")
    app.setDesktopFileName("me.guoyunhe.mast.qt6")

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())