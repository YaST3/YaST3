import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel, QToolButton

from mast.qt6.main_window import MainWindow
from mast.qt6.module_button import ModuleButton


class MainWindowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_window_has_button_for_each_module(self) -> None:
        window = MainWindow()

        buttons = window.findChildren(ModuleButton)

        self.assertEqual(len(buttons), len(window.modules))
        window.close()

    def test_experimental_modules_have_badges(self) -> None:
        window = MainWindow()

        badges = window.findChildren(QLabel, "experimental-badge")
        experimental_modules = [module for module in window.modules if module.experimental]

        self.assertEqual(len(badges), len(experimental_modules))
        window.close()


if __name__ == "__main__":
    unittest.main()
