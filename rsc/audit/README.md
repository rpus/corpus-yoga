# audit

The weekly five-lens audit of rpus/claude-export-yoga - a scheduled Claude Code
routine that clones the repo read-only, re-verifies the five audit rosters
(prose-rules, effects-census, gate-honesty, sibling-shape, referential-integrity,
parents first minted 2026-08-02 as #159-#163), sweeps for new findings, and files
everything as sub-issues plus a delta-report issue, using room name weekend-audit.

`prompt.md` in this directory is the committed source of its instructions.

## The trigger

Live config as at 2026-08-04: id `trig_01EzGa2CHkPyZDBJ92EqporR`, name "weekend
five-lens audit", created 2026-08-02 via the HTTP API, cron `0 7 * * 6` (Saturdays
07:00 UTC; the server schedules the actual firing a few minutes after, e.g.
next_run 07:08), enabled.

Session config: model `claude-fable-5`, environment
`env_01DtGPqKug8oAgdUXePhzkJm`, tools Bash/Read/Write/Edit/Glob/Grep, source a
fresh clone of `github.com/rpus/claude-export-yoga`, GitHub remote MCP connector
(`api.githubcopilot.com/mcp`) for all issue reads and writes, `persist_session`
false.

## Watching it

The routines dashboard is <https://claude.ai/code/routines> - API-created
triggers appear there like web-created ones; the routine's detail page shows the
config, the cron trigger with next run time, and the run history, where each
firing opens as a full Claude Code session with its transcript.

A green status in the run list means the session STARTED without infrastructure
error, not that the audit succeeded - open the run, and read the delta-report
issue (label `audit-delta`), which is the durable account: the prompt files it
first and edits it as it goes precisely so a cut-short run leaves a partial
report instead of silence.

## Drift and amendment

The trigger carries a copy of `prompt.md` prefixed with one line,

    Provenance: rsc/audit/prompt.md @ <sha> - amend via PR to that file

Drift is checked by fetching the trigger's message, stripping that prefix, and
diffing against `prompt.md` at the named sha.

Amending the audit means a PR to `prompt.md`; after merge, the coordinator
updates the trigger's message to the provenance line plus the merged file's
bytes via the trigger API. Issue #265 states this contract.

## History

| date | event |
| --- | --- |
| 2026-08-02 | trigger created |
| 2026-08-02 10:58 UTC | maiden firing, cut short by usage limits - the budget-discipline section in the prompt is its lesson |
| 2026-08-02 | prompt amended via API: delta-stub-first and budget discipline |
| 2026-08-03 | prompt amended via API: one-act create-label-attach filing |
| 2026-08-03 | prompt amended via API: issue grammar adoption (issue #264) |
| PR #295 | prompt committed to the tree |
