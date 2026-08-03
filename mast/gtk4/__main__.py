"""Entry point for the GTK4 GUI application."""

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk

from mast.core.i18n import init_i18n
from mast.gtk4.main_window import MainWindow


def main() -> int:

    app = Gtk.Application(application_id="me.guoyunhe.mast.gtk4")

    def on_activate(app):
        win = MainWindow(application=app)
        win.present()

    app.connect("activate", on_activate)

    return app.run(None)


if __name__ == "__main__":
    raise SystemExit(main())