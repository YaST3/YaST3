"""Language settings tab for GTK4."""

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk, GObject

from mast.core.i18n import _
from mast.core.languages import (
    get_current_language,
    get_use_utf8,
    save_language_settings,
    LanguageInfo,
    LocaleItem,
    build_locale_install_command,
)
from mast.gtk4.command.action import CommandAction


class LanguageSettingsTab(Gtk.Box):
    __gsignals__ = {
        "language-installed": (GObject.SIGNAL_RUN_FIRST, None, ()),
    }

    def __init__(self, locales: list[LocaleItem]):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self._all_locales = locales
        self.set_margin_top(12)
        self.set_margin_bottom(12)
        self.set_margin_start(12)
        self.set_margin_end(12)
        self._setup_ui()
        self._load_languages()

    def _setup_ui(self) -> None:
        language_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        label = Gtk.Label(label=_("Language"))
        label.set_size_request(100, -1)
        label.set_halign(Gtk.Align.START)
        language_box.append(label)

        self.language_combo = Gtk.ComboBoxText()
        self.language_combo.set_hexpand(True)
        language_box.append(self.language_combo)

        self.append(language_box)

        utf8_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        label = Gtk.Label(label=_("Use UTF-8"))
        label.set_size_request(100, -1)
        label.set_halign(Gtk.Align.START)
        utf8_box.append(label)

        self.utf8_switch = Gtk.Switch()
        self.utf8_switch.set_halign(Gtk.Align.START)
        utf8_box.append(self.utf8_switch)

        self.append(utf8_box)

        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        button_box.set_halign(Gtk.Align.END)

        self.save_btn = Gtk.Button(label=_("Save"))
        self.save_btn.add_css_class("suggested-action")
        self.save_btn.connect("clicked", self._on_save_clicked)
        button_box.append(self.save_btn)

        self.append(button_box)

    def _load_languages(self) -> None:
        try:
            sorted_locales = sorted(
                self._all_locales,
                key=lambda x: x.name
            )

            for loc in sorted_locales:
                self.language_combo.append(loc.code, loc.name)

            current_lang = get_current_language()
            if current_lang in [loc.code for loc in self._all_locales]:
                self.language_combo.set_active_id(current_lang)

            self.utf8_switch.set_active(get_use_utf8())
        except Exception as e:
            self._show_message_dialog(Gtk.MessageType.WARNING, _("Error"), _("Failed to load languages: {0}").format(str(e)))

    def _is_locale_installed(self, locale_code: str) -> bool:
        return any(loc.code == locale_code and loc.installed for loc in self._all_locales)

    def _on_save_clicked(self, button: Gtk.Button) -> None:
        lang_code = self.language_combo.get_active_id()
        use_utf8 = self.utf8_switch.get_active()

        if not lang_code:
            self._show_message_dialog(Gtk.MessageType.WARNING, _("Error"), _("Please select a language."))
            return

        if not self._is_locale_installed(lang_code):
            locale = next((loc for loc in self._all_locales if loc.code == lang_code), None)
            if locale:
                self._install_language_and_save(locale, lang_code, use_utf8)
            else:
                self._show_message_dialog(Gtk.MessageType.WARNING, _("Error"), _("Language '{0}' not found.").format(lang_code))
            return

        self._save_language_settings(lang_code, use_utf8)

    def _install_language_and_save(self, locale: LocaleItem, lang_code: str, use_utf8: bool) -> None:
        self.current_action = CommandAction(
            text=_("Install"),
            running_text=_("Installing..."),
            dialog_title=_("Install Language"),
            command=build_locale_install_command(lang_code),
            success_output=_("Language '{0}' installed successfully.").format(locale.name),
            parent_window=self.get_root(),
        )
        self.current_action.connect_finished(
            lambda success, error, stdout: self._on_install_finished(success, lang_code, use_utf8)
        )
        self.current_action.start_action()

    def _on_install_finished(self, success: bool, lang_code: str, use_utf8: bool) -> None:
        if success:
            for loc in self._all_locales:
                if loc.code == lang_code:
                    loc.installed = True
                    break
            self.emit("language-installed")
            self._save_language_settings(lang_code, use_utf8)

    def _save_language_settings(self, lang_code: str, use_utf8: bool) -> None:
        status, message = save_language_settings(lang_code, use_utf8=use_utf8)

        if status == "ok":
            locale = next((loc for loc in self._all_locales if loc.code == lang_code), None)
            lang_name = locale.name if locale else lang_code
            self._show_message_dialog(Gtk.MessageType.INFO, _("Success"), _("Language changed successfully to '{0}'. Changes will take effect after logout.").format(lang_name))
            window = self.get_root()
            if window:
                window.close()
        elif status == "permission_denied":
            self._show_message_dialog(Gtk.MessageType.ERROR, _("Error"), _("Permission denied. Root permission required."))
        elif status == "pkexec_failed":
            self._show_message_dialog(Gtk.MessageType.ERROR, _("Error"), _("Authentication failed or pkexec not available."))
        else:
            self._show_message_dialog(Gtk.MessageType.ERROR, _("Error"), _("Failed to set language: {0}").format(message))

    def _show_message_dialog(self, msg_type: Gtk.MessageType, title: str, message: str) -> None:
        dialog = Gtk.MessageDialog(
            transient_for=self.get_root(),
            modal=True,
            message_type=msg_type,
            buttons=Gtk.ButtonsType.OK,
            text=title,
        )
        dialog.set_property("secondary-text", message)
        dialog.connect("response", lambda d, r: d.destroy())
        dialog.present()
