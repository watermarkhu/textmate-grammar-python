from typing import TYPE_CHECKING

from .handler import ContentHandler, Pattern, Match
from .logging import LOGGER
from .elements import ContentElement, ContentBlockElement

if TYPE_CHECKING:
    from .parser import GrammarParser


def dispatch_list(captures: "list[ContentElement | Capture]"):
    """Dispatches all captured parsers in the list.
    """
    elements = []
    for capture in captures:
        if isinstance(capture, Capture):
            captured_elements = dispatch_list(capture.dispatch())
            elements.extend(captured_elements)
        else:
            elements.append(capture)
    return elements


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
        element.captures = parse_captures(element.captures, parent=element)

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
        """Dispatches the remaining parse of the capture group."""
        elements = []
        for group_id, parser in self.parsers.items():
            if group_id > self.pattern.number_of_captures():
                LOGGER.warning(f"The capture group {group_id} does not exist in pattern {self.pattern._pattern}")
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

            # Call the parse
            parsed, captured_elements, span = parser._parse(
                self.handler,
                starting=group_starting,
                boundary=group_boundary,
                find_one=self.kwargs.pop("find_one", False),
                **self.kwargs,
            )

            # Create ContentElement of token is defined
            if parser.token:
                if parsed and not type(parser) == "TokenParser":
                    element = ContentElement(
                        token=parser.token,
                        grammar=parser.grammar,
                        content=self.handler.read_pos(*span),
                        characters=self.handler.chars(*span),
                        captures=captured_elements,
                    )
                else:
                    element = ContentElement(
                        token=parser.token,
                        grammar=parser.grammar,
                        content=self.handler.read_pos(group_starting, group_boundary),
                        characters=self.handler.chars(group_starting, group_boundary),
                    )
                elements.append(element)
            # Return captures 
            else:
                elements.extend(captured_elements)

        return elements
