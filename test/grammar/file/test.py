import sys
import logging
from pathlib import Path

sys.path.append(str(Path(__file__).parents[1]))
sys.path.append(str(Path(__file__).parents[3]))

from textmate_grammar.language import LanguageParser
from textmate_grammar.grammars import matlab
from textmate_grammar.logging import LOGGER


# filePath =  Path(__file__).parents[2] / "test_data" / "ValidateProps.m"
# filePath =  Path(__file__).parents[3] / "syntaxes" / "matlab" / "Account.m"
# filePath =  Path(__file__).parents[3] / "syntaxes" / "matlab" / "CircleArea.m"
filePath =  Path(__file__).parents[3] / "syntaxes" / "matlab" / "argumentValidation.m"


# logging.getLogger().setLevel(logging.INFO)
# file_handler = logging.FileHandler('output.log')
# LOGGER.logger.addHandler(file_handler)

parser = LanguageParser(matlab.GRAMMAR)
parser.initialize_repository()
element = parser.parse_file(filePath, log_level=logging.WARNING)

element.print(flatten=False)