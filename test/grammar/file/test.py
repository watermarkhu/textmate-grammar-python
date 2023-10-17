import sys
import logging
from pathlib import Path

sys.path.append(str(Path(__file__).parents[1]))
sys.path.append(str(Path(__file__).parents[3]))



from textmate_grammar.language import LanguageParser
from textmate_grammar.grammars import matlab


logging.getLogger().setLevel(logging.DEBUG)
parser = LanguageParser(matlab.GRAMMAR)
parser.initialize_repository()

filePath =  Path(__file__).parents[3] / "syntaxes" / "matlab" / "Account.m"
# filePath =  Path(__file__).parents[3] / "syntaxes" / "matlab" / "CircleArea.m"
# filePath =  Path(__file__).parents[3] / "syntaxes" / "matlab" / "argumentValidation.m"

element = parser.parse_file(filePath, log_level=logging.INFO)


tokens = element.flatten()

element.print(flatten=True)