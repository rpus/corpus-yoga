# `~/.claude/` Directory Reference

This document explains the structure and purpose of every directory and key naming convention
inside `~/.claude/`, the local state store for Claude Code.

## Design overview

Claude Code is stateless at the API level — the server holds no filesystem knowledge between
requests. All durable local state lives in `~/.claude/`, keyed by a session UUID that is
stable across `projects/`, `session-env/`, and `file-history/`. This lets Claude recover edits,
spill large tool outputs to disk, and accumulate memory across conversations, all without the
server knowing anything about your machine.

---

## Top-level layout

```text
~/.claude/
├── backups/
├── cache/
├── file-history/
├── ide/
├── paste-cache/
├── plugins/
├── projects/
├── session-env/
├── sessions/
└── shell-snapshots/
```

---

## `backups/`

Timestamped snapshots of the main config file at `~/.claude.json`.

**Filename format:** `.claude.json.backup.{millisecond-unix-timestamp}`

Claude Code backs up the config before writing it. The timestamps use milliseconds (not seconds),
which is why they look like 13-digit numbers (`1777016077942`).

---

## `cache/`

Network-fetched data stored locally to avoid re-fetching on every startup.

Currently contains `changelog.md` — the release notes shown in-app, cached so startup is fast
and works offline. The key `changelogLastFetched` in `~/.claude.json` tracks when this was
last refreshed from the network.

---

## `file-history/`

Per-session undo history for every file Claude has edited.

**Directory names** are UUID conversation session IDs (matching the IDs in `projects/` and
`session-env/`).

**File names** have two parts joined by `@`:

- Left: a content hash of the file's absolute path (e.g., `097160b5d80550e6`)
- Right: `v{n}` where n is the edit version number (e.g., `@v2`, `@v12`)

Each file contains the previous content of the edited file at that version. This is what
powers the double-Esc "restore last edit" feature.

---

## `ide/`

IDE extension handshake state. When the VSCode (or JetBrains) extension connects, it writes
a JSON file here containing:

```json
{
  "pid": 76221,
  "workspaceFolders": ["/path/to/project", "..."],
  "ideName": "Visual Studio Code",
  "transport": "ws",
  "runningInWindows": false,
  "authToken": "<uuid>"
}
```

**Filename format:** `{pid}.json` (keyed by the IDE process's PID)

A corresponding `{pid}.lock` file prevents duplicate connections from the same process.

---

## `paste-cache/`

When you paste a large blob into the prompt, Claude Code hashes its content and stores it
here rather than duplicating it throughout the conversation data structures.

**Filename format:** `{content-hash}.txt`

The file content is a list of JSON path tuples pointing to every location in the conversation
that references this paste, e.g.:

```text
[4, "chat_messages", 8, "files", 0]
[4, "chat_messages", 20, "files", 1]
```

This means: conversation version 4, in `chat_messages[8].files[0]`. The same content is not
duplicated — only referenced.

---

## `plugins/`

The official Claude Code plugin marketplace, mirrored locally at:

```text
plugins/marketplaces/claude-plugins-official/
├── plugins/           # first-party plugins
└── external_plugins/  # third-party integrations
```

### First-party plugins (selection)

| Plugin | What it provides |
| --- | --- |
| `code-review` | Multi-agent PR review with confidence scoring (`/review`) |
| `feature-dev` | Feature development workflow agents |
| `pr-review-toolkit` | PR review slash commands |
| `hookify` | Hook writing and management |
| `skill-creator` | Tool for creating new skills |
| `mcp-server-dev` | Skills for building MCP servers |
| `plugin-dev` | Plugin authoring tools |
| `security-guidance` | Security-aware hooks |
| `commit-commands` | Git commit slash commands |
| `session-report` | Session summary skill |

### Third-party integrations (selection)

`discord`, `telegram`, `asana`, `linear`, `github`, `gitlab`, `firebase`, `greptile`, `context7`, `terraform`, `playwright`

### Plugin structure

Each plugin directory follows this layout:

```text
{plugin-name}/
├── .claude-plugin/
│   └── plugin.json        # name, description, author
├── commands/              # slash commands (markdown files)
├── skills/                # skill definitions
├── agents/                # subagent definitions
├── hooks/                 # hook scripts
└── ...
```

### Slash command format

Commands are markdown files with YAML frontmatter. The frontmatter controls tool access and
invocation behavior; the body is the prompt Claude receives when the command is run.

```markdown
---
allowed-tools: Bash(gh pr view:*), Bash(gh pr diff:*)
description: Short description shown in the / menu
disable-model-invocation: false
---

The prompt text goes here. Claude receives this as its instructions when the
slash command is invoked.
```

Key frontmatter fields:

| Field | Purpose |
| --- | --- |
| `allowed-tools` | Allowlist of tools this command can use, with optional argument glob patterns |
| `description` | One-line description shown in the slash-command picker |
| `disable-model-invocation` | If `true`, runs the command body as a shell script rather than a prompt |

### LSP plugins (stub directories)

Directories like `clangd-lsp`, `gopls-lsp`, `pyright-lsp`, `typescript-lsp`, `ruby-lsp`, etc.
contain only a `LICENSE` and `README.md`. Their actual behavior is compiled into the Claude
Code binary — these directories are placeholders for marketplace metadata only.

### Skill format (`SKILL.md`)

Some plugins define skills via a `SKILL.md` file rather than (or in addition to) the command
markdown format. The frontmatter fields are `name` and `description`; the body contains
step-by-step instructions for Claude. Skills may also bundle supporting scripts and templates
alongside the `SKILL.md`. Example (`session-report`):

```markdown
---
name: session-report
description: Generate an explorable HTML report of Claude Code session usage.
---

## Steps
1. Run the bundled analyzer: node <skill-dir>/analyze-sessions.mjs ...
```

Note: a small number of plugins (e.g. `session-report`) have no `.claude-plugin/plugin.json`
— they appear to predate that convention. Treat `.claude-plugin/` as typical but not
universal.

---

## `projects/`

Per-project conversation state. This is the main local storage for ongoing work.

**Directory naming:** the absolute path to the working directory, with `/` replaced by `-`.  
Example: `~/dev/Anthropic/claude-export-yoga` becomes
`~-dev-Anthropic-claude-export-yoga`.

Inside each project directory:

```text
{project-dir}/
├── {session-uuid}.jsonl   # conversation transcript (one JSON object per line)
├── {session-uuid}/
│   ├── tool-results/      # spilled tool outputs (see below)
│   └── subagents/         # subagent state
└── memory/                # persistent memory files (see below; created on first write)
```

### `{session-uuid}.jsonl` (conversation transcripts)

Each session's full conversation is stored as a JSON Lines file. One JSON object per line.
The first line(s) are queue-operation events (enqueue/dequeue with timestamp); subsequent
lines are conversation turns:

```json
{"type":"queue-operation","operation":"enqueue","timestamp":"...","sessionId":"..."}
{"parentUuid":null,"isSidechain":false,"promptId":"...","type":"user","message":{"role":"user","content":[]}}
```

This is why `sessions/` is empty — transcripts live here, not there.

**Important distinction:** this is the **Claude Code CLI session format**, not the same as
the `conversations.json` format produced by claude.ai's Settings > Export Data feature.
Both represent Claude conversations but differ in structure: the CLI format adds
`parentUuid`, `isSidechain`, `promptId`, and queue-operation framing; the claude.ai export
format uses `sender: human/assistant`, UUIDs at the conversation level, and a persistence
envelope (`display_content`, `integration_*`, etc.). See `doc/conversation-exports/conversations-schema.md` for
a full comparison.

### `tool-results/`

When a tool call produces output larger than the in-memory context threshold (roughly tens of
KB), Claude Code spills the raw output to a file here rather than holding it in memory. The
filename is a short random ID (e.g., `b7yoeheyn.txt`). The tool result visible in the
conversation contains a reference to this file path instead of the full content.

### `memory/`

Markdown files written by Claude to persist facts across conversations. Created on first
write — the directory does not pre-exist. Each file has YAML frontmatter (`name`,
`description`, `type`) and is indexed by a `MEMORY.md` file in the same directory.
Types: `user`, `feedback`, `project`, `reference`.

---

## `session-env/`

Per-session environment snapshots, one subdirectory per session UUID. Intended to capture
environment variable state at the start of a session. Currently empty in most setups — the
feature may not be fully activated.

---

## `sessions/`

Empty in practice. Conversation transcripts are stored as `.jsonl` files inside `projects/`
(see above), not here. Purpose of this directory is unknown — may be vestigial or reserved
for future use.

---

## `shell-snapshots/`

A complete dump of your shell state at session start: all zsh/bash functions, aliases,
completions, and environment variables. This lets Claude reproduce your exact shell environment
when running Bash tool calls, rather than starting from a bare login shell.

**Filename format:** `snapshot-{shell}-{millisecond-timestamp}-{random-id}.sh`

---

## `~/.claude.json` (the main config)

Not inside `~/.claude/` but paired with it. This is the primary configuration store.
Key fields:

| Key | What it is |
| --- | --- |
| `oauthAccount` | Your logged-in Anthropic account |
| `userID` | Stable user identifier |
| `projects` | Per-project settings (model overrides, permissions, etc.) |
| `tipsHistory` | Which onboarding tips have been shown |
| `numStartups` | Launch count |
| `cachedGrowthBookFeatures` | A/B test flags (see below) |
| `additionalModelOptionsCache` | Available models fetched from API |
| `additionalModelCostsCache` | Model pricing |
| `changelogLastFetched` | Timestamp of last changelog fetch |
| `lastReleaseNotesSeen` | Version of last-shown release notes |
| `hasCompletedOnboarding` | Onboarding flow complete flag |

### `tengu_*` keys (GrowthBook feature flags)

These are Anthropic's internal A/B experiment flags, fetched from GrowthBook and cached
locally. `tengu` is the internal prefix for all Claude Code experiments. The names are
deliberately opaque (`tengu_crimson_vector`, `tengu_sage_compass`) to prevent external
inference about what is being tested. Values can be booleans, objects, or strings — the
object form carries experiment configuration (prompts, thresholds, etc.).

---

## Key naming conventions summary

| Pattern | Meaning |
| --- | --- |
| `tengu_*` | GrowthBook A/B experiment flag |
| `097160b5d80550e6` | Content hash of a file path, used as a stable opaque ID |
| `@v2`, `@v12` | Edit version number (how many times Claude wrote this file in this session) |
| UUID directory name | Conversation session ID (stable across `projects/`, `session-env/`, `file-history/`) |
| `1777016077942` | Millisecond Unix timestamp |
| `{pid}.json` / `{pid}.lock` | IDE extension process ID |
| `~-foo` | Working directory path with `/` → `-` |
