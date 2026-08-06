# Release Procedure

## Pre‑release checklist

- [ ] Update CHANGELOG.md
- [ ] Update translation templates `make pot`
- [ ] Merge Crowdin pull requests with new translations
- [ ] Bump version in pyproject.toml
- [ ] Update packages and dependencies in pyproject.toml if needed
- [ ] Create tag and release on GitHub

## Packaging for distribution

- [ ] Update openSUSE Build Service package and submit for review
- [ ] Update Debian package and submit for review
- [ ] Update Ubuntu package and submit for review
- [ ] Update Arch Linux package and submit for review
- [ ] Update Fedora package and submit for review
