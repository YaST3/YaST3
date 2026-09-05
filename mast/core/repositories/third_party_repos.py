from mast.core.distro import read_os_release
from mast.core.repositories.repos import RepoEntry

os_release = read_os_release()

distro = os_release.get("PRETTY_NAME", "openSUSE Tumbleweed").replace(" ", "_")

third_party_repos = [
    RepoEntry(
        id="nvidia",
        name="NVIDIA",
        enabled=True,
        autorefresh=True,
        baseurl=f"https://download.nvidia.com/{distro.replace("_", "/").lower()}/",
        gpgkey=f"https://download.nvidia.com/{distro.replace("_", "/").lower()}/repodata/repomd.xml.key",
        gpgcheck=True,
        priority=120,
    ),
    RepoEntry(
        id="google-chrome",
        name="Google Chrome",
        enabled=True,
        autorefresh=True,
        baseurl="http://dl.google.com/linux/chrome/rpm/stable/$basearch/",
        gpgcheck=True,
        gpgkey="https://dl.google.com/linux/linux_signing_key.pub",
    ),
]

os_id = os_release.get("ID", "").lower()

if os_id == "fedora":
    third_party_repos.append(
        RepoEntry(
            id="rpmfusion-free",
            name="RPM Fusion for Fedora - Free",
            enabled=False,
            autorefresh=True,
            type="rpm-md",
            gpgcheck=False,
            repo_gpgcheck=False,
            other_options={
                "metalink": "https://mirrors.rpmfusion.org/metalink?repo=free-fedora-$releasever&arch=$basearch",
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
            enabled=True,
            autorefresh=True,
            baseurl=f"https://ftp.gwdg.de/pub/linux/misc/packman/suse/{distro}/",
            gpgkey=f"https://ftp.gwdg.de/pub/linux/misc/packman/suse/{distro}/repodata/repomd.xml.key",
            gpgcheck=True,
            priority=70,  # opi project recommends 70 for packman repo
        ),
    )
    third_party_repos.append(
        RepoEntry(
            id="vlc",
            name="VLC",
            enabled=True,
            autorefresh=True,
            baseurl=f"https://download.videolan.org/SuSE/{distro.replace("openSUSE_", "")}/",
            gpgkey=f"https://download.videolan.org/SuSE/{distro.replace("openSUSE_", "")}/repodata/repomd.xml.key",
            gpgcheck=True,
        )
    )