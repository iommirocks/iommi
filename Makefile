
help:
	@echo "clean-build - remove build artifacts"
	@echo "clean-pyc - remove Python file artifacts"
	@echo "lint - check style with ruff check"
	@echo "test - run tests"
	@echo "coverage - check code coverage quickly with the default Python"
	@echo "docs - generate Sphinx HTML documentation, including API docs"
	@echo "dist - package"
	@echo "tag - set a tag with the current version number"
	@echo "release-check - check release tag"

.PHONY: clean
clean: clean-build clean-pyc
	rm -rf htmlcov/
	rm -rf venv

.PHONY: clean-build
clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr lib/*.egg-info

.PHONY: clean-pyc
clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name "__pycache__" -type d -delete

clean-docs:
	rm -f docs/tri*.rst

.PHONY: lint
lint: ruff

.PHONY: ruff
ruff:
	tox -e venv -- ruff check .

.PHONY: ruff-format
ruff-format:
	tox -e venv -- ruff format .

test-all:
	tox --skip-missing-interpreters

.PHONY: test
test:
	python -m pytest

coverage:
	tox -e coverage

.PHONY: docs
docs:
	rm -f docs/test_doc__*
	tox -e docs

docs-viewer:
	echo "http://127.0.0.1:10331"
	cd docs/_build/html; ../../../venv/bin/python -m http.server 10331

test-docs:
	tox -e docs

.PHONY: coverage
docs-coverage:
	tox -e coverage-from-docs

.PHONY: dist
dist: clean-build clean-pyc venv
	venv/bin/python -m build
	ls -l dist

.PHONY: tag
tag:
	venv/bin/python util.py tag

.PHONY: release-check
release-check:
	venv/bin/python util.py release-check

.PHONY: venv
venv:
	tox -e venv

.PHONY: run-examples
run-examples: venv
	venv/bin/python examples/manage.py migrate
	venv/bin/python examples/manage.py runserver

.PHONY: test-live
test-live:
	watchmedo shell-command --patterns="*.py" --command="python -m hammett" iommi tests

.PHONY: makemessages
makemessages:
	(cd iommi && django-admin makemessages -a)
	(cd examples && django-admin makemessages -a)

.PHONY: compilemessages
compilemessages:
	(cd iommi && django-admin compilemessages)
	(cd examples && django-admin compilemessages)

.PHONY: release
release: clean-build clean-pyc venv release-check
	rm -rf dist/ build/ && \
	django-admin compilemessages \
	    --ignore=venv \
	    --ignore=.tox \
	    --ignore=examples && \
	venv/bin/python -m build && \
# 	twine upload dist/*
