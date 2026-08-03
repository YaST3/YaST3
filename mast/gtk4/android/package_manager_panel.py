"""Package manager panel for the GTK4 Android module."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk

from mast.core.i18n import _


class PackageManagerPanel(Gtk.Box):
    """Component for managing and displaying package lists and filters."""

    def __init__(self, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8, **kwargs)
        self._build_ui()

    def _build_ui(self) -> None:
        self.set_margin_start(8)
        self.set_margin_end(8)
        self.set_margin_top(8)
        self.set_margin_bottom(8)

        filter_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        self.search_entry = Gtk.Entry()
        self.search_entry.set_placeholder_text(_("Search packages"))
        self.search_entry.set_hexpand(True)
        filter_box.append(self.search_entry)

        self.blacklist_only = Gtk.CheckButton(label=_("Blacklist only"))
        filter_box.append(self.blacklist_only)

        self.system_only = Gtk.CheckButton(label=_("System apps"))
        filter_box.append(self.system_only)

        self.user_only = Gtk.CheckButton(label=_("User apps"))
        filter_box.append(self.user_only)

        self.append(filter_box)

        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        self.uninstall_btn = Gtk.Button(label=_("Uninstall"))
        self.uninstall_btn.set_sensitive(False)
        action_box.append(self.uninstall_btn)

        self.install_btn = Gtk.Button(label=_("Install APK"))
        action_box.append(self.install_btn)

        self.refresh_pkgs_btn = Gtk.Button(label=_("Refresh"))
        action_box.append(self.refresh_pkgs_btn)

        action_box.append(Gtk.Box(hexpand=True))
        self.append(action_box)

        self.package_list_store = Gtk.ListStore(str, str, str, bool, bool)
        self.package_tree = Gtk.TreeView(model=self.package_list_store)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("ID"), renderer, text=0)
        column.set_resizable(True)
        column.set_min_width(280)
        column.set_expand(True)
        self.package_tree.append_column(column)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Version"), renderer, text=1)
        column.set_resizable(True)
        column.set_min_width(120)
        self.package_tree.append_column(column)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Type"), renderer, text=2)
        column.set_resizable(True)
        column.set_min_width(80)
        self.package_tree.append_column(column)

        self.package_selection = self.package_tree.get_selection()
        self.package_selection.set_mode(Gtk.SelectionMode.SINGLE)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(self.package_tree)
        self.append(scrolled)

    def clear_packages(self) -> None:
        self.package_list_store.clear()
        self.uninstall_btn.set_sensitive(False)