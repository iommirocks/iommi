# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Testing
- `python -m pytest` - Run all tests
- `python -m pytest <module>__tests.py` - Run tests for a specific module (e.g., `python -m pytest iommi/form__tests.py`)
- `python -m pytest docs/test_doc_<name>.py` - Run documentation tests for a specific module
- `make test` - Alternative test runner using make
- `make test-docs` - Run documentation tests specifically
- `make coverage` - Run tests with coverage report
- `tox` - Run tests across multiple Django versions

### Code Quality
- `make lint` or `make ruff` - Run linting with ruff
- `make ruff-format` - Format code with ruff

### Development Environment
- `make venv` - Create virtual environment using tox
- `source venv/bin/activate` - Activate virtual environment
- `make run-examples` - Run the examples Django project for testing

### Documentation
- `make docs` - Generate Sphinx documentation
- `make docs-viewer` - Serve docs locally at http://127.0.0.1:10331

## Architecture Overview

iommi is a Django toolkit for building web applications with declarative components. The architecture is built around composable parts that render to HTML and handle interactions.

### Core Component Hierarchy
- **Part** (`iommi/part.py`) - Base class for all renderable components that can handle AJAX/POST
- **Page** (`iommi/page.py`) - Container for composing multiple parts into complete pages
- **Table** (`iommi/table.py`) - Data display component with sorting, filtering, pagination
- **Form** (`iommi/form.py`) - Form handling with validation and rendering
- **Fragment** (`iommi/fragment.py`) - Basic HTML building blocks and text components
- **Menu** (`iommi/menu.py`) - Navigation menu components

### Key Architectural Patterns

**Declarative System**: Components use a declarative syntax built on top of `iommi/declarative/` modules:
- `dispatch.py` - Method dispatch system for component configuration
- `namespace.py` - Hierarchical configuration namespace
- `with_meta.py` - Meta-class system for component inheritance

**Refinable System** (`iommi/refinable.py`): Components can be refined/configured at multiple levels (class, instance, runtime) before being "bound" to a request.

**Style System** (`iommi/style*.py`): Pluggable styling for different CSS frameworks (Bootstrap, Bulma, Foundation, etc.). Styles define how components render their HTML structure.

**Auto-generation**: Components can introspect Django models to automatically generate appropriate configurations (`iommi/from_model.py`).

**Path System** (`iommi/path.py`): URL routing for component endpoints, enabling AJAX interactions and deep linking.

### Testing Patterns

Tests follow a pattern where each module `foo.py` has corresponding `foo__tests.py`. Documentation tests are in `docs/test_doc_<module>.py`. The test configuration uses pytest with Django integration and includes:

- Model fixtures for Artist/Album/Track data (music database theme)
- Snapshot testing with pytest_snapshot
- Test isolation with automatic sequence resets
- Custom pytest configuration in `conftest.py`

### Development Settings

Test settings are in `tests/settings.py` with iommi-specific middleware and test configurations. The project uses tox for testing across Django versions and includes mutation testing with mutmut.

### Documentation and Testing

- The docs cookbooks aren't just documentation, they are also tests and part of the test suite. Treat them as full tests.
- The rst files are generated automatically from the pytests in the docs directory