# Textmate Grammar Python

[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with ty](https://img.shields.io/badge/ty-checked-blue)](https://docs.astral.sh/ty/)
[![prek](https://img.shields.io/badge/prek-enabled-brightgreen)](https://prek.j178.dev/)
[![CI/CD](https://github.com/watermarkhu/textmate-grammar-python/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/watermarkhu/textmate-grammar-python/blob/main/.github/workflows/ci.yml)

A Python port of the [vscode-textmate](https://github.com/microsoft/vscode-textmate) grammar tokenization engine. It parses TextMate grammars and tokenizes source line by line while preserving the state stack between lines.

The engine's token streams are checked against vscode-textmate 9.3.2 using a Node oracle and a differential corpus spanning MATLAB, Markdown, Python, and TypeScript.

```mermaid
flowchart LR
    G[TextMate grammar] --> R[Registry]
    C[source lines] --> R
    R --> T[tokens + rule stack]
    T -. differential comparison .-> O[vscode-textmate 9.3.2 oracle]
    click O "https://github.com/microsoft/vscode-textmate"
```

## Sources
- [Textmate guide](https://www.apeth.com/nonblog/stories/textmatebundle.html)
- [VSCode Syntax Highlighting guide](https://code.visualstudio.com/api/language-extensions/syntax-highlight-guide)
- [vscode-textmate](https://github.com/microsoft/vscode-textmate)
- [Macromates texmate](https://macromates.com/textmate/manual/)
