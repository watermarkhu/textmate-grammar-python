# %%
from parsers import Parser
from pathlib import Path
import plistlib

# %%
TMFILE = Path(__file__).parents[1] / "tmlanguage" / "MATLAB.tmLanguage"

with open(TMFILE, "rb") as file:
    tmlist = plistlib.load(file, fmt=plistlib.FMT_XML)

# %%

parser = Parser(tmlist["repository"]["comments"]["patterns"][2], key="inline_comment")
(parsed, res, data) = parser("  % Test\n ")


parser = Parser(tmlist["repository"]["comment_block"], key="comment_block")
(parsed, res, data) = parser("  %{\nThis is a comment\nmultiple\n %}")

pass
