import logging
from textmate_grammar.language import LanguageParser
from textmate_grammar.grammars import matlab


logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger("textmate_grammar").setLevel(logging.WARNING)
parser = LanguageParser(matlab.GRAMMAR)
parser._initialize_repository()