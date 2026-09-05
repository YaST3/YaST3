"""Unit tests for predefined third-party repositories."""

import unittest
from tempfile import NamedTemporaryFile
from unittest.mock import patch

from mast.core.repositories import repos
from mast.core.repositories.third_party_repos import third_party_repos


class TestThirdPartyRepos(unittest.TestCase):
    """Tests for predefined repository entries."""

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
        self.assertEqual(rpmfusion.name, "RPM Fusion for Fedora - Free")
        self.assertFalse(rpmfusion.enabled)
        self.assertEqual(
            rpmfusion.other_options["metalink"],
            "https://mirrors.rpmfusion.org/metalink?repo=free-fedora-$releasever&arch=$basearch",
        )
        self.assertEqual(rpmfusion.other_options["metadata_expire"], "14d")
        self.assertFalse(rpmfusion.repo_gpgcheck)
        self.assertEqual(rpmfusion.gpgkey, "")
        self.assertFalse(rpmfusion.gpgcheck)


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