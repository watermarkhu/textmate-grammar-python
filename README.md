# textmate-grammar-python

An interpreter for grammar files as defined by TextMate and used in VSCode, implemented in Python. TextMate grammars use the oniguruma dialect (https://github.com/kkos/oniguruma). Supports loading grammar files from JSON, PLIST, or YAML format. 

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
- [ ] Implement *injections*
- [ ] Implement Begin/While pattern

## Supported Languages
- [MATLAB](https://github.com/mathworks/MATLAB-Language-grammar)

## TextMate 2 features that are not used
- [Format strings](https://macromates.com/blog/2011/format-strings/)
