"""GTK4 Snap package management widgets."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Literal

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import GLib, Gtk

from mast.core.i18n import _
from mast.core.snap import SnapPackage, install_snap_package, list_snap_packages, search_snap_packages, uninstall_snap_package


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
    """Manage snap packages in search or installed mode."""

    MODE_SEARCH: Literal["search"] = "search"
    MODE_INSTALLED: Literal["installed"] = "installed"
    PAGE_SIZE = 100

    def __init__(self, mode: Literal["search", "installed"], parent_window: Gtk.ApplicationWindow, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8, **kwargs)
        self.mode = mode
        self.parent_window = parent_window

        self.remote_packages: list[SnapPackage] = []
        self.filtered_remote_packages: list[SnapPackage] = []
        self.installed_packages: list[SnapPackage] = []
        self.filtered_installed_packages: list[SnapPackage] = []
        self.installed_names: set[str] = set()
        self.search_page = 0
        self.installed_page = 0
        self.remote_loading = False
        self.remote_loader: _CatalogWorker | None = None
        self.installed_loading = False
        self.installed_loader: _InstalledCatalogWorker | None = None

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
        self.search_entry.set_placeholder_text("firefox")
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
            self.list_store = Gtk.ListStore(str, str, str, str, str, str)
            columns = [
                (_("Name"), 0),
                (_("Version"), 1),
                (_("Publisher"), 2),
                (_("Notes"), 3),
                (_("Summary"), 4),
                (_("Installed"), 5),
            ]
        else:
            self.list_store = Gtk.ListStore(str, str, str, str, str)
            columns = [
                (_("Name"), 0),
                (_("Version"), 1),
                (_("Revision"), 2),
                (_("Tracking"), 3),
                (_("Publisher"), 4),
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
            self.load_installed_packages()
        else:
            self.load_installed_packages()

    def _set_remote_loading(self, loading: bool) -> None:
        if self.mode != self.MODE_SEARCH:
            return

        self.remote_loading = loading
        is_loading = loading or self.installed_loading
        self.refresh_btn.set_label(_("Loading...") if is_loading else _("Refresh"))
        self.primary_btn.set_sensitive(not is_loading)
        self.search_btn.set_sensitive(not is_loading)
        self.reset_btn.set_sensitive(not is_loading)
        self.refresh_btn.set_sensitive(not is_loading)

    def load_remote_packages(self) -> None:
        if self.mode != self.MODE_SEARCH or self.remote_loader is not None:
            return

        self._set_remote_loading(True)
        self.remote_loader = _CatalogWorker(
            self.search_entry.get_text().strip(),
            on_loaded=self._on_remote_packages_loaded,
            on_failed=self._on_remote_packages_failed,
        )
        self.remote_loader.start()

    def _on_remote_packages_loaded(self, packages: list[SnapPackage]) -> bool:
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

    def load_installed_packages(self, _refresh_current: bool = True) -> None:
        if self.installed_loader is not None:
            return

        self._set_installed_loading(True)
        self.installed_loader = _InstalledCatalogWorker(
            on_loaded=self._on_installed_packages_loaded,
            on_failed=self._on_installed_packages_failed,
        )
        self.installed_loader.start()

    def _set_installed_loading(self, loading: bool) -> None:
        self.installed_loading = loading
        if self.mode == self.MODE_INSTALLED:
            is_loading = loading
        else:
            is_loading = loading or self.remote_loading
        self.refresh_btn.set_label(_("Loading...") if is_loading else _("Refresh"))
        self.primary_btn.set_sensitive(not is_loading)
        self.refresh_btn.set_sensitive(not is_loading)

    def _on_installed_packages_loaded(self, packages: list[SnapPackage]) -> bool:
        self.installed_packages = packages
        self.installed_names = {pkg.name for pkg in self.installed_packages}

        if self.mode == self.MODE_INSTALLED:
            self.filtered_installed_packages = self._filter_packages(
                self.installed_packages,
                self.search_entry.get_text().strip(),
            )
            self.installed_page = 0
            self._populate_table()
        else:
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

        if self.mode == self.MODE_INSTALLED:
            self.filtered_installed_packages = []
            self.installed_page = 0
            self._populate_table()
        else:
            self._populate_table()

        self._on_installed_loader_finished()
        return False

    def _on_installed_loader_finished(self) -> None:
        self.installed_loader = None
        self._set_installed_loading(False)

    def _on_search_clicked(self, _widget) -> None:
        if self.mode == self.MODE_SEARCH:
            self.load_remote_packages()
            return

        query = self.search_entry.get_text().strip()
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

    def _selected_package(self) -> SnapPackage | None:
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

        if package.name in self.installed_names:
            self._show_message_dialog(
                Gtk.MessageType.INFO,
                _("Information"),
                _("The selected package is already installed."),
            )
            return

        try:
            install_snap_package(package.name)
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
            _("Are you sure you want to uninstall package '{0}'?").format(package.name),
        )
        confirm_dialog.connect("response", self._on_uninstall_confirm, package)
        confirm_dialog.present()

    def _on_uninstall_confirm(self, dialog: Gtk.MessageDialog, response_id: Gtk.ResponseType, package: SnapPackage) -> None:
        dialog.destroy()
        if response_id != Gtk.ResponseType.YES:
            return

        try:
            uninstall_snap_package(package.name)
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

    def _page_items(self) -> list[SnapPackage]:
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
                installed_text = _("Yes") if package.name in self.installed_names else _("No")
                self.list_store.append(
                    [
                        package.name,
                        package.version,
                        package.publisher,
                        package.notes,
                        package.summary,
                        installed_text,
                    ]
                )
            else:
                self.list_store.append(
                    [
                        package.name,
                        package.version,
                        package.revision,
                        package.tracking,
                        package.publisher,
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
            or normalized_query in package.notes.lower()
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