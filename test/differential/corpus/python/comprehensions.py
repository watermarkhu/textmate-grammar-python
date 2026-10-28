from collections.abc import Iterable


def normalize(values: Iterable[str]) -> list[str]:
    return [cleaned for value in values if (cleaned := value.strip())]


def grouped(rows):
    return {key: [value for value in values] for key, values in rows}
