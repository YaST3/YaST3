# The default target of this Makefile is...
.PHONY: all
all:: pot mo

INSTALL = install
FIND = find
MKDIR_P = mkdir -p
PIP = $(PYTHON) -m pip
PYTHON ?= python3
RM = rm -f
RM_R = rm -fr
XARGS = xargs

prefix ?= $(HOME)/.local
datadir ?= $(prefix)/share
appdir ?= $(datadir)/applications
APPIMAGE_BUILDER ?= ./appimage-builder-x86_64.AppImage
APPIMAGE_BUILDER_URL ?= https://github.com/AppImageCrafters/appimage-builder/releases/download/v1.1.0/appimage-builder-1.1.0-x86_64.AppImage

install_args =
ifdef DESTDIR
	install_args += --root="$(DESTDIR)"
endif
install_args += --prefix="$(prefix)"
install_args += --disable-pip-version-check
install_args += --upgrade

PYTHON_DIRS = mast
PYTHON_DIRS += tests

.PHONY: install install-desktop-files install-system dist clean appimage
.PHONY: i18n-update i18n-compile

install:: all
	$(PIP) install $(install_args) .

install-system::
	@if [ "$$(id -u)" -ne 0 ]; then \
		echo "Error: install-system must be run as root (for example: sudo make install-system)." >&2; \
		exit 1; \
	fi
	$(MAKE) prefix=/usr/local install

dist:: clean
	$(PIP) install --upgrade build
	$(PYTHON) -m build --outdir dist .

# Download the standalone appimage-builder AppImage if it is missing.
$(APPIMAGE_BUILDER):
	wget -O $@ $(APPIMAGE_BUILDER_URL)
	chmod +x $@

appimage:: $(APPIMAGE_BUILDER)
	$(APPIMAGE_BUILDER) --recipe AppImageBuilder.yml

clean::
	$(FIND) $(PYTHON_DIRS) -name '*.py[cod]' -print0 | $(XARGS) -0 $(RM)

pot::
	pybabel extract -F babel.cfg -o locale/template/LC_MESSAGES/mast.pot mast/

mo::
	pybabel compile -d locale -D mast
