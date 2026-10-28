Install the repository after cloning with [uv](https://docs.astral.sh/uv/), and setup [pre-commit](https://pre-commit.com/) such that code is linted and formatted with [Ruff](https://docs.astral.sh/ruff/) and checked with [mypy](https://mypy-lang.org/).

```bash
uv sync --all-groups
pre-commit install
```

To install the git submodules used for regression testing:

```bash
git submodule update --init
```
