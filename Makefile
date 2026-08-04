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

install_args =
ifdef DESTDIR
	install_args += --root="$(DESTDIR)"
endif
install_args += --prefix="$(prefix)"
install_args += --disable-pip-version-check
install_args += --upgrade

PYTHON_DIRS = mast
PYTHON_DIRS += tests

.PHONY: install install-desktop-files install-system dist clean
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

clean::
	$(FIND) $(PYTHON_DIRS) -name '*.py[cod]' -print0 | $(XARGS) -0 $(RM)

pot::
	pybabel extract -F babel.cfg -o locale/template/LC_MESSAGES/mast.pot mast/

mo::
	pybabel compile -d locale -D mast
