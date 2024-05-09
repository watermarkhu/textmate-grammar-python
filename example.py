import logging
from pathlib import Path
from pprint import pprint

from textmate_grammar.grammars.matlab import MatlabGrammar
from textmate_grammar.language import LanguageParser
from textmate_grammar.utils.cache import init_cache

# Initialize shelved cache
init_cache("shelve")

# Enable debug logging
logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger("textmate_grammar").setLevel(logging.INFO)

# Initialize language parser
parser = LanguageParser(MatlabGrammar())

# Parse file
filePath = Path(__file__).parent / "syntaxes" / "matlab" / "AnEnum.m"
element = parser.parse_file(filePath)

# Print element
element.print()

# Find all enum members
enum_members = element.findall('variable.other.enummember.matlab')
pprint(enum_members)