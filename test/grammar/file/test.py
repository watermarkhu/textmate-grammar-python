import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parents[1]))
sys.path.append(str(Path(__file__).parents[3]))

from textmate_grammar.language import LanguageParser
from textmate_grammar.grammars import matlab


parser = LanguageParser(matlab.GRAMMAR)
parser.initialize_repository()
filePath =  Path(__file__).parents[2] / "test_data" / "ValidateProps.m"

# elements = parse_file(filePath, parser)

pass