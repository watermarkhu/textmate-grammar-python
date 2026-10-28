"""Public vscode-textmate-shaped tokenization API."""

from . import matcher, oniglib, plist, raw_grammar, regexsource, registry, rules, tokenize
from .oniglib import (
    DEFAULT_ONIG_LIB,
    FindOption,
    IOnigCaptureIndex,
    IOnigLib,
    IOnigMatch,
    OnigLib,
    OnigScanner,
    OnigString,
    disposeOnigString,
)
from .raw_grammar import (
    ILocation,
    IRawCaptures,
    IRawGrammar,
    IRawRepository,
    IRawRule,
    parse_raw_grammar,
)
from .registry import Registry, RegistryOptions, SyncRegistry
from .tokenize import (
    Grammar,
    IToken,
    ITokenizeLineResult,
    StateStack,
    StateStackImpl,
    create_grammar,
)

parseRawGrammar = parse_raw_grammar  # noqa: N816
createGrammar = create_grammar  # noqa: N816
INITIAL = StateStackImpl.NULL

__all__ = [
    "DEFAULT_ONIG_LIB",
    "FindOption",
    "Grammar",
    "INITIAL",
    "ILocation",
    "IOnigLib",
    "IOnigCaptureIndex",
    "IOnigMatch",
    "IRawCaptures",
    "IRawGrammar",
    "IRawRepository",
    "IRawRule",
    "IToken",
    "ITokenizeLineResult",
    "OnigLib",
    "OnigScanner",
    "OnigString",
    "Registry",
    "RegistryOptions",
    "StateStack",
    "StateStackImpl",
    "SyncRegistry",
    "createGrammar",
    "create_grammar",
    "disposeOnigString",
    "matcher",
    "oniglib",
    "parseRawGrammar",
    "parse_raw_grammar",
    "plist",
    "raw_grammar",
    "regexsource",
    "registry",
    "rules",
    "tokenize",
]
