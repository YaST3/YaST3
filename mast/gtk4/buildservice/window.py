"""GTK4 Build Service search window."""

from __future__ import annotations

import threading
from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk

from mast.core.buildservice import BuildServicePackage, build_install_command, search_packages
from mast.core.i18n import _
from mast.gtk4.command.action import CommandAction


class _SearchWorker(threading.Thread):
    def __init__(self, query: str, loaded: Callable[[list[BuildServicePackage]], bool], failed: Callable[[str], bool]) -> None:
        super().__init__(daemon=True)
        self.query, self.loaded, self.failed = query, loaded, failed

    def run(self) -> None:
        try:
            packages = search_packages(self.query)
        except Exception as error:
            GLib.idle_add(self.failed, str(error))
            return
        GLib.idle_add(self.loaded, packages)


class BuildServiceWindow(Gtk.ApplicationWindow):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.set_default_size(1200, 720)
        self.packages: list[BuildServicePackage] = []
        self.worker: _SearchWorker | None = None
        self.install_action: CommandAction | None = None

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(12); box.set_margin_bottom(12); box.set_margin_start(12); box.set_margin_end(12)
        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.search_entry = Gtk.SearchEntry(placeholder_text=_("Package name"), hexpand=True)
        self.search_entry.connect("activate", lambda *_args: self.search())
        controls.append(self.search_entry)
        self.search_btn = Gtk.Button(label=_("Search")); self.search_btn.connect("clicked", lambda *_args: self.search()); controls.append(self.search_btn)
        self.install_btn = Gtk.Button(label=_("Install")); self.install_btn.set_sensitive(False); self.install_btn.connect("clicked", lambda *_args: self.install_selected()); controls.append(self.install_btn)
        box.append(controls)

        self.store = Gtk.ListStore(str, str, str, str, str, str)
        self.tree = Gtk.TreeView(model=self.store)
        self.tree.get_selection().connect("changed", lambda *_args: self.install_btn.set_sensitive(self.tree.get_selection().get_selected()[1] is not None))
        for index, title in enumerate([_("Name"), _("Version"), _("Architecture"), _("Project"), _("Repository"), _("Package")]):
            column = Gtk.TreeViewColumn(title, Gtk.CellRendererText(), text=index); column.set_resizable(True); column.set_expand(index == 3); self.tree.append_column(column)
        scroll = Gtk.ScrolledWindow(); scroll.set_vexpand(True); scroll.set_child(self.tree); box.append(scroll)
        self.set_child(box)

    def search(self) -> None:
        query = self.search_entry.get_text().strip()
        if not query or self.worker is not None:
            return
        self.search_btn.set_sensitive(False); self.install_btn.set_sensitive(False); self.store.clear()
        self.worker = _SearchWorker(query, self._show_results, self._show_error); self.worker.start()

    def _show_results(self, packages: list[BuildServicePackage]) -> bool:
        self.packages = packages
        for package in packages:
            self.store.append([package.name, f"{package.version}-{package.release}", package.arch, package.project, package.repository, package.package])
        self._finish_search(); return False

    def _show_error(self, message: str) -> bool:
        dialog = Gtk.MessageDialog(transient_for=self, modal=True, message_type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.OK, text=_("Error")); dialog.set_property("secondary-text", _("Build Service search failed: {0}").format(message)); dialog.connect("response", lambda d, _r: d.close()); dialog.present(); self._finish_search(); return False

    def _finish_search(self) -> None:
        self.worker = None; self.search_btn.set_sensitive(True)

    def install_selected(self) -> None:
        model, tree_iter = self.tree.get_selection().get_selected()
        if tree_iter is None or self.install_action is not None:
            return
        package = self.packages[model.get_path(tree_iter).get_indices()[0]]
        self.install_action = CommandAction(text=_("Install"), running_text=_("Installing..."), dialog_title=_("Install Package"), command=build_install_command(package), success_output=_("Package installed successfully."), auto_close_on_success=True, parent_window=self)
        self.install_action.connect_finished(lambda *_args: setattr(self, "install_action", None))
        self.install_action.trigger()
