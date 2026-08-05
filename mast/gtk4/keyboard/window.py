"""UI components for the Keyboard module (GTK4)."""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("GLib", "2.0")

from gi.repository import Gtk, GLib

from mast.core.i18n import _
from mast.core.keyboard import (
    get_current_keyboard_layout,
    get_all_keyboard_layouts,
    set_keyboard_layout,
    get_layout_name,
)


class KeyboardWindow(Gtk.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.set_default_size(500, 400)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.main_box.set_margin_top(12)
        self.main_box.set_margin_bottom(12)
        self.main_box.set_margin_start(12)
        self.main_box.set_margin_end(12)

        label = Gtk.Label(label=_("Select Keyboard Layout"))
        label.set_halign(Gtk.Align.START)
        self.main_box.append(label)

        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.set_hexpand(True)
        self.scrolled_window.set_vexpand(True)

        self.layout_list = Gtk.ListBox()
        self.layout_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.scrolled_window.set_child(self.layout_list)

        self.main_box.append(self.scrolled_window)

        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        button_box.set_halign(Gtk.Align.END)

        self.save_btn = Gtk.Button(label=_("Save"))
        self.save_btn.add_css_class("suggested-action")
        self.save_btn.connect("clicked", self._on_save_clicked)
        button_box.append(self.save_btn)

        self.main_box.append(button_box)

        self.set_child(self.main_box)

        self._current_layout = ""
        self._selected_layout = ""
        self._load_layouts()

    def _load_layouts(self) -> None:
        child = self.layout_list.get_first_child()
        while child is not None:
            self.layout_list.remove(child)
            child = self.layout_list.get_first_child()

        current = get_current_keyboard_layout()
        self._current_layout = current
        self._selected_layout = current

        layouts = get_all_keyboard_layouts()

        first_radio = None
        selected_row = None

        for layout in layouts:
            name = get_layout_name(layout.code)
            row = Gtk.ListBoxRow()
            row.set_name(layout.code)
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            box.set_margin_top(6)
            box.set_margin_bottom(6)
            box.set_margin_start(6)
            box.set_margin_end(6)

            radio = Gtk.CheckButton()
            if first_radio is None:
                first_radio = radio
            else:
                radio.set_group(first_radio)

            radio.connect("toggled", self._on_radio_toggled, layout.code)
            box.append(radio)

            label = Gtk.Label(label=name)
            label.set_halign(Gtk.Align.START)
            box.append(label)

            code_label = Gtk.Label(label=f"({layout.code})")
            code_label.add_css_class("dim-label")
            code_label.set_halign(Gtk.Align.END)
            code_label.set_hexpand(True)
            box.append(code_label)

            row.set_child(box)
            self.layout_list.append(row)

            if layout.code == current:
                radio.set_active(True)
                self.layout_list.select_row(row)
                selected_row = row

        if selected_row:
            GLib.idle_add(self._scroll_to_selected_row, selected_row)

    def _scroll_to_selected_row(self, row: Gtk.ListBoxRow) -> bool:
        row.grab_focus()
        return False

    def _on_radio_toggled(self, radio: Gtk.CheckButton, layout_code: str) -> None:
        if radio.get_active():
            self._selected_layout = layout_code

    def _on_save_clicked(self, button: Gtk.Button) -> None:
        if self._selected_layout == self._current_layout:
            self._show_message_dialog(Gtk.MessageType.INFO, _("Info"), _("No changes to save."))
            return

        status, message = set_keyboard_layout(self._selected_layout)

        if status == "ok":
            self._show_message_dialog(Gtk.MessageType.INFO, _("Success"), _("Keyboard layout changed successfully to '{0}'.").format(get_layout_name(self._selected_layout)))
            self._current_layout = self._selected_layout
        elif status == "permission_denied":
            self._show_message_dialog(Gtk.MessageType.ERROR, _("Error"), _("Permission denied. Root permission required."))
        elif status == "pkexec_failed":
            self._show_message_dialog(Gtk.MessageType.ERROR, _("Error"), _("Authentication failed or pkexec not available."))
        else:
            self._show_message_dialog(Gtk.MessageType.ERROR, _("Error"), _("Failed to set keyboard layout: {0}").format(message))

    def _show_message_dialog(self, msg_type: Gtk.MessageType, title: str, message: str) -> None:
        dialog = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            message_type=msg_type,
            buttons=Gtk.ButtonsType.OK,
            text=title,
        )
        dialog.set_property("secondary-text", message)
        dialog.connect("response", lambda d, r: d.destroy())
        dialog.present()