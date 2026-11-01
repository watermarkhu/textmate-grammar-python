# Tokens and state

`Grammar.tokenizeLine(line, state)` returns an `ITokenizeLineResult` containing the line's tokens and the state stack for the next line. Start with `INITIAL`, then pass each result's `ruleStack` into the next call.

Each `IToken` has `startIndex`, `endIndex`, and `scopes`. The scopes are ordered from the outer grammar scope to the most specific scope. The returned stack preserves open begin/end and while rules across line boundaries.

See [Getting started](started.md) for a Registry example and the [API reference](api.md).
