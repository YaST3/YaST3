from mast.core.distro import read_os_release
from mast.core.repositories.repos import RepoEntry

os_release = read_os_release()

distro = os_release.get("PRETTY_NAME", "openSUSE Tumbleweed").replace(" ", "_")


def _jami_repo_url(os_release: dict[str, str]) -> str:
    """Return the Jami repository URL for the current RPM distribution."""
    id = os_release.get("ID", "").lower()
    version = os_release.get("VERSION_ID", "")

    if id == "opensuse-tumbleweed":
        return f"https://dl.jami.net/nightly/{id}/"
    return f"https://dl.jami.net/nightly/{id}_{version}/"


jami_repo_url = _jami_repo_url(os_release)

third_party_repos = [
    RepoEntry(
        id="antigravity",
        name="Antigravity",
        baseurl="https://us-central1-yum.pkg.dev/projects/antigravity-auto-updater-dev/antigravity-rpm",
        gpgkey="https://us-central1-yum.pkg.dev/doc/repo-signing-key.gpg",
    ),
    RepoEntry(
        id="anydesk",
        name="AnyDesk",
        baseurl="https://rpm.anydesk.com/opensuse/$basearch/",
        gpgkey="https://keys.anydesk.com/repos/RPM-GPG-KEY",
    ),
    RepoEntry(
        id="atom",
        name="Atom",
        baseurl="https://packagecloud.io/AtomEditor/atom/el/7/$basearch/?type=rpm",
        gpgkey="https://packagecloud.io/AtomEditor/atom/gpgkey",
    ),
    RepoEntry(
        id="brave-browser",
        name="Brave Browser",
        baseurl="https://brave-browser-rpm-release.s3.brave.com/$basearch/",
        gpgkey="https://brave-browser-rpm-release.s3.brave.com/brave-core.asc",
    ),
    RepoEntry(
        id="collabora-office",
        name="Collabora Office 24.04 Snapshot",
        baseurl="https://www.collaboraoffice.com/downloads/Collabora-Office-24-Snapshot/Linux/yum",
        gpgkey="https://www.collaboraoffice.com/downloads/Collabora-Office-24-Snapshot/Linux/yum/repodata/repomd.xml.key",
    ),
    RepoEntry(
        id="dotnet",
        name="Microsoft .NET",
        baseurl="https://packages.microsoft.com/opensuse/15/prod/",
        gpgkey="https://packages.microsoft.com/keys/microsoft.asc",
    ),
    RepoEntry(
        id="google-chrome",
        name="Google Chrome",
        enabled=True,
        autorefresh=True,
        baseurl="http://dl.google.com/linux/chrome/rpm/stable/$basearch/",
        gpgkey="https://dl.google.com/linux/linux_signing_key.pub",
    ),
    RepoEntry(
        id="softmaker",
        name="SoftMaker",
        baseurl="https://shop.softmaker.com/repo/rpm",
        gpgkey="https://shop.softmaker.com/repo/linux-repo-public.key",
    ),
    RepoEntry(
        id="jami",
        name="Jami",
        baseurl=jami_repo_url,
        gpgkey="https://dl.jami.net/jami.pub.key",
    ),
    RepoEntry(
        id="librewolf",
        name="LibreWolf",
        baseurl="https://rpm.librewolf.net",
        gpgkey="https://rpm.librewolf.net/pubkey.gpg",
    ),
    RepoEntry(
        id="mega",
        name="MEGA",
        baseurl=f"https://mega.nz/linux/repo/{distro}/",
        gpgkey=f"https://mega.nz/linux/repo/{distro}/repodata/repomd.xml.key",
    ),
    RepoEntry(
        id="microsoft-edge",
        name="Microsoft Edge",
        baseurl="https://packages.microsoft.com/yumrepos/edge",
        gpgkey="https://packages.microsoft.com/keys/microsoft.asc",
    ),
    RepoEntry(
        id="mullvad",
        name="Mullvad VPN",
        baseurl="https://repository.mullvad.net/rpm/stable/$basearch/",
        gpgkey="https://repository.mullvad.net/rpm/mullvad-keyring.asc",
    ),
    RepoEntry(
        id="nvidia",
        name="NVIDIA",
        baseurl=f"https://download.nvidia.com/{distro.replace("_", "/").lower()}/",
        gpgkey=f"https://download.nvidia.com/{distro.replace("_", "/").lower()}/repodata/repomd.xml.key",
        priority=120,
    ),
    RepoEntry(
        id="plex",
        name="PlexRepo",
        baseurl="https://repo.plex.tv/rpm/",
        gpgkey="https://downloads.plex.tv/plex-keys/PlexSign.v2.key",
    ),
    RepoEntry(
        id="resilio-sync",
        name="Resilio Sync",
        baseurl="https://linux-packages.resilio.com/resilio-sync/rpm/$basearch",
        gpgkey="https://linux-packages.resilio.com/resilio-sync/key.asc",
    ),
    RepoEntry(
        id="skype-stable",
        name="Microsoft Skype",
        baseurl="https://repo.skype.com/rpm/stable/",
        gpgkey="https://repo.skype.com/data/SKYPE-GPG-KEY",
    ),
    RepoEntry(
        id="slack",
        name="Slack",
        baseurl="https://packagecloud.io/slacktechnologies/slack/fedora/21/$basearch",
        gpgkey="https://packagecloud.io/slacktechnologies/slack/gpgkey",
    ),
    RepoEntry(
        id="sublime-text",
        name="Sublime Text",
        baseurl="https://download.sublimetext.com/rpm/stable/$basearch",
        gpgkey="https://download.sublimetext.com/sublimehq-rpm-pub.gpg",
    ),
    RepoEntry(
        id="teams-for-linux",
        name="Unofficial Teams for Linux",
        baseurl="https://repo.teamsforlinux.de/rpm/",
        gpgkey="https://repo.teamsforlinux.de/teams-for-linux.asc",
    ),
    RepoEntry(
        id="teamviewer",
        name="TeamViewer",
        baseurl="https://linux.teamviewer.com/yum/stable/main/binary-$basearch/",
        gpgkey="https://linux.teamviewer.com/pubkey/currentkey.asc",
    ),
    RepoEntry(
        id="hashicorp",
        name="HashiCorp",
        baseurl="https://rpm.releases.hashicorp.com/AmazonLinux/latest/$basearch/stable",
        gpgkey="https://rpm.releases.hashicorp.com/gpg",
    ),
    RepoEntry(
        id="vivaldi",
        name="Vivaldi",
        baseurl="https://repo.vivaldi.com/archive/rpm/$basearch",
        gpgkey="https://repo.vivaldi.com/archive/linux_signing_key.pub",
    ),
    RepoEntry(
        id="vscode",
        name="Visual Studio Code",
        baseurl="https://packages.microsoft.com/yumrepos/vscode",
        gpgkey="https://packages.microsoft.com/keys/microsoft.asc",
    ),
    RepoEntry(
        id="vscodium",
        name="Visual Studio Codium",
        baseurl="https://paulcarroty.gitlab.io/vscodium-deb-rpm-repo/rpms",
        gpgkey="https://gitlab.com/paulcarroty/vscodium-deb-rpm-repo/raw/master/pub.gpg",
    ),
    RepoEntry(
        id="yandex-browser",
        name="Yandex Browser",
        baseurl="https://repo.yandex.ru/yandex-browser/rpm/stable/$basearch/",
        gpgkey="https://repo.yandex.ru/yandex-browser/YANDEX-BROWSER-KEY.GPG",
    ),
    RepoEntry(
        id="yandex-disk",
        name="Yandex.Disk",
        baseurl="https://repo.yandex.ru/yandex-disk/rpm/stable/$basearch/",
        gpgkey="https://repo.yandex.ru/yandex-disk/YANDEX-DISK-KEY.GPG",
    ),
]

os_id = os_release.get("ID", "").lower()

if os_id == "fedora":
    third_party_repos.append(
        RepoEntry(
            id="rpmfusion-free",
            name="RPM Fusion Free",
            type="rpm-md",
            gpgcheck=False,
            repo_gpgcheck=False,
            priority=70,
            other_options={
                "metalink": "https://mirrors.rpmfusion.org/metalink?repo=free-fedora-$releasever&arch=$basearch",
                "metadata_expire": "14d",
            },
        )
    )
    third_party_repos.append(
        RepoEntry(
            id="rpmfusion-nonfree",
            name="RPM Fusion Nonfree",
            type="rpm-md",
            gpgcheck=False,
            repo_gpgcheck=False,
            priority=70,
            other_options={
                "metalink": "https://mirrors.rpmfusion.org/metalink?repo=nonfree-fedora-$releasever&arch=$basearch",
                "metadata_expire": "14d",
            },
        )
    )

if os_id == "opensuse" or os_id.startswith("opensuse-"):
    third_party_repos.insert(
        0,
        RepoEntry(
            id="packman",
            name="Packman",
            baseurl=f"https://ftp.gwdg.de/pub/linux/misc/packman/suse/{distro}/",
            gpgkey=f"https://ftp.gwdg.de/pub/linux/misc/packman/suse/{distro}/repodata/repomd.xml.key",
            priority=70,  # opi project recommends 70 for packman repo
        ),
    )
    third_party_repos.append(
        RepoEntry(
            id="vlc",
            name="VLC",
            baseurl=f"https://download.videolan.org/SuSE/{distro.replace("openSUSE_", "")}/",
            gpgkey=f"https://download.videolan.org/SuSE/{distro.replace("openSUSE_", "")}/repodata/repomd.xml.key",
        )
    )

third_party_repos.sort(key=lambda repo: repo.name.lower())