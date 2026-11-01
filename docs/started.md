# Getting started

Add the package to your project with uv:

```bash
uv add textmate-grammar-python
```

It supports Python 3.10 through 3.15. For development setup and test instructions, see [CONTRIBUTING.md](https://github.com/watermarkhu/textmate-grammar-python/blob/main/CONTRIBUTING.md).

## Tokenize with a grammar

The API follows vscode-textmate's `Registry` and stateful line-tokenization model. Load the grammar, tokenize each line, and carry the returned `ruleStack` forward:

```python
from pathlib import Path

from textmate_grammar import INITIAL, Registry, parseRawGrammar

path = Path("MATLAB.tmLanguage")
raw = parseRawGrammar(path.read_text(), str(path))
registry = Registry({"loadGrammar": lambda scope: raw if scope == "source.matlab" else None})
grammar = registry.loadGrammar("source.matlab")
state = INITIAL
for line in Path("example.m").read_text().splitlines():
    result = grammar.tokenizeLine(line, state)
    state = result.ruleStack
    print(result.tokens)
```

`textmate_grammar.parsers.matlab` and `textmate_grammar.parsers.markdown` provide helpers for the bundled grammars. See [Tokens and state](tokenization.md) for the result shape.
