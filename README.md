# textmate-grammar-python

An interpreter for grammar files as defined by TextMate and used in VSCode, implemented in Python. TextMate grammars use the oniguruma dialect (https://github.com/kkos/oniguruma). Supports loading grammar files from JSON, PLIST, or YAML format. 

```python
>>> from textmate_grammar.language import LanguageParser
>>> from textmate_grammar.grammars import matlab

>>> parser = LanguageParser(matlab.GRAMMAR)
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

## Sources
- [Textmate guide](https://www.apeth.com/nonblog/stories/textmatebundle.html)
- [VSCode Syntax Highlighting guide](https://code.visualstudio.com/api/language-extensions/syntax-highlight-guide)
- [vscode-textmate](https://github.com/microsoft/vscode-textmate)
- [Macromates texmate](https://macromates.com/textmate/manual/)

## TODO
- [x] Use yaml in stead of json
- [x] Grammar initialization with *repository* at any level
- [x] Proper line-by-line parsing
- [x] `\G` anchoring
- [x] Option to *disable* a grammar
- [x] Option to *applyEndPatternLast*
- [x] Implement *injections*
- [ ] Implement Begin/While pattern

## Supported Languages
- [MATLAB](https://github.com/mathworks/MATLAB-Language-grammar)

## TextMate 2 features that are not used
- [Format strings](https://macromates.com/blog/2011/format-strings/)
