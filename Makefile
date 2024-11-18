
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
	rm -rf docs/_build
	rm -f docs/iommi.rst
	rm -f docs/lib.iommi.rst
	rm -f docs/lib.rst
	rm -f docs/Table.rst
	rm -f docs/Column.rst
	rm -f docs/Query.rst
	rm -f docs/Filter.rst
	rm -f docs/Form.rst
	rm -f docs/Field.rst
	rm -f docs/Action.rst
	rm -f docs/Link.rst
	rm -f docs/Endpoint.rst
	rm -f docs/Members.rst
	rm -f docs/Menu.rst
	rm -f docs/MenuItem.rst
	rm -f docs/Part.rst
	rm -f docs/Page.rst
	rm -f docs/Traversable.rst
	rm -f docs/Fragment.rst
	rm -f docs/Attrs.rst
	rm -f docs/Cell.rst
	rm -f docs/ColumnHeader.rst
	rm -f docs/Header.rst
	rm -f docs/HeaderConfig.rst
	rm -f docs/Container.rst
	rm -f docs/Style.rst
	rm -f docs/Asset.rst
	rm -f docs/EditColumn.rst
	rm -f docs/EditTable.rst
	rm -f docs/Cells.rst
	rm -f docs/FormAutoConfig.rst
	rm -f docs/QueryAutoConfig.rst
	rm -f docs/TableAutoConfig.rst
	rm -f docs/views.rst

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
docs: clean-docs
	rm -f docs/test_doc__*
	tox -e docs

docs-viewer:
	echo "http://127.0.0.1:10331"
	cd docs/_build/html; ../../../venv/bin/python -m http.server 10331

test-docs:
	tox -e docs

.PHONY: docs-coverage
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
	(cd iommi && ../venv/bin/django-admin compilemessages)
	(cd examples && ../venv/bin/django-admin compilemessages)

.PHONY: release
release: clean-build clean-pyc venv release-check
	rm -rf dist/ build/ && \
	django-admin compilemessages \
	    --ignore=venv \
	    --ignore=.tox \
	    --ignore=examples && \
	venv/bin/python -m build && \
# 	twine upload dist/*
