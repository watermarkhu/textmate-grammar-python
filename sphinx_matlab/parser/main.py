# %%
from parsers import Parser
from pathlib import Path
from pprint import pprint
import plistlib

# %%
TMFILE = Path(__file__).parents[1] / "tmlanguage" / "MATLAB.tmLanguage"

with open(TMFILE, "rb") as file:
    tmlist = plistlib.load(file, fmt=plistlib.FMT_XML)

# %%
Parser(tmlist["repository"]["comment_block"], key="comment_block")
parser = Parser(tmlist["repository"]["comments"], key="comments")

# # Inline comment
(parsed, res, data) = parser(" % Test this is a comment. \n")
if parsed:
    pprint(data[0].to_dict())

# Section comment
(parsed, res, data) = parser("  %% This is a section comment \n")
if parsed:
    pprint(data[0].to_dict())

# Multiline comment
(parsed, res, data) = parser("  %{\nThis is a comment\nmultiple\n %}")
if parsed:
    pprint(data[0].to_dict())

# %%

# # Imports
parser = Parser(tmlist["repository"]["import"], key="import")
(parsed, res, data) = parser("import module.submodule.class")
if parsed:
    pprint(data[0].to_dict())


# # %%

# parser = Parser(tmlist["repository"]["anonymous_function"], key="anonymous_function")
