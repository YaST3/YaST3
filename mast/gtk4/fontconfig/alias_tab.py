"""Font alias tab component for Font Config module (GTK4)."""

from __future__ import annotations

import gi



gi.require_version("Gtk", "4.0")

from gi.repository import Gtk

from mast.core.fontconfig import FontAlias, FontConfig
from mast.core.i18n import _


class FontAliasTab(Gtk.Box):
    def __init__(
        self,
        config: FontConfig,
        system_fonts: list[str],
        show_message,
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.set_margin_top(8)
        self.set_margin_bottom(8)
        self.set_margin_start(8)
        self.set_margin_end(8)

        self.config = config
        self.system_fonts = system_fonts
        self.show_message = show_message

        self._build_ui()

    def _build_ui(self) -> None:
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        left_header = Gtk.Label(label=_("Original Font"), halign=Gtk.Align.START)
        left_header.set_hexpand(True)
        right_header = Gtk.Label(label=_("Preferred Font"), halign=Gtk.Align.START)
        right_header.set_hexpand(True)
        header.append(left_header)
        header.append(right_header)
        self.append(header)

        self.alias_list = Gtk.ListBox()
        self.alias_list.set_selection_mode(Gtk.SelectionMode.SINGLE)

        alias_scroller = Gtk.ScrolledWindow()
        alias_scroller.set_hexpand(True)
        alias_scroller.set_vexpand(True)
        alias_scroller.set_child(self.alias_list)
        self.append(alias_scroller)

        alias_controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.alias_family_entry = Gtk.Entry()
        self.alias_family_entry.set_hexpand(True)
        self.alias_family_entry.set_placeholder_text(_("Font family"))
        alias_controls.append(self.alias_family_entry)

        self.alias_prefer_combo = Gtk.ComboBoxText()
        self.alias_prefer_combo.set_hexpand(True)
        for font in self.system_fonts:
            self.alias_prefer_combo.append_text(font)
        self.alias_prefer_combo.set_active(0)
        alias_controls.append(self.alias_prefer_combo)

        add_alias_btn = Gtk.Button(label=_("Add"))
        add_alias_btn.connect("clicked", self._on_add_alias_clicked)
        alias_controls.append(add_alias_btn)

        remove_alias_btn = Gtk.Button(label=_("Remove"))
        remove_alias_btn.connect("clicked", self._on_remove_alias_clicked)
        alias_controls.append(remove_alias_btn)
        self.append(alias_controls)

    def refresh(self, selected_index: int | None = 0) -> None:
        self._clear_listbox(self.alias_list)
        for alias in self.config.alias_list:
            row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

            family_label = Gtk.Label(label=alias.family, xalign=0)
            family_label.set_hexpand(True)
            row_box.append(family_label)

            prefer_label = Gtk.Label(label=alias.prefer, xalign=0)
            prefer_label.set_hexpand(True)
            row_box.append(prefer_label)

            row = Gtk.ListBoxRow()
            row.set_child(row_box)
            self.alias_list.append(row)

        if not self.config.alias_list:
            return

        if selected_index is None:
            selected_index = len(self.config.alias_list) - 1
        selected_index = max(0, min(selected_index, len(self.config.alias_list) - 1))
        row = self.alias_list.get_row_at_index(selected_index)
        if row is not None:
            self.alias_list.select_row(row)

    def _selected_alias_index(self) -> int | None:
        row = self.alias_list.get_selected_row()
        if row is None:
            return None
        index = row.get_index()
        return index if 0 <= index < len(self.config.alias_list) else None

    def _clear_listbox(self, listbox: Gtk.ListBox) -> None:
        child = listbox.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            listbox.remove(child)
            child = next_child

    def _on_add_alias_clicked(self, _button: Gtk.Button) -> None:
        family = self.alias_family_entry.get_text().strip()
        prefer = self.alias_prefer_combo.get_active_text()

        if not family:
            self.show_message(
                Gtk.MessageType.WARNING,
                _("Error"),
                _("Font family is required."),
            )
            return
        if not prefer:
            return

        self.config.alias_list.append(FontAlias(family=family, prefer=prefer))
        self.alias_family_entry.set_text("")
        self.refresh(len(self.config.alias_list) - 1)

    def _on_remove_alias_clicked(self, _button: Gtk.Button) -> None:
        alias_index = self._selected_alias_index()
        if alias_index is None:
            return
        self.config.alias_list.pop(alias_index)
        self.refresh(alias_index)
