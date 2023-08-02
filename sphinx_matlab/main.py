# %%
from tmlanguage import TMLIST, write_json
from grammar import GrammarParser


# write_json()

parser = GrammarParser(TMLIST["repository"]["line_continuation"], key="line_continuation")
(parsed, res, data) = parser.parse("... ")

parser = GrammarParser(TMLIST["repository"]["anonymous_function"], key="anonymous_function")
(parsed, res, data) = parser.parse("@(x, y) x.^2+y;")

pass

