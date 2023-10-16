class IncludedParserNotFound(Exception):
    def __init__(self, key: str = "UNKNOWN", **kwargs) -> None:
        message = f"Included parser <{key}> not found in store."
        super().__init__(message, **kwargs)


class IncompatibleFileType(Exception):
    def __init__(self, extensions: list[str], **kwargs) -> None:
        message = f"Input file must have extension {' / '.join(extensions)}"
        super().__init__(message, **kwargs)


class FileNotFound(Exception):
    def __init__(self, file: str, **kwargs) -> None:
        message = f"File not found: {file}"
        super().__init__(message, **kwargs)


class FileNotParsed(Exception):
    def __init__(self, file: str, **kwargs) -> None:
        message = f"File not parsed: {file}"
        super().__init__(message, **kwargs)


class ImpossibleSpan(Exception):
    def __init__(self, **kwargs) -> None:
        super().__init__("The closing position cannot be less or equal than the starting position", **kwargs)
