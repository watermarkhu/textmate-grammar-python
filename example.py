from pathlib import Path

from textmate_grammar.parsers.matlab import tokenize_matlab

source_path = Path(__file__).parent / "syntaxes" / "matlab" / "AnEnum.m"
for line_number, tokens in enumerate(tokenize_matlab(source_path), start=1):
    print(f"{line_number}: {tokens}")
