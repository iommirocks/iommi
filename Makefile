.PHONY: clean-pyc clean-build docs clean lint test coverage docs dist tag release-check

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
	rm -f docs/tri*.rst

lint:
	tox -e lint

black:
	tox -e black

test-all:
	tox --skip-missing-interpreters

test:
	pytest

coverage:
	tox -e coverage

docs:
	tox -e docs

docs-viewer:
	echo "http://127.0.0.1:10331"
	cd docs/_build/html; python -m http.server 10331

test-docs:
	tox -e docs-tests

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
	rm -rf dist/ && python setup.py sdist bdist_wheel && twine upload dist/*
