#!/usr/bin/env python
"""
compare_markdown.py — Diff two saved sets of markdown, per conversation, pairing by filename:
  --api     the api-sourced markdown (project_markdown's output, rendered from apiConversation JSON)
  --scrape  the legacy DOM-scrape markdown (<id>/<title>.md under a captures dir)

Pure markdown-vs-markdown: it reads the two directories and compares the files. It does NOT
project anything itself (project_markdown already wrote the api side). While both sets exist,
this certifies that the projection and the scrape agree — each is the other's independent check.

Gate on the aligned TURN SEQUENCE (role + content prefix), which is machine-robust; full
content always differs in intended ways (better titles, trimmed leading spaces, separated
run-on blocks, attachment rendering) — use --diff to eyeball content, not to gate.

Turns are aligned scrape→api with difflib. Per conversation:
  turn-exact        = same turn sequence; aligned pairs may differ in content rendering
  api-more-complete = api has extra turns, within the scrape's [no capture] placeholder
                      budget (a placeholder licenses at most one extra api turn)
  REGRESSION        = api dropped turns present in the scrape, OR api has extra turns beyond
                      the placeholder budget, OR aligned turns disagree on role, OR the same
                      turns appear in a different order

Usage:
  src/run_python_script.sh src/main/browser-captures/compare_markdown.py \
    --api gen/markdown/claude --scrape ext/browser-captures/claude [--diff]

Exit status is non-zero iff a regression is found (suitable for pipeline gating).
"""
import argparse
import difflib
import re
import sys
from pathlib import Path

KEY_PREFIX = 80   # chars of normalized content used as a turn's alignment identity


def turn_seq(md):
    """Ordered [(role, normalized_body)] — role 'H' (Human) or 'A' (Claude/Gemini).
    The trailing --- turn divider is not part of the turn's content: an empty turn
    must normalize to '' (the empty-turn exemption in classify depends on it)."""
    parts = re.split(r'^## (Human|Claude|Gemini) [^\n]*\n', md, flags=re.M)
    seq = []
    for i in range(1, len(parts) - 1, 2):
        role = 'H' if parts[i] == 'Human' else 'A'
        body = re.sub(r'\s+', ' ', parts[i + 1]).strip()
        body = re.sub(r'\s*---$', '', body)
        seq.append((role, body))
    return seq


def _key(turn):
    role, body = turn
    return (role, body[:KEY_PREFIX])


def _is_placeholder(turn):
    return turn[1].startswith('[no capture')


def classify(s_seq, a_seq):
    """Align scrape→api turn sequences; return (kind, detail).
    kind: 'exact' | 'improved' | regression string."""
    sm = difflib.SequenceMatcher(None, [_key(t) for t in s_seq], [_key(t) for t in a_seq],
                                 autojunk=False)
    dropped = []   # scrape turns with no api alignment
    extra = []     # api turns with no scrape alignment
    pairs = []     # head-to-head aligned (scrape, api) turns from replace segments
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            continue
        if tag == 'replace':
            n = min(i2 - i1, j2 - j1)
            pairs.extend(zip(s_seq[i1:i1 + n], a_seq[j1:j1 + n]))
            dropped.extend(s_seq[i1 + n:i2])
            extra.extend(a_seq[j1 + n:j2])
        elif tag == 'delete':
            dropped.extend(s_seq[i1:i2])
        elif tag == 'insert':
            extra.extend(a_seq[j1:j2])

    # Reordering: the same content unmatched on BOTH sides (checked on the raw
    # unmatched turns, before head-to-head pairing — a same-role adjacent swap
    # must not be mistaken for a content rendering difference).
    s_unmatched_keys = {_key(t) for t in dropped + [s for s, _ in pairs] if not _is_placeholder(t)}
    a_unmatched_keys = {_key(t) for t in extra + [a for _, a in pairs]}
    reordered = s_unmatched_keys & a_unmatched_keys

    role_mismatch = sum(1 for s, a in pairs if s[0] != a[0])
    paired_diff = len(pairs) - role_mismatch
    placeholders = sum(1 for t in s_seq if _is_placeholder(t))
    unpaired_placeholders = sum(1 for t in dropped if _is_placeholder(t))
    real_dropped = [t for t in dropped if not _is_placeholder(t)]
    # An EMPTY api-only turn is uncapturable by construction: it renders nothing and
    # carries no copy button, so no scrape can ever contain it. Not an extra.
    extra = [t for t in extra if t[1].strip()]

    if reordered:
        return (f'{len(reordered)} turn(s) out of order',
                '; '.join(f'[{r}] {b}' for r, b in sorted(reordered)[:3]))
    if role_mismatch:
        return f'{role_mismatch} aligned turn(s) disagree on role', None
    if real_dropped:
        return (f'api dropped {len(real_dropped)} turn(s)',
                '; '.join(f'[{t[0]}] {t[1][:60]}' for t in real_dropped[:3]))
    if len(extra) > placeholders:
        return (f'{len(extra)} extra api turn(s) beyond {placeholders} placeholder(s)',
                '; '.join(f'[{t[0]}] {t[1][:60]}' for t in extra[:3]))
    if extra or unpaired_placeholders:
        return 'improved', None
    return 'exact', paired_diff


def conv_id(md):
    """The conversation id, from the <url> line both renderers emit (last path segment).
    Robust pairing key -- the two sides slugify different titles, so filenames can diverge."""
    m = re.search(r'<(https?://[^>]+)>', md)
    if not m:
        return None
    return m.group(1).split('?')[0].split('#')[0].rstrip('/').rsplit('/', 1)[-1]


def _index(paths):
    out = {}
    for f in paths:
        text = f.read_text()
        cid = conv_id(text)
        if cid:
            out[cid] = text
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--api', required=True,
                    help='dir of api-sourced <title>.md (project_markdown output)')
    ap.add_argument('--scrape', required=True,
                    help='captures dir of <id>/<title>.md DOM scrapes')
    ap.add_argument('--diff', action='store_true', help='print full per-conversation unified diffs')
    args = ap.parse_args()

    api_md = _index(Path(args.api).glob('*.md'))
    scrape_md = _index(Path(args.scrape).glob('*/*.md'))

    exact = improved = content_diff_pairs = 0
    regressions = []
    paired = sorted(set(api_md) & set(scrape_md))
    for name in paired:
        a = api_md[name]
        s = scrape_md[name]
        kind, detail = classify(turn_seq(s), turn_seq(a))
        if kind == 'exact':
            exact += 1
            content_diff_pairs += detail
        elif kind == 'improved':
            improved += 1
        else:
            regressions.append((name, kind, detail))
        if args.diff:
            print(f"===== {name} =====")
            print('\n'.join(difflib.unified_diff(s.splitlines(), a.splitlines(),
                                                 'scraped', 'api', lineterm='')))

    api_only = sorted(set(api_md) - set(scrape_md))
    scrape_only = sorted(set(scrape_md) - set(api_md))
    print(f"compared {len(paired)}: {exact} turn-exact, {improved} api-more-complete "
          f"(filled scrape gaps), {len(regressions)} regression(s)")
    if content_diff_pairs:
        print(f"  {content_diff_pairs} aligned pair(s) differ in content rendering only (use --diff to eyeball)")
    if api_only:
        print(f"  {len(api_only)} api md(s) with no scrape counterpart (not compared)", file=sys.stderr)
    if scrape_only:
        print(f"  {len(scrape_only)} scrape md(s) with no api counterpart (not compared)", file=sys.stderr)
    for name, kind, detail in regressions:
        print(f"  REGRESSION {name}: {kind}" + (f" — {detail}" if detail else ''), file=sys.stderr)
    return 1 if regressions else 0


if __name__ == '__main__':
    sys.exit(main())
