.PHONY: clean-pyc clean-build docs clean lint ruff ruff-format test coverage docs dist tag release-check

help:
	@echo "clean-build - remove build artifacts"
	@echo "clean-pyc - remove Python file artifacts"
	@echo "lint - check style with flake8"
	@echo "test - run tests"
	@echo "coverage - check code coverage quickly with the default Python"
	@echo "docs - generate Sphinx HTML documentation, including API docs"
	@echo "dist - package"
	@echo "tag - set a tag with the current version number"
	@echo "release-check - check release tag"

clean: clean-build clean-pyc
	rm -rf htmlcov/
	rm -rf venv

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr lib/*.egg-info

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

lint: ruff

ruff:
	tox -e venv -- ruff check .

ruff-format:
	tox -e venv -- ruff format .

test-all:
	tox --skip-missing-interpreters

test:
	python -m pytest

coverage:
	tox -e coverage

docs: clean-docs
	rm -f docs/test_doc__*
	tox -e docs

docs-viewer:
	echo "http://127.0.0.1:10331"
	cd docs/_build/html; python -m http.server 10331

test-docs:
	tox -e docs

docs-coverage:
	tox -e coverage-from-docs

dist: clean
	python setup.py sdist
	python setup.py bdist_wheel
	ls -l dist

tag:
	python setup.py tag

release-check:
	python setup.py release_check

venv:
	tox -e venv

run-examples: venv
	venv/bin/python examples/manage.py migrate
	venv/bin/python examples/manage.py runserver

test-live:
	watchmedo shell-command --patterns="*.py" --command="python -m hammett" iommi tests


makemessages:
	(cd iommi && django-admin makemessages -a)
	(cd examples && django-admin makemessages -a)


compilemessages:
	(cd iommi && django-admin compilemessages)
	(cd examples && django-admin compilemessages)

release:
	rm -rf dist/ build/ && django-admin compilemessages --ignore=venv --ignore=.tox --ignore=examples && python setup.py sdist bdist_wheel && twine upload dist/*
