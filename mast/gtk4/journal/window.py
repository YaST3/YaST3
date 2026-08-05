"""UI components for the Journal module (GTK4)."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk

from mast.core.i18n import _
from mast.core.journal import (
    JournalEntry,
    JournalConfig,
    get_journal_entries,
    get_journal_config,
    set_journal_config,
    clear_journal,
    PRIORITY_LEVELS,
)


class JournalWindow(Gtk.ApplicationWindow):
    """GTK4 window for managing journal logs."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.system_entries: list[JournalEntry] = []
        self.user_entries: list[JournalEntry] = []
        self.current_scope = "system"
        self.config: JournalConfig | None = None

        self.set_default_size(1280, 720)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.main_box.set_margin_top(8)
        self.main_box.set_margin_bottom(8)
        self.main_box.set_margin_start(8)
        self.main_box.set_margin_end(8)

        self._create_tabs()
        self._create_config_panel()

        self.set_child(self.main_box)

        self.load_journal("system")

    def _create_tabs(self) -> None:
        self.notebook = Gtk.Notebook()
        self.notebook.set_scrollable(True)

        self.system_tab = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.system_tab.set_hexpand(True)
        self.system_tab.set_vexpand(True)

        self.user_tab = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.user_tab.set_hexpand(True)
        self.user_tab.set_vexpand(True)

        self.config_tab = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.config_tab.set_hexpand(True)
        self.config_tab.set_vexpand(True)

        self.notebook.append_page(self.system_tab, Gtk.Label(label=_("System")))
        self.notebook.append_page(self.user_tab, Gtk.Label(label=_("User")))
        self.notebook.append_page(self.config_tab, Gtk.Label(label=_("Configuration")))

        self.notebook.connect("switch-page", self._on_tab_changed)
        self.main_box.append(self.notebook)

        self._create_system_log_page()
        self._create_user_log_page()

    def _create_system_log_page(self) -> None:
        filters_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        filters_box.append(Gtk.Label(label=_("Priority")))
        self.system_priority_filter = Gtk.ComboBoxText()
        self.system_priority_filter.append("all", _("All"))
        for level in PRIORITY_LEVELS:
            self.system_priority_filter.append(level, level.capitalize())
        self.system_priority_filter.set_active_id("all")
        self.system_priority_filter.connect("changed", self._on_system_filters_changed)
        filters_box.append(self.system_priority_filter)

        filters_box.append(Gtk.Label(label=_("Search")))
        self.system_search_entry = Gtk.Entry()
        self.system_search_entry.set_placeholder_text(_("Search messages"))
        self.system_search_entry.set_hexpand(True)
        self.system_search_entry.connect("changed", self._on_system_filters_changed)
        filters_box.append(self.system_search_entry)

        self.system_refresh_btn = Gtk.Button(label=_("Refresh"))
        self.system_refresh_btn.connect("clicked", lambda _button: self.load_journal("system"))
        filters_box.append(self.system_refresh_btn)

        self.system_tab.append(filters_box)

        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.system_clear_btn = Gtk.Button(label=_("Clear"))
        self.system_clear_btn.connect("clicked", lambda _button: self._clear_journal("system"))
        action_box.append(self.system_clear_btn)
        action_box.append(Gtk.Box(hexpand=True))
        self.system_tab.append(action_box)

        self.system_list_store = Gtk.ListStore(str, str, str, str, str, str)
        self.system_tree_view = Gtk.TreeView(model=self.system_list_store)
        self.system_tree_view.set_hexpand(True)
        self.system_tree_view.set_vexpand(True)

        self._add_columns(self.system_tree_view)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_child(self.system_tree_view)
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)
        self.system_tab.append(scrolled)

    def _create_user_log_page(self) -> None:
        filters_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        filters_box.append(Gtk.Label(label=_("Priority")))
        self.user_priority_filter = Gtk.ComboBoxText()
        self.user_priority_filter.append("all", _("All"))
        for level in PRIORITY_LEVELS:
            self.user_priority_filter.append(level, level.capitalize())
        self.user_priority_filter.set_active_id("all")
        self.user_priority_filter.connect("changed", self._on_user_filters_changed)
        filters_box.append(self.user_priority_filter)

        filters_box.append(Gtk.Label(label=_("Search")))
        self.user_search_entry = Gtk.Entry()
        self.user_search_entry.set_placeholder_text(_("Search messages"))
        self.user_search_entry.set_hexpand(True)
        self.user_search_entry.connect("changed", self._on_user_filters_changed)
        filters_box.append(self.user_search_entry)

        self.user_refresh_btn = Gtk.Button(label=_("Refresh"))
        self.user_refresh_btn.connect("clicked", lambda _button: self.load_journal("user"))
        filters_box.append(self.user_refresh_btn)

        self.user_tab.append(filters_box)

        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.user_clear_btn = Gtk.Button(label=_("Clear"))
        self.user_clear_btn.connect("clicked", lambda _button: self._clear_journal("user"))
        action_box.append(self.user_clear_btn)
        action_box.append(Gtk.Box(hexpand=True))
        self.user_tab.append(action_box)

        self.user_list_store = Gtk.ListStore(str, str, str, str, str, str)
        self.user_tree_view = Gtk.TreeView(model=self.user_list_store)
        self.user_tree_view.set_hexpand(True)
        self.user_tree_view.set_vexpand(True)

        self._add_columns(self.user_tree_view)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_child(self.user_tree_view)
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)
        self.user_tab.append(scrolled)

    def _add_columns(self, tree_view: Gtk.TreeView) -> None:
        time_renderer = Gtk.CellRendererText()
        time_column = Gtk.TreeViewColumn(_("Time"), time_renderer, text=0)
        time_column.set_resizable(True)
        time_column.set_min_width(180)
        tree_view.append_column(time_column)

        priority_renderer = Gtk.CellRendererText()
        priority_column = Gtk.TreeViewColumn(_("Priority"), priority_renderer, text=1, foreground=5)
        priority_column.set_resizable(True)
        priority_column.set_min_width(100)
        tree_view.append_column(priority_column)

        unit_renderer = Gtk.CellRendererText()
        unit_column = Gtk.TreeViewColumn(_("Unit"), unit_renderer, text=2)
        unit_column.set_resizable(True)
        unit_column.set_min_width(200)
        tree_view.append_column(unit_column)

        message_renderer = Gtk.CellRendererText()
        message_column = Gtk.TreeViewColumn(_("Message"), message_renderer, text=3)
        message_column.set_resizable(True)
        message_column.set_expand(True)
        tree_view.append_column(message_column)

    def _create_config_panel(self) -> None:
        grid = Gtk.Grid()
        grid.set_margin_top(16)
        grid.set_margin_bottom(16)
        grid.set_margin_start(16)
        grid.set_margin_end(16)
        grid.set_row_spacing(12)
        grid.set_column_spacing(12)

        row = 0

        grid.attach(Gtk.Label(label=_("Max File Size (e.g., 500M, 1G)")), 0, row, 1, 1)
        self.max_size_entry = Gtk.Entry()
        self.max_size_entry.set_placeholder_text(_("SystemMaxUse"))
        grid.attach(self.max_size_entry, 1, row, 1, 1)
        row += 1

        grid.attach(Gtk.Label(label=_("Max Number of Files")), 0, row, 1, 1)
        self.max_files_entry = Gtk.Entry()
        self.max_files_entry.set_placeholder_text(_("SystemMaxFiles"))
        grid.attach(self.max_files_entry, 1, row, 1, 1)
        row += 1

        grid.attach(Gtk.Label(label=_("Compress")), 0, row, 1, 1)
        self.compress_switch = Gtk.Switch()
        self.compress_switch.set_halign(Gtk.Align.START)
        grid.attach(self.compress_switch, 1, row, 1, 1)
        row += 1

        grid.attach(Gtk.Label(label=_("Rate Limit Interval (e.g., 30s)")), 0, row, 1, 1)
        self.rate_interval_entry = Gtk.Entry()
        self.rate_interval_entry.set_placeholder_text(_("RateLimitInterval"))
        grid.attach(self.rate_interval_entry, 1, row, 1, 1)
        row += 1

        grid.attach(Gtk.Label(label=_("Rate Limit Burst")), 0, row, 1, 1)
        self.rate_burst_entry = Gtk.Entry()
        self.rate_burst_entry.set_placeholder_text(_("RateLimitBurst"))
        grid.attach(self.rate_burst_entry, 1, row, 1, 1)
        row += 1

        self.save_config_btn = Gtk.Button(label=_("Save Configuration"))
        self.save_config_btn.connect("clicked", lambda _button: self._save_config())
        grid.attach(self.save_config_btn, 0, row, 2, 1)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_child(grid)
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)
        self.config_tab.append(scrolled)

    def _on_tab_changed(self, _notebook, _page, page_num) -> None:
        if page_num == 0:
            self.current_scope = "system"
        elif page_num == 1:
            self.current_scope = "user"
        elif page_num == 2:
            self.load_config()

    def _on_system_filters_changed(self, _widget) -> None:
        self.apply_filters("system")

    def _on_user_filters_changed(self, _widget) -> None:
        self.apply_filters("user")

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

    def load_journal(self, scope: str) -> None:
        try:
            if scope == "system":
                self.system_entries = get_journal_entries(scope="system")
                self.apply_filters("system")
            else:
                self.user_entries = get_journal_entries(scope="user")
                self.apply_filters("user")
        except Exception as error:
            self._show_message_dialog(
                Gtk.MessageType.ERROR,
                _("Error"),
                _("Failed to load journal: {0}").format(str(error)),
            )

    def apply_filters(self, scope: str) -> None:
        if scope == "system":
            priority_filter = self.system_priority_filter.get_active_id() or "all"
            search_text = self.system_search_entry.get_text().strip().lower()
            entries = self.system_entries
            list_store = self.system_list_store
        else:
            priority_filter = self.user_priority_filter.get_active_id() or "all"
            search_text = self.user_search_entry.get_text().strip().lower()
            entries = self.user_entries
            list_store = self.user_list_store

        filtered = []
        for entry in entries:
            if priority_filter != "all":
                priority_idx = PRIORITY_LEVELS.index(priority_filter)
                if entry.priority_num > priority_idx:
                    continue
            if search_text and search_text not in entry.message.lower():
                continue
            filtered.append(entry)

        self.populate_list(list_store, filtered)

    def populate_list(self, list_store: Gtk.ListStore, entries: list[JournalEntry]) -> None:
        list_store.clear()
        for entry in entries:
            list_store.append(
                [
                    entry.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    entry.priority.capitalize(),
                    entry.systemd_unit,
                    entry.message,
                    str(entry.process_id) if entry.process_id else "",
                    entry.priority_color(),
                ]
            )

    def load_config(self) -> None:
        try:
            self.config = get_journal_config()
            if self.config.max_file_size:
                self.max_size_entry.set_text(self.config.max_file_size)
            if self.config.max_files:
                self.max_files_entry.set_text(str(self.config.max_files))
            if self.config.compress is not None:
                self.compress_switch.set_active(self.config.compress)
            if self.config.rate_limit_interval:
                self.rate_interval_entry.set_text(self.config.rate_limit_interval)
            if self.config.rate_limit_burst:
                self.rate_burst_entry.set_text(str(self.config.rate_limit_burst))
        except Exception as error:
            self._show_message_dialog(
                Gtk.MessageType.ERROR,
                _("Error"),
                _("Failed to load configuration: {0}").format(str(error)),
            )

    def _save_config(self) -> None:
        config = JournalConfig()
        config.max_file_size = self.max_size_entry.get_text().strip() or None
        config.max_files = int(self.max_files_entry.get_text().strip()) if self.max_files_entry.get_text().strip() else None
        config.compress = self.compress_switch.get_active()
        config.rate_limit_interval = self.rate_interval_entry.get_text().strip() or None
        config.rate_limit_burst = int(self.rate_burst_entry.get_text().strip()) if self.rate_burst_entry.get_text().strip() else None

        try:
            success = set_journal_config(config)
            if success:
                self._show_message_dialog(
                    Gtk.MessageType.INFO,
                    _("Success"),
                    _("Journal configuration saved successfully."),
                )
            else:
                self._show_message_dialog(
                    Gtk.MessageType.ERROR,
                    _("Error"),
                    _("Failed to save journal configuration."),
                )
        except Exception as error:
            self._show_message_dialog(
                Gtk.MessageType.ERROR,
                _("Error"),
                _("Failed to save configuration: {0}").format(str(error)),
            )

    def _clear_journal(self, scope: str) -> None:
        dialog = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text=_("Clear Journal"),
        )
        dialog.set_property("secondary-text", _("Are you sure you want to clear all journal logs?"))

        def on_response(dialog, response):
            dialog.destroy()
            if response == Gtk.ResponseType.OK:
                try:
                    success = clear_journal(scope)
                    if success:
                        self._show_message_dialog(
                            Gtk.MessageType.INFO,
                            _("Success"),
                            _("Journal cleared successfully."),
                        )
                        self.load_journal(scope)
                    else:
                        self._show_message_dialog(
                            Gtk.MessageType.ERROR,
                            _("Error"),
                            _("Failed to clear journal."),
                        )
                except Exception as error:
                    self._show_message_dialog(
                        Gtk.MessageType.ERROR,
                        _("Error"),
                        _("Failed to clear journal: {0}").format(str(error)),
                    )

        dialog.connect("response", on_response)
        dialog.present()
