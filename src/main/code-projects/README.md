# code-projects

Pipeline for processing Claude Code CLI session transcripts: converts `.jsonl` files to JSON arrays and validates them against the session schema.

---

## Usage

```bash
src/main/code-projects/RUNME.sh --code-project  ext/code-projects/<project-slug>
src/main/code-projects/RUNME.sh --code-projects ext/code-projects
```

`ext/code-projects/` is a symlink to `~/.claude/projects/` — see `ABOUT.md` for setup.

---

## Stages

| # | Script | What it does | Output |
| --- | --- | --- | --- |
| 1 | `jsonl_to_json.sh` | Converts each `.jsonl` session to a JSON array. Also writes a `.title` file and creates a human-readable symlink named after the session title. | `gen/code-projects/<project>/<session>/session.json` |
| 2 | `validate.sh` | Validates `session.json` against all versions in `rsc/schema/code-projects/session/`. | `gen/code-projects/<project>/<session>/validation/session/` |

---

## Files

| File | What it does |
| --- | --- |
| `RUNME.sh` | Runs both stages for one project or all projects |
| `validate.sh` | Per-project validation; iterates sessions and schema versions |
| `jsonl_to_json.sh` / `jsonl_to_json.py` | JSONL → JSON array; writes `session.json` and `session.json.title` |
