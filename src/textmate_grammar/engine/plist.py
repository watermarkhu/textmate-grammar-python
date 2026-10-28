"""Faithful port of microsoft/vscode-textmate ``src/plist.ts`` (v9.3.2).

A very fast dependency-free property-list (XML) parser for TextMate grammars.
It is deliberately not a general XML parser: it understands exactly the tags
TextMate grammars use (``dict``, ``array``, ``key``, ``string``, ``real``,
``integer``, ``date``, ``data``, ``true``, ``false``, ``plist``) and skips
processing instructions, comments and doctypes. Semantics shipped here match
the TypeScript implementation 1:1, including its errors and quirks:

- Quirks preserved: closing tags and the ``plist`` tag are matched by string
  *prefix* (``</dictionary>`` closes as ``</dict>``); unterminated values at EOF
  are accepted; there is no CDATA support (``<![CDATA[...]]>`` is skipped to the
  next ``>`` like a comment); named entities only cover
  ``&amp;&lt;&gt;&quot;&apos;``, while numeric entities are decimal ``&#NNN;``
  and lowercase-hex ``&#xNNN;`` (uppercase hex digits are *not* decoded;
  ``&#x4A;`` stays literal); ``<true>``/``<false>`` ignore their text content;
  ``<integer>`` values always yield a JS ``number`` (a Python ``float``).
- Locations (``$vscodeTextmateLocation`` entries) are only produced in the
  ``parse_with_location`` debug path, exactly like upstream.
- Errors are ``ValueError`` with the upstream message format::

    Near offset <pos>: <message> ~~~<50 chars of input>~~~

See ``plist.ts`` in microsoft/vscode-textmate for the reference implementation.
"""

from __future__ import annotations

import re
from datetime import datetime
from enum import IntEnum
from typing import Any

__all__ = [
    "PLIST_LOCATION_KEY",
    "parse_plist",
    "parse_with_location",
]

#: The key ``parseRawGrammar.ts`` embeds locations under (debug mode).
PLIST_LOCATION_KEY = "$vscodeTextmateLocation"

# Character codes mirroring the TS ``ChCode`` enum. All of these are BMP values,
# so Python code points match JS UTF-16 code units character-for-character.
_CH_BOM = 0xFEFF
_CH_SPACE = 32
_CH_TAB = 9
_CH_CARRIAGE_RETURN = 13
_CH_LINE_FEED = 10

_CH_SLASH = ord("/")
_CH_LESS_THAN = ord("<")
_CH_QUESTION_MARK = ord("?")
_CH_EXCLAMATION_MARK = ord("!")


class _State(IntEnum):
    ROOT_STATE = 0
    DICT_STATE = 1
    ARR_STATE = 2


# Named entity table used by ``escapeVal``. TS first replaces numeric entities
# via regexes, then the named ones; the ordering is preserved in _escape_val.
_NAMED_ENTITIES: dict[str, str] = {
    "&amp;": "&",
    "&lt;": "<",
    "&gt;": ">",
    "&quot;": '"',
    "&apos;": "'",
}
_NAMED_ENTITIES_RE = re.compile("&amp;|&lt;|&gt;|&quot;|&apos;")
_DECIMAL_ENTITY_RE = re.compile("&#([0-9]+);")
_HEX_ENTITY_RE = re.compile("&#x([0-9a-f]+);")

# endregion

# endregion


def _js_lstrip(text: str) -> str:
    """Strip the JS ``StrWhiteSpace`` set (TS ``parseInt``/``parseFloat``)."""
    index = 0
    length = len(text)
    while index < length:
        ch = text[index]
        if ch.isspace() or ch == "\ufeff":  # JS treats BOM as whitespace
            index += 1
        else:
            break
    return text[index:]


def _units_of(content: str) -> str:
    """Spread astral characters into UTF-16 surrogate pairs (unit view).

    The TS parseInt/parser scans ``charCodeAt`` positions, i.e. UTF-16 code
    units — an astral character occupies *two* positions there. Grammar files
    are effectively always BMP/ASCII, so this is a no-op for them (fast path:
    ``str.isascii``); for non-BMP content it keeps positions, locations and
    error offsets byte-identical to the TS engine.
    """
    if content.isascii():
        return content
    if not any(ord(ch) > 0xFFFF for ch in content):
        return content
    out: list[str] = []
    for ch in content:
        code = ord(ch)
        if code > 0xFFFF:
            code -= 0x10000
            out.append(chr(0xD800 + (code >> 10)))
            out.append(chr(0xDC00 + (code & 0x3FF)))
        else:
            out.append(ch)
    return "".join(out)


def _text_of(units: str) -> str:
    """Inverse of _units_of: combine surrogate pairs, keep lone surrogates.

    This mirrors the TS view exactly: a high/low surrogate pair *is* the
    astral character in TS, while decode results like ``fromCodePoint(0xD83D)``
    stay lone surrogate units.
    """
    if not any(0xD800 <= ord(ch) <= 0xDFFF for ch in units):
        return units
    out: list[str] = []
    index = 0
    length = len(units)
    while index < length:
        code = ord(units[index])
        if 0xD800 <= code <= 0xDBFF and index + 1 < length:
            low = ord(units[index + 1])
            if 0xDC00 <= low <= 0xDFFF:
                out.append(chr(0x10000 + ((code - 0xD800) << 10) + (low - 0xDC00)))
                index += 2
                continue
        out.append(units[index])
        index += 1
    return "".join(out)


def _from_code_point(code: int) -> str:
    """JS ``String.fromCodePoint`` (same error message text on bad code)."""
    try:
        return chr(code)
    except ValueError:  # pragma: no cover - exercised by fuzz parity tests
        raise ValueError("Invalid code point " + str(code)) from None


def _js_parse_int(text: str) -> float:
    """JS ``parseInt(text, 10)``: longest decimal-digit prefix, else NaN.

    The TS source always calls this with radix 10, so no ``0x`` prefix handling
    applies (``parseInt("0x10", 10) === 0`` — verified against the TS source).
    Out-of-range integer values are widened to ``float`` (JS number semantics).
    """
    stripped = _js_lstrip(text)
    if not stripped:
        return float("nan")
    sign = 1
    if stripped[0] in "+-":
        if stripped[0] == "-":
            sign = -1
        stripped = stripped[1:]
    digits = stripped
    for index, letter in enumerate(stripped):
        if not "0" <= letter <= "9":
            digits = stripped[:index]
            break
    if not digits:
        return float("nan")
    return float(sign * int(digits))


_JS_FLOAT_RE = re.compile(r"[+-]?(?:Infinity|\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?")


def _js_parse_float(text: str) -> float:
    """JS ``parseFloat(text)``: longest valid numeric prefix, else NaN."""
    match = _JS_FLOAT_RE.match(_js_lstrip(text))
    if match is None:
        return float("nan")
    return float(match.group(0))


def _parse_js_date(text: str) -> Any:
    """Approximate the ES ``new Date(text)`` used for ``<date>`` values.

    ES defines only the ISO-8601 subset up front (other hosts parse it
    implementation-defined); invalid input yields the *Invalid Date* sentinel,
    represented here as ``NaN`` (its exposed numeric value). Valid ISO strings
    become timezone-aware ``datetime.datetime`` values. A Python object stands
    in for a JS ``Date`` — dates never appear in tmLanguage grammars, so the
    practical impact is nil.
    """
    try:
        if text.endswith("Z") or text.endswith("z"):
            text = text[:-1] + "+00:00"
        return datetime.fromisoformat(text)
    except ValueError:
        return float("nan")


def parse_with_location(content: str, filename: str | None, location_key_name: str | None) -> Any:
    """Parse ``content``, optionally embedding locations (debug mode)."""
    return _parse(content, filename, location_key_name)


def parse_plist(content: str) -> Any:
    """A very fast plist parser (``plist.parsePLIST`` upstream)."""
    return _parse(content, None, None)


def _parse(content: str, filename: str | None, location_key_name: str | None) -> Any:
    # The TS parser addresses content by UTF-16 code unit; use the unit view so
    # positions, locations and error offsets are identical even for non-BMP
    # input (a no-op for ASCII/BMP documents).
    content = _units_of(content)
    length = len(content)

    pos = 0
    line = 1
    char = 0

    # Skip UTF8 BOM
    if length > 0 and ord(content[0]) == _CH_BOM:
        pos = 1

    def char_code_at(index: int) -> int:
        """``charCodeAt`` with NaN stand-in (-1) for out-of-range indices."""
        if 0 <= index < length:
            return ord(content[index])
        return -1

    def advance_pos_by(by: int) -> None:
        nonlocal pos, line, char
        if location_key_name is None:
            pos = pos + by
        else:
            while by > 0:
                code = char_code_at(pos)
                if code == _CH_LINE_FEED:
                    pos += 1
                    line += 1
                    char = 0
                else:
                    pos += 1
                    char += 1
                by -= 1

    def advance_pos_to(to: int) -> None:
        nonlocal pos
        if location_key_name is None:
            pos = to
        else:
            advance_pos_by(to - pos)

    def skip_whitespace() -> None:
        while pos < length:
            code = char_code_at(pos)
            if (
                code != _CH_SPACE
                and code != _CH_TAB
                and code != _CH_CARRIAGE_RETURN
                and code != _CH_LINE_FEED
            ):
                break
            advance_pos_by(1)

    def advance_if_starts_with(string: str) -> bool:
        if content.startswith(string, pos):
            advance_pos_by(len(string))
            return True
        return False

    def advance_until(string: str) -> None:
        nonlocal pos
        next_occurence = content.find(string, pos)
        if next_occurence != -1:
            advance_pos_to(next_occurence + len(string))
        else:
            # EOF
            advance_pos_to(length)

    def capture_until(string: str) -> str:
        nonlocal pos
        next_occurence = content.find(string, pos)
        if next_occurence != -1:
            captured = content[pos:next_occurence]
            advance_pos_to(next_occurence + len(string))
            return captured
        # EOF
        captured = content[pos:]
        advance_pos_to(length)
        return captured

    state = _State.ROOT_STATE

    cur: Any = None
    state_stack: list[_State] = []
    obj_stack: list[Any] = []
    cur_key: str | None = None

    def push_state(new_state: _State, new_cur: Any) -> None:
        nonlocal state, cur
        state_stack.append(state)
        obj_stack.append(cur)
        state = new_state
        cur = new_cur

    def pop_state() -> None:
        nonlocal state, cur
        if len(state_stack) == 0:
            return fail("illegal state stack")
        state = state_stack.pop()
        cur = obj_stack.pop()

    def fail(msg: str) -> Any:
        raise ValueError(
            "Near offset "
            + str(pos)
            + ": "
            + msg
            + " ~~~"
            + _text_of(content[pos : pos + 50])
            + "~~~"
        )

    def make_location() -> dict[str, Any]:
        return {"filename": filename, "line": line, "char": char}

    def dict_state_enter_dict() -> None:
        nonlocal cur_key
        if cur_key is None:
            return fail("missing <key>")
        new_dict: Any = {}
        if location_key_name is not None:
            new_dict[location_key_name] = make_location()
        cur[cur_key] = new_dict
        cur_key = None
        push_state(_State.DICT_STATE, new_dict)

    def dict_state_enter_array() -> None:
        nonlocal cur_key
        if cur_key is None:
            return fail("missing <key>")
        new_array: list[Any] = []
        cur[cur_key] = new_array
        cur_key = None
        push_state(_State.ARR_STATE, new_array)

    def arr_state_enter_dict() -> None:
        new_dict: Any = {}
        if location_key_name is not None:
            new_dict[location_key_name] = make_location()
        cur.append(new_dict)
        push_state(_State.DICT_STATE, new_dict)

    def arr_state_enter_array() -> None:
        new_array: list[Any] = []
        cur.append(new_array)
        push_state(_State.ARR_STATE, new_array)

    def enter_dict() -> None:
        nonlocal cur
        if state is _State.DICT_STATE:
            dict_state_enter_dict()
        elif state is _State.ARR_STATE:
            arr_state_enter_dict()
        else:  # ROOT_STATE
            new_dict: Any = {}
            if location_key_name is not None:
                new_dict[location_key_name] = make_location()
            cur = new_dict
            push_state(_State.DICT_STATE, new_dict)

    def leave_dict() -> None:
        if state is _State.DICT_STATE:
            pop_state()
        elif state is _State.ARR_STATE:
            return fail("unexpected </dict>")
        else:  # ROOT_STATE
            return fail("unexpected </dict>")

    def enter_array() -> None:
        nonlocal cur
        if state is _State.DICT_STATE:
            dict_state_enter_array()
        elif state is _State.ARR_STATE:
            arr_state_enter_array()
        else:  # ROOT_STATE
            new_array: list[Any] = []
            cur = new_array
            push_state(_State.ARR_STATE, new_array)

    def leave_array() -> None:
        if state is _State.DICT_STATE:
            return fail("unexpected </array>")
        elif state is _State.ARR_STATE:
            pop_state()
        else:  # ROOT_STATE
            return fail("unexpected </array>")

    def accept_key(value: str) -> None:
        nonlocal cur_key
        if state is _State.DICT_STATE:
            if cur_key is not None:
                return fail("too many <key>")
            cur_key = value
        elif state is _State.ARR_STATE:
            return fail("unexpected <key>")
        else:  # ROOT_STATE
            return fail("unexpected <key>")

    def assign(value: Any) -> None:
        nonlocal cur, cur_key
        if state is _State.DICT_STATE:
            if cur_key is None:
                return fail("missing <key>")
            cur[cur_key] = value
            cur_key = None
        elif state is _State.ARR_STATE:
            cur.append(value)
        else:  # ROOT_STATE
            cur = value

    def accept_string(value: str) -> None:
        assign(value)

    def accept_real(value: float) -> None:
        if value != value:  # JS isNaN
            return fail("cannot parse float")
        assign(value)

    def accept_integer(value: float) -> None:
        if value != value:  # JS isNaN
            return fail("cannot parse integer")
        assign(value)

    def accept_date(value: Any) -> None:
        assign(value)

    def accept_data(value: str) -> None:
        assign(value)

    def accept_bool(value: bool) -> None:
        assign(value)

    def escape_val(raw: str) -> str:
        raw = _DECIMAL_ENTITY_RE.sub(lambda m: _from_code_point(int(m.group(1), 10)), raw)
        raw = _HEX_ENTITY_RE.sub(lambda m: _from_code_point(int(m.group(1), 16)), raw)
        raw = _NAMED_ENTITIES_RE.sub(lambda m: _NAMED_ENTITIES[m.group(0)], raw)
        return raw

    def parse_open_tag() -> tuple[str, bool]:
        raw = capture_until(">")
        is_closed = False
        if raw.endswith("/"):
            is_closed = True
            raw = raw[:-1]
        return _text_of(raw.strip()), is_closed

    def parse_tag_value(tag: tuple[str, bool]) -> str:
        if tag[1]:  # tag.isClosed
            return ""
        value = capture_until("</")
        advance_until(">")
        return _text_of(escape_val(value))

    while pos < length:
        skip_whitespace()
        if pos >= length:
            break

        ch_code = char_code_at(pos)
        advance_pos_by(1)
        if ch_code != _CH_LESS_THAN:
            return fail("expected <")

        if pos >= length:
            return fail("unexpected end of input")

        peek_ch_code = char_code_at(pos)

        if peek_ch_code == _CH_QUESTION_MARK:
            advance_pos_by(1)
            advance_until("?>")
            continue

        if peek_ch_code == _CH_EXCLAMATION_MARK:
            advance_pos_by(1)

            if advance_if_starts_with("--"):
                advance_until("-->")
                continue

            advance_until(">")
            continue

        if peek_ch_code == _CH_SLASH:
            advance_pos_by(1)
            skip_whitespace()

            if advance_if_starts_with("plist"):
                advance_until(">")
                continue

            if advance_if_starts_with("dict"):
                advance_until(">")
                leave_dict()
                continue

            if advance_if_starts_with("array"):
                advance_until(">")
                leave_array()
                continue

            return fail("unexpected closed tag")

        name, is_closed = parse_open_tag()

        if name == "dict":
            enter_dict()
            if is_closed:
                leave_dict()
            continue

        if name == "array":
            enter_array()
            if is_closed:
                leave_array()
            continue

        if name == "key":
            accept_key(parse_tag_value((name, is_closed)))
            continue

        if name == "string":
            accept_string(parse_tag_value((name, is_closed)))
            continue

        if name == "real":
            accept_real(_js_parse_float(parse_tag_value((name, is_closed))))
            continue

        if name == "integer":
            accept_integer(_js_parse_int(parse_tag_value((name, is_closed))))
            continue

        if name == "date":
            accept_date(_parse_js_date(parse_tag_value((name, is_closed))))
            continue

        if name == "data":
            accept_data(parse_tag_value((name, is_closed)))
            continue

        if name == "true":
            parse_tag_value((name, is_closed))
            accept_bool(True)
            continue

        if name == "false":
            parse_tag_value((name, is_closed))
            accept_bool(False)
            continue

        if name.startswith("plist"):
            continue

        return fail("unexpected opened tag " + name)

    return cur
