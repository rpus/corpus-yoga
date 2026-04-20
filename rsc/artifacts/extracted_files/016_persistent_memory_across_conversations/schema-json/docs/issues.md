# issues log

## open

### ISS-001 — keyword duplication
**status:** in progress  
**context:** keyword sets and canonical order are declared independently in
`src/extension.ts`, `server/src/server.ts`, and `package.json` defaults.  
**fix:** `shared/src/keywords.ts` as single source of truth; both extension
and server to import from it. `package.json` defaults to be derived or
kept in sync manually until a build step generates them.

### ISS-002 — grammar incomplete
**status:** open  
**context:** `JSONSchema.g4` is missing several restriction keywords:
`maxItems`, `minProperties`, `maxProperties`, `minimum`, `maximum`,
`exclusiveMinimum`, `exclusiveMaximum`, `multipleOf`, `minLength`,
`maxLength`, `pattern`, `format`, `patternProperties`, `uniqueItems`,
`dependencies`. `type` only handles named types, not array-of-types.  
**fix:** extend grammar to cover all keywords in `RESTRICTION_KEYWORDS`.

### ISS-003 — grammar inlines JSON rules
**status:** open  
**context:** `JSONSchema.g4` inlines a copy of the JSON grammar rather than
importing it. `JSON.g4` exists as a separate file with cleaner factoring
(`j`-prefixed rules, fragment aliases).  
**fix:** add `import JSON;` to `JSONSchema.g4` and replace inlined rules
with references to `jSONValue`, `jSONObjectValue` etc.

### ISS-004 — grammar keyword classification mismatch
**status:** open  
**context:** `JSONSchema.g4` classifies `id` and `definitions` as
annotations. Per the restriction algebra, both are structural (identity
and reference machinery, paired with `$ref`). `title` and `description`
are missing from annotations entirely.  
**fix:** move `id` and `definitions` to a `structural` rule; add `title`
and `description` to `annotation`.

### ISS-005 — completion provider fires on value side
**status:** open (superseded by ISS-006)  
**context:** the client-side completion provider in `src/extension.ts`
fires everywhere — keys, values, inside strings. No parse-tree awareness.  
**fix:** superseded by LSP server completion with regex context guard
(ISS-006). Full fix requires ANTLR4 parse tree (ISS-007).

### ISS-006 — LSP completion regex context guard
**status:** open  
**context:** the server-side completion provider uses a regex
(`/[{,]\s*"[^"]*$/`) to detect key position. Better than nothing but
still not parse-tree-aware — will misfire in edge cases.  
**fix:** replace with ANTLR4 parse tree position lookup (ISS-007).

### ISS-007 — ANTLR4 grammar not yet integrated into LSP server
**status:** open  
**context:** the LSP server uses `JSON.parse` and regex for document
analysis. The ANTLR4 grammar exists but is not yet generating a TypeScript
parser or being used for diagnostics or completions.  
**fix:** install `antlr4ng` and `antlr4ng-cli`; generate TypeScript parser
from grammar; replace `JSON.parse` + regex with parse tree walking in
`server/src/server.ts`.

### ISS-008 — formatter not implemented
**status:** open  
**context:** VS Code reports no formatter for `schema+json`. The formatter
should be the canonicaliser: emit structural keywords first, then
restrictions in canonical order, then annotations.  
**fix:** implement `connection.onDocumentFormatting` in server; register
`documentFormattingProvider: true` in capabilities.

### ISS-009 — `package.json` defaults not derived from shared
**status:** open  
**context:** `schemaJson.restrictionOrder` default array in `package.json`
is a manual duplicate of `DEFAULT_RESTRICTION_ORDER` in
`shared/src/keywords.ts`. They can drift.  
**fix:** add a build step that generates the `package.json` defaults from
`shared/src/keywords.ts`, or accept manual sync with a lint check.

### ISS-010 — no test runner for shouldPass/shouldFail examples
**status:** open  
**context:** `examples/shouldPass/` and `examples/shouldFail/` exist but
there is no automated runner that validates each file and checks whether
diagnostics were produced as expected.  
**fix:** implement a test script that runs the server validation logic
against each example file and asserts zero diagnostics for `shouldPass`
and at least one diagnostic for `shouldFail`.

## closed

### ISS-C001 — TypeScript 6.0 / vscode-jsonrpc incompatibility
**status:** closed  
**context:** `npm init` in `server/` resolved `typescript` to 6.0, which
introduced `[Symbol.dispose]` on iterator types. `vscode-jsonrpc` (a
dependency of `vscode-languageserver`) uses `IterableIterator` which does
not satisfy the new `MapIterator` constraint.  
**fix:** pinned `typescript` to `5.3.3` in `server/package.json`.

### ISS-C002 — mocha types missing in root tsconfig
**status:** closed  
**context:** generated test scaffold `src/test/extension.test.ts` uses
`suite` and `test` globals without `@types/mocha` installed, causing
compile errors.  
**fix:** excluded `src/test` from root `tsconfig.json`.

### ISS-C003 — pull diagnostics advertised but not implemented
**status:** closed  
**context:** server capabilities declared `diagnosticProvider` (LSP 3.17
pull model) but only implemented push via `connection.sendDiagnostics`.
VS Code sent `textDocument/diagnostic` requests which returned
`-32601 Unhandled method`.  
**fix:** removed `diagnosticProvider` from capabilities; push model only.

### ISS-C004 — `grammars` nested inside `languages` in `package.json`
**status:** closed  
**context:** `grammars` contribution was placed inside the language object
rather than as a sibling of `languages` at the `contributes` level.
Syntax colouring did not activate.  
**fix:** moved `grammars` to correct level in `contributes`.

### ISS-C005 — `activationEvents` redundant
**status:** closed  
**context:** explicit `onLanguage:schema+json` activation event was
declared; VS Code 1.74+ infers this automatically from `contributes.languages`.  
**fix:** removed `activationEvents` array.

### ISS-C006 — server `rootDir` not excluded from root `tsconfig.json`
**status:** closed  
**context:** root `tsconfig.json` matched `server/src/server.ts` via
default `**/*` include pattern, causing `rootDir` violation error.  
**fix:** added `server` and `src/test` to `exclude` in root `tsconfig.json`.
