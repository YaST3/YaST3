"""Unit tests for Flatpak cache management core logic."""

import unittest
from unittest.mock import patch

from mast.core.flatpak.flatpak import (
    FLATPAK_CACHE_DIR,
    clear_flatpak_cache_command,
    get_flatpak_cache_size,
)


class TestGetFlatpakCacheSize(unittest.TestCase):
    """Tests for get_flatpak_cache_size function."""

    @patch("mast.core.flatpak.flatpak.os.path.isdir")
    def test_returns_zero_when_cache_dir_missing(self, mock_isdir) -> None:
        mock_isdir.return_value = False

        size = get_flatpak_cache_size()

        self.assertEqual(size, "0 B")

    @patch("mast.core.flatpak.flatpak.os.path.getsize")
    @patch("mast.core.flatpak.flatpak.os.walk")
    @patch("mast.core.flatpak.flatpak.os.path.isdir")
    def test_sums_file_sizes_in_cache_dir(self, mock_isdir, mock_walk, mock_getsize) -> None:
        mock_isdir.return_value = True
        mock_walk.return_value = [
            (FLATPAK_CACHE_DIR, [], ["a.bin", "b.bin"]),
        ]
        mock_getsize.side_effect = [1024, 2048]

        size = get_flatpak_cache_size()

        self.assertEqual(size, "3 KiB")


class TestClearFlatpakCacheCommand(unittest.TestCase):
    """Tests for clear_flatpak_cache_command function."""

    def test_command_uses_pkexec_and_rm_rf(self) -> None:
        command = clear_flatpak_cache_command()

        self.assertEqual(command[0], "pkexec")
        self.assertEqual(command[1], "bash")
        self.assertEqual(command[2], "-c")
        self.assertIn("rm -rf", command[3])
        self.assertIn(FLATPAK_CACHE_DIR, command[3])


if __name__ == "__main__":
    unittest.main()
