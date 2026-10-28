# Changelog

## 0.7.0

This is a breaking 0.x release and a full port of the vscode-textmate 9.3.2 tokenization engine. It includes the rule model, scope-selector matcher, state stacks, tokenization loop, plist/JSON grammar loading, and Registry.

- The public API now follows vscode-textmate: `Registry`, `parseRawGrammar`, `Grammar.tokenizeLine`, `IToken`, and line-to-line `ruleStack` state.
- **Breaking:** the legacy element-tree API was removed. `ContentElement`, `flatten`, `parse_file`, and `parse_string` are no longer available.
- The minimum supported Python version is 3.10.
- Differential CI compares the Python engine with the pinned Node oracle across a 50-case MATLAB, Markdown, Python, and TypeScript corpus.
- Consolidates the dependency updates from the preceding implementation work (`onigurumacffi`, PyYAML, and `charset-normalizer`); test, development, and documentation tools are managed in uv dependency groups.
