"""GTK4 Snap package management widgets."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Literal

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import GLib, Gtk

from mast.core.i18n import _
from mast.core.snap import SnapPackage, list_snap_packages, search_snap_packages
from mast.gtk4.command.action import CommandAction
from mast.gtk4.snap.settings import SnapSettingsDialog


FILTER_ALL: Literal["all"] = "all"
FILTER_INSTALLED: Literal["installed"] = "installed"


class _CatalogWorker(threading.Thread):
    """Worker that loads snap package search results outside the UI thread."""

    def __init__(
        self,
        query: str,
        on_loaded: Callable[[list[SnapPackage]], bool],
        on_failed: Callable[[str], bool],
    ) -> None:
        super().__init__(daemon=True)
        self.query = query
        self.on_loaded = on_loaded
        self.on_failed = on_failed

    def run(self) -> None:
        try:
            packages = search_snap_packages(self.query)
        except Exception as e:
            GLib.idle_add(self.on_failed, str(e))
            return

        GLib.idle_add(self.on_loaded, packages)


class _InstalledCatalogWorker(threading.Thread):
    """Worker that loads installed snap packages outside the UI thread."""

    def __init__(
        self,
        on_loaded: Callable[[list[SnapPackage]], bool],
        on_failed: Callable[[str], bool],
    ) -> None:
        super().__init__(daemon=True)
        self.on_loaded = on_loaded
        self.on_failed = on_failed

    def run(self) -> None:
        try:
            packages = list_snap_packages()
        except Exception as e:
            GLib.idle_add(self.on_failed, str(e))
            return

        GLib.idle_add(self.on_loaded, packages)


class SnapPackageManager(Gtk.Box):
    """Manage snap packages with an All/Installed filter."""

    def __init__(self, parent_window: Gtk.ApplicationWindow, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8, **kwargs)
        self.parent_window = parent_window

        self.remote_packages: list[SnapPackage] = []
        self.filtered_remote_packages: list[SnapPackage] = []
        self.installed_packages: list[SnapPackage] = []
        self.filtered_installed_packages: list[SnapPackage] = []
        self.installed_names: set[str] = set()
        self.current_filter: Literal["all", "installed"] = FILTER_ALL
        self.remote_loading = False
        self.remote_loader: _CatalogWorker | None = None
        self.installed_loading = False
        self.installed_loader: _InstalledCatalogWorker | None = None
        self.action: CommandAction | None = None

        self._build_layout()
        self.refresh()

    def _build_layout(self) -> None:
        controls_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        self.primary_btn = Gtk.Button(label=_("Install"))
        self.primary_btn.set_sensitive(False)
        self.primary_btn.connect("clicked", self._on_primary_clicked)
        controls_row.append(self.primary_btn)

        self.update_btn = Gtk.Button(label=_("Update"))
        self.update_btn.set_sensitive(False)
        self.update_btn.connect("clicked", self._on_update_clicked)
        controls_row.append(self.update_btn)

        self.update_all_btn = Gtk.Button(label=_("Update All"))
        self.update_all_btn.set_sensitive(False)
        self.update_all_btn.connect("clicked", self._on_update_all_clicked)
        controls_row.append(self.update_all_btn)

        controls_row.append(Gtk.Box(hexpand=True))

        self.filter_combo = Gtk.ComboBoxText()
        self.filter_combo.append(FILTER_ALL, _("All"))
        self.filter_combo.append(FILTER_INSTALLED, _("Installed"))
        self.filter_combo.set_active_id(FILTER_ALL)
        self.filter_combo.connect("changed", self._on_filter_changed)
        controls_row.append(self.filter_combo)

        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text(_("Search"))
        self.search_entry.connect("activate", self._on_search_clicked)
        self.search_entry.set_hexpand(True)
        controls_row.append(self.search_entry)

        self.search_btn = Gtk.Button(label=_("Search"))
        self.search_btn.connect("clicked", self._on_search_clicked)
        controls_row.append(self.search_btn)

        self.settings_btn = Gtk.Button(label=_("Settings"))
        self.settings_btn.connect("clicked", self._on_settings_clicked)
        controls_row.append(self.settings_btn)

        self.append(controls_row)

        self._create_table()

    def _create_table(self) -> None:
        self.list_store = Gtk.ListStore(str, str, str, str, str, str, str)

        self.tree_view = Gtk.TreeView(model=self.list_store)
        self.tree_view.set_hexpand(True)
        self.tree_view.set_vexpand(True)
        self.tree_view.props.has_tooltip = True
        self.tree_view.connect("query-tooltip", self._on_query_tooltip)
        self.selection = self.tree_view.get_selection()
        self.selection.set_mode(Gtk.SelectionMode.SINGLE)
        self.selection.connect("changed", self._on_selection_changed)

        name_column = Gtk.TreeViewColumn(_("Name"), Gtk.CellRendererText(), text=0)
        name_column.set_resizable(True)
        self.tree_view.append_column(name_column)

        version_column = Gtk.TreeViewColumn(_("Version"), Gtk.CellRendererText(), text=1)
        version_column.set_resizable(True)
        version_column.set_max_width(80)
        self.tree_view.append_column(version_column)

        publisher_column = Gtk.TreeViewColumn(_("Publisher"))
        self.publisher_icon_renderer = Gtk.CellRendererPixbuf()
        self.publisher_text_renderer = Gtk.CellRendererText()
        publisher_column.pack_start(self.publisher_icon_renderer, False)
        publisher_column.pack_start(self.publisher_text_renderer, True)
        publisher_column.add_attribute(self.publisher_text_renderer, "text", 2)
        publisher_column.set_cell_data_func(
            self.publisher_icon_renderer, self._publisher_icon_data_func
        )
        publisher_column.set_resizable(True)
        publisher_column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        self.tree_view.append_column(publisher_column)

        summary_column = Gtk.TreeViewColumn(_("Summary"), Gtk.CellRendererText(), text=3)
        summary_column.set_resizable(True)
        summary_column.set_expand(True)
        self.tree_view.append_column(summary_column)

        installed_renderer = Gtk.CellRendererText()
        installed_column = Gtk.TreeViewColumn(_("Installed"), installed_renderer)
        installed_column.set_resizable(True)
        installed_column.set_cell_data_func(installed_renderer, self._installed_text_data_func)
        self.tree_view.append_column(installed_column)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_child(self.tree_view)
        self.append(scrolled)

    def refresh(self) -> None:
        self.load_remote_packages()
        self.load_installed_packages()

    def _is_busy(self) -> bool:
        return self.remote_loading or self.installed_loading or (self.action is not None and self.action.is_running())

    def _set_loading(self) -> None:
        is_loading = self.remote_loading or self.installed_loading
        is_busy = self._is_busy()
        loading_label = _("Loading...") if is_loading else _("Search")
        self.search_btn.set_label(loading_label)
        self.search_btn.set_sensitive(not is_busy)
        self.settings_btn.set_sensitive(not is_busy)
        self.filter_combo.set_sensitive(not is_busy)
        self._sync_primary_button()

    def _updatable_names(self) -> set[str]:
        installed_versions = {p.name: p.version for p in self.installed_packages}
        remote_versions = {p.name: p.version for p in self.remote_packages}
        updatable: set[str] = set()
        for name, v in installed_versions.items():
            if name in remote_versions and remote_versions[name] != v:
                updatable.add(name)
        return updatable

    def _selected_status(self) -> str:
        package = self._selected_package()
        if package is None:
            return "not_installed"
        installed_versions = {p.name: p.version for p in self.installed_packages}
        remote_versions = {p.name: p.version for p in self.remote_packages}
        return self._compute_status(package.name, installed_versions, remote_versions)

    def load_remote_packages(self) -> None:
        if self.remote_loader is not None:
            return

        self.remote_loading = True
        self._set_loading()
        self.remote_loader = _CatalogWorker(
            self.search_entry.get_text().strip(),
            on_loaded=self._on_remote_packages_loaded,
            on_failed=self._on_remote_packages_failed,
        )
        self.remote_loader.start()

    def _on_remote_packages_loaded(self, packages: list[SnapPackage]) -> bool:
        self.remote_packages = packages
        self.filtered_remote_packages = self._filter_packages(self.remote_packages, self.search_entry.get_text().strip())
        self._populate_table()
        self._on_remote_loader_finished()
        return False

    def _on_remote_packages_failed(self, error: str) -> bool:
        self._show_message_dialog(
            Gtk.MessageType.ERROR,
            _("Error"),
            _("Failed to load package catalog: {0}").format(error),
        )
        self.remote_packages = []
        self.filtered_remote_packages = []
        self._populate_table()
        self._on_remote_loader_finished()
        return False

    def _on_remote_loader_finished(self) -> None:
        self.remote_loader = None
        self.remote_loading = False
        self._set_loading()

    def load_installed_packages(self, _refresh_current: bool = True) -> None:
        if self.installed_loader is not None:
            return

        self.installed_loading = True
        self._set_loading()
        self.installed_loader = _InstalledCatalogWorker(
            on_loaded=self._on_installed_packages_loaded,
            on_failed=self._on_installed_packages_failed,
        )
        self.installed_loader.start()

    def _on_installed_packages_loaded(self, packages: list[SnapPackage]) -> bool:
        self.installed_packages = packages
        self.installed_names = {pkg.name for pkg in self.installed_packages}
        self.filtered_installed_packages = self._filter_packages(
            self.installed_packages,
            self.search_entry.get_text().strip(),
        )
        self._populate_table()
        self._on_installed_loader_finished()
        return False

    def _on_installed_packages_failed(self, error: str) -> bool:
        self._show_message_dialog(
            Gtk.MessageType.ERROR,
            _("Error"),
            _("Failed to load Snap packages: {0}").format(error),
        )
        self.installed_packages = []
        self.installed_names = set()
        self.filtered_installed_packages = []
        self._populate_table()
        self._on_installed_loader_finished()
        return False

    def _on_installed_loader_finished(self) -> None:
        self.installed_loader = None
        self.installed_loading = False
        self._set_loading()

    def _on_filter_changed(self, _combo) -> None:
        active = self.filter_combo.get_active_id()
        if active in (FILTER_ALL, FILTER_INSTALLED):
            self.current_filter = active  # type: ignore[assignment]
        self._populate_table()
        self._sync_primary_button()

    def _on_search_clicked(self, _widget) -> None:
        self.refresh()

    def _on_settings_clicked(self, _widget) -> None:
        dialog = SnapSettingsDialog(self.parent_window)
        dialog.present()

    def _on_selection_changed(self, _selection) -> None:
        self._sync_primary_button()

    def _sync_primary_button(self) -> None:
        is_busy = self._is_busy()
        status = self._selected_status()
        if status == "not_installed":
            self.primary_btn.set_label(_("Install"))
            self.primary_btn.set_sensitive(not is_busy and self._selected_package() is not None)
        else:
            self.primary_btn.set_label(_("Uninstall"))
            self.primary_btn.set_sensitive(not is_busy)

        self.update_btn.set_sensitive(not is_busy and status == "updatable")

        updatable_count = len(self._updatable_names())
        self.update_all_btn.set_sensitive(not is_busy and updatable_count > 0)
        self.update_all_btn.set_label(
            _("Update All ({0})").format(updatable_count) if updatable_count > 0 else _("Update All")
        )

    def _selected_package(self) -> SnapPackage | None:
        model, tree_iter = self.selection.get_selected()
        if tree_iter is None:
            return None

        path = model.get_path(tree_iter)
        index = int(path.to_string())
        items = self._current_items()
        if 0 <= index < len(items):
            return items[index]
        return None

    def _current_items(self) -> list[SnapPackage]:
        if self.current_filter == FILTER_ALL:
            return self.filtered_remote_packages
        return self.filtered_installed_packages

    def _start_action(self, action: str, name: str = "") -> None:
        if self.action is not None and self.action.is_running():
            return

        if action == "refresh":
            cmd: list[str]
            if name:
                cmd = ["pkexec", "snap", "refresh", name]
                success_text = _("Package updated successfully.")
                title = _("Update Snap Package")
            else:
                cmd = ["pkexec", "snap", "refresh"]
                success_text = _("All packages updated successfully.")
                title = _("Update All Snap Packages")
            self.action = CommandAction(
                text=_("Update"),
                running_text=_("Updating..."),
                dialog_title=title,
                command=cmd,
                success_output=success_text,
                auto_close_on_success=True,
                parent_window=self.parent_window,
            )
        else:
            is_install = action == "install"
            self.action = CommandAction(
                text=_("Install") if is_install else _("Uninstall"),
                running_text=_("Installing...") if is_install else _("Uninstalling..."),
                dialog_title=_("Install Snap Package") if is_install else _("Uninstall Snap Package"),
                command=["pkexec", "snap", "install" if is_install else "remove", name],
                success_output=_("Package installed successfully.") if is_install else _("Package uninstalled successfully."),
                auto_close_on_success=True,
                parent_window=self.parent_window,
            )
        self.action.connect_finished(self._on_action_finished)
        self.action.trigger()
        self._set_loading()

    def _on_action_finished(self, success: bool, error: str, _stdout: str) -> None:
        self.action = None
        if success:
            self.refresh()
            return

        package = self._selected_package()
        is_install_error = package is not None and package.name not in self.installed_names
        self._show_message_dialog(
            Gtk.MessageType.ERROR,
            _("Error"),
            (_("Failed to install package: {0}") if is_install_error
             else _("Failed to uninstall package: {0}")).format(error),
        )
        self._set_loading()

    def _on_primary_clicked(self, _button: Gtk.Button) -> None:
        package = self._selected_package()
        if package is None:
            self._show_message_dialog(
                Gtk.MessageType.INFO,
                _("Information"),
                _("Please select a package from the list."),
            )
            return

        is_installed = package.name in self.installed_names
        if is_installed:
            confirm_dialog = Gtk.MessageDialog(
                transient_for=self.parent_window,
                modal=True,
                message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.YES_NO,
                text=_("Confirm"),
            )
            confirm_dialog.set_property(
                "secondary-text",
                _("Are you sure you want to uninstall package '{0}'?").format(package.name),
            )
            confirm_dialog.connect("response", self._on_uninstall_confirm, package)
            confirm_dialog.present()
        else:
            self._start_action("install", package.name)

    def _on_uninstall_confirm(self, dialog: Gtk.MessageDialog, response_id: Gtk.ResponseType, package: SnapPackage) -> None:
        dialog.destroy()
        if response_id != Gtk.ResponseType.YES:
            return

        self._start_action("uninstall", package.name)

    def _on_update_clicked(self, _button: Gtk.Button) -> None:
        package = self._selected_package()
        if package is None:
            return
        status = self._selected_status()
        if status != "updatable":
            return
        self._start_action("refresh", package.name)

    def _on_update_all_clicked(self, _button: Gtk.Button) -> None:
        updatable = self._updatable_names()
        if not updatable:
            return
        self._start_action("refresh")

    def _populate_table(self) -> None:
        self.list_store.clear()
        installed_versions = {p.name: p.version for p in self.installed_packages}
        remote_versions = {p.name: p.version for p in self.remote_packages}
        for package in self._current_items():
            status = self._compute_status(package.name, installed_versions, remote_versions)
            self.list_store.append(
                [
                    package.name,
                    package.version,
                    package.publisher,
                    package.summary,
                    "",
                    package.publisher_validation,
                    status,
                ]
            )
        self._sync_primary_button()

    @staticmethod
    def _compute_status(name: str, installed_versions: dict[str, str], remote_versions: dict[str, str]) -> str:
        """Compute install status: 'installed', 'updatable', or 'not_installed'."""
        if name not in installed_versions:
            return "not_installed"
        if name in remote_versions and remote_versions[name] != installed_versions[name]:
            return "updatable"
        return "installed"

    def _installed_text_data_func(self, _column, cell, model, iter, _data=None) -> None:
        status = model.get_value(iter, 6) if iter is not None else "not_installed"
        if status == "installed":
            cell.set_property("text", _("Yes"))
            cell.set_property("foreground", "#22c55e")
        elif status == "updatable":
            cell.set_property("text", _("Update"))
            cell.set_property("foreground", "#f97316")
        else:
            cell.set_property("text", _("No"))
            cell.set_property("foreground", None)

    def _publisher_icon_data_func(self, _column, cell, model, iter, _data=None) -> None:
        validation = model.get_value(iter, 5) if iter is not None else ""
        if validation == "verified":
            cell.set_property("pixbuf", None)
            cell.set_property("icon-name", "data-success")
        elif validation == "starred":
            cell.set_property("pixbuf", None)
            cell.set_property("icon-name", "preferences-desktop-default-applications")
        else:
            cell.set_property("icon-name", None)
            cell.set_property("pixbuf", None)

    def _on_query_tooltip(self, _widget, x, y, keyboard_mode, tooltip) -> bool:
        if keyboard_mode:
            return False

        result = self.tree_view.get_path_at_pos(x, y)
        if result is None:
            return False

        path, column, _cx, _cy = result
        if path is None or column is not self.tree_view.get_column(2):
            return False

        model = self.tree_view.get_model()
        if model is None:
            return False
        iter = model.get_iter(path)
        validation = model.get_value(iter, 5)

        if validation == "verified":
            tooltip.set_text(_("Verified Account"))
            return True
        if validation == "starred":
            tooltip.set_text(_("Star Developer"))
            return True

        return False

    def _filter_packages(self, packages: list[SnapPackage], query: str) -> list[SnapPackage]:
        normalized_query = query.strip().lower()
        if not normalized_query:
            return list(packages)

        return [
            package
            for package in packages
            if normalized_query in package.name.lower()
            or normalized_query in package.version.lower()
            or normalized_query in package.publisher.lower()
            or normalized_query in package.summary.lower()
            or normalized_query in package.revision.lower()
            or normalized_query in package.tracking.lower()
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
