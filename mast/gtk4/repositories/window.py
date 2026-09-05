"""UI components for the Repositories module (GTK4)."""

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk

from mast.core.i18n import _
from mast.core.repositories import (
    RepoEntry,
    delete_repo_entry,
    save_repo_entry,
    switch_mirror,
)
from mast.gtk4.repositories.import_repo_button import ImportRepoButton
from mast.gtk4.repositories.repo_edit_dialog import RepoEditDialog
from mast.gtk4.repositories.switch_mirror_dialog import SwitchMirrorDialog


class RepositoriesWindow(Gtk.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.repo_entries: list[RepoEntry] = []

        self.set_default_size(1200, 600)

        # Main container
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.main_box.set_margin_top(8)
        self.main_box.set_margin_bottom(8)
        self.main_box.set_margin_start(8)
        self.main_box.set_margin_end(8)

        # Button bar
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        self.add_btn = Gtk.Button(label=_("Add"))
        self.add_btn.connect("clicked", self._on_add_clicked)
        button_box.append(self.add_btn)

        self.import_btn = ImportRepoButton(self._on_import_repo_selected)
        button_box.append(self.import_btn)

        self.edit_btn = Gtk.Button(label=_("Edit"))
        self.edit_btn.connect("clicked", self._on_edit_clicked)
        button_box.append(self.edit_btn)

        self.delete_btn = Gtk.Button(label=_("Delete"))
        self.delete_btn.connect("clicked", self._on_delete_clicked)
        button_box.append(self.delete_btn)

        self.switch_mirror_btn = Gtk.Button(label=_("Switch Mirror"))
        self.switch_mirror_btn.connect("clicked", self._on_switch_mirror_clicked)
        button_box.append(self.switch_mirror_btn)

        self.main_box.append(button_box)

        # Create list view
        self._create_list_view()

        self.set_child(self.main_box)

        # Load repos
        self._load_repos()

    def _create_list_view(self) -> None:
        """Create the list view for repositories."""
        # Create list store
        self.list_store = Gtk.ListStore(str, str, int, bool, bool)

        # Create tree view
        self.tree_view = Gtk.TreeView(model=self.list_store)
        self.tree_view.set_hexpand(True)
        self.tree_view.set_vexpand(True)

        # Name column
        name_renderer = Gtk.CellRendererText()
        name_column = Gtk.TreeViewColumn(_("Name"), name_renderer, text=0)
        name_column.set_resizable(True)
        name_column.set_min_width(200)
        self.tree_view.append_column(name_column)

        # URL column
        url_renderer = Gtk.CellRendererText()
        url_column = Gtk.TreeViewColumn(_("URL"), url_renderer, text=1)
        url_column.set_resizable(True)
        self.tree_view.append_column(url_column)

        # Priority column
        priority_renderer = Gtk.CellRendererText()
        priority_column = Gtk.TreeViewColumn(_("Priority"), priority_renderer, text=2)
        priority_column.set_resizable(True)
        priority_column.set_min_width(60)
        self.tree_view.append_column(priority_column)

        # Enabled column
        enabled_renderer = Gtk.CellRendererToggle()
        enabled_renderer.connect("toggled", self._on_enabled_toggled)
        enabled_column = Gtk.TreeViewColumn(_("Enabled"), enabled_renderer, active=3)
        enabled_column.set_resizable(True)
        enabled_column.set_min_width(60)
        self.tree_view.append_column(enabled_column)

        # Auto Refresh column
        autorefresh_renderer = Gtk.CellRendererToggle()
        autorefresh_renderer.connect("toggled", self._on_autorefresh_toggled)
        autorefresh_column = Gtk.TreeViewColumn(_("Auto Refresh"), autorefresh_renderer, active=4)
        autorefresh_column.set_resizable(True)
        autorefresh_column.set_min_width(80)
        self.tree_view.append_column(autorefresh_column)

        # Selection
        self.selection = self.tree_view.get_selection()
        self.selection.set_mode(Gtk.SelectionMode.SINGLE)

        # Add tree view to scrolled window
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_child(self.tree_view)
        self.main_box.append(scrolled)

    def _load_repos(self) -> None:
        """Load repositories from /etc/zypp/repos.d/*.repo files."""
        self.repo_entries.clear()
        self.list_store.clear()

        try:
            self.repo_entries = RepoEntry.load_repos()
        except PermissionError:
            self._show_message_dialog(Gtk.MessageType.WARNING, _("Error"), _("Cannot read repository directory. Root permission required."))
            return

        self._populate_list()

    def _populate_list(self) -> None:
        """Populate the list with repository entries."""
        for entry in self.repo_entries:
            self.list_store.append([
                entry.name,
                entry.url,
                entry.priority,
                entry.enabled,
                entry.autorefresh,
            ])

    def _on_enabled_toggled(self, renderer, path) -> None:
        """Handle enabled toggle."""
        index = int(path)
        if 0 <= index < len(self.repo_entries):
            self.repo_entries[index].enabled = not self.repo_entries[index].enabled
            # Update the list store
            tree_iter = self.list_store.get_iter(path)
            self.list_store.set_value(tree_iter, 3, self.repo_entries[index].enabled)
            # Save the single entry
            self._save_single_entry(index)

    def _on_autorefresh_toggled(self, renderer, path) -> None:
        """Handle autorefresh toggle."""
        index = int(path)
        if 0 <= index < len(self.repo_entries):
            self.repo_entries[index].autorefresh = not self.repo_entries[index].autorefresh
            # Update the list store
            tree_iter = self.list_store.get_iter(path)
            self.list_store.set_value(tree_iter, 4, self.repo_entries[index].autorefresh)
            # Save the single entry
            self._save_single_entry(index)

    def _save_single_entry(self, index: int) -> None:
        """Save a single repository entry."""
        entry = self.repo_entries[index]
        result = save_repo_entry(entry)
        if result != "ok":
            self._handle_save_error(result)
            # Revert the change
            entry.enabled = not entry.enabled
            self._populate_list()

    def _on_add_clicked(self, button: Gtk.Button) -> None:
        """Add a new repository."""
        dialog = RepoEditDialog(self)
        dialog.connect("response", self._on_add_dialog_response)
        dialog.present()

    def _on_add_dialog_response(self, dialog, response_id) -> None:
        """Handle add dialog response."""
        if response_id == Gtk.ResponseType.OK:
            values = dialog.get_values()
            repo_id = values["id"]
            url = values["baseurl"] or values["mirrorlist"]

            if not repo_id:
                self._show_message_dialog(Gtk.MessageType.WARNING, _("Error"), _("Repository ID is required."))
                dialog.destroy()
                return
            if not url:
                self._show_message_dialog(Gtk.MessageType.WARNING, _("Error"), _("URL is required."))
                dialog.destroy()
                return

            new_entry = RepoEntry(
                id=repo_id,
                name=values["name"],
                enabled=values["enabled"],
                autorefresh=values["autorefresh"],
                baseurl=values["baseurl"],
                mirrorlist=values["mirrorlist"],
                path=values["path"],
                type=values["type"],
                gpgcheck=values["gpgcheck"],
                gpgkey=values["gpgkey"],
                priority=values["priority"],
                keep_packages=values["keep_packages"],
            )
            self.repo_entries.append(new_entry)
            self._populate_list()

            result = save_repo_entry(new_entry)
            if result != "ok":
                self._handle_save_error(result)
        dialog.destroy()

    def _on_import_repo_selected(self, entry: RepoEntry) -> None:
        """Import a predefined third-party repository."""
        if any(entry.id == existing_entry.id for existing_entry in self.repo_entries):
            self._show_message_dialog(
                Gtk.MessageType.INFO,
                _("Information"),
                _("Repository '{}' already exists.").format(entry.name),
            )
            return

        result = save_repo_entry(entry)
        if result != "ok":
            self._show_message_dialog(
                Gtk.MessageType.ERROR,
                _("Error"),
                _("Failed to import repository: %s") % result,
            )
            return

        self._show_message_dialog(
            Gtk.MessageType.INFO,
            _("Success"),
            _("Repository '{}' imported successfully.").format(entry.name),
        )
        self._load_repos()

    def _on_edit_clicked(self, button: Gtk.Button) -> None:
        """Edit the selected repository."""
        model, tree_iter = self.selection.get_selected()
        if tree_iter is None:
            self._show_message_dialog(Gtk.MessageType.INFO, _("Information"), _("Please select a repository to edit."))
            return

        path = model.get_path(tree_iter)
        index = int(path.to_string())
        entry = self.repo_entries[index]

        dialog = RepoEditDialog(self, entry)
        dialog.connect("response", self._on_edit_dialog_response, index)
        dialog.present()

    def _on_edit_dialog_response(self, dialog, response_id, index: int) -> None:
        """Handle edit dialog response."""
        if response_id == Gtk.ResponseType.OK:
            values = dialog.get_values()
            repo_id = values["id"]
            url = values["baseurl"] or values["mirrorlist"]

            if not repo_id:
                self._show_message_dialog(Gtk.MessageType.WARNING, _("Error"), _("Repository ID is required."))
                dialog.destroy()
                return
            if not url:
                self._show_message_dialog(Gtk.MessageType.WARNING, _("Error"), _("URL is required."))
                dialog.destroy()
                return

            entry = self.repo_entries[index]
            self.repo_entries[index] = RepoEntry(
                id=repo_id,
                name=values["name"],
                enabled=values["enabled"],
                autorefresh=values["autorefresh"],
                baseurl=values["baseurl"],
                mirrorlist=values["mirrorlist"],
                path=values["path"],
                type=values["type"],
                gpgcheck=values["gpgcheck"],
                gpgkey=values["gpgkey"],
                priority=values["priority"],
                keep_packages=values["keep_packages"],
            )
            self._populate_list()

            result = save_repo_entry(self.repo_entries[index])
            if result != "ok":
                self._handle_save_error(result)
        dialog.destroy()

    def _on_delete_clicked(self, button: Gtk.Button) -> None:
        """Delete the selected repository."""
        model, tree_iter = self.selection.get_selected()
        if tree_iter is None:
            self._show_message_dialog(Gtk.MessageType.INFO, _("Information"), _("Please select a repository to delete."))
            return

        path = model.get_path(tree_iter)
        index = int(path.to_string())
        entry = self.repo_entries[index]

        # Show confirmation dialog
        confirm_dialog = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=_("Confirm"),
        )
        confirm_dialog.set_property("secondary-text", 
            _("Are you sure you want to delete repository '{}'?"
            ).format(entry.name)
        )
        confirm_dialog.connect("response", self._on_delete_confirm_response, tree_iter, index)
        confirm_dialog.present()

    def _on_delete_confirm_response(self, dialog, response_id, tree_iter, index: int) -> None:
        """Handle delete confirmation response."""
        if response_id == Gtk.ResponseType.YES:
            entry = self.repo_entries[index]
            result = delete_repo_entry(entry)
            if result == "ok":
                self.repo_entries.pop(index)
                self.list_store.remove(tree_iter)
            else:
                self._handle_save_error(result)
        dialog.destroy()

    def _on_switch_mirror_clicked(self, button: Gtk.Button) -> None:
        """Switch mirrors for openSUSE and Packman repositories."""
        dialog = SwitchMirrorDialog(self)
        dialog.connect("response", self._on_switch_mirror_response)
        dialog.present()

    def _on_switch_mirror_response(self, dialog, response_id) -> None:
        """Handle switch mirror dialog response."""
        if response_id == Gtk.ResponseType.OK:
            values = dialog.get_values()
            opensuse_url = values["opensuse_mirror"]
            packman_url = values["packman_mirror"]

            confirm_dialog = Gtk.MessageDialog(
                transient_for=self,
                modal=True,
                message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.YES_NO,
                text=_("Confirm"),
            )
            confirm_dialog.set_property("secondary-text", 
                _("Are you sure you want to switch mirrors?\n\nopenSUSE mirror: {}\nPackman mirror: {}").format(
                    opensuse_url, packman_url
                )
            )
            confirm_dialog.connect("response", self._on_switch_mirror_confirm, opensuse_url, packman_url)
            confirm_dialog.present()
        dialog.destroy()

    def _on_switch_mirror_confirm(self, dialog, response_id, opensuse_url: str, packman_url: str) -> None:
        """Handle switch mirror confirmation response."""
        if response_id == Gtk.ResponseType.YES:
            result = switch_mirror(opensuse_url, packman_url)
            if result == "ok":
                self._show_message_dialog(Gtk.MessageType.INFO, _("Success"), _("Mirror switching completed successfully."))
                self._load_repos()
            else:
                self._handle_save_error(result)
        dialog.destroy()

    def _handle_save_error(self, result: str) -> None:
        """Handle save error."""
        if result == "permission_denied":
            self._show_message_dialog(Gtk.MessageType.ERROR, _("Error"), _("Cannot write to repository directory. Root permission required."))
        elif result == "pkexec_failed":
            self._show_message_dialog(Gtk.MessageType.ERROR, _("Error"), _("Authentication failed or pkexec not available."))
        else:
            self._show_message_dialog(Gtk.MessageType.ERROR, _("Error"), _("Failed to save repository configuration."))

    def _show_message_dialog(self, msg_type: Gtk.MessageType, title: str, message: str) -> None:
        """Show a message dialog."""
        dialog = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            message_type=msg_type,
            buttons=Gtk.ButtonsType.OK,
            text=title,
        )
        dialog.set_property("secondary-text", message)
        dialog.connect("response", lambda d, r: d.destroy())
        dialog.present()