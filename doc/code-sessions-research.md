# Code Sessions: Research Workflow

This document records the archaeological process used to discover and understand the
Claude Code CLI session format — the `.jsonl` files in `~/.claude/projects/`. It also
covers the `../code-sessions/` directory setup.

---

## Why this was needed

`~/.claude/` is an opaque directory with machine-generated naming conventions (UUID
subdirectories, hex-hashed filenames, millisecond timestamps). The `.jsonl` session
transcripts are not documented anywhere. The goal was to understand the format well
enough to write a JSON Schema for it and map it to the MCP protocol — completing a
three-way join between the MCP protocol, the claude.ai export format, and the Claude
Code CLI session format.

---

## Phase 1: Discovering the files exist

Initial exploration of `~/.claude/` (see `doc/investigation-methodology.md`) revealed
`~/.claude/projects/` contains per-project subdirectories. Each subdirectory contains:

- `{session-uuid}.jsonl` — the session transcript
- `{session-uuid}/tool-results/` — large tool outputs spilled from context
- `{session-uuid}/subagents/` — subagent state

The naming convention for project directories: the absolute working directory path with
`/` replaced by `-`. For this repo:
`~/.claude/projects/$(pwd | sed 's|/|-|g')/` (the absolute path with `/` replaced by `-`)

---

## Phase 2: Reading the format

The first few lines of a `.jsonl` file revealed the basic structure:

```json
{"type":"queue-operation","operation":"enqueue","timestamp":"...","sessionId":"..."}
{"parentUuid":null,"isSidechain":false,"promptId":"...","type":"user","message":{...}}
```

From this: two apparent record types (queue-operation and conversation turns), each JSON
object on its own line.

---

## Phase 3: Systematic survey across both available sessions

The decisive step was running a Python survey script against both `.jsonl` files for this
project simultaneously. The second session (7,248 records) was much larger than the first
(406 records) and revealed four record types absent from session 1:

```bash
python3 - <<'EOF'
import json, collections
from pathlib import Path
files = [Path("~/.claude/projects/.../a40a0813....jsonl"),
         Path("~/.claude/projects/.../60c07575....jsonl")]
all_records = [json.loads(l) for f in files for l in f.read_text().splitlines() if l.strip()]
by_type = collections.defaultdict(list)
for r in all_records:
    by_type[r.get('type')].append(r)
for rtype, recs in sorted(by_type.items(), key=lambda x: -len(x[1])):
    keys = sorted(set(k for r in recs for k in r))
    print(f"{rtype} (n={len(recs)}): {keys}")
EOF
```

This produced the full inventory: 9 record types, not 2. It also revealed that turn
records carry many more fields than initially visible (`cwd`, `gitBranch`, `slug`,
`entrypoint`, `version`, `userType`, `requestId`, `apiErrorStatus`, `sourceToolAssistantUUID`,
etc.).

**Key lesson:** always survey the full corpus before writing a schema. A single sample
record, or a small session, will miss record types that only appear occasionally
(e.g. `permission-mode`, `system`).

---

## Phase 4: Sampling novel record types

A second survey script sampled one record of each novel type to see its full field set:

```python
for rtype in ('system', 'file-history-snapshot', 'attachment', 'permission-mode'):
    ex = next(r for r in all_records if r.get('type') == rtype)
    print(rtype, sorted(ex.keys()))
```

Key findings:

- **`system`** has `subtype: "turn_duration"`, `durationMs`, `messageCount` — a performance
  metric record written at the end of each turn.
- **`file-history-snapshot`** with `isSnapshotUpdate: false` has no `snapshot` key; with
  `true` it has `snapshot: {messageId, timestamp, trackedFileBackups}`. This directly
  links the JSONL to `~/.claude/file-history/`.
- **`attachment.attachment`** is a Python `repr()` string, not JSON — an anomaly noted
  as an open question.
- **`queue-operation`** has four `operation` values: `enqueue`, `dequeue`, `popAll`,
  `remove` (session 1 only showed `enqueue`/`dequeue`).

---

## Phase 5: Content block survey

A targeted survey extracted all content block types and tool names:

```python
block_types = collections.Counter()
tool_names = collections.Counter()
for r in all_records:
    for block in r.get('message', {}).get('content', []):
        block_types[block.get('type')] += 1
        if block.get('type') == 'tool_use':
            tool_names[block.get('name')] += 1
```

Result: `text`, `tool_use`, `tool_result`, `thinking` — four types. Tool names: `Bash`,
`Read`, `Edit`, `Write`, `Agent` (built-ins). The `tool_use` blocks have a `caller` field
not present in the claude.ai export format.

---

## Schema design decisions

**Parse-then-validate as array.** JSONL cannot be validated directly by JSON Schema.
The approach: parse each line, wrap results in a JSON array, validate against a schema
with `"type": "array"`. This mirrors the existing `conversations.json` schema exactly
(which is also an array at root). The only difference is a pre-processing step.

**`TurnBase` for shared envelope.** Four record types (`user`, `assistant`, `attachment`,
`system`) share a large set of envelope fields. These are factored into a `TurnBase`
definition using the same wrapper/base/subtype pattern from the conversations schema
`principles.md`.

**Closed `additionalProperties` on simple records.** Records with a fully-surveyed fixed
field set (`QueueOperation`, `PermissionModeRecord`, `LastPromptRecord`, `FileHistorySnapshot`,
`AiTitleRecord`, `TextBlock`, `ToolUseBlock`, `ToolResultBlock`, `ThinkingBlock`) use
`additionalProperties: false`. The `TurnBase` and message subtypes do not, because the
turn envelope has optional fields that vary by version.

**Open questions explicitly documented.** Fields and enums that are not fully understood
(`attachment.attachment`, `Entrypoint` enum completeness, `userType` values) are noted
in `CHANGELOG.md` and inline in the schema descriptions.

---

## Setting up `../code-sessions/`

Because `~/.claude/` uses opaque machine-generated directory names, direct access to
session files requires knowing the full path. The `../code-sessions/` sibling directory
provides stable, human-readable access via symlinks:

```bash
mkdir -p ../code-sessions
# General form:
ln -sfn ~/.claude/projects/-Users-{user}-{path...} ../code-sessions/my-project-name

# For this repo:
ln -sfn "$HOME/.claude/projects/$(pwd | sed 's|/|-|g')" \
        ../code-sessions/claude-export-yoga
```

Git tracks symlinks natively. The `../code-sessions/` directory itself is outside the
repo (a peer to `../data-exports/`), but the workspace file references it and the
`RUNME-code-sessions.sh` script reads from it.

To find the correct `~/.claude/projects/` subdirectory for any repo, apply the path
transformation: replace every `/` in the absolute path with `-`. The result (without a
leading slash) is the subdirectory name.

```bash
# Find the ~/.claude/projects/ name for the current repo:
echo "$(pwd)" | sed 's|/|-|g'
# → the encoded path, e.g. -Users-alice-dev-Anthropic-claude-export-yoga
```
