# doc/

Documentation for this repo, written during Claude Code sessions. Split into three groups
by subject matter.

---

## [`project-overview.md`](project-overview.md) — Architecture

End-to-end description of the repo: pipeline stages, artifact recovery, schemas, output
structure, provenance. Read this first.

---

## [`chat-exports/`](chat-exports/)

Docs specific to the claude.ai export pipeline.

### [`chat-exports/conversations-schema.md`](chat-exports/conversations-schema.md) — Conversations schema reference

Deep-dive on `rsc/schema/conversations/`: versioned JSON Schemas, two-format distinction,
schema development workflow, MCP field-level correspondence table.

---

## [`code-projects/`](code-projects/)

Docs specific to the Claude Code CLI sessions pipeline.

### [`code-projects/sessions-schema.md`](code-projects/sessions-schema.md) — CLI sessions schema reference

Reference for `rsc/schema/sessions/`: nine record types, turn envelope fields,
content block types, MCP field mapping, open questions.

### [`code-projects/research.md`](code-projects/research.md) — Research workflow

How the CLI session format was reverse-engineered: discovery, survey scripts, schema design
decisions, and how to set up `../code-projects/`.

---

## [`tool-context/`](tool-context/)

These document `~/.claude/` — the local state of Claude Code itself, not the project's
subject matter.

### [`tool-context/claude-home-directory.md`](tool-context/claude-home-directory.md) — `~/.claude/` reference

Directory-by-directory breakdown of `~/.claude/` and `~/.claude.json`: what each file and
directory is for, naming conventions, design overview. Reverse-engineered; uncertain points
flagged inline.

### [`tool-context/investigation-methodology.md`](tool-context/investigation-methodology.md) — Investigation how-to

Step-by-step account of how the `~/.claude/` reference was produced. Reusable for
investigating any unknown directory.

---

## How the tool-context docs were produced

1. User asked Claude to explain `~/.claude/`
2. Claude ran the investigation live, then wrote `tool-context/claude-home-directory.md`
3. User asked Claude to document the methodology → `tool-context/investigation-methodology.md`
4. Claude re-ran the investigation following its own methodology to validate the reference
   doc, found three corrections, and applied them
5. This README was added; project docs added in a later session once the full repo was surveyed
