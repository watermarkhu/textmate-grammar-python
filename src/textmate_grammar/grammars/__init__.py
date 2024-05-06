from typing import Protocol


class BasePreProcessor(Protocol):

    def process(self, input: str) -> str:
        ...
