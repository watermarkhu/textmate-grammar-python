# %%
from tmlanguage import TMLIST
from grammar import GrammarParser
from pprint import pprint


parser = GrammarParser(TMLIST["repository"]["anonymous_function"], key="anonymous_function")
