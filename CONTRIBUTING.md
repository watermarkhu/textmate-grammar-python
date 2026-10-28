Use [uv](https://docs.astral.sh/uv/) to install the project and test dependencies. Install [pre-commit](https://pre-commit.com/) to run Ruff and mypy checks automatically:

```bash
uv sync --group test
uv run pre-commit install
```

Run the unit tests with:

```bash
uv run pytest -q test/unit
```

The differential suite compares this port with the pinned Node oracle. It needs Node on `PATH`, the grammar corpus submodules, and the oracle's npm dependencies:

```bash
git submodule update --init
(cd test/differential/node_root && npm ci)
uv run pytest -q test/differential
```

Run the full checks with `uv run ruff check src/` and `uv run mypy .`. For the documentation build, install the doc group (`uv sync --no-dev --group doc`) and run `uv run make -C docs html`.
