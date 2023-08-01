class IncludedParserNotFound(Exception):
    def __init__(self, key: str = "UNKNOWN", **kwargs) -> None:
        message = f"Included parser <{key}> not found in store."
        super().__init__(message, **kwargs)


class CannotCloseEnd(Exception):
    def __init__(self, source: str = "", **kwargs) -> None:
        message = f"Could not close end in parser for source '{source}'"
        super().__init__(message, **kwargs)


class RegexGroupsMismatch(Exception):
    def __init__(self, **kwargs) -> None:
        message = f"Number of captures does not match regex"
        super().__init__(message, **kwargs)