
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
	rm -rf venv .venv

.PHONY: clean-build
clean-build:
	rm -fr build/
	rm -fr dist/

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
	uv run ruff check .

.PHONY: ruff-format
ruff-format:
	uv run ruff format .

test-all:
	tox --skip-missing-interpreters

.PHONY: test
test:
	uv run pytest

coverage:
	uv run pytest \
        --cov iommi \
        --cov tests \
        --cov-config .coveragerc
	uv run coverage report -m
	uv run coverage html

.PHONY: docs
docs: venv clean-docs
	rm -f docs/test_doc__*
	make -C docs clean SPHINXBUILD=../.venv/bin/sphinx-build
	make -C docs html SPHINXBUILD=../.venv/bin/sphinx-build

docs-viewer:
	echo "http://127.0.0.1:10331"
	cd docs/_build/html; uv run python -m http.server 10331

test-docs:
	make -C docs html

.PHONY: dist
dist: clean-build clean-pyc
	uv build
	ls -l dist

.PHONY: venv
venv:
	uv venv
	uv sync --dev

.PHONY: run-examples
run-examples:
	uv run --script examples/manage.py migrate
	uv run --script examples/manage.py runserver

.PHONY: test-live
test-live:
	uv run watchmedo shell-command --patterns="*.py" --command="uv run hammett" iommi tests


.PHONY: makemessages
makemessages:
	(cd iommi && uv run django-admin makemessages -a)
	(cd examples && uv run django-admin makemessages -a)

.PHONY: compilemessages
compilemessages:
	(cd iommi && uv run django-admin compilemessages)
	(cd examples && uv run django-admin compilemessages)

.PHONY: tag
tag:
	uv run --script util.py tag

.PHONY: release-check
release-check:
	uv run --script util.py release-check

.PHONY: release
release: clean-build release-check
	(cd iommi && uv run django-admin compilemessages)
	uv build
# 	uv publish
