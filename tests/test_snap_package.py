"""Unit tests for Snap package management core logic."""

import unittest
from subprocess import CompletedProcess
from unittest.mock import patch

from mast.core.snap.package import install_snap_package, list_snap_packages, search_snap_packages, uninstall_snap_package


class TestListSnapPackages(unittest.TestCase):
    """Tests for list_snap_packages function."""

    @patch("mast.core.snap.snap.shutil.which")
    def test_returns_empty_when_snap_missing(self, mock_which) -> None:
        mock_which.return_value = None

        packages = list_snap_packages()

        self.assertEqual(packages, [])

    @patch("mast.core.snap.snap.os.path.exists")
    @patch("mast.core.snap.snap.shutil.which")
    def test_returns_empty_when_snapd_socket_missing(self, mock_which, mock_exists) -> None:
        mock_which.return_value = "/usr/bin/snap"
        mock_exists.return_value = False

        packages = list_snap_packages()

        self.assertEqual(packages, [])

    @patch("mast.core.snap.package.subprocess.run")
    @patch("mast.core.snap.snap.os.path.exists")
    @patch("mast.core.snap.snap.shutil.which")
    def test_parses_installed_packages(self, mock_which, mock_exists, mock_run) -> None:
        mock_which.return_value = "/usr/bin/snap"
        mock_exists.return_value = True
        mock_run.return_value = CompletedProcess(
            args=["snap", "list"],
            returncode=0,
            stdout=(
                "Name               Version    Rev   Tracking       Publisher   Notes\n"
                "bare               1.0        5     latest/stable  canonical**  base\n"
                "firefox            139.0-1    6091  latest/stable  mozilla**   -\n"
            ),
            stderr="",
        )

        packages = list_snap_packages()

        self.assertEqual(len(packages), 2)
        self.assertEqual(packages[0].name, "bare")
        self.assertEqual(packages[0].tracking, "latest/stable")
        self.assertEqual(packages[1].name, "firefox")
        self.assertEqual(packages[1].revision, "6091")


class TestSearchSnapPackages(unittest.TestCase):
    """Tests for search_snap_packages function."""

    @patch("mast.core.snap.package.subprocess.run")
    @patch("mast.core.snap.snap.os.path.exists")
    @patch("mast.core.snap.snap.shutil.which")
    def test_parses_search_results(self, mock_which, mock_exists, mock_run) -> None:
        mock_which.return_value = "/usr/bin/snap"
        mock_exists.return_value = True
        mock_run.return_value = CompletedProcess(
            args=["snap", "find", "firefox"],
            returncode=0,
            stdout=(
                "Name       Version    Publisher   Notes  Summary\n"
                "firefox    139.0-1    mozilla**   -      Mozilla Firefox web browser\n"
                "floorp     11.30.0    floorp**    -      Privacy-focused Firefox fork\n"
            ),
            stderr="",
        )

        packages = search_snap_packages("firefox")

        self.assertEqual(len(packages), 2)
        self.assertEqual(packages[0].name, "firefox")
        self.assertEqual(packages[0].summary, "Mozilla Firefox web browser")
        self.assertEqual(packages[1].publisher, "floorp**")


class TestSnapPackageCommands(unittest.TestCase):
    """Tests for install and uninstall command execution."""

    @patch("mast.core.snap.package.subprocess.run")
    def test_install_uses_pkexec(self, mock_run) -> None:
        mock_run.return_value = CompletedProcess(args=[], returncode=0, stdout="", stderr="")

        install_snap_package("firefox")

        mock_run.assert_called_once_with(
            ["pkexec", "snap", "install", "firefox"],
            capture_output=True,
            text=True,
        )

    @patch("mast.core.snap.package.subprocess.run")
    def test_uninstall_uses_pkexec(self, mock_run) -> None:
        mock_run.return_value = CompletedProcess(args=[], returncode=0, stdout="", stderr="")

        uninstall_snap_package("firefox")

        mock_run.assert_called_once_with(
            ["pkexec", "snap", "remove", "firefox"],
            capture_output=True,
            text=True,
        )


if __name__ == "__main__":
    unittest.main()