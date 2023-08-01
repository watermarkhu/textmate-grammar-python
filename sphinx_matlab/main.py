# %%
from tmlanguage import TMLIST, write_json
from grammar import GrammarParser



parser = GrammarParser(TMLIST["repository"]["anonymous_function"], key="anonymous_function")

(parsed, res, data) = parser.parse("@(x) x.^2;")

pass