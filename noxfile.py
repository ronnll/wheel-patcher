import nox

# Use uv for fast package installation
nox.options.default_venv_backend = "uv"

# Test on all supported Python versions from pyproject.toml
@nox.session(python=["3.9", "3.10", "3.11", "3.12"])
def tests(session):
    """Run tests with pytest."""
    session.install("pytest")
    session.install("-e", ".")
    session.run("pytest", "tests/", "-v")


@nox.session(python="3.12")
def lint(session):
    """Run code linting with ruff."""
    session.install("ruff")
    session.run("ruff", "check", "src/", "tests/")


@nox.session(python="3.12")
def format_check(session):
    """Check code formatting with ruff."""
    session.install("ruff")
    session.run("ruff", "format", "--check", "src/", "tests/")


@nox.session(python="3.12")
def format(session):
    """Auto-format code with ruff."""
    session.install("ruff")
    session.run("ruff", "format", "src/", "tests/")


@nox.session(python="3.12")
def type_check(session):
    """Run type checking with mypy."""
    session.install("mypy")
    session.install("-e", ".")
    session.run("mypy", "src/", "--strict")
