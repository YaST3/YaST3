# MaST - GUI & TUI System Setup Tool for GNU/Linux

[![Crowdin](https://badges.crowdin.net/mast/localized.svg)](https://crowdin.com/project/mast)

MaST (**M**aybe **a**nthoer **S**etup **T**ool) is continuous development of YaST with Python & Qt6 / GTK4 / TUI. Our mission is to help GNU/Linux users to set up their systems easily without remembering complex commands.

## Modules

| Name         | Core | Qt6 | GTK4 | TUI |
|--------------|:----:|:---:|:----:|:---:|
| Android      | ✅   | ✅  | ✅   | ❌  |
| Cron         | 🚧   | 🚧  | 🚧   | 🚧  |
| DateTime     | ✅   | ✅  | ✅   | ✅  |
| Flatpak      | ✅   | ✅  | ✅   | ❌  |
| Font Config  | ✅   | ✅  | ✅   | ❌  |
| Git          | ✅   | ✅  | ✅   | ✅  |
| Hostname     | ✅   | ✅  | ✅   | ✅  |
| Hosts        | ✅   | ✅  | ✅   | ✅  |
| Journal      | ✅   | ✅  | ✅   | ✅  |
| Keyboard     | ✅   | ✅  | ✅   | ✅  |
| Languages    | ✅   | ✅  | ✅   | ✅  |
| Packages     | 🚧   | 🚧  | 🚧   | 🚧  |
| Proxy        | ✅   | ✅  | ✅   | ✅  |
| Repositories | ✅   | ✅  | ✅   | ✅  |
| Services     | ✅   | ✅  | ✅   | ✅  |
| Snapshots    | ✅   | ✅  | ✅   | ✅  |
| SSH Client   | ✅   | ✅  | ✅   | ✅  |

**Planned:** SSH Server (system)

## Installation

### openSUSE

```bash
# Tumbleweed
sudo zypper addrepo https://download.opensuse.org/repositories/home:guoyunhe/openSUSE_Tumbleweed/home:guoyunhe.repo
sudo zypper install mast-qt6 # or mast-gtk4 or mast-tui

# Slowroll
sudo zypper addrepo https://download.opensuse.org/repositories/home:guoyunhe/openSUSE_Slowroll/home:guoyunhe.repo
sudo zypper install mast-qt6 # or mast-gtk4 or mast-tui

# Leap 16.0
sudo zypper addrepo https://download.opensuse.org/repositories/home:guoyunhe/16.0/home:guoyunhe.repo
sudo zypper install mast-qt6 # or mast-gtk4 or mast-tui
```

### Fedora

```bash
# Fedora Rawhide
sudo dnf config-manager addrepo --from-repofile=https://download.opensuse.org/repositories/home:guoyunhe:fedora/Fedora_Rawhide/home:guoyunhe:fedora.repo
sudo dnf install mast-qt6 # or mast-gtk4 or mast-tui

# Fedora 44
sudo dnf config-manager addrepo --from-repofile=https://download.opensuse.org/repositories/home:guoyunhe:fedora/Fedora_44/home:guoyunhe:fedora.repo
sudo dnf install mast-qt6 # or mast-gtk4 or mast-tui

# Fedora 43
sudo dnf config-manager addrepo --from-repofile=https://download.opensuse.org/repositories/home:guoyunhe:fedora/Fedora_43/home:guoyunhe:fedora.repo
sudo dnf install mast-qt6 # or mast-gtk4 or mast-tui
```

## Development

```bash
# install dependencies
sudo zypper install make python3 python3-adbutils python3-bytesize python3-pyside6 python3-gobject python3-gobject-stubs gtk4-devel python3-Babel python3-python-crontab python3-configobj python3-python-dotenv python3-pytest python3-systemd

# compile translations
make

# start apps
python3 -m mast.qt6
python3 -m mast.gtk4
python3 -m mast.tui
```

## Translations

Contribute to translations on [Crowdin](https://crowdin.com/project/mast)

## Release

Project maintainers: see [RELEASE.md](./RELEASE.md) for release procedure.

## FAQ

### Distribution support

Currently, it is only tested on openSUSE and SLE. But we plan to support more distributions in the future. Feel free to [open an issue](https://github.com/guoyunhe/mast/issues/new) if you want your distribution supported.

### Why not KDE/GNOME system settings

1. They miss some features that YaST/MaST provides.
2. Some Linux users don't use GNOME/KDE, they use other desktop environments or window managers that do not provide system settings or with limited features.
3. YaST/MaST provides TUI interface for server users.

### Why not Cockpit

1. Project scopes are different.

   Cockpit is a server administration tool sponsored by Red Hat, focused on providing a modern-looking and user-friendly interface to manage and administer servers. [Source](https://www.redhat.com/en/blog/intro-cockpit)

   MaST is system setup tool for both desktop and server users.

2. User interfaces are different.

   Cockpit is a web-based interface, which require a web browser.

   MaST is a native application provide both GUI (Qt6 / GTK4) and TUI (Python console).

3. Security levels are different.

   Cockpit is a web-shell exposing 9090 port by default. If you did not enable firewall, it is accessible from the network. (Many VPS providers, e.g. Linode, do not have firewall enabled by default.)

   MaST is a native application exposing no port. It require no additional security measures.
