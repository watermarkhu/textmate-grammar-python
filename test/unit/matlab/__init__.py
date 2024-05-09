import logging

from textmate_grammar.grammars.matlab import MatlabGrammar
from textmate_grammar.language import LanguageParser

logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger("textmate_grammar").setLevel(logging.INFO)
parser = LanguageParser(MatlabGrammar())
