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
            const file = path.join(__dirname, '../../../syntaxes/matlab/Matlab.tmbundle/Syntaxes/MATLAB.tmLanguage')
            return readFile(file).then(data => vsctm.parseRawGrammar(data.toString()))
        }
        console.log(`Unknown scope name: ${scopeName}`);
        return null;
    }
});

const scope = process.argv[2];
const file = process.argv[3];
const jsonl = process.argv.slice(4).includes('--format=jsonl');

function stateScopes(ruleStack) {
    const scopes = [];
    for (let stack = ruleStack; stack; stack = stack.parent) {
        const scopeName = (stack.nameScopesList && stack.nameScopesList.scopeName) ||
            (stack.contentNameScopesList && stack.contentNameScopesList.scopeName) ||
            undefined;
        if (scopeName) {
            scopes.unshift(scopeName);
        }
    }
    return scopes;
}

// Load the JavaScript grammar and any other grammars included by it async.
registry.loadGrammar(scope).then(grammar => {
    const text = fs.readFileSync(file).toString().split("\n");
    let ruleStack = vsctm.INITIAL;
    for (let i = 0; i < text.length; i++) {
        const line = text[i];
        const lineTokens = grammar.tokenizeLine(line, ruleStack);
        // console.log(`\nTokenizing line: ${line}`);
        for (let j = 0; j < lineTokens.tokens.length; j++) {
            const token = lineTokens.tokens[j];
            if (jsonl) {
                console.log(JSON.stringify({
                    type: 'token',
                    line: i,
                    start: token.startIndex,
                    end: token.endIndex,
                    scopes: token.scopes,
                    content: line.substring(token.startIndex, token.endIndex)
                }));
            } else {
                console.log(`${i}-${token.startIndex}` +
                    `:${token.scopes.join('|')}` +
                    `:${line.substring(token.startIndex, token.endIndex)}`
                );
            }
        }
        ruleStack = lineTokens.ruleStack;
    }
    if (jsonl) {
        console.log(JSON.stringify({
            type: 'state',
            scopes: stateScopes(ruleStack)
        }));
    }
});
