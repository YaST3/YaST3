"""GTK4 Flatpak package management widgets."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Literal

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import GLib, Gtk

from mast.core.flatpak import (
    FlatpakPackage,
    install_flatpak_package,
    list_flatpak_packages,
    list_remote_flatpak_packages,
    uninstall_flatpak_package,
)
from mast.core.i18n import _


class _RemoteCatalogWorker(threading.Thread):
    """Worker that loads remote package IDs outside the UI thread."""

    def __init__(
        self,
        remote: str,
        on_loaded: Callable[[list[FlatpakPackage]], bool],
        on_failed: Callable[[str], bool],
    ) -> None:
        super().__init__(daemon=True)
        self.remote = remote
        self.on_loaded = on_loaded
        self.on_failed = on_failed

    def run(self) -> None:
        try:
            packages = list_remote_flatpak_packages(self.remote)
        except Exception as e:
            GLib.idle_add(self.on_failed, str(e))
            return

        GLib.idle_add(self.on_loaded, packages)


class FlatpakPackageManager(Gtk.Box):
    """Manage Flatpak packages in search or installed mode."""

    DEFAULT_REMOTE = "flathub"
    MODE_SEARCH: Literal["search"] = "search"
    MODE_INSTALLED: Literal["installed"] = "installed"
    PAGE_SIZE = 100

    def __init__(self, mode: Literal["search", "installed"], parent_window: Gtk.ApplicationWindow, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8, **kwargs)
        self.mode = mode
        self.parent_window = parent_window

        self.remote_packages: list[FlatpakPackage] = []
        self.filtered_remote_packages: list[FlatpakPackage] = []
        self.installed_packages: list[FlatpakPackage] = []
        self.filtered_installed_packages: list[FlatpakPackage] = []
        self.installed_app_ids: set[str] = set()
        self.search_page = 0
        self.installed_page = 0
        self.remote_loading = False
        self.remote_loader: _RemoteCatalogWorker | None = None

        self._build_layout()
        self.refresh()

    def _build_layout(self) -> None:
        controls_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        if self.mode == self.MODE_SEARCH:
            self.primary_btn = Gtk.Button(label=_("Install"))
            self.primary_btn.connect("clicked", self._on_install_clicked)
        else:
            self.primary_btn = Gtk.Button(label=_("Uninstall"))
            self.primary_btn.connect("clicked", self._on_uninstall_clicked)
        controls_row.append(self.primary_btn)

        controls_row.append(Gtk.Box(hexpand=True))

        self.search_entry = Gtk.Entry()
        self.search_entry.set_placeholder_text("org.example")
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

        self._create_table()

        pager_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.prev_btn = Gtk.Button(label=_("Prev"))
        self.prev_btn.connect("clicked", self._on_prev_clicked)
        pager_row.append(self.prev_btn)

        self.page_label = Gtk.Label(label="1/1")
        pager_row.append(self.page_label)

        self.next_btn = Gtk.Button(label=_("Next"))
        self.next_btn.connect("clicked", self._on_next_clicked)
        pager_row.append(self.next_btn)
        pager_row.append(Gtk.Box(hexpand=True))
        self.append(pager_row)

    def _create_table(self) -> None:
        if self.mode == self.MODE_SEARCH:
            self.list_store = Gtk.ListStore(str, str, str, str, str, str, str, str, str)
            columns = [
                (_("ID"), 0),
                (_("Name"), 1),
                (_("Description"), 2),
                (_("Version"), 3),
                (_("Download Size"), 4),
                (_("Branch"), 5),
                (_("Remote"), 6),
                (_("Scope"), 7),
                (_("Installed"), 8),
            ]
        else:
            self.list_store = Gtk.ListStore(str, str, str, str, str, str, str, str)
            columns = [
                (_("ID"), 0),
                (_("Name"), 1),
                (_("Description"), 2),
                (_("Version"), 3),
                (_("Installed Size"), 4),
                (_("Branch"), 5),
                (_("Remote"), 6),
                (_("Scope"), 7),
            ]

        self.tree_view = Gtk.TreeView(model=self.list_store)
        self.tree_view.set_hexpand(True)
        self.tree_view.set_vexpand(True)
        self.selection = self.tree_view.get_selection()
        self.selection.set_mode(Gtk.SelectionMode.SINGLE)

        for title, index in columns:
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(title, renderer, text=index)
            column.set_resizable(True)
            self.tree_view.append_column(column)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_child(self.tree_view)
        self.append(scrolled)

    def refresh(self) -> None:
        if self.mode == self.MODE_SEARCH:
            self.load_remote_packages()
            self.load_installed_packages(refresh_current=True)
        else:
            self.load_installed_packages(refresh_current=True)

    def _set_remote_loading(self, loading: bool) -> None:
        if self.mode != self.MODE_SEARCH:
            return

        self.remote_loading = loading
        self.refresh_btn.set_label(_("Loading...") if loading else _("Refresh"))
        self.primary_btn.set_sensitive(not loading)
        self.search_btn.set_sensitive(not loading)
        self.reset_btn.set_sensitive(not loading)
        self.refresh_btn.set_sensitive(not loading)

    def load_remote_packages(self) -> None:
        if self.mode != self.MODE_SEARCH:
            return

        if self.remote_loader is not None:
            return

        self._set_remote_loading(True)
        self.remote_loader = _RemoteCatalogWorker(
            self.DEFAULT_REMOTE,
            on_loaded=self._on_remote_packages_loaded,
            on_failed=self._on_remote_packages_failed,
        )
        self.remote_loader.start()

    def _on_remote_packages_loaded(self, packages: list[FlatpakPackage]) -> bool:
        if self.mode != self.MODE_SEARCH:
            self._on_remote_loader_finished()
            return False

        self.remote_packages = packages
        self.filtered_remote_packages = self._filter_packages(self.remote_packages, self.search_entry.get_text().strip())
        self.search_page = 0
        self._populate_table()
        self._on_remote_loader_finished()
        return False

    def _on_remote_packages_failed(self, error: str) -> bool:
        if self.mode != self.MODE_SEARCH:
            self._on_remote_loader_finished()
            return False

        self._show_message_dialog(
            Gtk.MessageType.ERROR,
            _("Error"),
            _("Failed to load package catalog: {0}").format(error),
        )
        self.remote_packages = []
        self.filtered_remote_packages = []
        self.search_page = 0
        self._populate_table()
        self._on_remote_loader_finished()
        return False

    def _on_remote_loader_finished(self) -> None:
        self.remote_loader = None
        self._set_remote_loading(False)

    def load_installed_packages(self, refresh_current: bool = True) -> None:
        try:
            self.installed_packages = list_flatpak_packages()
            self.installed_app_ids = {pkg.app_id for pkg in self.installed_packages}
        except Exception as e:
            self._show_message_dialog(
                Gtk.MessageType.ERROR,
                _("Error"),
                _("Failed to load packages: {0}").format(str(e)),
            )
            self.installed_packages = []
            self.installed_app_ids = set()

        if self.mode == self.MODE_INSTALLED:
            self.filtered_installed_packages = self._filter_packages(
                self.installed_packages,
                self.search_entry.get_text().strip(),
            )
            self.installed_page = 0
            self._populate_table()
            return

        if refresh_current:
            self._populate_table()

    def _on_search_clicked(self, _widget) -> None:
        query = self.search_entry.get_text().strip()
        if self.mode == self.MODE_SEARCH:
            self.filtered_remote_packages = self._filter_packages(self.remote_packages, query)
            self.search_page = 0
        else:
            self.filtered_installed_packages = self._filter_packages(self.installed_packages, query)
            self.installed_page = 0
        self._populate_table()

    def _on_reset_clicked(self, _button: Gtk.Button) -> None:
        self.search_entry.set_text("")
        if self.mode == self.MODE_SEARCH:
            self.filtered_remote_packages = list(self.remote_packages)
            self.search_page = 0
        else:
            self.filtered_installed_packages = list(self.installed_packages)
            self.installed_page = 0
        self._populate_table()

    def _on_refresh_clicked(self, _button: Gtk.Button) -> None:
        self.refresh()

    def _selected_package(self) -> FlatpakPackage | None:
        model, tree_iter = self.selection.get_selected()
        if tree_iter is None:
            return None

        path = model.get_path(tree_iter)
        index = int(path.to_string())
        page_items = self._page_items()
        if 0 <= index < len(page_items):
            return page_items[index]
        return None

    def _on_install_clicked(self, _button: Gtk.Button) -> None:
        package = self._selected_package()
        if package is None:
            self._show_message_dialog(
                Gtk.MessageType.INFO,
                _("Information"),
                _("Please select a package from the list to install."),
            )
            return

        if package.app_id in self.installed_app_ids:
            self._show_message_dialog(
                Gtk.MessageType.INFO,
                _("Information"),
                _("The selected package is already installed."),
            )
            return

        try:
            install_flatpak_package(package.app_id, package.remote or self.DEFAULT_REMOTE, package.scope)
            self._show_message_dialog(Gtk.MessageType.INFO, _("Success"), _("Package installed successfully."))
            self.refresh()
        except Exception as e:
            self._show_message_dialog(
                Gtk.MessageType.ERROR,
                _("Error"),
                _("Failed to install package: {0}").format(str(e)),
            )

    def _on_uninstall_clicked(self, _button: Gtk.Button) -> None:
        package = self._selected_package()
        if package is None:
            self._show_message_dialog(
                Gtk.MessageType.INFO,
                _("Information"),
                _("Please select an installed package from the list."),
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
            _("Are you sure you want to uninstall package '{0}'?").format(package.app_id),
        )
        confirm_dialog.connect("response", self._on_uninstall_confirm, package)
        confirm_dialog.present()

    def _on_uninstall_confirm(self, dialog: Gtk.MessageDialog, response_id: Gtk.ResponseType, package: FlatpakPackage) -> None:
        dialog.destroy()
        if response_id != Gtk.ResponseType.YES:
            return

        try:
            uninstall_flatpak_package(package.app_id, package.scope)
            self._show_message_dialog(Gtk.MessageType.INFO, _("Success"), _("Package uninstalled successfully."))
            self.refresh()
        except Exception as e:
            self._show_message_dialog(
                Gtk.MessageType.ERROR,
                _("Error"),
                _("Failed to uninstall package: {0}").format(str(e)),
            )

    def _on_prev_clicked(self, _button: Gtk.Button) -> None:
        if self.mode == self.MODE_SEARCH:
            if self.search_page <= 0:
                return
            self.search_page -= 1
        else:
            if self.installed_page <= 0:
                return
            self.installed_page -= 1
        self._populate_table()

    def _on_next_clicked(self, _button: Gtk.Button) -> None:
        items = self.filtered_remote_packages if self.mode == self.MODE_SEARCH else self.filtered_installed_packages
        total_pages = self._total_pages(len(items))
        if self.mode == self.MODE_SEARCH:
            if self.search_page + 1 >= total_pages:
                return
            self.search_page += 1
        else:
            if self.installed_page + 1 >= total_pages:
                return
            self.installed_page += 1
        self._populate_table()

    def _page_items(self) -> list[FlatpakPackage]:
        if self.mode == self.MODE_SEARCH:
            start = self.search_page * self.PAGE_SIZE
            end = start + self.PAGE_SIZE
            return self.filtered_remote_packages[start:end]

        start = self.installed_page * self.PAGE_SIZE
        end = start + self.PAGE_SIZE
        return self.filtered_installed_packages[start:end]

    def _populate_table(self) -> None:
        self.list_store.clear()
        for package in self._page_items():
            if self.mode == self.MODE_SEARCH:
                installed_text = _("Yes") if package.app_id in self.installed_app_ids else _("No")
                self.list_store.append(
                    [
                        package.app_id,
                        package.name,
                        package.description,
                        package.version,
                        package.download_size,
                        package.branch,
                        package.remote,
                        package.scope,
                        installed_text,
                    ]
                )
            else:
                self.list_store.append(
                    [
                        package.app_id,
                        package.name,
                        package.description,
                        package.version,
                        package.installed_size,
                        package.branch,
                        package.remote,
                        package.scope,
                    ]
                )

        if self.mode == self.MODE_SEARCH:
            total = len(self.filtered_remote_packages)
            current_page = self.search_page
        else:
            total = len(self.filtered_installed_packages)
            current_page = self.installed_page

        total_pages = self._total_pages(total)
        self.page_label.set_text(f"{current_page + 1}/{total_pages}")
        self.prev_btn.set_sensitive(current_page > 0)
        self.next_btn.set_sensitive(current_page + 1 < total_pages)

    def _total_pages(self, total_rows: int) -> int:
        if total_rows <= 0:
            return 1
        return (total_rows + self.PAGE_SIZE - 1) // self.PAGE_SIZE

    def _filter_packages(self, packages: list[FlatpakPackage], query: str) -> list[FlatpakPackage]:
        normalized_query = query.strip().lower()
        if not normalized_query:
            return list(packages)

        return [
            package
            for package in packages
            if normalized_query in package.app_id.lower()
            or normalized_query in package.name.lower()
            or normalized_query in package.description.lower()
            or normalized_query in package.version.lower()
            or normalized_query in package.installed_size.lower()
            or normalized_query in package.download_size.lower()
            or normalized_query in package.branch.lower()
            or normalized_query in package.remote.lower()
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
