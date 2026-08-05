"""UI components for the Date & Time module (GTK4)."""

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk

from mast.core.i18n import _
from mast.core.datetime import (
    get_current_timezone,
    get_timezone_list,
    set_timezone,
    is_hwclock_utc,
    set_hwclock_utc,
    get_ntp_status,
    get_ntp_servers,
    set_ntp_servers,
    enable_ntp,
    disable_ntp,
    sync_time_now,
)


class DateTimeWindow(Gtk.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.set_default_size(600, 500)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.main_box.set_margin_top(16)
        self.main_box.set_margin_bottom(16)
        self.main_box.set_margin_start(16)
        self.main_box.set_margin_end(16)

        self._create_timezone_section()
        self._create_hwclock_section()
        self._create_ntp_section()
        self._create_save_button()

        self.set_child(self.main_box)

        self._load_settings()

    def _create_timezone_section(self):
        frame = Gtk.Frame(label=_("Timezone"))
        frame.set_margin_bottom(8)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)

        input_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        label = Gtk.Label(label=_("Timezone"))
        label.set_size_request(120, -1)
        label.set_halign(Gtk.Align.START)
        input_box.append(label)

        self.timezone_store = Gtk.ListStore(str)
        self.timezone_combo = Gtk.ComboBox.new_with_model_and_entry(self.timezone_store)
        self.timezone_combo.set_entry_text_column(0)
        self.timezone_combo.set_hexpand(True)

        renderer = Gtk.CellRendererText()
        self.timezone_combo.pack_start(renderer, True)
        self.timezone_combo.add_attribute(renderer, "text", 0)

        entry = self.timezone_combo.get_child()
        entry.set_placeholder_text(_("Search timezone..."))
        entry.connect("changed", self._on_timezone_search)

        input_box.append(self.timezone_combo)

        box.append(input_box)

        frame.set_child(box)
        self.main_box.append(frame)

    def _create_hwclock_section(self):
        frame = Gtk.Frame(label=_("Hardware Clock"))
        frame.set_margin_bottom(8)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)

        self.hwclock_switch = Gtk.Switch()
        self.hwclock_switch.set_halign(Gtk.Align.START)
        self.hwclock_switch.set_active(True)

        switch_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        label = Gtk.Label(label=_("Set hardware clock to UTC"))
        label.set_halign(Gtk.Align.START)
        switch_box.append(label)
        switch_box.append(self.hwclock_switch)

        box.append(switch_box)

        frame.set_child(box)
        self.main_box.append(frame)

    def _create_ntp_section(self):
        frame = Gtk.Frame(label=_("NTP Synchronization"))
        frame.set_margin_bottom(8)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)

        self.ntp_switch = Gtk.Switch()
        self.ntp_switch.set_halign(Gtk.Align.START)
        ntp_switch_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        ntp_label = Gtk.Label(label=_("Enable NTP synchronization"))
        ntp_label.set_halign(Gtk.Align.START)
        ntp_switch_box.append(ntp_label)
        ntp_switch_box.append(self.ntp_switch)
        box.append(ntp_switch_box)

        servers_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        servers_label = Gtk.Label(label=_("NTP Servers"))
        servers_label.set_size_request(120, -1)
        servers_label.set_halign(Gtk.Align.START)
        servers_box.append(servers_label)

        self.ntp_entry = Gtk.Entry()
        self.ntp_entry.set_placeholder_text(_("Enter NTP servers separated by spaces"))
        self.ntp_entry.set_hexpand(True)
        servers_box.append(self.ntp_entry)
        box.append(servers_box)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        self.sync_now_btn = Gtk.Button(label=_("Sync Now"))
        self.sync_now_btn.connect("clicked", self._on_sync_now)
        btn_box.append(self.sync_now_btn)

        box.append(btn_box)

        self.ntp_status_label = Gtk.Label(label="")
        self.ntp_status_label.set_halign(Gtk.Align.START)
        box.append(self.ntp_status_label)

        frame.set_child(box)
        self.main_box.append(frame)

    def _create_save_button(self):
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        btn_box.set_halign(Gtk.Align.END)
        btn_box.set_margin_top(12)

        self.save_btn = Gtk.Button(label=_("Save"))
        self.save_btn.add_css_class("suggested-action")
        self.save_btn.connect("clicked", self._on_save_all)
        btn_box.append(self.save_btn)

        self.main_box.append(btn_box)

    def _load_settings(self):
        try:
            timezone = get_current_timezone()
            self.all_timezones = sorted(get_timezone_list())

            self._update_timezone_store("")

            for idx, tz in enumerate(self.all_timezones):
                if tz == timezone:
                    self.timezone_combo.set_active(idx)
                    entry = self.timezone_combo.get_child()
                    entry.set_text(tz)
                    break
        except Exception as e:
            self._show_message_dialog(Gtk.MessageType.WARNING, _("Error"), _("Failed to load timezone: {0}").format(str(e)))

    def _update_timezone_store(self, search_text):
        self.timezone_store.clear()
        search_text = search_text.lower()
        for tz in self.all_timezones:
            if search_text in tz.lower():
                self.timezone_store.append([tz])

    def _on_timezone_search(self, entry):
        search_text = entry.get_text()
        self._update_timezone_store(search_text)

    def _on_save_all(self, button: Gtk.Button):
        errors = []

        idx = self.timezone_combo.get_active()
        if idx >= 0:
            model = self.timezone_combo.get_model()
            if model is not None:
                timezone = model[idx][0]
                if timezone:
                    status, message = set_timezone(timezone)
                    if status != "ok":
                        errors.append(_("Timezone: {0}").format(message))

        utc = self.hwclock_switch.get_active()
        status, message = set_hwclock_utc(utc)
        if status != "ok":
            errors.append(_("Hardware clock: {0}").format(message))

        enabled = self.ntp_switch.get_active()
        servers = self.ntp_entry.get_text().strip().split()
        if enabled:
            if not servers:
                servers = ["pool.ntp.org"]
            status, message = set_ntp_servers(servers)
            if status == "ok":
                status2, message2 = enable_ntp()
                if status2 != "ok":
                    errors.append(_("NTP: {0}").format(message2))
            else:
                errors.append(_("NTP: {0}").format(message))
        else:
            status, message = disable_ntp()
            if status != "ok":
                errors.append(_("NTP: {0}").format(message))

        if errors:
            self._show_message_dialog(Gtk.MessageType.ERROR, _("Error"), "\n".join(errors))
        else:
            self._show_message_dialog(Gtk.MessageType.INFO, _("Success"), _("All settings saved successfully."))

    def _on_sync_now(self, button: Gtk.Button):
        status, message = sync_time_now()

        if status == "ok":
            self._show_message_dialog(Gtk.MessageType.INFO, _("Success"), message)
            self._load_settings()
        elif status == "permission_denied":
            self._show_message_dialog(Gtk.MessageType.ERROR, _("Error"), _("Permission denied. Root permission required."))
        elif status == "pkexec_failed":
            self._show_message_dialog(Gtk.MessageType.ERROR, _("Error"), _("Authentication failed or pkexec not available."))
        else:
            self._show_message_dialog(Gtk.MessageType.ERROR, _("Error"), message)

    def _show_message_dialog(self, msg_type: Gtk.MessageType, title: str, message: str) -> None:
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