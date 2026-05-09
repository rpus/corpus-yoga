# How the `.claude` Investigation Was Conducted

This document explains the actual mechanics of the previous session: what commands I ran,
in what order, and how I derived the explanations from the raw output.

---

## Phase 1: Orient with structure before content

The first move was two parallel `find` calls:

```bash
find ~/.claude -type f | sort   # every file
find ~/.claude -type d | sort   # every directory
```

Running both in parallel (a single message with two tool calls) gave the full skeleton at
once without waiting for one to complete before seeing the other.

**Why `find` first, not reading individual files?** With an unknown directory, reading files
before knowing the shape wastes effort — you might read the wrong things. The directory tree
tells you which files are worth reading in depth. This is the same approach you'd use
exploring an unfamiliar repo: `ls -R` or `tree` before `cat`.

**Why `| sort`?** `find` output is filesystem-order (inode order), which groups nothing
meaningfully. Sorting puts all files in the same directory together, making the structure
readable as a tree in plain text.

The file listing came back at 188KB — too large to hold in context. Claude Code's tool
machinery automatically spilled it to `tool-results/` and gave me a truncated preview.
I could still see the first 2KB, which covered the `backups/`, `cache/`, and `file-history/`
directories — enough to understand the naming conventions there before reading further.

---

## Phase 2: Read representative samples, not everything

Rather than reading every file (impossible at this scale), I picked one example from each
directory type that would tell me the most:

| What I read | Why that file |
|---|---|
| A `backups/` file | Oldest backup = the base config; shows all top-level keys |
| `~/.claude/cache/changelog.md` | Short, self-explanatory, reveals the cache's purpose |
| A `file-history/` entry | Small text file; naming convention needed confirmation |
| `ide/` contents | Two files only; read both immediately |
| A `paste-cache/` entry | Content reveals the reference-tracking scheme |
| A `shell-snapshots/` file | First 30 lines confirm it's a shell dump |
| A `plugins/` command file | Longest read; `code-review.md` is the richest example |
| `plugin.json` | Confirms plugin metadata structure |

The key heuristic: **read the file most likely to be self-describing**. A `changelog.md`
will explain itself. A `plugin.json` will have `name` and `description`. A backup of the
main config will have all top-level keys. Don't start with opaque binary-looking files.

**For the `backups/` file**, rather than reading the whole 50-line JSON I immediately ran a
Python one-liner to extract just the key names:

```bash
python3 -c "import json,sys; d=json.load(sys.stdin); print(list(d.keys()))"
```

This gave me all 31 config keys in one line without wading through hundreds of lines of
cached values. The keys are the map; the values are details I could look up selectively.

---

## Phase 3: Resolve naming conventions by reading, not guessing

Several naming conventions were opaque:
- Why do `file-history` filenames look like `097160b5d80550e6@v2`?
- What is `tengu_*`?
- Why do project directories start with `-Users-...`?

For **`file-history` filenames**: reading the actual file content (it contained the
`conversations schema changelog`) told me the session UUID directory corresponded to a
specific Claude Code session. The `@v{n}` suffix was readable as a version number. The
hex prefix was clearly a hash — of what? The most obvious candidate for a stable file
identifier is the file path itself. Combined with knowing Claude Code tracks file edits
for undo, the full picture fell into place.

For **`tengu_*`**: the backup file contained a large `cachedGrowthBookFeatures` key with
a `tengu_flint_harbor_prompt` entry containing a full prompt template for an "onboarding
guide" feature. GrowthBook is a common open-source feature flagging system; "tengu" is
clearly a namespace prefix (the specific word is an Anthropic internal choice). The values
being booleans or objects confirmed these are feature flags, not config settings.

For **project directory naming**: the directory `~-dev-Anthropic-claude-export-yoga`
maps exactly to the current working directory `~/dev/Anthropic/claude-export-yoga`
with `/` replaced by `-`. This is a simple and common approach to turning filesystem paths
into flat directory names without escaping.

---

## Phase 4: Confirm empty directories are intentionally empty

Several plugin directories (`clangd-lsp`, `gopls-lsp`, etc.) had no commands, skills, or
agents. Rather than skipping them, I listed one:

```bash
ls ~/.claude/plugins/marketplaces/claude-plugins-official/plugins/clangd-lsp/
# → LICENSE  README.md
```

Just a `LICENSE` and `README.md`. This is a meaningful signal: these are stub entries —
the plugin exists in the marketplace registry but its behavior is built into the binary.
The directory presence is required for the marketplace to know they're installed, but they
carry no executable content.

---

## How the explanations were generated

The written explanations are not retrieved from documentation — there is no official
`~/.claude/` reference document. They were inferred by combining:

1. **File content** — what the files actually contain tells you what they're for
2. **Naming patterns** — consistent patterns (UUIDs, hashes, timestamps) are recognizable
   from general software engineering conventions
3. **Cross-referencing** — e.g., the same UUID appearing in `projects/`, `session-env/`,
   and `file-history/` proves these are all session-scoped
4. **Feature knowledge** — knowing Claude Code features (undo with double-Esc, IDE
   extension, paste handling, plugin system) and then matching each feature to the data
   structures that would need to support it

The explanation was written bottom-up: figure out what each file contains first, then
name the concept. Not the other way around (don't name it and then fit data to the name).

---

## What was left uncertain

A few things remained ambiguous after the investigation:

- **`session-env/` subdirectories were empty** — the directory exists and is named with
  session UUIDs, suggesting it's meant to store per-session env state, but it contained
  nothing. This could be a not-yet-activated feature or content that gets cleaned up
  after sessions end.

- **`sessions/` was empty** — transcripts may be stored in a different location,
  may be pruned aggressively, or may be stored on the server rather than locally.

- **The exact hash function** for `file-history` filenames was not confirmed — the output
  is consistent with xxHash or a truncated SHA but was not verified by running the hash
  function against a known path.

- **`paste-cache` tuple format** — the tuples `[4, "chat_messages", 8, "files", 0]` look
  like JSON pointer coordinates (version, key, index, key, index) but the exact schema
  was not verified against source code.

These gaps are noted rather than papered over with confident-sounding guesses.

---

## Tool execution pattern

Throughout the investigation, independent queries ran in parallel (single message, multiple
tool calls) and dependent queries ran sequentially. For example:

- `find -type f` and `find -type d` ran in parallel — neither depends on the other
- Reading `ide/` contents and reading `paste-cache/` ran in parallel — independent
- Listing `plugins/code-review/commands/` before reading `code-review.md` ran sequentially —
  I needed to know the filename before reading it

This keeps wall-clock time low: the investigation finished in roughly 4 round-trips rather
than 15+ sequential ones.
