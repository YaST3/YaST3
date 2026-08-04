"""MaST GTK4 GUI application."""

from mast.gtk4.android import AndroidModule
from mast.gtk4.cron import CronModule
from mast.gtk4.datetime import DateTimeModule
from mast.gtk4.flatpak import FlatpakModule
from mast.gtk4.git import GitModule
from mast.gtk4.hostname import HostnameModule
from mast.gtk4.hosts import HostsModule
from mast.gtk4.journal import JournalModule
from mast.gtk4.languages import LanguagesModule
from mast.gtk4.packages import PackagesModule
from mast.gtk4.proxy import ProxyModule
from mast.gtk4.repositories import RepositoriesModule
from mast.gtk4.services import ServicesModule
from mast.gtk4.snapshots import SnapshotsModule
from mast.gtk4.ssh import SSHClientModule
from mast.gtk4.users import UsersModule

__all__ = [
    "AndroidModule",
    "CronModule",
    "DateTimeModule",
    "FlatpakModule",
    "GitModule",
    "HostnameModule",
    "HostsModule",
    "JournalModule",
    "LanguagesModule",
    "PackagesModule",
    "ProxyModule",
    "RepositoriesModule",
    "ServicesModule",
    "SnapshotsModule",
    "SSHClientModule",
    "UsersModule",
]