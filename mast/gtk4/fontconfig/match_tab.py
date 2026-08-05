"""Font match tab component for Font Config module (GTK4)."""

from __future__ import annotations

import gi



gi.require_version("Gtk", "4.0")

from gi.repository import GLib, Gtk

from mast.core.fontconfig import FontConfig, FontMatch
from mast.core.i18n import _


class FontMatchTab(Gtk.Box):
    DEFAULT_MATCH_FAMILIES = ("sans-serif", "serif", "monospace")

    def __init__(
        self,
        config: FontConfig,
        system_fonts: list[str],
        parent_window: Gtk.Window,
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.set_margin_top(8)
        self.set_margin_bottom(8)
        self.set_margin_start(8)
        self.set_margin_end(8)

        self.config = config
        self.system_fonts = system_fonts
        self.parent_window = parent_window

        self._build_ui()

    def _build_ui(self) -> None:
        left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        left_box.set_hexpand(True)
        left_box.set_vexpand(True)
        left_box.append(Gtk.Label(label=_("Match List"), halign=Gtk.Align.START))

        self.match_list = Gtk.ListBox()
        self.match_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.match_list.connect("row-selected", self._on_match_row_selected)

        match_scroller = Gtk.ScrolledWindow()
        match_scroller.set_hexpand(True)
        match_scroller.set_vexpand(True)
        match_scroller.set_child(self.match_list)
        left_box.append(match_scroller)

        match_buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        create_match_btn = Gtk.Button(label=_("Create"))
        create_match_btn.connect("clicked", self._on_create_match_clicked)
        match_buttons.append(create_match_btn)

        delete_match_btn = Gtk.Button(label=_("Delete"))
        delete_match_btn.connect("clicked", self._on_delete_match_clicked)
        match_buttons.append(delete_match_btn)
        left_box.append(match_buttons)

        right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        right_box.set_hexpand(True)
        right_box.set_vexpand(True)
        right_box.append(Gtk.Label(label=_("Font List"), halign=Gtk.Align.START))

        self.font_list = Gtk.ListBox()
        self.font_list.set_selection_mode(Gtk.SelectionMode.SINGLE)

        font_scroller = Gtk.ScrolledWindow()
        font_scroller.set_hexpand(True)
        font_scroller.set_vexpand(True)
        font_scroller.set_child(self.font_list)
        right_box.append(font_scroller)

        font_buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        move_up_btn = Gtk.Button(label=_("Move Up"))
        move_up_btn.connect("clicked", self._on_move_font_up_clicked)
        font_buttons.append(move_up_btn)

        move_down_btn = Gtk.Button(label=_("Move Down"))
        move_down_btn.connect("clicked", self._on_move_font_down_clicked)
        font_buttons.append(move_down_btn)

        remove_font_btn = Gtk.Button(label=_("Remove"))
        remove_font_btn.connect("clicked", self._on_remove_font_clicked)
        font_buttons.append(remove_font_btn)
        right_box.append(font_buttons)

        font_add_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.font_add_combo = Gtk.ComboBoxText()
        self.font_add_combo.set_hexpand(True)
        for font in self.system_fonts:
            self.font_add_combo.append_text(font)
        self.font_add_combo.set_active(0)
        font_add_box.append(self.font_add_combo)

        add_font_btn = Gtk.Button(label=_("Add"))
        add_font_btn.connect("clicked", self._on_add_font_clicked)
        font_add_box.append(add_font_btn)
        right_box.append(font_add_box)

        self.append(left_box)
        self.append(right_box)

    def refresh(self, selected_match_index: int | None = 0) -> None:
        self._clear_listbox(self.match_list)
        for match in self.config.match_list:
            row = Gtk.ListBoxRow()
            row.set_child(Gtk.Label(label=self._format_match_label(match), xalign=0))
            self.match_list.append(row)

        if not self.config.match_list:
            self._refresh_font_list(None)
            return

        if selected_match_index is None:
            selected_match_index = 0
        selected_match_index = max(0, min(selected_match_index, len(self.config.match_list) - 1))
        row = self.match_list.get_row_at_index(selected_match_index)
        if row is not None:
            self.match_list.select_row(row)
        self._refresh_font_list(selected_match_index)

    def _selected_match_index(self) -> int | None:
        row = self.match_list.get_selected_row()
        if row is None:
            return None
        index = row.get_index()
        return index if 0 <= index < len(self.config.match_list) else None

    def _selected_font_index(self) -> int | None:
        row = self.font_list.get_selected_row()
        if row is None:
            return None
        index = row.get_index()
        match_index = self._selected_match_index()
        if match_index is None:
            return None
        fonts = self.config.match_list[match_index].family_edit
        return index if 0 <= index < len(fonts) else None

    def _clear_listbox(self, listbox: Gtk.ListBox) -> None:
        child = listbox.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            listbox.remove(child)
            child = next_child

    def _format_match_label(self, match: FontMatch) -> str:
        if match.lang_test:
            return f"{match.family_test} [{match.lang_test}]"
        return match.family_test

    def _refresh_font_list(
        self,
        match_index: int | None = None,
        selected_index: int | None = None,
    ) -> None:
        self._clear_listbox(self.font_list)

        if match_index is None or not (0 <= match_index < len(self.config.match_list)):
            return

        fonts = self.config.match_list[match_index].family_edit
        for font in fonts:
            row = Gtk.ListBoxRow()
            row.set_child(Gtk.Label(label=font, xalign=0))
            self.font_list.append(row)

        if not fonts:
            return
        if selected_index is None:
            selected_index = 0
        selected_index = max(0, min(selected_index, len(fonts) - 1))
        row = self.font_list.get_row_at_index(selected_index)
        if row is not None:
            self.font_list.select_row(row)

    def _show_create_match_dialog(self) -> tuple[str, str | None] | None:
        dialog = Gtk.Dialog(
            title=_("Create"),
            transient_for=self.parent_window,
            modal=True,
        )
        dialog.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
        dialog.add_button(_("Create"), Gtk.ResponseType.OK)

        content = dialog.get_content_area()
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        content.set_margin_start(12)
        content.set_margin_end(12)

        grid = Gtk.Grid()
        grid.set_row_spacing(12)
        grid.set_column_spacing(12)

        family_combo = Gtk.ComboBoxText()
        for family in self.DEFAULT_MATCH_FAMILIES:
            family_combo.append_text(family)
        family_combo.set_active(0)

        language_entry = Gtk.Entry()
        language_entry.set_placeholder_text(_("Language"))

        grid.attach(Gtk.Label(label=_("Font family"), halign=Gtk.Align.START), 0, 0, 1, 1)
        grid.attach(family_combo, 1, 0, 1, 1)
        grid.attach(Gtk.Label(label=_("Language"), halign=Gtk.Align.START), 0, 1, 1, 1)
        grid.attach(language_entry, 1, 1, 1, 1)
        content.append(grid)

        response = self._run_dialog_blocking(dialog)
        if response != Gtk.ResponseType.OK:
            return None

        family = family_combo.get_active_text() or "sans-serif"
        language_raw = language_entry.get_text().strip()
        language = language_raw if language_raw else None
        return family, language

    def _run_dialog_blocking(self, dialog: Gtk.Dialog) -> int:
        loop = GLib.MainLoop()
        result = {"response": int(Gtk.ResponseType.CANCEL)}

        def on_response(_dialog: Gtk.Dialog, response_id: int) -> None:
            result["response"] = response_id
            dialog.hide()
            loop.quit()

        dialog.connect("response", on_response)
        dialog.present()
        loop.run()
        dialog.destroy()
        return int(result["response"])

    def _on_match_row_selected(self, _listbox: Gtk.ListBox, row: Gtk.ListBoxRow | None) -> None:
        if row is None:
            self._refresh_font_list(None)
            return
        self._refresh_font_list(row.get_index())

    def _on_create_match_clicked(self, _button: Gtk.Button) -> None:
        result = self._show_create_match_dialog()
        if result is None:
            return
        family, language = result
        self.config.match_list.append(
            FontMatch(family_test=family, lang_test=language, family_edit=[])
        )
        self.refresh(len(self.config.match_list) - 1)

    def _on_delete_match_clicked(self, _button: Gtk.Button) -> None:
        match_index = self._selected_match_index()
        if match_index is None:
            return
        self.config.match_list.pop(match_index)
        self.refresh(match_index)

    def _on_add_font_clicked(self, _button: Gtk.Button) -> None:
        match_index = self._selected_match_index()
        if match_index is None:
            return
        font = self.font_add_combo.get_active_text()
        if not font:
            return
        self.config.match_list[match_index].family_edit.append(font)
        self._refresh_font_list(
            match_index,
            len(self.config.match_list[match_index].family_edit) - 1,
        )

    def _on_remove_font_clicked(self, _button: Gtk.Button) -> None:
        match_index = self._selected_match_index()
        font_index = self._selected_font_index()
        if match_index is None or font_index is None:
            return

        fonts = self.config.match_list[match_index].family_edit
        fonts.pop(font_index)
        self._refresh_font_list(match_index, font_index)

    def _on_move_font_up_clicked(self, _button: Gtk.Button) -> None:
        match_index = self._selected_match_index()
        font_index = self._selected_font_index()
        if match_index is None or font_index is None or font_index <= 0:
            return

        fonts = self.config.match_list[match_index].family_edit
        fonts[font_index - 1], fonts[font_index] = fonts[font_index], fonts[font_index - 1]
        self._refresh_font_list(match_index, font_index - 1)

    def _on_move_font_down_clicked(self, _button: Gtk.Button) -> None:
        match_index = self._selected_match_index()
        font_index = self._selected_font_index()
        if match_index is None or font_index is None:
            return

        fonts = self.config.match_list[match_index].family_edit
        if font_index >= len(fonts) - 1:
            return
        fonts[font_index + 1], fonts[font_index] = fonts[font_index], fonts[font_index + 1]
        self._refresh_font_list(match_index, font_index + 1)
