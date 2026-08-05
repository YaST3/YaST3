"""UI components for the Snapshots module (GTK4)."""

from __future__ import annotations

from collections.abc import Callable

import gi
from bytesize import GB, KB, MB, Size

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk

from mast.core.i18n import _
from mast.core.snapshots import (
    SnapshotEntry,
    build_snapshot_create_command,
    build_snapshot_delete_command,
    build_snapshot_list_command,
    parse_snapshots_from_json,
)
from mast.gtk4.command.action import CommandAction
from mast.gtk4.snapshots.config_dialog import SnapperConfigDialog


class SnapshotsWindow(Gtk.ApplicationWindow):
    """GTK4 window for managing snapper snapshots."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.snapshots: list[SnapshotEntry] = []
        self.current_action: CommandAction | None = None
        self._list_action: CommandAction | None = None

        self.set_default_size(1280, 720)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.main_box.set_margin_top(8)
        self.main_box.set_margin_bottom(8)
        self.main_box.set_margin_start(8)
        self.main_box.set_margin_end(8)

        self._create_actions()
        self._create_list_view()

        self.set_child(self.main_box)

        self.connect("realize", self._on_window_realized)

    def _create_actions(self) -> None:
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        self.description_entry = Gtk.Entry()
        self.description_entry.set_placeholder_text(_("Description"))
        self.description_entry.set_hexpand(True)
        action_box.append(self.description_entry)

        self.refresh_btn = Gtk.Button(label=_("Refresh"))
        self.refresh_btn.connect("clicked", lambda _button: self.load_snapshots())
        action_box.append(self.refresh_btn)

        self.create_btn = Gtk.Button(label=_("Create"))
        self.create_btn.connect("clicked", lambda _button: self.create_snapshot())
        action_box.append(self.create_btn)

        self.delete_btn = Gtk.Button(label=_("Delete"))
        self.delete_btn.connect("clicked", lambda _button: self.delete_snapshot())
        action_box.append(self.delete_btn)

        self.config_btn = Gtk.Button(label=_("Configure"))
        self.config_btn.connect("clicked", lambda _button: self.show_config_dialog())
        action_box.append(self.config_btn)

        action_box.append(Gtk.Box(hexpand=True))
        self.main_box.append(action_box)

    def _create_list_view(self) -> None:
        self.list_store = Gtk.ListStore(str, str, str, str, str, str, str)

        self.tree_view = Gtk.TreeView(model=self.list_store)
        self.tree_view.set_hexpand(True)
        self.tree_view.set_vexpand(True)

        number_column = Gtk.TreeViewColumn(_("ID"), Gtk.CellRendererText(), text=0)
        number_column.set_resizable(True)
        number_column.set_min_width(80)
        self.tree_view.append_column(number_column)

        type_column = Gtk.TreeViewColumn(_("Type"), Gtk.CellRendererText(), text=1)
        type_column.set_resizable(True)
        type_column.set_min_width(120)
        self.tree_view.append_column(type_column)

        date_column = Gtk.TreeViewColumn(_("Date"), Gtk.CellRendererText(), text=2)
        date_column.set_resizable(True)
        date_column.set_min_width(180)
        self.tree_view.append_column(date_column)

        user_column = Gtk.TreeViewColumn(_("User"), Gtk.CellRendererText(), text=3)
        user_column.set_resizable(True)
        user_column.set_min_width(120)
        self.tree_view.append_column(user_column)

        size_column = Gtk.TreeViewColumn(_("Size"), Gtk.CellRendererText(), text=4)
        size_column.set_resizable(True)
        size_column.set_min_width(120)
        self.tree_view.append_column(size_column)

        description_column = Gtk.TreeViewColumn(_("Description"), Gtk.CellRendererText(), text=5)
        description_column.set_resizable(True)
        self.tree_view.append_column(description_column)

        cleanup_column = Gtk.TreeViewColumn(_("Cleanup"), Gtk.CellRendererText(), text=6)
        cleanup_column.set_resizable(True)
        cleanup_column.set_min_width(120)
        self.tree_view.append_column(cleanup_column)

        self.selection = self.tree_view.get_selection()
        self.selection.set_mode(Gtk.SelectionMode.SINGLE)
        self.selection.connect("changed", self._on_selection_changed)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_child(self.tree_view)
        self.main_box.append(scrolled)

    @staticmethod
    def _format_size(used_space: int | None) -> str:
        if used_space is None:
            return "-"
        if used_space <= 0:
            return "0 KB"

        size = Size(used_space)
        gb = float(size.convert_to(GB))
        if gb >= 1:
            return f"{gb:.2f} GB"

        mb = float(size.convert_to(MB))
        if mb >= 1:
            return f"{mb:.2f} MB"

        kb = float(size.convert_to(KB))
        return f"{kb:.2f} KB"

    def _on_selection_changed(self, _selection) -> None:
        self.update_action_buttons()

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

    def _confirm_delete(self, snapshot_number: int) -> bool:
        dialog = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.NONE,
            text=_("Delete Snapshot"),
        )
        dialog.set_property(
            "secondary-text",
            _("Delete snapshot #{0}? This action cannot be undone.").format(snapshot_number),
        )
        dialog.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
        dialog.add_button(_("Delete"), Gtk.ResponseType.OK)

        confirmed: dict[str, bool] = {"value": False}

        def _on_response(dlg: Gtk.MessageDialog, response_id: int) -> None:
            confirmed["value"] = response_id == Gtk.ResponseType.OK
            dlg.destroy()

        dialog.connect("response", _on_response)
        dialog.present()

        loop = Gtk.main_context_default()
        while dialog.get_visible():
            loop.iteration(True)

        return confirmed["value"]

    def _on_window_realized(self, _widget) -> None:
        self.load_snapshots()

    def load_snapshots(self) -> None:
        if self._list_action is not None and self._list_action.is_running():
            return

        self.refresh_btn.set_sensitive(False)
        self.refresh_btn.set_label(_("Loading..."))

        self._list_action = CommandAction(
            text=_("Refresh"),
            running_text=_("Loading..."),
            dialog_title=_("Load Snapshots"),
            command=build_snapshot_list_command(),
            success_output=_("Snapshots loaded successfully."),
            auto_close_on_success=True,
            auto_close_delay_ms=200,
            parent_window=self,
        )
        self._list_action.connect_finished(self._on_snapshots_loaded)
        self._list_action.start_action()

    def _on_snapshots_loaded(self, success: bool, error: str, stdout: str) -> None:
        self._list_action = None
        self.refresh_btn.set_sensitive(True)
        self.refresh_btn.set_label(_("Refresh"))

        if success:
            try:
                self.snapshots = parse_snapshots_from_json(stdout)
                self.populate_list()
            except Exception as parse_error:
                self._show_message_dialog(
                    Gtk.MessageType.ERROR,
                    _("Error"),
                    _("Failed to parse snapshot data: {0}").format(str(parse_error)),
                )
        else:
            self._show_message_dialog(
                Gtk.MessageType.ERROR,
                _("Error"),
                _("Failed to load snapshots: {0}").format(error or _("Unknown error")),
            )

    def populate_list(self) -> None:
        self.list_store.clear()
        for snapshot in self.snapshots:
            self.list_store.append(
                [
                    str(snapshot.number),
                    snapshot.snapshot_type,
                    snapshot.date,
                    snapshot.user,
                    self._format_size(snapshot.used_space),
                    snapshot.description,
                    snapshot.cleanup,
                ]
            )

        if self.snapshots:
            self.selection.select_path(Gtk.TreePath.new_from_string("0"))
        self.update_action_buttons()

    def selected_snapshot(self) -> SnapshotEntry | None:
        model, tree_iter = self.selection.get_selected()
        if tree_iter is None:
            return None

        path = model.get_path(tree_iter)
        index = int(path.to_string())
        if index < 0 or index >= len(self.snapshots):
            return None
        return self.snapshots[index]

    def update_action_buttons(self) -> None:
        self.delete_btn.set_sensitive(self.selected_snapshot() is not None)

    def create_snapshot(self) -> None:
        description = self.description_entry.get_text().strip()
        if not description:
            self._show_message_dialog(
                Gtk.MessageType.INFO,
                _("Information"),
                _("Description cannot be empty."),
            )
            return

        self.current_action = self._create_action(
            text=_("Create"),
            running_text=_("Creating..."),
            dialog_title=_("Create Snapshot"),
            command=build_snapshot_create_command(description),
            success_output=_("Snapshot created successfully."),
            on_finished=self._reload_after_action,
        )
        self.current_action.start_action()

    def delete_snapshot(self) -> None:
        snapshot = self.selected_snapshot()
        if snapshot is None:
            self._show_message_dialog(
                Gtk.MessageType.INFO,
                _("Information"),
                _("Please select a snapshot."),
            )
            return

        if not self._confirm_delete(snapshot.number):
            return

        self.current_action = self._create_action(
            text=_("Delete"),
            running_text=_("Deleting..."),
            dialog_title=_("Delete Snapshot"),
            command=build_snapshot_delete_command(snapshot.number),
            success_output=_("Snapshot #{0} deleted successfully.").format(snapshot.number),
            on_finished=self._reload_after_action,
        )
        self.current_action.start_action()

    def _reload_after_action(self, success: bool, _error: str, _stdout: str) -> None:
        if success:
            self.description_entry.set_text("")
            self.load_snapshots()

    def show_config_dialog(self) -> None:
        dialog = SnapperConfigDialog(self)
        dialog.show()

    def _create_action(
        self,
        text: str,
        running_text: str,
        dialog_title: str,
        command: list[str],
        success_output: str,
        on_finished: Callable[[bool, str, str], None] | None,
    ) -> CommandAction:
        action = CommandAction(
            text=text,
            running_text=running_text,
            dialog_title=dialog_title,
            command=command,
            success_output=success_output,
            parent_window=self,
        )
        if on_finished is not None:
            action.connect_finished(on_finished)
        return action
