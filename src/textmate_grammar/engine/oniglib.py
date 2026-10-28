"""Port of vscode-textmate's ``src/onigLib.ts`` — the oniguruma library adapter.

vscode-textmate drives tokenization through an injectable ``IOnigLib`` that provides
 scanners and strings. Upstream this is backed by ``vscode-oniguruma`` (a wasm build of
oniguruma ~6.9). Here the same surface is provided on top of :mod:`onigurumacffi`, an
ffi binding of oniguruma 6.9 — the same engine family, so the semantics carry over:

- **Pattern selection** (leftmost match wins, ties resolved by the lowest pattern
  index) is done by oniguruma's RegSet API (``onig_regset_search`` with
  ``ONIG_REGSET_POSITION_LEAD``), which is exactly the strategy vscode-oniguruma's
  C++ ``findNextOnigScannerMatch`` uses for short strings.

- **The critical semantic** (see the parity plan): ``\\G`` matches *exactly at the
  start offset of the scan*, i.e. at the ``start_position`` passed to each
  :meth:`OnigScanner.find_next_match_sync` call, not at a stored anchor. oniguruma
  binds ``\\G`` to the search start, and vscode-textmate passes the token offset per
  call — ``Pattern.search(content, start=start_position)`` reproduces this 1:1.
  A pattern compiled once therefore matches at different offsets for different
  ``start_position`` values.

Capture indices are returned in Python code-point offsets (consistent with the rest
of the Python port; upstream returns UTF-16 offsets, having decoded the UTF-8 wasm
buffer). Unmatched capture groups — which oniguruma reports with offsets of ``-1`` —
are mapped to ``start == end == 0``, the same clamp vscode-oniguruma applies when its
``convertUtf8OffsetToUtf16`` encounters values below zero.

Every non-obvious piece references the ported section of vscode-oniguruma / onigLib.ts.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import IntFlag
from typing import Protocol

import onigurumacffi
from onigurumacffi import _Match as OnigurumaMatch

__all__: tuple[str, ...] = (
    "DEFAULT_ONIG_LIB",
    "FindOption",
    "IOnigCaptureIndex",
    "IOnigLib",
    "IOnigMatch",
    "OnigLib",
    "OnigScanner",
    "OnigString",
    "disposeOnigString",
)


class FindOption(IntFlag):
    """Port of the ``FindOption`` const enum from ``onigLib.ts`` (onigLib.ts:23-41).

    The bit values are vscode-textmate's own numbering; they are translated to the
    oniguruma search options named in the upstream member comments
    (:func:`_translate_options`). ``DEBUG_CALL`` is a debugging marker only and is
    dropped, like the ``debugCall`` flag is in vscode-oniguruma's non-debug path.
    """

    NONE = 0
    #: (str) isn't considered as begin of string — ``\\A`` fails
    NOT_BEGIN_STRING = 1
    #: (end) isn't considered as end of string — ``\\z`` and ``\\Z`` fail
    NOT_END_STRING = 2
    #: (start) isn't considered as begin of the search — ``\\G`` fails
    NOT_BEGIN_POSITION = 4
    #: used for debugging purposes (onigLib.ts:40)
    DEBUG_CALL = 8


@dataclass(frozen=True)
class IOnigCaptureIndex:
    """Port of ``IOnigCaptureIndex`` (onigLib.ts:12-16)."""

    start: int
    end: int
    length: int


@dataclass(frozen=True)
class IOnigMatch:
    """Port of ``IOnigMatch`` (onigLib.ts:18-21): the index of the matching pattern
    within the scanner and the captured regions of that match."""

    index: int
    capture_indices: tuple[IOnigCaptureIndex, ...]


# onigLib.ts:23-41 comments name the oniguruma equivalents of the vscode-textmate
# FindOption values; vscode-oniguruma's ``onigOptions`` (index.ts) performs exactly
# this translation when talking to the wasm module.
_ONIG_FLAG_MAP: tuple[tuple[FindOption, onigurumacffi.OnigSearchOption], ...] = (
    (FindOption.NOT_BEGIN_STRING, onigurumacffi.OnigSearchOption.NOT_BEGIN_STRING),
    (FindOption.NOT_END_STRING, onigurumacffi.OnigSearchOption.NOT_END_STRING),
    (FindOption.NOT_BEGIN_POSITION, onigurumacffi.OnigSearchOption.NOT_BEGIN_POSITION),
)


def _translate_options(options: FindOption) -> onigurumacffi.OnigSearchOption:
    """Translate vscode-textmate ``FindOption`` bits into oniguruma search flags."""
    flags = 0
    for bit, onig_flag in _ONIG_FLAG_MAP:
        if options & bit:
            flags |= int(onig_flag)
    return onigurumacffi.OnigSearchOption(flags)


def _to_capture_indices(match: OnigurumaMatch) -> tuple[IOnigCaptureIndex, ...]:
    """Port of the region → ``IOnigCaptureIndex[]`` conversion in vscode-oniguruma's
    ``findNextMatchSync`` (index.ts): one ``IOnigCaptureIndex`` per entry of the
    onig region, ``length = end - start``.

    Oniguruma reports groups that did not participate in the match with ``-1``
    offsets; those are clamped to ``start == end == 0`` (length 0), mirroring
    vscode-oniguruma's ``convertUtf8OffsetToUtf16``, which maps values below zero
    to 0. (onigurumacffi's own ``span`` cannot distinguish an unmatched group from
    an empty match — it slices the encoded string with the ``-1``, so the raw
    region arrays are read here; they are UTF-8 byte offsets that are converted to
    code-point offsets the same way onigurumacffi does it.)
    """
    capture_indices: list[IOnigCaptureIndex] = []
    for beg, end in zip(match._begs, match._ends, strict=True):
        if beg < 0 or end < 0:
            capture_indices.append(IOnigCaptureIndex(start=0, end=0, length=0))
            continue
        start = len(match._s_b[:beg].decode())
        end_code_point = len(match._s_b[:end].decode())
        capture_indices.append(
            IOnigCaptureIndex(start=start, end=end_code_point, length=end_code_point - start)
        )
    return tuple(capture_indices)


class OnigString:
    """Port of ``OnigString`` (onigLib.ts:48-51).

    Upstream this wraps the wasm-resident UTF-8 encoding of the string and carries
    the UTF-8/UTF-16 offset translation tables; Python strings are indexed by code
    point natively, so this is the light wrapper keeping ``content`` around, with a
    no-op ``dispose`` (parity of the optional ``dispose?`` member).
    """

    __slots__ = ("content",)

    def __init__(self, content: str) -> None:
        self.content = content

    def dispose(self) -> None:
        """No-op — there is no wasm string buffer to release."""


def disposeOnigString(string: OnigString) -> None:
    """Port of ``disposeOnigString`` (onigLib.ts:53-57)."""
    if callable(getattr(string, "dispose", None)):
        string.dispose()


class OnigScanner:
    """Port of ``OnigScanner`` from vscode-oniguruma — the scanner behind
    ``IOnigLib.createOnigScanner`` (onigLib.ts:43-46).

    Patterns are compiled eagerly at construction, like vscode-oniguruma does; an
    invalid pattern raises :class:`onigurumacffi.OnigError` where upstream throws
    the oniguruma error message. Matching uses one RegSet search per call, whose
    ``ONIG_REGSET_POSITION_LEAD`` strategy yields the same candidate selection as
    vscode-oniguruma's C++ ``findNextOnigScannerMatch``: the match beginning at the
    smallest offset wins and ties break toward the lowest pattern index.
    """

    def __init__(self, sources: Sequence[str]) -> None:
        self._sources: tuple[str, ...] = tuple(sources)
        self._regset: onigurumacffi._RegSet | None  # set here, dropped by dispose()
        self._regset = onigurumacffi.compile_regset(*self._sources)

    @property
    def sources(self) -> tuple[str, ...]:
        return self._sources

    def find_next_match_sync(
        self,
        string: str | OnigString,
        start_position: int = 0,
        options: FindOption = FindOption.NONE,
    ) -> IOnigMatch | None:
        """Port of ``OnigScanner.findNextMatchSync`` (onigLib.ts:44).

        ``string`` may be a plain string or an :class:`OnigString`, as upstream.
        ``start_position`` is the offset the scan starts at, which is where
        ``\\G`` binds: a pattern containing ``\\G`` is compiled once and still
        matches at whatever initial offset the caller passes.
        """
        if self._regset is None:
            raise RuntimeError("scanner has been disposed")
        content = string.content if isinstance(string, OnigString) else string
        flags = _translate_options(options)
        index, match = self._regset.search(content, start=start_position, flags=flags)
        if index < 0 or match is None:
            return None
        return IOnigMatch(index=index, capture_indices=_to_capture_indices(match))

    def find_best_match(
        self,
        position: int,
        line: str,
        has_anchor: bool = False,
        has_back_references: bool = False,
    ) -> IOnigMatch | None:
        """Convenience mirroring the pre-4.0 ``IOnigScanner.findBestMatch(position,
        line, hasAnchor, hasBackReferences)`` surface named in the porting plan.

        ``position`` is the scan offset, so a ``\\G`` binds there: with
        ``has_anchor=True`` the patterns are scanned as-is, with ``has_anchor=False``
        ``FindOption.NOT_BEGIN_POSITION`` makes every ``\\G`` fail (the same
        equivalent option vscode-textmate's ``getFindOptions`` builds for
        ``allowG=False`` in ``grammar/tokenizeString.ts:549-557``).

        ``has_back_references`` is bookkeeping parity for the old signature only:
        in the current vscode-textmate, ``\\n`` backreference patterns are resolved
        *before* scanning (``rule.ts`` ``resolveBackReferences``, ported in
        :mod:`textmate_grammar.engine.regexsource`), so the scanner has nothing to
        do with them — the flag is accepted and unused.
        """
        options = FindOption.NONE if has_anchor else FindOption.NOT_BEGIN_POSITION
        return self.find_next_match_sync(line, position, options)

    def dispose(self) -> None:
        """Port of the optional ``dispose`` member: drops the compiled pattern set."""
        self._regset = None


class IOnigLib(Protocol):
    """Port of the ``IOnigLib`` interface (onigLib.ts:7-10): the library surface
    vscode-textmate expects the tokenization engine to be wired against."""

    def create_onig_scanner(self, sources: Sequence[str]) -> OnigScanner:
        """Port of ``createOnigScanner(sources)``."""
        ...

    def create_onig_string(self, string: str) -> OnigString:
        """Port of ``createOnigString(str)``."""
        ...


class OnigLib:
    """The concrete onigurumacffi-backed :class:`IOnigLib` — the role
    vscode-oniguruma plays upstream when ``main.ts`` wires up the default library."""

    def create_onig_scanner(self, sources: Sequence[str]) -> OnigScanner:
        return OnigScanner(sources)

    def create_onig_string(self, string: str) -> OnigString:
        return OnigString(string)


#: Default library instance for the engine, upstream equivalent of the
#: ``onigLib`` value handed to ``Registry``/``Grammar`` by ``main.ts``.
DEFAULT_ONIG_LIB: IOnigLib = OnigLib()
