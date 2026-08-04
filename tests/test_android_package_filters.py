"""Unit tests for Android package filters."""

import unittest

from mast.core.android.package_filters import (
    PACKAGE_TYPE_ALL,
    PACKAGE_TYPE_BLOATWARE,
    PACKAGE_TYPE_SYSTEM,
    PACKAGE_TYPE_USER,
    is_bloatware_package,
    matches_package_type,
)


class TestAndroidPackageFilters(unittest.TestCase):
    """Tests for Android package type filters."""

    def test_bloatware_filter_matches_exact_id(self) -> None:
        self.assertTrue(is_bloatware_package("com.miui.hybrid"))

    def test_bloatware_filter_matches_fastapp_prefix(self) -> None:
        self.assertTrue(is_bloatware_package("com.huawei.fastapp.engine"))

    def test_bloatware_filter_rejects_regular_package(self) -> None:
        self.assertFalse(is_bloatware_package("org.fdroid.fdroid"))

    def test_matches_package_type_for_bloatware(self) -> None:
        self.assertTrue(
            matches_package_type(False, PACKAGE_TYPE_BLOATWARE, "com.vivo.hybrid.app")
        )
        self.assertFalse(
            matches_package_type(True, PACKAGE_TYPE_BLOATWARE, "org.fdroid.fdroid")
        )

    def test_matches_package_type_for_system_user_and_all(self) -> None:
        self.assertTrue(matches_package_type(True, PACKAGE_TYPE_SYSTEM, "any.pkg"))
        self.assertFalse(matches_package_type(False, PACKAGE_TYPE_SYSTEM, "any.pkg"))
        self.assertTrue(matches_package_type(False, PACKAGE_TYPE_USER, "any.pkg"))
        self.assertFalse(matches_package_type(True, PACKAGE_TYPE_USER, "any.pkg"))
        self.assertTrue(matches_package_type(True, PACKAGE_TYPE_ALL, "any.pkg"))


if __name__ == "__main__":
    unittest.main()