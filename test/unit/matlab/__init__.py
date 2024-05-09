import logging

from textmate_grammar.parsers.matlab import MatlabParser

logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger("textmate_grammar").setLevel(logging.INFO)
parser = MatlabParser()
