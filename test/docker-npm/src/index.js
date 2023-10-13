const fs = require('fs');
const path = require('path');
const vsctm = require('vscode-textmate');
const oniguruma = require('vscode-oniguruma');

/**
 * Utility to read a file as a promise
 */
function readFile(path) {
    return new Promise((resolve, reject) => {
        fs.readFile(path, (error, data) => error ? reject(error) : resolve(data));
    })
}

const wasmBin = fs.readFileSync(path.join(__dirname, './node_modules/vscode-oniguruma/release/onig.wasm')).buffer;
const vscodeOnigurumaLib = oniguruma.loadWASM(wasmBin).then(() => {
    return {
        createOnigScanner(patterns) { return new oniguruma.OnigScanner(patterns); },
        createOnigString(s) { return new oniguruma.OnigString(s); }
    };
});

// Create a registry that can create a grammar from a scope name.
const registry = new vsctm.Registry({
    onigLib: vscodeOnigurumaLib,
    loadGrammar: (scopeName) => {
        if (scopeName === 'source.matlab') {
            // https://github.com/textmate/javascript.tmbundle/blob/master/Syntaxes/syntax/MATLAB.tmLanguage
            return readFile('./syntax/MATLAB.tmLanguage').then(data => vsctm.parseRawGrammar(data.toString()))
        }
        console.log(`Unknown scope name: ${scopeName}`);
        return null;
    }
});

// Load the JavaScript grammar and any other grammars included by it async.
registry.loadGrammar('source.matlab').then(grammar => {
    const text = [
        `function sayHello(name) {`,
        `\treturn "Hello, " + name;`,
        `}`
    ];
    let ruleStack = vsctm.INITIAL;
    for (let i = 0; i < text.length; i++) {
        const line = text[i];
        const lineTokens = grammar.tokenizeLine(line, ruleStack);
        console.log(`\nTokenizing line: ${line}`);
        for (let j = 0; j < lineTokens.tokens.length; j++) {
            const token = lineTokens.tokens[j];
            console.log(` - token from ${token.startIndex} to ${token.endIndex} ` +
              `(${line.substring(token.startIndex, token.endIndex)}) ` +
              `with scopes ${token.scopes.join(', ')}`
            );
        }
        ruleStack = lineTokens.ruleStack;
    }
});

/* OUTPUT:

Unknown scope name: source.matlab.regexp

Tokenizing line: function sayHello(name) {
 - token from 0 to 8 (function) with scopes source.matlab, meta.function.js, storage.type.function.js
 - token from 8 to 9 ( ) with scopes source.matlab, meta.function.js
 - token from 9 to 17 (sayHello) with scopes source.matlab, meta.function.js, entity.name.function.js
 - token from 17 to 18 (() with scopes source.matlab, meta.function.js, punctuation.definition.parameters.begin.js
 - token from 18 to 22 (name) with scopes source.matlab, meta.function.js, variable.parameter.function.js
 - token from 22 to 23 ()) with scopes source.matlab, meta.function.js, punctuation.definition.parameters.end.js
 - token from 23 to 24 ( ) with scopes source.matlab
 - token from 24 to 25 ({) with scopes source.matlab, punctuation.section.scope.begin.js

Tokenizing line:        return "Hello, " + name;
 - token from 0 to 1 (  ) with scopes source.matlab
 - token from 1 to 7 (return) with scopes source.matlab, keyword.control.js
 - token from 7 to 8 ( ) with scopes source.matlab
 - token from 8 to 9 (") with scopes source.matlab, string.quoted.double.js, punctuation.definition.string.begin.js
 - token from 9 to 16 (Hello, ) with scopes source.matlab, string.quoted.double.js
 - token from 16 to 17 (") with scopes source.matlab, string.quoted.double.js, punctuation.definition.string.end.js
 - token from 17 to 18 ( ) with scopes source.matlab
 - token from 18 to 19 (+) with scopes source.matlab, keyword.operator.arithmetic.js
 - token from 19 to 20 ( ) with scopes source.matlab
 - token from 20 to 24 (name) with scopes source.matlab, support.constant.dom.js
 - token from 24 to 25 (;) with scopes source.matlab, punctuation.terminator.statement.js

Tokenizing line: }
 - token from 0 to 1 (}) with scopes source.matlab, punctuation.section.scope.end.js

*/

