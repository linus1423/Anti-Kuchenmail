PYTHON ?= python3

.PHONY: test lint

# unittest aus der Standardbibliothek, damit auf Fedora nichts nachinstalliert werden muss
test:
	$(PYTHON) -m unittest discover -s tests -t . -v

lint:
	$(PYTHON) -m compileall -q guard tests
