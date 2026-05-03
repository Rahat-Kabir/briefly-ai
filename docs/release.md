# Release Process

This document describes how maintainers publish Briefly AI.

## Version Policy

- Public package versions start at `0.1.0`.
- Use patch bumps for fixes, docs polish, and small improvements.
- Use minor bumps for meaningful user-facing features.
- Do not reuse a PyPI version. Uploaded PyPI files are immutable.

## Files To Update

For each public release, update version references in:

- `pyproject.toml`
- `packages/briefly-core/pyproject.toml`
- `packages/briefly-cli/pyproject.toml`
- `packages/briefly-cli/src/briefly_cli/__init__.py`
- `tests/cli/test_help.py`
- `uv.lock`

Also update:

- `README.md` when user-facing behavior or install guidance changes.
- `docs/progress.md` for each completed version.
- `docs/tech_spec.md` when behavior or architecture changes.
- `docs/testing.md` when test workflow or coverage changes.

## Build And Test

From the repo root:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
$env:UV_LINK_MODE='copy'
uv lock
uv run pytest
uv run ruff check
uv build
```

Test the built wheel locally:

```powershell
uvx --from .\dist\briefly_ai-<version>-py3-none-any.whl briefly --version
uvx --from .\dist\briefly_ai-<version>-py3-none-any.whl briefly "hello" --extract
```

## GitHub

Commit and push the release source:

```powershell
git status
git add .
git commit -m "Release v<version>"
git push origin main
```

Tag the release commit:

```powershell
git tag v<version>
git push origin v<version>
```

## TestPyPI

Publish to TestPyPI first:

```powershell
uv publish --publish-url https://test.pypi.org/legacy/ .\dist\briefly_ai-<version>.tar.gz .\dist\briefly_ai-<version>-py3-none-any.whl
```

Test the TestPyPI install with PyPI as the dependency fallback:

```powershell
uvx --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ --from briefly-ai briefly --version
uvx --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ --from briefly-ai briefly "hello from testpypi" --extract
```

## PyPI

Publish to PyPI after TestPyPI verification:

```powershell
uv publish .\dist\briefly_ai-<version>.tar.gz .\dist\briefly_ai-<version>-py3-none-any.whl
```

Test the public install:

```powershell
uvx --from briefly-ai briefly --version
uvx --from briefly-ai briefly "hello from pypi" --extract
```
