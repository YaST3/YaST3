"""UI components for the Keyboard module (Qt6)."""

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QMessageBox,
    QLineEdit,
)

from mast.core.i18n import _
from mast.core.keyboard import (
    get_current_keyboard_layout,
    get_all_keyboard_layouts,
    set_keyboard_layout,
    get_layout_name,
)


class KeyboardWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setMinimumSize(500, 400)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setSpacing(12)
        self.main_layout.setContentsMargins(12, 12, 12, 12)

        label = QLabel(_("Select Keyboard Layout"))
        self.main_layout.addWidget(label)

        self.layout_list = QListWidget()
        self.layout_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.main_layout.addWidget(self.layout_list)

        test_label = QLabel(_("Test Input:"))
        self.main_layout.addWidget(test_label)

        self.test_input = QLineEdit()
        self.test_input.setPlaceholderText(_("Type here to test the keyboard layout..."))
        self.main_layout.addWidget(self.test_input)

        button_box = QHBoxLayout()
        button_box.addStretch()

        self.save_btn = QPushButton(_("Save"))
        self.save_btn.clicked.connect(self._on_save_clicked)
        button_box.addWidget(self.save_btn)

        self.main_layout.addLayout(button_box)

        self._current_layout = ""
        self._load_layouts()

    def _load_layouts(self) -> None:
        self.layout_list.clear()
        current = get_current_keyboard_layout()
        self._current_layout = current

        layouts = get_all_keyboard_layouts()

        for layout in layouts:
            name = get_layout_name(layout.code)
            item = QListWidgetItem(f"{name} ({layout.code})")
            item.setData(1, layout.code)
            self.layout_list.addItem(item)

        for i in range(self.layout_list.count()):
            item = self.layout_list.item(i)
            if item and item.data(1) == current:
                self.layout_list.setCurrentItem(item)
                item.setSelected(True)
                self.layout_list.scrollToItem(item)
                break

    def _on_save_clicked(self) -> None:
        selected_item = self.layout_list.currentItem()
        if not selected_item:
            return

        selected_layout = selected_item.data(1)

        if selected_layout == self._current_layout:
            QMessageBox.information(self, _("Info"), _("No changes to save."))
            return

        status, message = set_keyboard_layout(selected_layout)

        if status == "ok":
            QMessageBox.information(self, _("Success"), _("Keyboard layout changed successfully to '{0}'.").format(get_layout_name(selected_layout)))
            self._current_layout = selected_layout
        elif status == "permission_denied":
            QMessageBox.critical(self, _("Error"), _("Permission denied. Root permission required."))
        elif status == "pkexec_failed":
            QMessageBox.critical(self, _("Error"), _("Authentication failed or pkexec not available."))
        else:
            QMessageBox.critical(self, _("Error"), _("Failed to set keyboard layout: {0}").format(message))