# %%
from tmlanguage import TMLIST, write_json
from grammar import GrammarParser
from io import StringIO

write_json()

parser = GrammarParser(TMLIST["repository"]["line_continuation"], key="line_continuation")
(parsed, data) = parser.parse(StringIO("..."))

parser = GrammarParser(TMLIST["repository"]["import"], key="import")
# (parsed, data) = parser.parse(StringIO("import module.submodule.*"))

GrammarParser(TMLIST["repository"]["comment_block"], key="comment_block")
# parser = GrammarParser(TMLIST["repository"]["comments"], key="comments")

# (parsed, data) = parser.parse(StringIO(" % Test this is a comment. "))
# (parsed, data) = parser.parse(StringIO("  %% This is a section comment\n"))
# (parsed, data) = parser.parse(StringIO("  %{\nThis is a comment\nmultiple\n %}"))

parser = GrammarParser(TMLIST["repository"]["anonymous_function"], key="anonymous_function")
# (parsed, data) = parser.parse(StringIO("@(x,  y) x.^2+y;"))
# (parsed, data) = parser.parse(StringIO("@(x, ...\n    y) x.^2+y;"))

data[0].print()
pass
