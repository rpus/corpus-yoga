#!/usr/bin/env python
"""
compare_markdown.py — Diff two saved sets of markdown, per conversation, pairing by conversation id:
  --projection  the PROJECTION of the API capture (project_markdown's output under data/output/markdown)
  --dom         the DOM capture's own markdown (<id>/<title>.md under a captures dir)

A conversation has two CAPTURES — API and DOM. Neither is read here. What is compared is
markdown against markdown: the projection of the API capture against the DOM capture. No
JSON is opened by this file, so a difference it reports may belong to project_markdown's
RENDERING rather than to either capture — which is why the messages name the projection and
not the API capture, and why "refresh the capture" is not automatically the remedy.

The PRECEDENT this file now enacts (ruled 2026-07-31): severity attaches to the
RECORD, never to witness agreement. Of a conversation's two captures, one holds the
record role (claude: the API capture — the DOM capture retired into a witness) and the
other is a witness. A witness diverging from a complete record is DRIFT — stated,
remedied (reconcile or discharge the witness), never gating; only a loss to the RECORD
itself may fail a run, and that is the renderer's and validator's to catch, since the
projection derives from the record. The rule is role-indexed, not mechanism-indexed:
were the roles reversed (gemini's DOM capture IS its record), the same rule gates the
same drift hard. So this reports DRIFT and always exits 0; the atom-voice for these
findings is audit_captures' (atom and remedy in one voice), and stating them twice
would double the table's counts.

Gate on the aligned TURN SEQUENCE (role + content prefix), which is machine-robust; full
content always differs in intended ways (better titles, trimmed leading spaces, separated
run-on blocks, attachment rendering) — use --diff to eyeball content, not to gate.

Turns are aligned DOM-capture→projection with difflib. Per conversation:
  turn-exact               = same turn sequence; aligned pairs may differ in content rendering
  projection-more-complete = the projection has extra turns, within the DOM capture's
                             [no capture] placeholder budget (a placeholder licenses at most
                             one extra projected turn)
  DRIFT                    = the projection dropped turns present in the DOM capture, OR has
                             extra turns beyond the placeholder budget, OR aligned turns
                             disagree on role, OR the same turns appear in a different order

Usage:
  src/run_python_script.sh src/main/browser-captures/compare_markdown.py \
    --projection data/output/markdown/claude/chat/conversations \
    --dom data/input/claude/chat/browser-DOM [--diff]

Exit status is non-zero iff a regression is found (suitable for pipeline gating).
"""
import argparse
import difflib
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/main/ on the path
from markdown_projection import turn_seq, conv_id  # the format authority owns the parsers

KEY_PREFIX = 80   # chars of normalized content used as a turn's alignment identity


HEADING = re.compile(r'^## (Human|Claude|Gemini) \((\d+)\)', re.M)


def turn_labels(md):
    """The turn headings as the file itself writes them — 'Human (12)' — in turn_seq order.
    A locator beats an excerpt: it can be grepped, it is what the projection's anchors and
    the markdown server's deep links key on, and it does not go stale when a turn is edited.
    Empty if the headings carry no ordinal, in which case callers fall back to content."""
    return [f'{who} ({n})' for who, n in HEADING.findall(md)]


def _key(turn):
    role, body = turn
    return (role, body[:KEY_PREFIX])


def _is_placeholder(turn):
    return turn[1].startswith('[no capture')


def classify(s_seq, a_seq, s_labels=(), a_labels=()) -> tuple[str, Any, list]:
    """Align DOM-capture→projection turn sequences; return (kind, detail).
    kind: 'exact' | 'improved' | regression string. detail is kind-dependent:
    an int (content-diff pair count) for 'exact', a message otherwise.

    s_labels/a_labels are the two sides' turn headings (turn_labels). Given them, a
    regression cites WHERE — 'Human (2), Human (3)' — instead of quoting the first 60
    characters of each turn; without them it falls back to the excerpt.

    The third return value is the DEFICIENT TURNS as (label, body) — the evidence, handed
    to a caller that can check it. This file compares two markdowns and never opens a
    capture, so it cannot say whether a turn the projection lacks is missing from the API
    CAPTURE or merely rendered differently by project_markdown. audit_captures holds the
    API capture and can; nobody else should guess."""
    sm = difflib.SequenceMatcher(None, [_key(t) for t in s_seq], [_key(t) for t in a_seq],
                                 autojunk=False)
    # indices, not turns: the report cites each turn's heading, which is positional
    dropped = []   # DOM-capture turn indices with no projection alignment
    extra = []     # projection turn indices with no DOM-capture alignment
    pairs = []     # head-to-head aligned (dom, projection) turns from replace segments
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            continue
        if tag == 'replace':
            n = min(i2 - i1, j2 - j1)
            pairs.extend(zip(s_seq[i1:i1 + n], a_seq[j1:j1 + n]))
            dropped.extend(range(i1 + n, i2))
            extra.extend(range(j1 + n, j2))
        elif tag == 'delete':
            dropped.extend(range(i1, i2))
        elif tag == 'insert':
            extra.extend(range(j1, j2))

    # Reordering: the same content unmatched on BOTH sides (checked on the raw
    # unmatched turns, before head-to-head pairing — a same-role adjacent swap
    # must not be mistaken for a content rendering difference).
    s_unmatched_keys = {_key(t) for t in [s_seq[i] for i in dropped] + [s for s, _ in pairs]
                        if not _is_placeholder(t)}
    a_unmatched_keys = {_key(t) for t in [a_seq[j] for j in extra] + [a for _, a in pairs]}
    reordered = s_unmatched_keys & a_unmatched_keys

    role_mismatch = sum(1 for s, a in pairs if s[0] != a[0])
    paired_diff = len(pairs) - role_mismatch
    placeholders = sum(1 for t in s_seq if _is_placeholder(t))
    unpaired_placeholders = sum(1 for i in dropped if _is_placeholder(s_seq[i]))
    real_dropped = [i for i in dropped if not _is_placeholder(s_seq[i])]
    # An EMPTY projection-only turn is uncapturable by construction: it renders nothing and
    # carries no copy button, so no DOM capture can ever contain it. Not an extra.
    extra = [j for j in extra if a_seq[j][1].strip()]

    def where(idx, labels, seq):
        """Cite the turns by heading; fall back to their text where headings carry no
        ordinal (an older capture, or a format that never wrote one)."""
        if labels and all(i < len(labels) for i in idx[:3]):
            return ', '.join(labels[i] for i in idx[:3]) + ('  …' if len(idx) > 3 else '')
        return '; '.join(f'[{seq[i][0]}] {seq[i][1][:60]}' for i in idx[:3])

    # The DEFICIENT side leads, always in the same slot, so three WARNs can be read at a
    # glance instead of parsed: two sentences differing only in subject/object order do not
    # scan, and the direction is the whole point — a projection missing a turn the capture
    # holds is content outside the record, while a DOM capture missing one is a retired
    # mechanism lagging, which is a non-event.
    def turns(n):
        return f'{n} turn' if n == 1 else f'{n} turns'

    def evidence(idx, labels, seq):
        return [(labels[i] if labels and i < len(labels) else None, seq[i][1]) for i in idx]

    if reordered:
        return (f'turn order disagrees: {turns(len(reordered))} in a different position',
                '; '.join(f'[{r}] {b}' for r, b in sorted(reordered)[:3]), [])
    if role_mismatch:
        return f'speaker role disagrees on {turns(role_mismatch)}', None, []
    if real_dropped:
        return (f'projection missing {turns(len(real_dropped))}',
                where(real_dropped, s_labels, s_seq),
                evidence(real_dropped, s_labels, s_seq))
    if len(extra) > placeholders:
        # the placeholder budget is only worth naming when there IS one: "0 excusable"
        # is a clause that reports the absence of an exception nobody claimed
        budget = (f' ({placeholders} excusable as "[no capture" placeholder(s))'
                  if placeholders else '')
        return (f'DOM capture missing {turns(len(extra))}{budget}',
                where(extra, a_labels, a_seq), evidence(extra, a_labels, a_seq))
    if extra or unpaired_placeholders:
        return 'improved', None, []
    return 'exact', paired_diff, []


def _index(paths):
    """conversation id -> (markdown, filename stem). The stem is kept because the
    projection's filename is the humane identity — data/output/markdown names every
    conversation <NNN>-<title>.md — and a report keyed only by uuid cannot be looked up."""
    out = {}
    for f in paths:
        text = f.read_text()
        cid = conv_id(text)
        if cid:
            out[cid] = (text, f.stem)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--projection', required=True,
                    help='dir of projected <NNN>-<title>.md (project_markdown output)')
    ap.add_argument('--dom', required=True,
                    help='captures dir of <id>/<title>.md DOM captures')
    ap.add_argument('--diff', action='store_true', help='print full per-conversation unified diffs')
    args = ap.parse_args()

    projected = _index(Path(args.projection).glob('*.md'))
    dom = _index(Path(args.dom).glob('*/*.md'))

    exact = improved = content_diff_pairs = 0
    regressions = []
    paired = sorted(set(projected) & set(dom))
    for cid in paired:
        a, name = projected[cid]        # name: the corpus filename, <NNN>-<title>
        s, _ = dom[cid]
        kind, detail, _ = classify(turn_seq(s), turn_seq(a), turn_labels(s), turn_labels(a))
        if kind == 'exact':
            exact += 1
            content_diff_pairs += detail
        elif kind == 'improved':
            improved += 1
        else:
            regressions.append((f'{name} ({cid[:8]})', kind, detail))
        if args.diff:
            print(f"===== {name} ({cid[:8]}) =====")
            print('\n'.join(difflib.unified_diff(s.splitlines(), a.splitlines(),
                                                 'dom-capture', 'projection', lineterm='')))

    api_only = sorted(set(projected) - set(dom))
    dom_only = sorted(set(dom) - set(projected))
    print(f"compared {len(paired)}: {exact} turn-exact, {improved} projection-more-complete "
          f"(filled DOM-capture gaps), {len(regressions)} drift(s)")
    if content_diff_pairs:
        print(f"  {content_diff_pairs} aligned pair(s) differ in content rendering only (use --diff to eyeball)")
    if api_only:
        print(f"  {len(api_only)} projected md(s) with no DOM capture (not compared)", file=sys.stderr)
    if dom_only:
        print(f"  {len(dom_only)} DOM capture(s) with no projection (not compared)", file=sys.stderr)
    for name, kind, detail in regressions:
        print(f"  DRIFT {name}: {kind}" + (f" — {detail}" if detail else ''), file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
