class IncludedParserNotFound(Exception):
    def __init__(self, key: str = "UNKNOWN") -> None:
        message = f"Included parser <{key}> not found in store."
        super().__init__(message)
