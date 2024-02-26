import atexit
from pathlib import Path
from pickle import UnpicklingError
from typing import Protocol

from .elements import ContentElement

CACHE_DIR = (Path() / ".textmate_cache").resolve()
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _path_to_key(path: Path) -> str:
    return str(path.resolve())


class TextmateCache(Protocol):
    def cache_valid(self, filepath: Path) -> bool:
        ...

    def load(self, filepath: Path) -> ContentElement:
        ...

    def save(self, filePath: Path, element: ContentElement) -> None:
        ...


class SimpleCache(TextmateCache):
    def __init__(self) -> None:
        self._element_cache: dict[str, ContentElement] = dict()
        self._element_timestamp: dict[str, float] = dict()

    def cache_valid(self, filepath: Path) -> bool:
        key = _path_to_key(filepath)
        if key not in self._element_cache:
            return False
        timestamp = filepath.resolve().stat().st_mtime
        return timestamp == self._element_timestamp[key]

    def load(self, filepath: Path) -> ContentElement:
        key = _path_to_key(filepath)
        return self._element_cache[key]

    def save(self, filepath: Path, element: ContentElement) -> None:
        key = _path_to_key(filepath)
        self._element_cache[key] = element
        self._element_timestamp[key] = filepath.resolve().stat().st_mtime


class ShelveCache(TextmateCache):
    def __init__(self) -> None:
        import shelve

        database_path = CACHE_DIR / "textmate.db"
        self._database = shelve.open(str(database_path))

        def exit():
            self._database.sync()
            self._database.close()

        atexit.register(exit)

    def cache_valid(self, filepath: Path) -> bool:
        key = _path_to_key(filepath)
        if key not in self._database:
            return False
        timestamp = filepath.resolve().stat().st_mtime
        try:
            valid = timestamp == self._database[key][0]
        except UnpicklingError:
            valid = False
        else:
            valid = False
        return valid

    def load(self, filepath: Path) -> ContentElement:
        key = _path_to_key(filepath)
        return self._database[key][1]

    def save(self, filepath: Path, element: ContentElement) -> None:
        element._dispatch(nested=True)
        key = _path_to_key(filepath)
        timestamp = filepath.resolve().stat().st_mtime
        self._database[key] = (timestamp, element)


CACHE: "TextmateCache" = SimpleCache()


def init_cache(type: str = "simple") -> "TextmateCache":
    global CACHE
    match type:
        case "shelve":
            CACHE = ShelveCache()
        case "simple":
            CACHE = SimpleCache()
    return CACHE
