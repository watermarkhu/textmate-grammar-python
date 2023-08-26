
from .parser import LanguageParser
from .exceptions import IncompatibleFileType, FileNotFound, FileNotParsed
from .elements import ParsedElement
from charset_normalizer import from_path
from pathlib import Path
from typing import Union, List
from io import StringIO


def parse_file(filePath: Union[str, Path], parser: LanguageParser) -> List[ParsedElement]:

    if type(filePath) != Path:
        filePath = Path(filePath)

    if filePath.suffix.split('.')[-1] not in parser.fileTypes:
        raise IncompatibleFileType(extensions=parser.fileTypes)

    if not filePath.exists():
        raise FileNotFound(str(filePath))
    
    stream = StringIO(str(from_path(filePath).best()))

    parsed, elements, _ = parser.parse(stream)

    if not parsed:
        raise FileNotParsed(str(filePath))

    return elements
