"""Tests for openSUSE Build Service package search."""

import unittest
from unittest.mock import patch

from mast.core.buildservice.package import BuildServicePackage, build_install_command, search_packages


class TestBuildServicePackage(unittest.TestCase):
    @patch("mast.core.buildservice.package.urllib.request.urlopen")
    @patch("mast.core.buildservice.package._distribution", return_value="openSUSE:Factory")
    @patch("mast.core.buildservice.package._architecture", return_value="x86_64")
    def test_search_filters_results(self, _arch, _distribution, urlopen) -> None:
        xml = b"""<collection>
          <binary name="firefox" version="1" release="1" arch="x86_64" project="openSUSE:Factory" repository="snapshot" package="MozillaFirefox" />
          <binary name="firefox" version="1" release="1" arch="x86_64" project="home:user:firefox" repository="snapshot" />
          <binary name="firefox" version="1" release="1" arch="x86_64" project="openSUSE:Factory" repository="openSUSE_Factory_ARM" />
          <binary name="firefox-debuginfo" version="1" release="1" arch="x86_64" project="openSUSE:Factory" repository="snapshot" />
          <binary name="firefox" version="1" release="1" arch="aarch64" project="openSUSE:Factory" repository="snapshot" />
        </collection>"""
        response = urlopen.return_value.__enter__.return_value
        response.read.return_value = xml

        packages = search_packages("firefox")

        self.assertEqual([package.name for package in packages], ["firefox", "firefox"])
        official = next(package for package in packages if package.project == "openSUSE:Factory")
        personal = next(package for package in packages if package.project == "home:user:firefox")
        self.assertEqual(official.package, "MozillaFirefox")
        self.assertEqual(personal.package, "firefox")

    def test_build_install_command_uses_obs_rpm_url(self) -> None:
        package = BuildServicePackage("foo", "1", "2", "x86_64", "home:user:project", "Tumbleweed")

        command = build_install_command(package)

        self.assertEqual(command[:3], ["pkexec", "bash", "-c"])
        self.assertIn("zypper --non-interactive ar --refresh", command[3])
        self.assertIn("https://download.opensuse.org/repositories/home:/user:/project/Tumbleweed/", command[3])
        self.assertIn("--gpg-auto-import-keys refresh home_user_project", command[3])
        self.assertIn("--from home_user_project", command[3])
        self.assertIn("foo.x86_64", command[3])


if __name__ == "__main__":
    unittest.main()