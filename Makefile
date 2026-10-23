PYTHON ?= python3

.PHONY: test test-js lint check sign-webmail

# unittest aus der Standardbibliothek, damit auf Fedora nichts nachinstalliert werden muss
test:
	$(PYTHON) -m unittest discover -s tests -t . -v

# Tests der Erweiterungen (braucht Node.js und einmal `npm install`)
test-js:
	node --test tests/js/*.test.mjs

lint:
	$(PYTHON) -m compileall -q guard tests
	sh -n install.sh
	sh -n uninstall.sh
	@if [ -x node_modules/.bin/web-ext ]; then \
		node_modules/.bin/web-ext lint -s extensions/webmail --warnings-as-errors && \
		node_modules/.bin/web-ext lint -s extensions/thunderbird --self-hosted; \
	else echo "web-ext nicht installiert (npm install), Lint der Erweiterungen übersprungen"; fi

check: lint test test-js

# Firefox-Erweiterung bei addons.mozilla.org als "unlisted" signieren lassen.
# Schlüssel: addons.mozilla.org → Werkzeuge → API-Schlüssel verwalten. Nicht ins Repo schreiben.
sign-webmail:
	@if [ -z "$$AMO_JWT_ISSUER" ] || [ -z "$$AMO_JWT_SECRET" ]; then \
		echo "Bitte AMO_JWT_ISSUER und AMO_JWT_SECRET setzen (addons.mozilla.org → API-Schlüssel)."; exit 1; fi
	node_modules/.bin/web-ext sign -s extensions/webmail --channel=unlisted \
		--api-key="$$AMO_JWT_ISSUER" --api-secret="$$AMO_JWT_SECRET" --artifacts-dir dist
