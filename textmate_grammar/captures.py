from typing import TYPE_CHECKING

from .handler import ContentHandler, Pattern, Match
from .logging import LOGGER
from .elements import ContentElement, ContentBlockElement

if TYPE_CHECKING:
    from .parser import GrammarParser


def dispatch_list(captures: "list[ContentElement | Captures]"):
    elements = []
    for capture in captures:
        if isinstance(capture, Captures):
            captured_elements = dispatch_list(capture.dispatch())
            elements.extend(captured_elements)
        else:
            elements.append(capture)
    return elements


def parse_captures(
    captures: "list[ContentElement | Captures]", parent: ContentElement | None = None
) -> list[ContentElement]:
    elements = dispatch_list(captures)

    if parent:
        elements = [element for element in elements if element != parent]

    for element in elements:
        if isinstance(element, ContentBlockElement):
            element.begin = parse_captures(element.begin, parent=element)
            element.end = parse_captures(element.end, parent=element)
        element.captures = parse_captures(element.captures, parent=element)

    return elements


class Captures(object):
    def __init__(
        self,
        handler: ContentHandler,
        pattern: Pattern,
        matching: Match,
        parsers: dict[str, "GrammarParser"],
        starting,
        boundary,
        **kwargs,
    ) -> None:
        self.handler = handler
        self.pattern = pattern
        self.matching = matching
        self.parsers = parsers
        self.starting = starting
        self.boundary = boundary
        self.kwargs = kwargs

    def __repr__(self) -> str:
        content = self.handler.read_pos(self.starting, self.boundary)
        return f"@captures<<{content}>>"

    def dispatch(self):
        elements = []
        for group_id, parser in self.parsers.items():
            if group_id > self.pattern.number_of_captures():
                LOGGER.warning(f"The capture group {group_id} does not exist in pattern {self.pattern._pattern}")
                continue

            group_span = self.matching.span(group_id)

            if group_span[0] == group_span[1]:
                continue

            group_starting = (self.starting[0], group_span[0])
            group_boundary = (self.starting[0], group_span[1])

            if parser == self and group_starting == self.starting and group_boundary == self.boundary:
                LOGGER.warning("Parser loop detected, continuing...", self, self.starting)
                continue

            parsed, captures, capture_span = parser._parse(
                self.handler,
                starting=group_starting,
                boundary=group_boundary,
                find_one=self.kwargs.pop("find_one", False),
                **self.kwargs,
            )

            if parser.token:
                if parsed and not type(parser) == "TokenParser":
                    element = ContentElement(
                        token=parser.token,
                        grammar=parser.grammar,
                        content=self.handler.read_pos(*capture_span),
                        indices=self.handler.chars(*capture_span),
                        captures=captures,
                    )
                else:
                    element = ContentElement(
                        token=parser.token,
                        grammar=parser.grammar,
                        content=self.handler.read_pos(group_starting, group_boundary),
                        indices=self.handler.chars(group_starting, group_boundary),
                    )
                elements.append(element)
            else:
                elements.extend(captures)

        return elements
