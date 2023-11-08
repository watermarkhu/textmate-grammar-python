from typing import TYPE_CHECKING

from .logging import LOGGER
from .handler import ContentHandler, Pattern, Match
from .elements import ContentElement, ContentBlockElement

if TYPE_CHECKING:
    from .parser import GrammarParser


def parse_captures(
    captures: "list[ContentElement | Capture]", parent: ContentElement | None = None
) -> list[ContentElement]:
    """Dispatches all nested captured parsers in list of elements."""
    elements = dispatch_list(captures)

    if parent:
        elements = [element for element in elements if element != parent]

    for element in elements:
        if isinstance(element, ContentBlockElement):
            element.begin = parse_captures(element.begin, parent=element)
            element.end = parse_captures(element.end, parent=element)
        element.children = parse_captures(element.children, parent=element)

    return elements


def dispatch_list(captures: "list[ContentElement | Capture]"):
    """Dispatches all captured parsers in the list."""
    elements = []
    for capture in captures:
        if isinstance(capture, Capture):
            captured_elements = dispatch_list(capture.dispatch())
            elements.extend(captured_elements)
        else:
            elements.append(capture)
    return elements


class Capture(object):
    """A captured matching group.

    After mathing, any pattern can have a number of capture groups for which subsequent parsers can be defined.
    The Capture object stores this subsequent parse to be dispatched at a later moment.
    """

    def __init__(
        self,
        handler: ContentHandler,
        pattern: Pattern,
        matching: Match,
        parsers: dict[str, "GrammarParser"],
        starting: tuple[int, int],
        boundary: tuple[int, int],
        key: str = "",
        **kwargs,
    ) -> None:
        self.handler = handler
        self.pattern = pattern
        self.matching = matching
        self.parsers = parsers
        self.starting = starting
        self.boundary = boundary
        self.key = key
        self.kwargs = kwargs

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Capture):
            return (
                True
                if self.key == other.key
                and self.starting == other.starting
                and self.matching.group() == other.matching.group()
                else False
            )
        else:
            return False

    def __repr__(self) -> str:
        return f"@capture<{self.key}>"

    def dispatch(self):
        """Dispatches the remaining parse of the capture group."""
        elements = []
        for group_id, parser in self.parsers.items():
            if group_id > self.pattern.number_of_captures():
                LOGGER.warning(
                    f"The capture group {group_id} does not exist in pattern {self.pattern._pattern}"
                )
                continue

            group_span = self.matching.span(group_id)

            # Empty group
            if group_span[0] == group_span[1]:
                continue

            group_starting = (self.starting[0], group_span[0])
            group_boundary = (self.starting[0], group_span[1])

            if parser == self and group_starting == self.starting and group_boundary == self.boundary:
                LOGGER.warning("Parser loop detected, continuing...", self, self.starting)
                continue

            # Dispatch the parse
            self.kwargs.pop("leading_chars", None)
            parsed, captured_elements, _ = parser._parse(
                self.handler,
                starting=group_starting,
                boundary=group_boundary,
                find_one=self.kwargs.pop("find_one", False),
                parent_capture=self,
                **self.kwargs,
            )

            if parsed:
                elements.extend(captured_elements)

        return elements
