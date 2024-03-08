# Textmate Grammar Python

[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://img.shields.io/badge/mypy-checked-blue)](http://mypy-lang.org/)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
[![CI/CD](https://github.com/watermarkhu/textmate-grammar-python/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/watermarkhu/textmate-grammar-python/blob/main/.github/workflows/ci.yml)
[![readthedocs](https://readthedocs.org/projects/textmate-grammar-python/badge/?version=latest)](https://textmate-grammar-python.readthedocs.io)

A lexer and tokenizer for grammar files as defined by TextMate and used in VSCode, implemented in Python. 

Textmate grammars are made for [vscode-texmate](https://github.com/microsoft/vscode-textmate), allowing for syntax highlighting in VSCode after tokenization. This presents textmate-grammar-python with a large list of potentially supported languages. 

```{mermaid}
flowchart LR
    G[grammar file] 
    C[code]
    PY("`textmate-grammar-**python**`")
    JS("`vscode-textmate **js**`")
    T[tokens]
    click JS "https://github.com/microsoft/vscode-textmate"
    C --> PY
    C --> JS
    G -.-> PY
    G -.-> JS
    PY --> T
    JS --> T
```

## Index 

```{toctree}
:maxdepth: 2

started
languages
element
apidocs/index
```

## Sources
- [Textmate guide](https://www.apeth.com/nonblog/stories/textmatebundle.html)
- [VSCode Syntax Highlighting guide](https://code.visualstudio.com/api/language-extensions/syntax-highlight-guide)
- [vscode-textmate](https://github.com/microsoft/vscode-textmate)
- [Macromates texmate](https://macromates.com/textmate/manual/)
