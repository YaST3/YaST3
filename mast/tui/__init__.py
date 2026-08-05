"""TUI module packages for MaST settings sections."""

from mast.tui.cron import CronModule
from mast.tui.datetime import DateTimeModule
from mast.tui.git import GitModule
from mast.tui.hostname import HostnameModule
from mast.tui.hosts import HostsModule
from mast.tui.keyboard import KeyboardModule
from mast.tui.languages import LanguagesModule
from mast.tui.packages import PackagesModule
from mast.tui.proxy import ProxyModule
from mast.tui.repositories import RepositoriesModule
from mast.tui.services import ServicesModule
from mast.tui.snapshots import SnapshotsModule
from mast.tui.ssh import SSHClientModule
from mast.tui.users import UsersModule

__all__ = [
    "CronModule",
    "DateTimeModule",
    "GitModule",
    "HostnameModule",
    "HostsModule",
    "KeyboardModule",
    "LanguagesModule",
    "PackagesModule",
    "ProxyModule",
    "RepositoriesModule",
    "ServicesModule",
    "SnapshotsModule",
    "SSHClientModule",
    "UsersModule",
]