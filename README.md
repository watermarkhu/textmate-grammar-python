[![PyPI - Version](https://img.shields.io/pypi/v/textmate-grammar-python.svg)](https://pypi.python.org/pypi/textmate-grammar-python)
[![PyPI - License](https://img.shields.io/pypi/l/textmate-grammar-python.svg)](https://github.com/watermarkhu/textmate-grammar-python/tree/main?tab=MIT-1-ov-file)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://img.shields.io/badge/mypy-checked-blue)](http://mypy-lang.org/)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
[![Python versions](https://img.shields.io/pypi/pyversions/textmate-grammar-python.svg)](https://pypi.python.org/pypi/textmate-grammar-python)
[![CI/CD](https://github.com/watermarkhu/textmate-grammar-python/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/watermarkhu/textmate-grammar-python/blob/main/.github/workflows/ci.yml)
[![readthedocs](https://readthedocs.org/projects/textmate-grammar-python/badge/?version=latest)](https://textmate-grammar-python.readthedocs.io)

# textmate-grammar-python

A lexer and tokenizer for grammar files as defined by TextMate and used in VSCode, implemented in Python. 

Textmate grammars are made for [vscode-texmate](https://github.com/microsoft/vscode-textmate), allowing for syntax highlighting in VSCode after tokenization. This presents textmate-grammar-python with a large list of potentially supported languages. 

## Usage
Install the module with:
```bash
pip install textmate-grammar-python
```

Before tokenization is possible, a `LanguageParser` needs to be initialized using a loaded grammar. 

```python
from textmate_grammar.parsers.matlab import MatlabParser
parser = MatlabParser()
```

After this, one can either choose to call [`parser.parsing_string`](https://textmate-grammar-python.readthedocs.io/en/latest/apidocs/textmate_grammar/textmate_grammar.language.html#textmate_grammar.language.LanguageParser.parse_string) to parse a input string directly, or call [`parser.parse_file`](https://textmate-grammar-python.readthedocs.io/en/latest/apidocs/textmate_grammar/textmate_grammar.language.html#textmate_grammar.language.LanguageParser.parse_file) with the path to the appropiate source file as the first argument, such as in the example [`example.py`](https://github.com/watermarkhu/textmate-grammar-python/blob/main/example.py). 

The parsed `element` object can be displayed directly by calling the [`print`](https://textmate-grammar-python.readthedocs.io/en/latest/apidocs/textmate_grammar/textmate_grammar.elements.html#textmate_grammar.elements.ContentElement.print) method. By default the element is printed as an element tree in a dictionary format. 

```python
>>> element = parser.parse_string("value = num2str(10);")
>>> element.print()

{'token': 'source.matlab',
 'children': [{'token': 'meta.assignment.variable.single.matlab', 
               'children': [{'token': 'variable.other.readwrite.matlab', 'content': 'value'}]},
              {'token': 'keyword.operator.assignment.matlab', 'content': '='},
              {'token': 'meta.function-call.parens.matlab',
               'begin': [{'token': 'entity.name.function.matlab', 'content': 'num2str'},
                         {'token': 'punctuation.section.parens.begin.matlab', 'content': '('}],
               'end': [{'token': 'punctuation.section.parens.end.matlab', 'content': ')'}],
               'children': [{'token': 'constant.numeric.decimal.matlab', 'content': '10'}]},
              {'token': 'punctuation.terminator.semicolon.matlab', 'content': ';'}]}

```
Alternatively, with the keyword argument `flatten` the element is displayed as a list per unique token. Here the first item in the list is the starting position (line, column) of the unique tokenized element. 

```python
>>> element.print(flatten=True)

[[(0, 0), 'value', ['source.matlab', 'meta.assignment.variable.single.matlab', 'variable.other.readwrite.matlab']],
 [(0, 5), ' ', ['source.matlab']],
 [(0, 6), '=', ['source.matlab', 'keyword.operator.assignment.matlab']],
 [(0, 7), ' ', ['source.matlab']],
 [(0, 8), 'num2str', ['source.matlab', 'meta.function-call.parens.matlab', 'entity.name.function.matlab']],
 [(0, 15), '(', ['source.matlab', 'meta.function-call.parens.matlab', 'punctuation.section.parens.begin.matlab']],
 [(0, 16), '10', ['source.matlab', 'meta.function-call.parens.matlab', 'constant.numeric.decimal.matlab']],
 [(0, 18), ')', ['source.matlab', 'meta.function-call.parens.matlab', 'punctuation.section.parens.end.matlab']],
 [(0, 19), ';', ['source.matlab', 'punctuation.terminator.semicolon.matlab']]]
```

## Information

- For further information, please checkout the [documentation](https://textmate-grammar-python.readthedocs.io/en/latest/). 
- To setup an environment for development, see [CONTRIBUTING.md](https://github.com/watermarkhu/textmate-grammar-python/blob/main/CONTRIBUTING.md)