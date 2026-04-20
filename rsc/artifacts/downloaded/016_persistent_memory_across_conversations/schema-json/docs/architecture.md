# schema+json — architecture

## overview

A VS Code extension and LSP server providing language support for JSON Schema Draft 4,
grounded in the restriction algebra.

## components

```
schema-json/          (VS Code extension — client)
  src/extension.ts    thin LSP client; launches server, registers language
  package.json        language registration, configuration schema, defaults

server/               (LSP server)
  src/server.ts       diagnostics, completions, hover (planned), formatter (planned)

shared/               (planned — single source of truth)
  src/keywords.ts     keyword sets derived from grammar
```

## language registration

Files with extension `.schema.json` are assigned the language ID `schema+json`,
distinct from VS Code's built-in `json` language. This prevents interference with
Microsoft's JSON mode while inheriting JSON syntax colouring via grammar delegation.

## LSP communication

The extension launches the server as a Node.js child process communicating over IPC.
Diagnostics are pushed from server to client via `textDocument/publishDiagnostics`.
Completions are served by the server in response to `textDocument/completion` requests.

## diagnostic model

Each diagnostic category has a configurable severity level (`error`, `warning`,
`information`, `hint`, `off`) settable in VS Code user or workspace settings:

| category | default | meaning |
|---|---|---|
| `postDraft4Intrusion` | error | keyword not in Draft 4 at all |
| `canonicalOrderViolation` | warning | restriction keywords out of canonical order |
| `annotationMixed` | information | annotation keyword outside annotation allOf |
| `structuralMixed` | information | structural keyword outside structural allOf |
| `unknownKeyword` | warning | keyword not in any known set |

## planned features

- completion provider with parse-tree-aware context (ANTLR4 grammar)
- hover provider (keyword set, canonical position, description)
- formatter (canonicaliser — emits structural, then restrictions, then annotations)
- `propertyOrder` keyword support
- `shouldPass`/`shouldFail` test runner against examples/
