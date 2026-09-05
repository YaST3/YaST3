"""Unit tests for predefined third-party repositories."""

import unittest

from mast.core.repositories.third_party_repos import third_party_repos


class TestThirdPartyRepos(unittest.TestCase):
    """Tests for predefined repository entries."""

    def test_vlc_repository(self) -> None:
        """VLC should be available from the repository import menu."""
        vlc = next(repo for repo in third_party_repos if repo.id == "vlc")

        self.assertEqual(vlc.filename, "vlc.repo")
        self.assertEqual(vlc.name, "VLC")
        self.assertEqual(vlc.baseurl, "https://download.videolan.org/SuSE/")
        self.assertTrue(vlc.enabled)
        self.assertTrue(vlc.autorefresh)
        self.assertFalse(vlc.gpgcheck)


if __name__ == "__main__":
    unittest.main()