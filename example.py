import logging
from pathlib import Path
from textmate_grammar.language import LanguageParser
from textmate_grammar.grammars import matlab
from textmate_grammar.cache import init_cache

# Initialize shelved cache
init_cache("shelve")

# Initialize language parser
logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger("textmate_grammar").setLevel(logging.INFO)
parser = LanguageParser(matlab.GRAMMAR)

# Parse file
filePath = Path(__file__).parent / "syntaxes" / "matlab" / "AnEnum.m"
element = parser.parse_file(filePath)

# Print element
element.print()
