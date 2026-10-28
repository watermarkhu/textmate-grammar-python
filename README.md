[![PyPI - Version](https://img.shields.io/pypi/v/textmate-grammar-python.svg)](https://pypi.python.org/pypi/textmate-grammar-python)
[![PyPI - License](https://img.shields.io/pypi/l/textmate-grammar-python.svg)](https://github.com/watermarkhu/textmate-grammar-python/tree/main?tab=MIT-1-ov-file)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://img.shields.io/badge/mypy-checked-blue)](http://mypy-lang.org/)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
[![Python versions](https://img.shields.io/pypi/pyversions/textmate-grammar-python.svg)](https://pypi.python.org/pypi/textmate-grammar-python)
[![CI/CD](https://github.com/watermarkhu/textmate-grammar-python/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/watermarkhu/textmate-grammar-python/blob/main/.github/workflows/ci.yml)
[![readthedocs](https://readthedocs.org/projects/textmate-grammar-python/badge/?version=latest)](https://textmate-grammar-python.readthedocs.io)

# textmate-grammar-python

A lexer and tokenizer for grammar files as defined by TextMate and used in VSCode, implemented in Python. 

TextMate grammars are made for [vscode-textmate](https://github.com/microsoft/vscode-textmate), allowing for syntax highlighting in VS Code after tokenization. This presents textmate-grammar-python with a large list of potentially supported languages.

## Usage
Install the module with:
```bash
pip install textmate-grammar-python
```

The public API follows vscode-textmate's registry and line-tokenization model. A registry loads raw grammar data by scope name, and the returned grammar carries a state stack from line to line:

```python
from pathlib import Path

from textmate_grammar import INITIAL, Registry, parseRawGrammar

grammar_path = Path("MATLAB.tmLanguage")
raw_grammar = parseRawGrammar(grammar_path.read_text(), str(grammar_path))
registry = Registry({"loadGrammar": lambda scope: raw_grammar if scope == "source.matlab" else None})
grammar = registry.loadGrammar("source.matlab")
state = INITIAL
for line in Path("example.m").read_text().splitlines():
    result = grammar.tokenizeLine(line, state)
    state = result.ruleStack
    print(result.tokens)  # each token has startIndex, endIndex, and scopes
```

Language helpers are also available via `textmate_grammar.parsers.matlab` and `.markdown` for the bundled grammars.

## Migrating from 0.6.x

The old `LanguageParser` / `ContentElement` tree API has been removed without compatibility shims. Use the vscode-textmate-shaped `Registry`, `parseRawGrammar`, `Grammar.tokenizeLine`, `IToken` tokens, and `ruleStack` state API instead; this is a breaking change in the 0.x series.

## Information

- For further information, please checkout the [documentation](https://textmate-grammar-python.readthedocs.io/en/latest/). 
- To setup an environment for development, see [CONTRIBUTING.md](https://github.com/watermarkhu/textmate-grammar-python/blob/main/CONTRIBUTING.md)
