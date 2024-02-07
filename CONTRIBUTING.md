Install the repository after cloning with [poetry](https://python-poetry.org/), and setup [pre-commit](https://pre-commit.com/) such that code is linted and formatted with [Ruff](https://docs.astral.sh/ruff/).

```bash
> pip install poetry
> cd textmate-grammar-python
> poetry install
> pre-commit install
```

Run unit tests
```bash
> tox run
```

Run static type checker
```bash
> tox run -e mypy
```

Run regression testing against vscode-textmate (will install npm and required packages)
```bash
> tox run -e regression
```
