"""UI components for the Font Config module (GTK4)."""

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk

from mast.core.fontconfig import FontConfig
from mast.core.i18n import _


class FontConfigWindow(Gtk.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.set_default_size(560, 360)
        self.config = FontConfig()

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.main_box.set_margin_top(16)
        self.main_box.set_margin_bottom(16)
        self.main_box.set_margin_start(16)
        self.main_box.set_margin_end(16)

        self._build_form()
        self._build_buttons()

        self.set_child(self.main_box)
        self.load_config()

    def _build_form(self) -> None:
        grid = Gtk.Grid()
        grid.set_row_spacing(12)
        grid.set_column_spacing(16)

        row = 0

        self.antialias_switch = Gtk.Switch()
        grid.attach(Gtk.Label(label=_("Antialias"), halign=Gtk.Align.START), 0, row, 1, 1)
        grid.attach(self.antialias_switch, 1, row, 1, 1)
        row += 1

        self.hinting_switch = Gtk.Switch()
        grid.attach(Gtk.Label(label=_("Hinting"), halign=Gtk.Align.START), 0, row, 1, 1)
        grid.attach(self.hinting_switch, 1, row, 1, 1)
        row += 1

        self.hintstyle_combo = Gtk.ComboBoxText()
        for option in FontConfig.HINTSTYLE_OPTIONS:
            self.hintstyle_combo.append_text(option)
        grid.attach(Gtk.Label(label=_("Hint Style"), halign=Gtk.Align.START), 0, row, 1, 1)
        grid.attach(self.hintstyle_combo, 1, row, 1, 1)
        row += 1

        self.rgba_combo = Gtk.ComboBoxText()
        for option in FontConfig.RGBA_OPTIONS:
            self.rgba_combo.append_text(option)
        grid.attach(Gtk.Label(label=_("Subpixel Render"), halign=Gtk.Align.START), 0, row, 1, 1)
        grid.attach(self.rgba_combo, 1, row, 1, 1)
        row += 1

        self.lcdfilter_combo = Gtk.ComboBoxText()
        for option in FontConfig.LCDFILTER_OPTIONS:
            self.lcdfilter_combo.append_text(option)
        grid.attach(Gtk.Label(label=_("LCD Filter"), halign=Gtk.Align.START), 0, row, 1, 1)
        grid.attach(self.lcdfilter_combo, 1, row, 1, 1)
        row += 1

        self.embeddedbitmap_switch = Gtk.Switch()
        grid.attach(Gtk.Label(label=_("Embedded Bitmap"), halign=Gtk.Align.START), 0, row, 1, 1)
        grid.attach(self.embeddedbitmap_switch, 1, row, 1, 1)

        self.main_box.append(grid)

    def _build_buttons(self) -> None:
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        button_box.set_halign(Gtk.Align.END)

        reload_btn = Gtk.Button(label=_("Reload"))
        reload_btn.connect("clicked", self._on_reload_clicked)
        button_box.append(reload_btn)

        save_btn = Gtk.Button(label=_("Save"))
        save_btn.add_css_class("suggested-action")
        save_btn.connect("clicked", self._on_save_clicked)
        button_box.append(save_btn)

        self.main_box.append(button_box)

    def _set_combo_value(self, combo: Gtk.ComboBoxText, value: str) -> None:
        model = combo.get_model()
        if model is None:
            return
        active_index = 0
        for index, row in enumerate(model):
            if row[0] == value:
                active_index = index
                break
        combo.set_active(active_index)

    def _get_combo_value(self, combo: Gtk.ComboBoxText, fallback: str) -> str:
        text = combo.get_active_text()
        return text if text else fallback

    def load_config(self) -> None:
        try:
            self.config.reload()
            self.antialias_switch.set_active(self.config.antialias)
            self.hinting_switch.set_active(self.config.hinting)
            self._set_combo_value(self.hintstyle_combo, self.config.hintstyle)
            self._set_combo_value(self.rgba_combo, self.config.rgba)
            self._set_combo_value(self.lcdfilter_combo, self.config.lcdfilter)
            self.embeddedbitmap_switch.set_active(self.config.embeddedbitmap)
        except Exception as e:
            self._show_message_dialog(
                Gtk.MessageType.ERROR,
                _("Error"),
                _("Failed to load font config: {0}").format(str(e)),
            )

    def _on_reload_clicked(self, button: Gtk.Button) -> None:
        self.load_config()

    def _on_save_clicked(self, button: Gtk.Button) -> None:
        self.config.antialias = self.antialias_switch.get_active()
        self.config.hinting = self.hinting_switch.get_active()
        self.config.hintstyle = self._get_combo_value(self.hintstyle_combo, "hintfull")
        self.config.rgba = self._get_combo_value(self.rgba_combo, "none")
        self.config.lcdfilter = self._get_combo_value(self.lcdfilter_combo, "lcddefault")
        self.config.embeddedbitmap = self.embeddedbitmap_switch.get_active()

        try:
            self.config.write()
            self._show_message_dialog(
                Gtk.MessageType.INFO,
                _("Success"),
                _("Font configuration saved successfully."),
            )
        except Exception as e:
            self._show_message_dialog(
                Gtk.MessageType.ERROR,
                _("Error"),
                _("Failed to save font config: {0}").format(str(e)),
            )

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
