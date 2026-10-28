"""Smoke coverage for the bundled language convenience APIs."""

from textmate_grammar.parsers.markdown import markdown_grammar, tokenize_markdown


def test_markdown_wrapper_tokenizes_with_stateful_grammar() -> None:
    lines = tokenize_markdown("# Heading\n\nBody")

    assert len(lines) == 3
    assert any("markup.heading.markdown" in token.scopes for token in lines[0])
    assert any(token.scopes[0] == "text.html.markdown" for token in lines[2])
    assert markdown_grammar() is markdown_grammar()
