PYTHON ?= python3

.PHONY: test test-js lint check

# unittest aus der Standardbibliothek, damit auf Fedora nichts nachinstalliert werden muss
test:
	$(PYTHON) -m unittest discover -s tests -t . -v

# Tests der Erweiterungen (braucht Node.js)
test-js:
	node --test tests/js/*.test.mjs

lint:
	$(PYTHON) -m compileall -q guard tests
	sh -n install.sh
	sh -n uninstall.sh

check: lint test test-js
