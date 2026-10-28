[![PyPI - Version](https://img.shields.io/pypi/v/textmate-grammar-python.svg)](https://pypi.python.org/pypi/textmate-grammar-python)
[![PyPI - License](https://img.shields.io/pypi/l/textmate-grammar-python.svg)](https://github.com/watermarkhu/textmate-grammar-python/tree/main?tab=MIT-1-ov-file)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with ty](https://img.shields.io/badge/ty-checked-blue)](https://docs.astral.sh/ty/)
[![prek](https://img.shields.io/badge/prek-enabled-brightgreen)](https://prek.j178.dev/)
[![Python versions](https://img.shields.io/pypi/pyversions/textmate-grammar-python.svg)](https://pypi.python.org/pypi/textmate-grammar-python)
[![CI/CD](https://github.com/watermarkhu/textmate-grammar-python/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/watermarkhu/textmate-grammar-python/blob/main/.github/workflows/ci.yml)
[![readthedocs](https://readthedocs.org/projects/textmate-grammar-python/badge/?version=latest)](https://textmate-grammar-python.readthedocs.io)

# textmate-grammar-python

A Python port of the [vscode-textmate](https://github.com/microsoft/vscode-textmate) grammar tokenization engine. It loads TextMate grammars and tokenizes source one line at a time, carrying the rule stack between lines.

The `textmate_grammar.engine` modules port the rule model, scope matcher, grammar loading and registry, and stateful tokenization loop. A differential suite compares token boundaries and scope paths against the real vscode-textmate 9.3.2 Node oracle across a 50-case MATLAB, Markdown, Python, and TypeScript corpus.

## Usage
Requires Python 3.10 or newer. Install with:
```bash
pip install textmate-grammar-python
```

The public API follows vscode-textmate's registry and line-tokenization model. A registry loads raw grammar data by scope name; pass each line's returned `ruleStack` into the next call:

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

The bundled MATLAB and Markdown grammar helpers are also available from `textmate_grammar.parsers.matlab` and `textmate_grammar.parsers.markdown`.

## Migrating from 0.6.x

This 1.0.0 release is the first stable release; it breaks the old 0.x element-tree API. The old `LanguageParser` / `ContentElement` tree API (including `parse_file`, `parse_string`, and `flatten`) is removed without compatibility shims. Replace it with `Registry`, `parseRawGrammar`, `Grammar.tokenizeLine`, `IToken` tokens, and the `ruleStack` state API shown above.

## Information

- For further information, please checkout the [documentation](https://textmate-grammar-python.readthedocs.io/en/latest/).
- To setup an environment for development, see [CONTRIBUTING.md](https://github.com/watermarkhu/textmate-grammar-python/blob/main/CONTRIBUTING.md)
