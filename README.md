# sphinx-matlab

## Sources
- [Textmate guide](https://www.apeth.com/nonblog/stories/textmatebundle.html)
- [VSCode Syntax Highlighting guide](https://code.visualstudio.com/api/language-extensions/syntax-highlight-guide)
- [vscode-textmate](https://github.com/microsoft/vscode-textmate)

## TextMate 2 features that are not used
- begin/while match pattern
- [Format strings](https://macromates.com/blog/2011/format-strings/)

## TODO
- [x] Use yaml in stead of json
- [x] Grammar initialization with *repository* at any level
- [x] Proper line-by-line parsing
- [x] `\G` anchoring
- [x] Option to *disable* a grammar
- [x] Apply *applyEndPatternLast* option
- [ ] Something with *injections*

## Tokenization

The tokenization engine is based on the [syntax](https://github.com/mathworks/MATLAB-Language-grammar) created by Mathworks for its integration in IDE's such as VSCode. The syntax is a recursive list of regular expressions, normally read by the [TypeScript engine](https://github.com/microsoft/TypeScript-TmLanguage). The work here hopes also to improve the syntax such to improve the MATLAB [extension](https://github.com/mathworks/matlab-extension-for-vscode) for VSCode.