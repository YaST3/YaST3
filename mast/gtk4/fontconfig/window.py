"""UI components for the Font Config module (GTK4)."""

from __future__ import annotations

import subprocess

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk

from mast.core.fontconfig import FontConfig
from mast.core.i18n import _
from mast.gtk4.fontconfig.alias_tab import FontAliasTab
from mast.gtk4.fontconfig.match_tab import FontMatchTab
from mast.gtk4.fontconfig.option_tab import FontOptionTab


class FontConfigWindow(Gtk.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.set_default_size(760, 480)
        self.config = FontConfig()
        self.system_fonts = self._load_system_fonts()

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.main_box.set_margin_top(16)
        self.main_box.set_margin_bottom(16)
        self.main_box.set_margin_start(16)
        self.main_box.set_margin_end(16)

        self._build_tabs()
        self._build_buttons()

        self.set_child(self.main_box)
        self.load_config()

    def _load_system_fonts(self) -> list[str]:
        default_fonts = ["Sans", "Serif", "Monospace"]

        try:
            proc = subprocess.run(
                ["fc-list", ":", "family"],
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError:
            return default_fonts

        if proc.returncode != 0 or not proc.stdout:
            return default_fonts

        seen: set[str] = set()
        fonts: list[str] = []
        for line in proc.stdout.splitlines():
            for item in line.split(","):
                name = item.strip()
                if not name:
                    continue
                if name in seen:
                    continue
                seen.add(name)
                fonts.append(name)

        return sorted(fonts, key=str.casefold) if fonts else default_fonts

    def _build_tabs(self) -> None:
        self.notebook = Gtk.Notebook()

        self.match_tab = FontMatchTab(self.config, self.system_fonts, self)
        self.notebook.append_page(self.match_tab, Gtk.Label(label=_("Font Match")))

        self.alias_tab = FontAliasTab(self.config, self.system_fonts, self._show_message_dialog)
        self.notebook.append_page(self.alias_tab, Gtk.Label(label=_("Font Alias")))

        self.option_tab = FontOptionTab()
        self.notebook.append_page(self.option_tab, Gtk.Label(label=_("Font Option")))

        self.main_box.append(self.notebook)

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

    def load_config(self) -> None:
        try:
            self.config.reload()
            self.match_tab.refresh(0)
            self.alias_tab.refresh(0)
            self.option_tab.load_from_config(self.config)
        except Exception as e:
            self._show_message_dialog(
                Gtk.MessageType.ERROR,
                _("Error"),
                _("Failed to load font config: {0}").format(str(e)),
            )

    def _on_reload_clicked(self, _button: Gtk.Button) -> None:
        self.load_config()

    def _on_save_clicked(self, _button: Gtk.Button) -> None:
        self.option_tab.apply_to_config(self.config)

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
        dialog.connect("response", lambda d, _r: d.destroy())
        dialog.present()
