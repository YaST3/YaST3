"""Unit tests for predefined third-party repositories."""

import unittest
from unittest.mock import patch

from mast.core.repositories import repos
from mast.core.repositories.third_party_repos import third_party_repos


class TestThirdPartyRepos(unittest.TestCase):
    """Tests for predefined repository entries."""

    def test_vlc_repository(self) -> None:
        """VLC should be available from the repository import menu."""
        vlc = next(repo for repo in third_party_repos if repo.id == "vlc")

        self.assertEqual(vlc.filename, "vlc.repo")
        self.assertEqual(vlc.name, "VLC")
        self.assertTrue(vlc.baseurl.startswith("https://download.videolan.org/SuSE/"))
        self.assertTrue(vlc.gpgkey.endswith("/repodata/repomd.xml.key"))
        self.assertTrue(vlc.enabled)
        self.assertTrue(vlc.autorefresh)
        self.assertTrue(vlc.gpgcheck)


class TestRepositoryDirectory(unittest.TestCase):
    """Tests for distribution-specific repository directories."""

    def test_fedora_directory(self) -> None:
        with patch.object(repos, "read_os_release", return_value={"ID": "fedora"}):
            self.assertEqual(repos._repository_dir(), "/etc/yum.repos.d")

    def test_opensuse_directory(self) -> None:
        with patch.object(repos, "read_os_release", return_value={"ID": "opensuse"}):
            self.assertEqual(repos._repository_dir(), "/etc/zypp/repos.d")


if __name__ == "__main__":
    unittest.main()