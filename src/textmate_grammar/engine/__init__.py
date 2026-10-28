"""Tokenization engine ported 1:1 from microsoft/vscode-textmate.

Work in progress — see the parity plan (/home/dev/.opencode/plan).
Modules land per task: regexsource, rules, matcher, tokenize, captures,
raw_grammar, plist, registry. The legacy recursive-descent parsers
(parser.py/handler.py/elements.py) are retired once the engine covers them.
"""
