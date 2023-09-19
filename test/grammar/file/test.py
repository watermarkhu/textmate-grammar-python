import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parents[1]))
sys.path.append(str(Path(__file__).parents[3]))

from sphinx_matlab.grammar import LanguageParser, parse_file
from sphinx_matlab.tmlanguage import TMLIST


parser = LanguageParser(TMLIST)
filePath =  Path(__file__).parents[2] / "test_data" / "ValidateProps.m"

elements = parse_file(filePath, parser)

pass