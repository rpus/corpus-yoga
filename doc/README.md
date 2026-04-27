# doc/

Documentation for this repo, written during Claude Code sessions. Split into two groups:
**project docs** (about the work) and **tool-context docs** (about Claude Code itself,
the tool used to do the work).

---

## Project docs

### [`project-overview.md`](project-overview.md) — Architecture

**What it is:** End-to-end description of the repo: what it does, how the pipeline works
(validate → extract → infer → present), how artifact recovery works, what each schema
covers, and the output structure.

**When to use it:** Starting point for understanding the project. Read this before the
schema doc.

---

### [`code-sessions-schema.md`](code-sessions-schema.md) — CLI sessions schema reference

**What it is:** Reference for `rsc/schema/claude-code-sessions/` — the nine record types,
the turn envelope fields, content block types, MCP field mapping, and open questions.

**When to use it:** When working on the CLI sessions schema or comparing the CLI and
export formats field by field.

---

### [`code-sessions-research.md`](code-sessions-research.md) — Research workflow

**What it is:** Step-by-step account of how the CLI session format was reverse-engineered:
discovering the files, the survey scripts used, the key findings from each phase, schema
design decisions, and how to set up `../code-sessions/` for a new project.

**When to use it:** When adding a new project's sessions, extending the schema, or
following the same process for another undocumented directory.

---

### [`conversations-schema.md`](conversations-schema.md) — Conversations schema reference

**What it is:** Deep-dive on `rsc/schema/conversations/` — the versioned JSON Schemas,
the two-format distinction (Claude Code CLI `.jsonl` vs claude.ai export), the schema
development workflow, and the MCP field-level correspondence table.

**When to use it:** When working on the schema, incorporating a new export, or trying to
understand the format comparison.

---

## Tool-context docs

These document `~/.claude/` — the local state directory of Claude Code, the CLI tool used
to develop this repo. They are not about the project's subject matter (Claude.ai exports)
but about the environment in which the work was done.

### [`claude-home-directory.md`](claude-home-directory.md) — `~/.claude/` reference

**What it is:** Directory-by-directory breakdown of `~/.claude/` and `~/.claude.json`:
what each file and directory is for, naming conventions, and the design overview.

**Accuracy:** Reverse-engineered from file contents; no official docs exist at time of
writing. Uncertain points are flagged inline.

---

### [`investigation-methodology.md`](investigation-methodology.md) — Investigation how-to

**What it is:** Step-by-step account of how the `~/.claude/` reference was produced.
Reusable for investigating any unknown directory.

---

## How the tool-context docs were produced

1. User asked Claude to explain `~/.claude/`
2. Claude ran the investigation live, then wrote `claude-home-directory.md`
3. User asked Claude to document the methodology → `investigation-methodology.md`
4. Claude re-ran the investigation following its own methodology to validate the reference
   doc, found three corrections, and applied them
5. This README was added; project docs added in a later session once the full repo was surveyed
