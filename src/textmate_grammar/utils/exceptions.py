from __future__ import annotations


class IncludedParserNotFound(Exception):
    """Exception raised when an included parser is not found in the store."""

    def __init__(self, key: str = "UNKNOWN", **kwargs) -> None:
        """
        Initialize the exception.

        :param key: The key of the included parser.
        :param kwargs: Additional keyword arguments.
        """
        message = f"Included parser <{key}> not found in store."
        super().__init__(message, **kwargs)


class IncompatibleFileType(Exception):
    """Exception raised when the input file has an incompatible file type."""

    def __init__(self, extensions: list[str], **kwargs) -> None:
        """
        Initialize the exception.

        :param extensions: List of compatible file extensions.
        :param kwargs: Additional keyword arguments.
        """
        message = f"Input file must have extension {' / '.join(extensions)}"
        super().__init__(message, **kwargs)


class FileNotFound(Exception):
    """Exception raised when a file is not found."""

    def __init__(self, file: str, **kwargs) -> None:
        """
        Initialize the exception.

        :param file: The path of the file.
        :param kwargs: Additional keyword arguments.
        """
        message = f"File not found: {file}"
        super().__init__(message, **kwargs)


class FileNotParsed(Exception):
    """Exception raised when a file is not parsed."""

    def __init__(self, file: str, **kwargs) -> None:
        """
        Initialize the exception.

        :param file: The path of the file.
        :param kwargs: Additional keyword arguments.
        """
        message = f"File not parsed: {file}"
        super().__init__(message, **kwargs)


class ImpossibleSpan(Exception):
    """Exception raised when a span is impossible."""

    def __init__(self, **kwargs) -> None:
        """
        Initialize the exception.

        :param kwargs: Additional keyword arguments.
        """
        super().__init__(
            "The closing position cannot be less or equal than the starting position",
            **kwargs,
        )
