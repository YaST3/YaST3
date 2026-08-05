"""GTK4 Flatpak runtime management widget."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk

from mast.core.flatpak import FlatpakRuntime, list_flatpak_runtimes, uninstall_flatpak_runtime
from mast.core.i18n import _


class FlatpakRuntimeManager(Gtk.Box):
    """Manage installed Flatpak runtimes."""

    def __init__(self, parent_window: Gtk.ApplicationWindow, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8, **kwargs)
        self.parent_window = parent_window

        self.runtimes: list[FlatpakRuntime] = []
        self.filtered_runtimes: list[FlatpakRuntime] = []

        self._build_layout()
        self.load_runtimes()

    def _build_layout(self) -> None:
        controls_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        self.remove_btn = Gtk.Button(label=_("Uninstall"))
        self.remove_btn.connect("clicked", self._on_remove_clicked)
        controls_row.append(self.remove_btn)

        controls_row.append(Gtk.Box(hexpand=True))

        self.search_entry = Gtk.Entry()
        self.search_entry.set_placeholder_text("org.example.Platform")
        self.search_entry.connect("activate", self._on_search_clicked)
        self.search_entry.set_hexpand(True)
        controls_row.append(self.search_entry)

        self.search_btn = Gtk.Button(label=_("Search"))
        self.search_btn.connect("clicked", self._on_search_clicked)
        controls_row.append(self.search_btn)

        self.reset_btn = Gtk.Button(label=_("Reset"))
        self.reset_btn.connect("clicked", self._on_reset_clicked)
        controls_row.append(self.reset_btn)

        self.refresh_btn = Gtk.Button(label=_("Refresh"))
        self.refresh_btn.connect("clicked", self._on_refresh_clicked)
        controls_row.append(self.refresh_btn)

        self.append(controls_row)

        self.list_store = Gtk.ListStore(str, str, str, str, str, str, str, str)
        self.tree_view = Gtk.TreeView(model=self.list_store)
        self.tree_view.set_hexpand(True)
        self.tree_view.set_vexpand(True)
        self.selection = self.tree_view.get_selection()
        self.selection.set_mode(Gtk.SelectionMode.SINGLE)

        for title, index in [
            (_("ID"), 0),
            (_("Name"), 1),
            (_("Description"), 2),
            (_("Version"), 3),
            (_("Branch"), 4),
            (_("Installed Size"), 5),
            (_("Remote"), 6),
            (_("Scope"), 7),
        ]:
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(title, renderer, text=index)
            column.set_resizable(True)
            self.tree_view.append_column(column)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_child(self.tree_view)
        self.append(scrolled)

    def load_runtimes(self) -> None:
        try:
            self.runtimes = list_flatpak_runtimes()
        except Exception as e:
            self._show_message_dialog(
                Gtk.MessageType.ERROR,
                _("Error"),
                _("Failed to load Flatpak runtimes: {0}").format(str(e)),
            )
            self.runtimes = []

        self.filtered_runtimes = self._filter_runtimes(self.runtimes, self.search_entry.get_text().strip())
        self._populate_table()

    def _selected_runtime(self) -> FlatpakRuntime | None:
        model, tree_iter = self.selection.get_selected()
        if tree_iter is None:
            return None

        path = model.get_path(tree_iter)
        index = int(path.to_string())
        if 0 <= index < len(self.filtered_runtimes):
            return self.filtered_runtimes[index]
        return None

    def _on_remove_clicked(self, _button: Gtk.Button) -> None:
        runtime = self._selected_runtime()
        if runtime is None:
            self._show_message_dialog(
                Gtk.MessageType.INFO,
                _("Information"),
                _("Please select an installed runtime from the list."),
            )
            return

        confirm_dialog = Gtk.MessageDialog(
            transient_for=self.parent_window,
            modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=_("Confirm"),
        )
        confirm_dialog.set_property(
            "secondary-text",
            _("Are you sure you want to uninstall runtime '{0}'?").format(runtime.runtime_id),
        )
        confirm_dialog.connect("response", self._on_remove_confirm, runtime)
        confirm_dialog.present()

    def _on_remove_confirm(self, dialog: Gtk.MessageDialog, response_id: Gtk.ResponseType, runtime: FlatpakRuntime) -> None:
        dialog.destroy()
        if response_id != Gtk.ResponseType.YES:
            return

        try:
            uninstall_flatpak_runtime(runtime.runtime_id, runtime.scope)
            self._show_message_dialog(Gtk.MessageType.INFO, _("Success"), _("Runtime uninstalled successfully."))
            self.load_runtimes()
        except Exception as e:
            self._show_message_dialog(
                Gtk.MessageType.ERROR,
                _("Error"),
                _("Failed to uninstall runtime: {0}").format(str(e)),
            )

    def _on_search_clicked(self, _widget) -> None:
        self.filtered_runtimes = self._filter_runtimes(self.runtimes, self.search_entry.get_text().strip())
        self._populate_table()

    def _on_reset_clicked(self, _button: Gtk.Button) -> None:
        self.search_entry.set_text("")
        self.filtered_runtimes = list(self.runtimes)
        self._populate_table()

    def _on_refresh_clicked(self, _button: Gtk.Button) -> None:
        self.load_runtimes()

    def _populate_table(self) -> None:
        self.list_store.clear()
        for runtime in self.filtered_runtimes:
            self.list_store.append(
                [
                    runtime.runtime_id,
                    runtime.name,
                    runtime.description,
                    runtime.version,
                    runtime.branch,
                    runtime.installed_size,
                    runtime.remote,
                    runtime.scope,
                ]
            )

    def _filter_runtimes(self, runtimes: list[FlatpakRuntime], query: str) -> list[FlatpakRuntime]:
        normalized_query = query.strip().lower()
        if not normalized_query:
            return list(runtimes)

        return [
            runtime
            for runtime in runtimes
            if normalized_query in runtime.runtime_id.lower()
            or normalized_query in runtime.name.lower()
            or normalized_query in runtime.description.lower()
            or normalized_query in runtime.version.lower()
            or normalized_query in runtime.branch.lower()
            or normalized_query in runtime.remote.lower()
            or normalized_query in runtime.installed_size.lower()
        ]

    def _show_message_dialog(self, msg_type: Gtk.MessageType, title: str, message: str) -> None:
        dialog = Gtk.MessageDialog(
            transient_for=self.parent_window,
            modal=True,
            message_type=msg_type,
            buttons=Gtk.ButtonsType.OK,
            text=title,
        )
        dialog.set_property("secondary-text", message)
        dialog.connect("response", lambda d, _r: d.destroy())
        dialog.present()
