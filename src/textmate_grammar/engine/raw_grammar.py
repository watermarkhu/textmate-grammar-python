"""Faithful port of microsoft/vscode-textmate ``src/rawGrammar.ts``,
``src/parseRawGrammar.ts`` and ``src/json.ts`` (v9.3.2).

``rawGrammar.ts`` in the pinned upstream release is purely **type-level**
(``IRawGrammar``, ``IRawRule``, ``IRawCaptures``, ``IRawRepository``,
``ILocation``): there is no runtime ``RawGrammar``/``RawCaptures`` class and no
``valueAsString`` coercion in the pinned source (those notions date back to
pre-1.0 vscode-textmate; the modern engine simply runs on the ``any`` objects
produced by ``JSON.parse``/``plist.parsePLIST``, so upstream types are runtime
lies). The upstream interfaces are mirrored here as ``TypedDict`` shapes; the
scalar coercion helper :func:`value_as_string` covers the one coercion
downstream rule-building code must not guess at (JS ``String()`` semantics for
string-typed fields that may technically hold plist scalars).

``parseRawGrammar.ts`` semantics, exactly as upstream:

- a file path ending with ``.json`` (case sensitive suffix test: ``/\\.json$/``)
  → JSON grammar; everything else → plist grammar. There is **no** content
  sniffing and **no** YAML support upstream: unknown extensions are handed to
  the plist parser, which fails with ``Near offset ...: expected <`` for
  non-XML content (preserved here).
- the production path is **strict JSON**: upstream calls ``JSON.parse`` and
  only uses the hand-rolled ``parseJSON`` tokenizer from ``json.ts`` in debug
  mode. ``json.loads`` mirrors ``JSON.parse`` (strict JSON: no comments, no
  trailing commas).

``json.ts`` is ported in full and exported as :func:`parse_json` for the debug
path (``VSCODE_TEXTMATE_DEBUG`` environment variable, standing in for
upstream ``DebugFlags.InDebugMode``). Its tolerances — verified against the TS
source — are *not* jsonc: it supports neither comments nor trailing commas; its
leniency lies in JS ``parseFloat``-style number tokens (``1-2`` parses as
``1``) and in accepting trailing garbage after the root construct.
"""

from __future__ import annotations

import json
import re
from enum import IntEnum
from typing import Any, TypedDict

from .debug import DebugFlags
from .plist import _js_parse_float, _text_of, _units_of

__all__ = [
    "IN_DEBUG_MODE",
    "ILocation",
    "IRawCaptures",
    "IRawGrammar",
    "IRawRepository",
    "IRawRule",
    "LOCATION_KEY",
    "JSONStreamState",
    "parse_json",
    "parse_raw_grammar",
    "value_as_string",
]

# ---------------------------------------------------------------------------
# rawGrammar.ts — the raw grammar object model
# ---------------------------------------------------------------------------

#: Key under which ``parseRawGrammar`` (debug mode) embeds source locations.
LOCATION_KEY = "$vscodeTextmateLocation"


class ILocation(TypedDict):
    """Source location of a grammar construct (``ILocation`` upstream)."""

    #: Upstream declares ``string`` but ``parseRawGrammar`` may pass ``null``.
    filename: str | None
    line: int
    char: int


#: ``ILocatable`` upstream: objects produced by the debug-mode parsers may carry
#: an extra ``$vscodeTextmateLocation`` entry.
ILocatable = TypedDict(
    "ILocatable", {"$vscodeTextmateLocation": ILocation}, total=False
)

#: ``IRawCapturesMap & ILocatable`` upstream: maps capture ids (``"1"``, ...)
#: to raw rules, plus the optional location entry.
IRawCaptures = dict[str, Any]

#: ``IRawRepositoryMap & ILocatable`` upstream: maps repository keys to raw
#: rules plus the optional location entry. ``$self``/``$base`` entries are
#: added by the rules code (task 1b), not by the parsers.
IRawRepository = dict[str, Any]

IRawRule = TypedDict(  # noqa: TC001 — used by the TypedDicts below
    "IRawRule",
    {
        "$vscodeTextmateLocation": ILocation,
        "id": int,  # RuleId upstream — internal only, not part of the spec
        "include": str,
        "name": str,
        "contentName": str,
        "match": str,
        "captures": IRawCaptures,
        "begin": str,
        "beginCaptures": IRawCaptures,
        "end": str,
        "endCaptures": IRawCaptures,
        "while": str,
        "whileCaptures": IRawCaptures,
        "patterns": "list[IRawRule]",
        "repository": IRawRepository,
        "applyEndPatternLast": bool,
    },
    total=False,
)

IRawGrammar = TypedDict(
    "IRawGrammar",
    {
        "$vscodeTextmateLocation": ILocation,
        "scopeName": str,  # required upstream
        "patterns": "list[IRawRule]",  # required upstream
        "repository": IRawRepository,  # required upstream
        "injections": "dict[str, IRawRule]",
        "injectionSelector": str,
        "fileTypes": "list[str]",
        "name": str,
        "firstLineMatch": str,
    },
    total=False,
)


def value_as_string(value: Any) -> str:
    """Coerce a raw grammar scalar to a string with JS ``String()`` semantics.

    Practical fallback for rule-building code that must not guess how grammar
    scalars (which may technically be ``<integer>``/``<real>``/``<true>``
    values in wayward tmLanguage files) render as strings:

    - ``true``/``false`` → ``"true"``/``"false"`` (JS, not Python capitalization)
    - numbers → shortest double representation (``1.0`` → ``"1"``),
      ``NaN``/``Infinity`` match JS tokens
    - everything else → ``str(value)``
    """
    if isinstance(value, bool):  # before int: bool is an int subclass
        return "true" if value else "false"
    if isinstance(value, float):
        return _js_number_to_string(value)
    return str(value)


def _js_number_to_string(value: float) -> str:
    if value != value:  # nan
        return "NaN"
    if value == float("inf"):
        return "Infinity"
    if value == float("-inf"):
        return "-Infinity"
    if value.is_integer() and abs(value) <= 2**53:
        return str(int(value))
    return repr(value)


# ---------------------------------------------------------------------------
# parseRawGrammar.ts
# ---------------------------------------------------------------------------

#: Compatibility alias for upstream ``DebugFlags.InDebugMode``.
IN_DEBUG_MODE = DebugFlags.is_in_debug_mode()


def parse_raw_grammar(content: str, file_path: str | None = None) -> Any:
    """Parse a grammar from ``content`` (``parseRawGrammar.ts`` upstream).

    Routing is by file path only: paths ending in ``.json`` parse as JSON,
    everything else (including ``.jsonc``, ``.yaml`` and ``.xml``) parses as
    plist — upstream supports nothing else.
    """
    if file_path is not None and file_path.endswith(".json"):
        return _parse_json_grammar(content, file_path)
    return _parse_plist_grammar(content, file_path)


def _parse_json_grammar(contents: str, filename: str | None) -> Any:
    if IN_DEBUG_MODE:
        return parse_json(contents, filename, True)
    # Upstream: `return <IRawGrammar>JSON.parse(contents);`
    return json.loads(contents)


def _parse_plist_grammar(contents: str, filename: str | None) -> Any:
    from . import plist

    if IN_DEBUG_MODE:
        return plist.parse_with_location(contents, filename, LOCATION_KEY)
    return plist.parse_plist(contents)


# ---------------------------------------------------------------------------
# json.ts — the tolerant JSON tokenizer (debug path)
# ---------------------------------------------------------------------------


class JSONStreamState:
    """Tokenizer state (``JSONStreamState`` upstream)."""

    __slots__ = ("source", "pos", "length", "line", "char")

    source: str
    pos: int
    length: int
    line: int
    char: int

    def __init__(self, source: str) -> None:
        self.source = source
        self.pos = 0
        self.length = len(source)
        self.line = 1
        self.char = 0


class _JSONTokenType(IntEnum):
    UNKNOWN = 0
    STRING = 1
    LEFT_SQUARE_BRACKET = 2  # [
    LEFT_CURLY_BRACKET = 3  # {
    RIGHT_SQUARE_BRACKET = 4  # ]
    RIGHT_CURLY_BRACKET = 5  # }
    COLON = 6  # :
    COMMA = 7  # ,
    NULL = 8
    TRUE = 9
    FALSE = 10
    NUMBER = 11


class _JSONState(IntEnum):
    ROOT_STATE = 0
    DICT_STATE = 1
    DICT_STATE_COMMA = 2
    DICT_STATE_NO_CLOSE = 3
    ARR_STATE = 4
    ARR_STATE_COMMA = 5
    ARR_STATE_NO_CLOSE = 6


class _ChCode:  # character codes of the TS ChCode enum
    SPACE = 0x20
    HORIZONTAL_TAB = 0x09
    CARRIAGE_RETURN = 0x0D
    LINE_FEED = 0x0A
    QUOTATION_MARK = 0x22
    BACKSLASH = 0x5C

    LEFT_SQUARE_BRACKET = 0x5B
    LEFT_CURLY_BRACKET = 0x7B
    RIGHT_SQUARE_BRACKET = 0x5D
    RIGHT_CURLY_BRACKET = 0x7D
    COLON = 0x3A
    COMMA = 0x2C
    DOT = 0x2E

    D0 = 0x30
    D9 = 0x39

    MINUS = 0x2D
    PLUS = 0x2B

    E_UPPER = 0x45  # E
    E_LOWER = 0x65  # e

    A = 0x61  # a
    F = 0x66  # f
    L = 0x6C  # l
    N = 0x6E  # n
    R = 0x72  # r
    S = 0x73  # s
    T = 0x74  # t
    U = 0x75  # u


def _code_at(source: str, index: int) -> int:
    """``charCodeAt`` with NaN stand-in (-1) for out-of-range indices."""
    if 0 <= index < len(source):
        return ord(source[index])
    return -1


class _JSONToken:
    """Token accumulator (``JSONToken`` upstream)."""

    __slots__ = ("value", "type", "offset", "length", "line", "char")

    value: str | None
    type: _JSONTokenType
    offset: int
    length: int

    line: int  # 1 based line number
    char: int

    def __init__(self) -> None:
        self.value = None
        self.type = _JSONTokenType.UNKNOWN
        self.offset = -1
        self.length = -1
        self.line = -1
        self.char = -1

    def to_location(self, filename: str | None) -> dict[str, Any]:
        return {"filename": filename, "line": self.line, "char": self.char}


# endregion


def _do_fail(stream_state: JSONStreamState, msg: str) -> Any:
    raise ValueError(
        "Near offset "
        + str(stream_state.pos)
        + ": "
        + msg
        + " ~~~"
        + _text_of(stream_state.source[stream_state.pos : stream_state.pos + 50])
        + "~~~"
    )


_JSON_UNICODE_ESCAPE_RE = re.compile(r"\\u([0-9A-Fa-f]{4})")
_JSON_ESCAPE_RE = re.compile(r"\\(.)")

_JSON_SIMPLE_ESCAPES: dict[str, str] = {
    '"': '"',
    "\\": "\\",
    "/": "/",
    "b": "\b",
    "f": "\f",
    "n": "\n",
    "r": "\r",
    "t": "\t",
}


def _decode_json_string(raw: str, stream_state: JSONStreamState) -> str:
    """The two-pass string value replacement upstream performs verbatim.

    The order matters and is quirky: ``\\uXXXX`` sequences are resolved first
    (even inside ``\\\\uXXXX``, which leaves ``\\A`` behind and then rejects the
    leftover ``\\A`` as an invalid escape — a quirk of upstream, preserved).
    """
    value = _JSON_UNICODE_ESCAPE_RE.sub(lambda m: chr(int(m.group(1), 16)), raw)

    def unescape(match: re.Match[str]) -> str:
        mapped = _JSON_SIMPLE_ESCAPES.get(match.group(1))
        if mapped is None:
            _do_fail(stream_state, "invalid escape sequence")
            raise AssertionError("unreachable")
        return mapped

    return _JSON_ESCAPE_RE.sub(unescape, value)


def next_json_token(stream_state: JSONStreamState, out_token: _JSONToken) -> bool:
    """Produce the next token (``nextJSONToken`` upstream).

    Precondition upstream: the source is known to be valid JSON.
    Note the quirks: on ``False`` (EOS or an invalid keyword tail) the stream
    state is *not* updated; a failing string/keyword read leaves ``out_token``
    with the type set but no value/updated state.
    """
    out_token.value = None
    out_token.type = _JSONTokenType.UNKNOWN
    out_token.offset = -1
    out_token.length = -1
    out_token.line = -1
    out_token.char = -1

    source = stream_state.source
    pos = stream_state.pos
    length = stream_state.length
    line = stream_state.line
    char = stream_state.char

    # ------------------------ skip whitespace
    code = -1  # sentinel; the loop below always assigns before it breaks
    while True:
        if pos >= length:
            return False  # EOS

        code = _code_at(source, pos)
        if code in (_ChCode.SPACE, _ChCode.HORIZONTAL_TAB, _ChCode.CARRIAGE_RETURN):
            # regular whitespace
            pos += 1
            char += 1
            continue

        if code == _ChCode.LINE_FEED:
            # newline
            pos += 1
            line += 1
            char = 0
            continue

        # not whitespace
        break

    out_token.offset = pos
    out_token.line = line
    out_token.char = char

    if code == _ChCode.QUOTATION_MARK:
        # ------------------------ strings
        out_token.type = _JSONTokenType.STRING

        pos += 1
        char += 1

        while True:
            if pos >= length:
                return False  # EOS (state intentionally not updated)

            code = _code_at(source, pos)
            pos += 1
            char += 1

            if code == _ChCode.BACKSLASH:
                # skip next char
                pos += 1
                char += 1
                continue

            if code == _ChCode.QUOTATION_MARK:
                # end of the string
                break

        out_token.value = _text_of(
            _decode_json_string(source[out_token.offset + 1 : pos - 1], stream_state)
        )

    elif code == _ChCode.LEFT_SQUARE_BRACKET:
        out_token.type = _JSONTokenType.LEFT_SQUARE_BRACKET
        pos += 1
        char += 1

    elif code == _ChCode.LEFT_CURLY_BRACKET:
        out_token.type = _JSONTokenType.LEFT_CURLY_BRACKET
        pos += 1
        char += 1

    elif code == _ChCode.RIGHT_SQUARE_BRACKET:
        out_token.type = _JSONTokenType.RIGHT_SQUARE_BRACKET
        pos += 1
        char += 1

    elif code == _ChCode.RIGHT_CURLY_BRACKET:
        out_token.type = _JSONTokenType.RIGHT_CURLY_BRACKET
        pos += 1
        char += 1

    elif code == _ChCode.COLON:
        out_token.type = _JSONTokenType.COLON
        pos += 1
        char += 1

    elif code == _ChCode.COMMA:
        out_token.type = _JSONTokenType.COMMA
        pos += 1
        char += 1

    elif code == _ChCode.N:
        # ------------------------ null
        out_token.type = _JSONTokenType.NULL
        pos += 1
        char += 1
        code = _code_at(source, pos)
        if code != _ChCode.U:
            return False  # INVALID
        pos += 1
        char += 1
        code = _code_at(source, pos)
        if code != _ChCode.L:
            return False  # INVALID
        pos += 1
        char += 1
        code = _code_at(source, pos)
        if code != _ChCode.L:
            return False  # INVALID
        pos += 1
        char += 1

    elif code == _ChCode.T:
        # ------------------------ true
        out_token.type = _JSONTokenType.TRUE
        pos += 1
        char += 1
        code = _code_at(source, pos)
        if code != _ChCode.R:
            return False  # INVALID
        pos += 1
        char += 1
        code = _code_at(source, pos)
        if code != _ChCode.U:
            return False  # INVALID
        pos += 1
        char += 1
        code = _code_at(source, pos)
        if code != _ChCode.E_LOWER:
            return False  # INVALID
        pos += 1
        char += 1

    elif code == _ChCode.F:
        # ------------------------ false
        out_token.type = _JSONTokenType.FALSE
        pos += 1
        char += 1
        code = _code_at(source, pos)
        if code != _ChCode.A:
            return False  # INVALID
        pos += 1
        char += 1
        code = _code_at(source, pos)
        if code != _ChCode.L:
            return False  # INVALID
        pos += 1
        char += 1
        code = _code_at(source, pos)
        if code != _ChCode.S:
            return False  # INVALID
        pos += 1
        char += 1
        code = _code_at(source, pos)
        if code != _ChCode.E_LOWER:
            return False  # INVALID
        pos += 1
        char += 1

    else:
        # ------------------------ numbers
        out_token.type = _JSONTokenType.NUMBER
        while True:
            if pos >= length:
                return False  # EOS (state intentionally not updated)

            code = _code_at(source, pos)
            if (
                code == _ChCode.DOT
                or _ChCode.D0 <= code <= _ChCode.D9
                or code in (_ChCode.E_UPPER, _ChCode.E_LOWER)
                or code in (_ChCode.MINUS, _ChCode.PLUS)
            ):
                # looks like a piece of a number
                pos += 1
                char += 1
                continue

            break

    out_token.length = pos - out_token.offset
    if out_token.value is None:
        # substr semantics: clamped slice
        out_token.value = _text_of(
            source[out_token.offset : out_token.offset + out_token.length]
        )

    stream_state.pos = pos
    stream_state.line = line
    stream_state.char = char

    return True


def parse_json(source: str, filename: str | None, with_metadata: bool) -> Any:
    """``parseJSON`` upstream — the hand-rolled, JS-quirky JSON tokenizer.

    Only used on the debug path upstream (``VSCODE_TEXTMATE_DEBUG``); embeds
    ``$vscodeTextmateLocation`` when ``with_metadata`` is set.

    Like the TS engine, positions are indexed by UTF-16 code units; python
    values are returned with surrogate pairs recombined into astral characters
    (see ``plist._units_of``/``_text_of``).
    """
    # Index by UTF-16 code units so positions, locations and error offsets
    # match the TS engine exactly (no-op for ASCII/BMP documents).
    stream_state = JSONStreamState(_units_of(source))
    token = _JSONToken()
    state = _JSONState.ROOT_STATE
    cur: Any = None
    state_stack: list[_JSONState] = []
    obj_stack: list[Any] = []

    def push_state() -> None:
        nonlocal state, cur
        state_stack.append(state)
        obj_stack.append(cur)

    def pop_state() -> None:
        nonlocal state, cur
        state = state_stack.pop()
        cur = obj_stack.pop()

    def fail(msg: str) -> Any:
        return _do_fail(stream_state, msg)

    while next_json_token(stream_state, token):

        if state is _JSONState.ROOT_STATE:
            if cur is not None:
                fail("too many constructs in root")

            if token.type is _JSONTokenType.LEFT_CURLY_BRACKET:
                new_dict: Any = {}
                if with_metadata:
                    new_dict[LOCATION_KEY] = token.to_location(filename)
                cur = new_dict
                push_state()
                state = _JSONState.DICT_STATE
                continue

            if token.type is _JSONTokenType.LEFT_SQUARE_BRACKET:
                cur = []
                push_state()
                state = _JSONState.ARR_STATE
                continue

            fail("unexpected token in root")

        if state is _JSONState.DICT_STATE_COMMA:

            if token.type is _JSONTokenType.RIGHT_CURLY_BRACKET:
                pop_state()
                continue

            if token.type is _JSONTokenType.COMMA:
                state = _JSONState.DICT_STATE_NO_CLOSE
                continue

            fail("expected , or }")

        if state in (_JSONState.DICT_STATE, _JSONState.DICT_STATE_NO_CLOSE):

            if (
                state is _JSONState.DICT_STATE
                and token.type is _JSONTokenType.RIGHT_CURLY_BRACKET
            ):
                pop_state()
                continue

            if token.type is _JSONTokenType.STRING:
                key_value: Any = token.value

                next_json_token(stream_state, token)
                if token.type is not _JSONTokenType.COLON:
                    fail("expected colon")
                if not next_json_token(stream_state, token):
                    fail("expected value")

                state = _JSONState.DICT_STATE_COMMA

                if token.type is _JSONTokenType.STRING:
                    cur[key_value] = token.value
                    continue
                if token.type is _JSONTokenType.NULL:
                    cur[key_value] = None
                    continue
                if token.type is _JSONTokenType.TRUE:
                    cur[key_value] = True
                    continue
                if token.type is _JSONTokenType.FALSE:
                    cur[key_value] = False
                    continue
                if token.type is _JSONTokenType.NUMBER:
                    cur[key_value] = _js_parse_float(token.value or "")
                    continue
                if token.type is _JSONTokenType.LEFT_SQUARE_BRACKET:
                    new_array: list[Any] = []
                    cur[key_value] = new_array
                    push_state()
                    state = _JSONState.ARR_STATE
                    cur = new_array
                    continue
                if token.type is _JSONTokenType.LEFT_CURLY_BRACKET:
                    new_dict = {}
                    if with_metadata:
                        new_dict[LOCATION_KEY] = token.to_location(filename)
                    cur[key_value] = new_dict
                    push_state()
                    state = _JSONState.DICT_STATE
                    cur = new_dict
                    continue

            fail("unexpected token in dict")

        if state is _JSONState.ARR_STATE_COMMA:

            if token.type is _JSONTokenType.RIGHT_SQUARE_BRACKET:
                pop_state()
                continue

            if token.type is _JSONTokenType.COMMA:
                state = _JSONState.ARR_STATE_NO_CLOSE
                continue

            fail("expected , or ]")

        if state in (_JSONState.ARR_STATE, _JSONState.ARR_STATE_NO_CLOSE):

            if (
                state is _JSONState.ARR_STATE
                and token.type is _JSONTokenType.RIGHT_SQUARE_BRACKET
            ):
                pop_state()
                continue

            state = _JSONState.ARR_STATE_COMMA

            if token.type is _JSONTokenType.STRING:
                cur.append(token.value)
                continue
            if token.type is _JSONTokenType.NULL:
                cur.append(None)
                continue
            if token.type is _JSONTokenType.TRUE:
                cur.append(True)
                continue
            if token.type is _JSONTokenType.FALSE:
                cur.append(False)
                continue
            if token.type is _JSONTokenType.NUMBER:
                cur.append(_js_parse_float(token.value or ""))
                continue

            if token.type is _JSONTokenType.LEFT_SQUARE_BRACKET:
                new_array = []
                cur.append(new_array)
                push_state()
                state = _JSONState.ARR_STATE
                cur = new_array
                continue
            if token.type is _JSONTokenType.LEFT_CURLY_BRACKET:
                new_dict = {}
                if with_metadata:
                    new_dict[LOCATION_KEY] = token.to_location(filename)
                cur.append(new_dict)
                push_state()
                state = _JSONState.DICT_STATE
                cur = new_dict
                continue

            fail("unexpected token in array")

        fail("unknown state")

    if len(obj_stack) != 0:
        fail("unclosed constructs")

    return cur
