# session schema changelog

The family describes the transcript an Antigravity session leaves, as
`corpus-yoga agent capture` stashes it under
data/input/gemini/code/machine-transport/<machine>/<project>/<session>/: the
plain transcript.jsonl and the untruncated transcript_full.jsonl, one family for
both. Each definition's description ends with its layer, drawn from `layer.csv`
beside the version file - the record's own layers, named as a first reading and
free to evolve with evidence, beside the MCP factoring's (#634).

---

## v1

Minted 2026-09-15 on home-room from the two sessions the shared store held that
day: home-room's 5bb62af7 (88 steps, written 2026-09-14, Antigravity 2.13.0) and
reading-room's a821b300 (2069 steps, 2026-09-09 to 2026-09-15), each in both
files. Every step carries five envelope fields; beyond them a user input carries
content, a planner response any of content, thinking and tool calls, and a
generic, system-message or checkpoint step its content. The plain transcript
names, per step, the fields the harness truncated (content on 172 steps,
tool_calls on 26, thinking on 5, all on reading-room's session bar 13); the full
transcript carries them whole and never has that entry. Reading-room's session
shows what home-room's does not: the SYSTEM source with its two step kinds, the
RUNNING status on steps captured live, and step indices that repeat where the
harness resumed the session, so the array order is the record's order. All four
files validate at v1.

The step database beside the transcripts is protobuf and is not described; the
model a step ran on sits inside it, undecoded (#633).
