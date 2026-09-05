"""Unit tests for predefined third-party repositories."""

import unittest
from tempfile import NamedTemporaryFile
from unittest.mock import patch

from mast.core.repositories import repos
from mast.core.repositories.third_party_repos import third_party_repos


class TestThirdPartyRepos(unittest.TestCase):
    """Tests for predefined repository entries."""

    def test_vscode_repository(self) -> None:
        """Visual Studio Code should be available from the import menu."""
        vscode = next(repo for repo in third_party_repos if repo.id == "vscode")

        self.assertEqual(vscode.filename, "vscode.repo")
        self.assertEqual(vscode.name, "Visual Studio Code")
        self.assertEqual(
            vscode.baseurl,
            "https://packages.microsoft.com/yumrepos/vscode",
        )
        self.assertTrue(vscode.enabled)
        self.assertTrue(vscode.gpgcheck)
        self.assertEqual(
            vscode.gpgkey,
            "https://packages.microsoft.com/keys/microsoft.asc",
        )

    def test_opi_repository_entries(self) -> None:
        """Repositories imported from OPI should have complete definitions."""
        repositories = {repo.id: repo for repo in third_party_repos}

        for repo_id in (
            "antigravity",
            "anydesk",
            "atom",
            "brave-browser",
            "collabora-office",
            "dotnet",
            "softmaker",
            "jami",
            "librewolf",
            "mega",
            "microsoft-edge",
            "mullvad",
            "plex",
            "resilio-sync",
            "skype-stable",
            "slack",
            "sublime-text",
            "teams-for-linux",
            "teamviewer",
            "hashicorp",
            "vivaldi",
            "vscodium",
            "yandex-browser",
            "yandex-disk",
        ):
            self.assertIn(repo_id, repositories)
            self.assertTrue(repositories[repo_id].baseurl)
            self.assertTrue(repositories[repo_id].gpgkey)

    def test_all_repositories_are_enabled_and_autorefreshed(self) -> None:
        """All predefined repositories should be enabled and auto-refreshed."""
        self.assertTrue(all(repo.enabled for repo in third_party_repos))
        self.assertTrue(all(repo.autorefresh for repo in third_party_repos))

    def test_repositories_with_gpg_keys_check_packages(self) -> None:
        """Repositories with signing keys should enable package verification."""
        for repo in third_party_repos:
            if repo.gpgkey:
                self.assertTrue(repo.gpgcheck, repo.id)

    def test_google_chrome_repository(self) -> None:
        """Google Chrome should be available from the repository import menu."""
        chrome = next(repo for repo in third_party_repos if repo.id == "google-chrome")

        self.assertEqual(chrome.filename, "google-chrome.repo")
        self.assertEqual(chrome.name, "Google Chrome")
        self.assertEqual(
            chrome.baseurl,
            "http://dl.google.com/linux/chrome/rpm/stable/$basearch/",
        )
        self.assertTrue(chrome.enabled)
        self.assertTrue(chrome.gpgcheck)
        self.assertEqual(
            chrome.gpgkey,
            "https://dl.google.com/linux/linux_signing_key.pub",
        )

    def test_vlc_repository(self) -> None:
        """VLC should be available from the repository import menu."""
        if not any(repo.id == "vlc" for repo in third_party_repos):
            self.skipTest("VLC is only available on openSUSE")
        vlc = next(repo for repo in third_party_repos if repo.id == "vlc")

        self.assertEqual(vlc.filename, "vlc.repo")
        self.assertEqual(vlc.name, "VLC")
        self.assertTrue(vlc.baseurl.startswith("https://download.videolan.org/SuSE/"))
        self.assertTrue(vlc.gpgkey.endswith("/repodata/repomd.xml.key"))
        self.assertTrue(vlc.enabled)
        self.assertTrue(vlc.autorefresh)
        self.assertTrue(vlc.gpgcheck)

    def test_rpmfusion_free_repository(self) -> None:
        """RPM Fusion Free should preserve its Fedora repository options."""
        if not any(repo.id == "rpmfusion-free" for repo in third_party_repos):
            self.skipTest("RPM Fusion is only available on Fedora")
        rpmfusion = next(
            repo for repo in third_party_repos if repo.id == "rpmfusion-free"
        )

        self.assertEqual(rpmfusion.filename, "rpmfusion-free.repo")
        self.assertEqual(rpmfusion.name, "RPM Fusion Free")
        self.assertTrue(rpmfusion.enabled)
        self.assertEqual(
            rpmfusion.other_options["metalink"],
            "https://mirrors.rpmfusion.org/metalink?repo=free-fedora-$releasever&arch=$basearch",
        )
        self.assertEqual(rpmfusion.other_options["metadata_expire"], "14d")
        self.assertFalse(rpmfusion.repo_gpgcheck)
        self.assertEqual(rpmfusion.gpgkey, "")
        self.assertFalse(rpmfusion.gpgcheck)
        self.assertEqual(rpmfusion.priority, 70)

    def test_rpmfusion_nonfree_repository(self) -> None:
        """RPM Fusion Nonfree should be available on Fedora."""
        if not any(repo.id == "rpmfusion-nonfree" for repo in third_party_repos):
            self.skipTest("RPM Fusion is only available on Fedora")
        rpmfusion = next(
            repo for repo in third_party_repos if repo.id == "rpmfusion-nonfree"
        )

        self.assertEqual(rpmfusion.filename, "rpmfusion-nonfree.repo")
        self.assertEqual(rpmfusion.name, "RPM Fusion Nonfree")
        self.assertTrue(rpmfusion.enabled)
        self.assertEqual(
            rpmfusion.other_options["metalink"],
            "https://mirrors.rpmfusion.org/metalink?repo=nonfree-fedora-$releasever&arch=$basearch",
        )
        self.assertEqual(rpmfusion.other_options["metadata_expire"], "14d")
        self.assertFalse(rpmfusion.repo_gpgcheck)
        self.assertFalse(rpmfusion.gpgcheck)
        self.assertEqual(rpmfusion.priority, 70)


class TestRepositoryDirectory(unittest.TestCase):
    """Tests for distribution-specific repository directories."""

    def test_fedora_directory(self) -> None:
        with patch.object(repos, "read_os_release", return_value={"ID": "fedora"}):
            self.assertEqual(repos._repository_dir(), "/etc/yum.repos.d")

    def test_opensuse_directory(self) -> None:
        with patch.object(repos, "read_os_release", return_value={"ID": "opensuse"}):
            self.assertEqual(repos._repository_dir(), "/etc/zypp/repos.d")


class TestRepoGpgCheckFallback(unittest.TestCase):
    """Tests for the repository GPG check fallback."""

    def test_missing_repo_gpgcheck_falls_back_to_gpgcheck(self) -> None:
        with NamedTemporaryFile(mode="w+") as repo_file:
            repo_file.write("[repo]\ngpgcheck=0\n")
            repo_file.flush()

            entry = repos.RepoEntry.parse_file(repo_file.name)[0]

        self.assertFalse(entry.repo_gpgcheck)

    def test_explicit_repo_gpgcheck_is_preserved(self) -> None:
        with NamedTemporaryFile(mode="w+") as repo_file:
            repo_file.write("[repo]\ngpgcheck=0\nrepo_gpgcheck=1\n")
            repo_file.flush()

            entry = repos.RepoEntry.parse_file(repo_file.name)[0]

        self.assertTrue(entry.repo_gpgcheck)


if __name__ == "__main__":
    unittest.main()