"""Python port of vscode-textmate's grammar tokenizer."""

from .engine import (
    INITIAL,
    Grammar,
    IToken,
    ITokenizeLineResult,
    Registry,
    RegistryOptions,
    StateStack,
    SyncRegistry,
    create_grammar,
    createGrammar,
    parse_raw_grammar,
    parseRawGrammar,
)

__version__ = "0.6.1"

__all__ = [
    "Grammar",
    "INITIAL",
    "IToken",
    "ITokenizeLineResult",
    "Registry",
    "RegistryOptions",
    "StateStack",
    "SyncRegistry",
    "__version__",
    "createGrammar",
    "create_grammar",
    "parseRawGrammar",
    "parse_raw_grammar",
]
