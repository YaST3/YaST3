"""Unit tests for Snap package management core logic."""

import unittest
from unittest.mock import MagicMock, patch

from mast.core.snap.package import install_snap_package, list_snap_packages, search_snap_packages, uninstall_snap_package


def _make_response(result, *, type="sync", change=None):
    """Create a mock SnapdResponse-like object."""
    resp = MagicMock()
    resp.type = type
    resp.result = result
    resp.change = change
    return resp


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

    @patch("mast.core.snap.package.snap_http.list")
    @patch("mast.core.snap.snap.os.path.exists")
    @patch("mast.core.snap.snap.shutil.which")
    def test_parses_installed_packages(self, mock_which, mock_exists, mock_list) -> None:
        mock_which.return_value = "/usr/bin/snap"
        mock_exists.return_value = True
        mock_list.return_value = _make_response([
            {
                "name": "bare",
                "version": "1.0",
                "revision": "5",
                "tracking-channel": "latest/stable",
                "publisher": {"display-name": "Canonical", "username": "canonical"},
                "summary": "",
            },
            {
                "name": "firefox",
                "version": "139.0-1",
                "revision": "6091",
                "tracking-channel": "latest/stable",
                "publisher": {"display-name": "Mozilla", "username": "mozilla"},
                "summary": "Mozilla Firefox web browser",
            },
        ])

        packages = list_snap_packages()

        self.assertEqual(len(packages), 2)
        self.assertEqual(packages[0].name, "bare")
        self.assertEqual(packages[0].tracking, "latest/stable")
        self.assertEqual(packages[1].name, "firefox")
        self.assertEqual(packages[1].revision, "6091")
        self.assertEqual(packages[1].publisher, "Mozilla")


class TestSearchSnapPackages(unittest.TestCase):
    """Tests for search_snap_packages function."""

    @patch("mast.core.snap.package.snap_http_http._make_request")
    @patch("mast.core.snap.snap.os.path.exists")
    @patch("mast.core.snap.snap.shutil.which")
    def test_loads_featured_when_query_blank(self, mock_which, mock_exists, mock_make_request) -> None:
        mock_which.return_value = "/usr/bin/snap"
        mock_exists.return_value = True
        mock_make_request.return_value = {
            "type": "sync",
            "status-code": 200,
            "result": [
                {
                    "name": "firefox",
                    "version": "139.0-1",
                    "publisher": {"display-name": "Mozilla", "username": "mozilla"},
                    "summary": "Mozilla Firefox web browser",
                },
            ],
        }

        packages = search_snap_packages("")

        self.assertEqual(len(packages), 1)
        self.assertEqual(packages[0].name, "firefox")
        mock_make_request.assert_called_once_with(
            "/find", "GET", query_params={"scope": "wide", "section": "featured"}
        )

    @patch("mast.core.snap.package.snap_http_http._make_request")
    @patch("mast.core.snap.snap.os.path.exists")
    @patch("mast.core.snap.snap.shutil.which")
    def test_parses_search_results(self, mock_which, mock_exists, mock_make_request) -> None:
        mock_which.return_value = "/usr/bin/snap"
        mock_exists.return_value = True
        mock_make_request.return_value = {
            "type": "sync",
            "status-code": 200,
            "result": [
                {
                    "name": "firefox",
                    "version": "139.0-1",
                    "publisher": {"display-name": "Mozilla", "username": "mozilla"},
                    "summary": "Mozilla Firefox web browser",
                },
                {
                    "name": "floorp",
                    "version": "11.30.0",
                    "publisher": {"display-name": "Floorp", "username": "floorp"},
                    "summary": "Privacy-focused Firefox fork",
                },
            ],
        }

        packages = search_snap_packages("firefox")

        self.assertEqual(len(packages), 2)
        self.assertEqual(packages[0].name, "firefox")
        self.assertEqual(packages[0].summary, "Mozilla Firefox web browser")
        self.assertEqual(packages[1].publisher, "Floorp")


class TestSnapPackageCommands(unittest.TestCase):
    """Tests for install and uninstall via snap_http."""

    @patch("mast.core.snap.package.snap_http.check_change")
    @patch("mast.core.snap.package.snap_http.install")
    def test_install_calls_snap_http(self, mock_install, mock_check_change) -> None:
        mock_install.return_value = _make_response(
            result={"status": "Done"}, type="async", change="change-1"
        )
        mock_check_change.return_value = _make_response({"status": "Done"})

        install_snap_package("firefox")

        mock_install.assert_called_once_with("firefox")

    @patch("mast.core.snap.package.snap_http.check_change")
    @patch("mast.core.snap.package.snap_http.remove")
    def test_uninstall_calls_snap_http(self, mock_remove, mock_check_change) -> None:
        mock_remove.return_value = _make_response(
            result={"status": "Done"}, type="async", change="change-1"
        )
        mock_check_change.return_value = _make_response({"status": "Done"})

        uninstall_snap_package("firefox")

        mock_remove.assert_called_once_with("firefox")

    @patch("mast.core.snap.package.snap_http.check_change")
    @patch("mast.core.snap.package.snap_http.install")
    def test_install_raises_on_change_error(self, mock_install, mock_check_change) -> None:
        mock_install.return_value = _make_response(
            result={}, type="async", change="change-1"
        )
        mock_check_change.return_value = _make_response({"status": "Error", "err": "snap not found"})

        with self.assertRaises(RuntimeError):
            install_snap_package("nonexistent")


if __name__ == "__main__":
    unittest.main()
