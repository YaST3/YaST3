"""openSUSE Build Service package search and installation helpers."""

from .package import BuildServicePackage, build_install_command, search_packages

__all__ = ["BuildServicePackage", "build_install_command", "search_packages"]