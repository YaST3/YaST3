"""UI components for the Services module (GTK4)."""

from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk

from mast.core.i18n import _
from mast.core.services import (
    ServiceEntry,
    build_service_action_command,
    build_service_logs_command,
    list_services,
)
from mast.gtk4.command.action import CommandAction


class ServicesWindow(Gtk.ApplicationWindow):
    """GTK4 window for managing systemd services."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.services: list[ServiceEntry] = []
        self.filtered_services: list[ServiceEntry] = []
        self.current_action: CommandAction | None = None
        self.log_action: CommandAction | None = None

        self.set_default_size(1280, 720)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.main_box.set_margin_top(8)
        self.main_box.set_margin_bottom(8)
        self.main_box.set_margin_start(8)
        self.main_box.set_margin_end(8)

        self._create_filters()
        self._create_actions()
        self._create_list_view()

        self.set_child(self.main_box)

        self.load_services()

    def _create_filters(self) -> None:
        filters_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        filters_box.append(Gtk.Label(label=_("Status")))
        self.status_filter = Gtk.ComboBoxText()
        self.status_filter.append("all", _("All"))
        self.status_filter.append("active", _("Active"))
        self.status_filter.append("inactive", _("Inactive"))
        self.status_filter.append("failed", _("Failed"))
        self.status_filter.append("activating", _("Activating"))
        self.status_filter.set_active_id("all")
        self.status_filter.connect("changed", self._on_filters_changed)
        filters_box.append(self.status_filter)

        filters_box.append(Gtk.Label(label=_("Scope")))
        self.scope_filter = Gtk.ComboBoxText()
        self.scope_filter.append("all", _("All"))
        self.scope_filter.append("system", _("System"))
        self.scope_filter.append("user", _("User"))
        self.scope_filter.set_active_id("all")
        self.scope_filter.connect("changed", self._on_filters_changed)
        filters_box.append(self.scope_filter)

        filters_box.append(Gtk.Label(label=_("Search")))
        self.search_entry = Gtk.Entry()
        self.search_entry.set_placeholder_text(_("Service name or description"))
        self.search_entry.set_hexpand(True)
        self.search_entry.connect("changed", self._on_filters_changed)
        filters_box.append(self.search_entry)

        self.refresh_btn = Gtk.Button(label=_("Refresh"))
        self.refresh_btn.connect("clicked", lambda _button: self.load_services())
        filters_box.append(self.refresh_btn)

        self.main_box.append(filters_box)

    def _create_actions(self) -> None:
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        self.start_btn = Gtk.Button(label=_("Start"))
        self.start_btn.connect("clicked", lambda _button: self.run_selected_action("start"))
        action_box.append(self.start_btn)

        self.stop_btn = Gtk.Button(label=_("Stop"))
        self.stop_btn.connect("clicked", lambda _button: self.run_selected_action("stop"))
        action_box.append(self.stop_btn)

        self.enable_btn = Gtk.Button(label=_("Enable"))
        self.enable_btn.connect("clicked", lambda _button: self.run_selected_action("enable"))
        action_box.append(self.enable_btn)

        self.disable_btn = Gtk.Button(label=_("Disable"))
        self.disable_btn.connect("clicked", lambda _button: self.run_selected_action("disable"))
        action_box.append(self.disable_btn)

        self.logs_btn = Gtk.Button(label=_("Logs"))
        self.logs_btn.connect("clicked", lambda _button: self.show_selected_logs())
        action_box.append(self.logs_btn)

        action_box.append(Gtk.Box(hexpand=True))
        self.main_box.append(action_box)

    def _create_list_view(self) -> None:
        # Columns: name, scope, status, enabled, description, status_color
        self.list_store = Gtk.ListStore(str, str, str, str, str, str)

        self.tree_view = Gtk.TreeView(model=self.list_store)
        self.tree_view.set_hexpand(True)
        self.tree_view.set_vexpand(True)

        name_renderer = Gtk.CellRendererText()
        name_column = Gtk.TreeViewColumn(_("Name"), name_renderer, text=0)
        name_column.set_resizable(True)
        name_column.set_min_width(260)
        self.tree_view.append_column(name_column)

        scope_renderer = Gtk.CellRendererText()
        scope_column = Gtk.TreeViewColumn(_("Scope"), scope_renderer, text=1)
        scope_column.set_resizable(True)
        scope_column.set_min_width(90)
        self.tree_view.append_column(scope_column)

        status_renderer = Gtk.CellRendererText()
        status_column = Gtk.TreeViewColumn(_("Status"), status_renderer, text=2, foreground=5)
        status_column.set_resizable(True)
        status_column.set_min_width(160)
        self.tree_view.append_column(status_column)

        enabled_renderer = Gtk.CellRendererText()
        enabled_column = Gtk.TreeViewColumn(_("Enabled"), enabled_renderer, text=3)
        enabled_column.set_resizable(True)
        enabled_column.set_min_width(120)
        self.tree_view.append_column(enabled_column)

        description_renderer = Gtk.CellRendererText()
        description_column = Gtk.TreeViewColumn(_("Description"), description_renderer, text=4)
        description_column.set_resizable(True)
        self.tree_view.append_column(description_column)

        self.selection = self.tree_view.get_selection()
        self.selection.set_mode(Gtk.SelectionMode.SINGLE)
        self.selection.connect("changed", self._on_selection_changed)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_child(self.tree_view)
        self.main_box.append(scrolled)

    def _on_filters_changed(self, _widget) -> None:
        self.apply_filters()

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

    def load_services(self) -> None:
        try:
            self.services = list_services()
            self.apply_filters()
        except Exception as error:
            self._show_message_dialog(
                Gtk.MessageType.ERROR,
                _("Error"),
                _("Failed to load services: {0}").format(str(error)),
            )

    def apply_filters(self) -> None:
        status_filter = self.status_filter.get_active_id() or "all"
        scope_filter = self.scope_filter.get_active_id() or "all"
        search_text = self.search_entry.get_text().strip().lower()

        self.filtered_services = []
        for service in self.services:
            if status_filter != "all" and service.active_state != status_filter:
                continue
            if scope_filter != "all" and service.scope != scope_filter:
                continue
            if search_text:
                haystack = f"{service.name} {service.description}".lower()
                if search_text not in haystack:
                    continue
            self.filtered_services.append(service)

        self.populate_list()

    def populate_list(self) -> None:
        self.list_store.clear()
        for service in self.filtered_services:
            self.list_store.append(
                [
                    service.name,
                    self._display_scope(service.scope),
                    service.status_text,
                    service.enabled_text,
                    service.description,
                    self._status_color(service.active_state),
                ]
            )

        if self.filtered_services:
            self.selection.select_path(Gtk.TreePath.new_from_string("0"))
        self.update_action_buttons()

    def _display_scope(self, scope: str) -> str:
        return _("System") if scope == "system" else _("User")

    def _status_color(self, status: str) -> str:
        return {
            "active": "#188038",
            "inactive": "#5f6368",
            "failed": "#c5221f",
            "activating": "#b06000",
            "deactivating": "#b06000",
            "reloading": "#1a73e8",
        }.get(status, "#202124")

    def selected_service(self) -> ServiceEntry | None:
        model, tree_iter = self.selection.get_selected()
        if tree_iter is None:
            return None

        path = model.get_path(tree_iter)
        index = int(path.to_string())
        if index < 0 or index >= len(self.filtered_services):
            return None
        return self.filtered_services[index]

    def update_action_buttons(self) -> None:
        service = self.selected_service()
        has_selection = service is not None

        self.start_btn.set_sensitive(has_selection)
        self.stop_btn.set_sensitive(has_selection)
        self.enable_btn.set_sensitive(has_selection)
        self.disable_btn.set_sensitive(has_selection)
        self.logs_btn.set_sensitive(has_selection)

        if service is None:
            return

        self.start_btn.set_sensitive(service.active_state != "active")
        self.stop_btn.set_sensitive(service.active_state == "active")
        self.enable_btn.set_sensitive(service.enabled_state not in {"enabled", "static", "alias"})
        self.disable_btn.set_sensitive(service.enabled_state == "enabled")

    def run_selected_action(self, action_name: str) -> None:
        service = self.selected_service()
        if service is None:
            self._show_message_dialog(
                Gtk.MessageType.INFO,
                _("Information"),
                _("Please select a service."),
            )
            return

        action_text = {
            "start": _("Start"),
            "stop": _("Stop"),
            "enable": _("Enable"),
            "disable": _("Disable"),
        }[action_name]
        action_result = {
            "start": _("Started"),
            "stop": _("Stopped"),
            "enable": _("Enabled"),
            "disable": _("Disabled"),
        }[action_name]

        self.current_action = self._create_action(
            text=action_text,
            running_text=_("Working..."),
            dialog_title=_("{0} Service").format(action_text),
            command=build_service_action_command(service, action_name),
            success_output=_("Service '{0}' {1} successfully.").format(service.name, action_result),
            on_finished=self._reload_after_action,
        )
        self.current_action.start_action()

    def show_selected_logs(self) -> None:
        service = self.selected_service()
        if service is None:
            self._show_message_dialog(
                Gtk.MessageType.INFO,
                _("Information"),
                _("Please select a service."),
            )
            return

        self.log_action = self._create_action(
            text=_("Logs"),
            running_text=_("Loading logs..."),
            dialog_title=_("Journal Logs: {0}").format(service.name),
            command=build_service_logs_command(service),
            success_output=_("End of journal output."),
            on_finished=None,
        )
        self.log_action.start_action()

    def _reload_after_action(self, success: bool, _error: str, _stdout: str) -> None:
        if success:
            self.load_services()

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
