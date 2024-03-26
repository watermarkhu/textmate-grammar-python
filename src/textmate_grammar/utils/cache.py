from __future__ import annotations

import atexit
from pathlib import Path
from pickle import UnpicklingError
from typing import Protocol

from ..elements import ContentElement

CACHE_DIR = (Path() / ".textmate_cache").resolve()
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _path_to_key(path: Path) -> str:
    return str(path.resolve())


class TextmateCache(Protocol):
    """Interface for a Textmate cache."""

    def cache_valid(self, filepath: Path) -> bool:
        """
        Check if the cache for the given filepath is valid.

        :param filepath: The path to the file.
        :return: True if the cache is valid, False otherwise.
        """
        ...

    def load(self, filepath: Path) -> ContentElement:
        """
        Load the content from the specified filepath.

        :param filepath: The path to the file to load.
        :return: The loaded content element.
        """
        ...

    def save(self, filePath: Path, element: ContentElement) -> None:
        """
        Save the given content element to the specified file path.

        :param filePath: The file path where the content element should be saved.
        :param element: The content element to be saved.
        :return: None
        """
        ...


class SimpleCache(TextmateCache):
    """A simple cache implementation for storing content elements."""

    def __init__(self) -> None:
        """Initialize the SimpleCache."""
        self._element_cache: dict[str, ContentElement] = dict()
        self._element_timestamp: dict[str, float] = dict()

    def cache_valid(self, filepath: Path) -> bool:
        """Check if the cache is valid for the given filepath.

        :param filepath: The filepath to check.
        :return: True if the cache is valid, False otherwise.
        """
        key = _path_to_key(filepath)
        if key not in self._element_cache:
            return False
        timestamp = filepath.resolve().stat().st_mtime
        return timestamp == self._element_timestamp[key]

    def load(self, filepath: Path) -> ContentElement:
        """Load the content element from the cache for the given filepath.

        :param filepath: The filepath to load the content element from.
        :return: The loaded content element.
        """
        key = _path_to_key(filepath)
        return self._element_cache[key]

    def save(self, filepath: Path, element: ContentElement) -> None:
        """Save the content element to the cache for the given filepath.

        :param filepath: The filepath to save the content element to.
        :param element: The content element to save.
        :return: None
        """
        key = _path_to_key(filepath)
        self._element_cache[key] = element
        self._element_timestamp[key] = filepath.resolve().stat().st_mtime


class ShelveCache(TextmateCache):
    """A cache implementation using the shelve module."""

    def __init__(self) -> None:
        """Initialize the ShelveCache."""
        import shelve

        database_path = CACHE_DIR / "textmate.db"
        self._database = shelve.open(str(database_path))

        def exit():
            self._database.sync()
            self._database.close()

        atexit.register(exit)

    def cache_valid(self, filepath: Path) -> bool:
        """Check if the cache is valid for the given filepath.

        :param filepath: The filepath to check.
        :return: True if the cache is valid, False otherwise.
        """
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
        """Load the content element from the cache for the given filepath.

        :param filepath: The path for the cached content element.
        :return: The loaded content element.
        """
        key = _path_to_key(filepath)
        return self._database[key][1]

    def save(self, filepath: Path, element: ContentElement) -> None:
        """Save the content element to the cache for the given filepath.

        :param filepath: The filepath to save the content element to.
        :param element: The content element to save.
        """
        element._dispatch(nested=True)
        key = _path_to_key(filepath)
        timestamp = filepath.resolve().stat().st_mtime
        self._database[key] = (timestamp, element)


CACHE: TextmateCache = SimpleCache()


def init_cache(type: str = "simple") -> TextmateCache:
    """
    Initialize the cache based on the given type.

    :param type: The type of cache to initialize. Defaults to "simple".
    :return: The initialized cache object.
    """
    global CACHE
    if type == "shelve":
        CACHE = ShelveCache()
    elif type == "simple":
        CACHE = SimpleCache()
    else:
        raise NotImplementedError(f"Cache type {type} not implemented.")
    return CACHE
