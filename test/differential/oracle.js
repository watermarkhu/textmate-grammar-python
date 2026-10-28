/**
 * Standalone vscode-textmate oracle for the differential test harness.
 *
 * Usage:
 *     node oracle.js <grammar-file> <text-file>
 *
 * Prints one JSON object per line (JSONL) per token:
 *     {"type":"token","line":<0-based>,"start":<col>,"end":<col>,"scopes":[...],"content":"..."}
 * with the scope stack verbatim from grammars `tokenizeLine` (root scope first), and after the
 * last line:
 *     {"type":"state","scopes":[<final ruleStack scope names, root first>]}
 *
 * The grammar is loaded from the grammar file argument via `vsctm.parseRawGrammar`; any grammar
 * request for its own scopeName resolves to the parsed grammar, every other request (embedded
 * languages, injections) resolves to `null`, which makes vscode-textmate silently skip those
 * includes.
 */
'use strict';

const fs = require('fs');
const path = require('path');

// Resolve the oracle's dependencies from the local node_root install directory.
module.paths.unshift(path.join(__dirname, 'node_root', 'node_modules'));

const vsctm = require('vscode-textmate');
const oniguruma = require('vscode-oniguruma');

/** Emit one JSON record to stdout. */
function emit(record) {
    process.stdout.write(JSON.stringify(record) + '\n');
}

/**
 * Scope names of the final rule stack, root first. Each stack frame contributes its "name" scope
 * list; this digest is what makes cross-line state drift detectable when comparing files.
 */
function stateScopeNames(stack) {
    const frames = [];
    for (let node = stack; node; node = node.parent) {
        frames.unshift(node);
    }
    return frames.map((frame) => (frame.nameScopesList ? frame.nameScopesList.getScopeNames().join(' ') : ''));
}

async function main() {
    const [grammarFile, textFile] = process.argv.slice(2);
    if (!grammarFile || !textFile) {
        process.stderr.write('usage: node oracle.js <grammar-file> <text-file>\n');
        process.exit(2);
    }

    // Set up the vscode-oniguruma wasm bindings (same setup as test/regression/index.js).
    const wasmBin = fs.readFileSync(
        path.join(__dirname, 'node_root', 'node_modules', 'vscode-oniguruma', 'release', 'onig.wasm')
    ).buffer;
    const vscodeOnigurumaLib = oniguruma.loadWASM(wasmBin).then(() => ({
        createOnigScanner(patterns) {
            return new oniguruma.OnigScanner(patterns);
        },
        createOnigString(s) {
            return new oniguruma.OnigString(s);
        },
    }));

    // Load the grammar from the file path argument and keep handing it back for its own scope name.
    const parsedGrammar = vsctm.parseRawGrammar(fs.readFileSync(grammarFile).toString());
    const scopeName = parsedGrammar.scopeName;

    const registry = new vsctm.Registry({
        onigLib: vscodeOnigurumaLib,
        loadGrammar: function (requested) {
            if (requested === scopeName) {
                return Promise.resolve(parsedGrammar);
            }
            // Unresolved includes (embedded languages etc.) are skipped silently.
            return Promise.resolve(null);
        },
    });

    /** @type {import('vscode-textmate').IGrammar} */
    const grammar = await registry.loadGrammar(scopeName);
    if (!grammar) {
        throw new Error(`Failed to load grammar ${scopeName} from ${grammarFile}`);
    }

    // Tokenize line by line, handing the rule stack back (multi-line while rules).
    let ruleStack = vsctm.INITIAL;
    const text = fs.readFileSync(textFile).toString().split('\n');
    for (let i = 0; i < text.length; i++) {
        const line = text[i];
        const lineTokens = grammar.tokenizeLine(line, ruleStack);
        ruleStack = lineTokens.ruleStack;
        // vscode-textmate appends a virtual trailing "\n" to the line content before scanning
        // (see Grammar.tokenizeLine), so token indices live in that augmented coordinate space
        // and tokens may extend past the real line end and cover that virtual newline. Emit the
        // content on the augmented line, then trim the virtual newline back off so that the
        // records line up with newline-less line tokenization (what the legacy engine yields).
        const scanLine = line + '\n';
        for (const token of lineTokens.tokens) {
            let end = token.endIndex;
            let content = scanLine.substring(token.startIndex, end);
            if (end > line.length) {
                end -= 1;
                content = content.slice(0, -1);
            }
            emit({
                type: 'token',
                line: i,
                start: token.startIndex,
                end,
                scopes: token.scopes,
                content,
            });
        }
    }
    emit({ type: 'state', scopes: stateScopeNames(ruleStack) });
}

main().catch((error) => {
    process.stderr.write(`${error && error.stack ? error.stack : String(error)}\n`);
    process.exit(1);
});
