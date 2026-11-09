#!/usr/bin/env python
"""
audit.py - "are the captures I have any good?", read from the captures alone. Whether the
account has moved on since is corpus-yoga browser's, against the account as last fetched
(src/main/cli/browser/account.py).

  claude — nothing to check offline: the API capture is the record (DOM retired,
  issues/418, issues/431), and validate.sh already gates each capture against the schema.
  gemini — no API capture exists, so heuristics: a DOM capture with exactly
  RENDER_CEILING human turns is flagged as likely truncated (the pre-walking window), and
  '[no capture' placeholders are counted informationally.

Usage:
  src/run_python_script.sh src/main/pipeline/chat-capture/audit.py

The captures are read under the tiers' data/input and the projections under their
data/output/markdown - the checkout's, or a rehearsal's scratch (src/main/tier.py).

Exit status is non-zero iff anything actionable is found.
"""
import sys
from dataclasses import dataclass
from pathlib import Path

SELF = 'src/main/pipeline/chat-capture/audit.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
sys.path.insert(0, str(REPO / 'src' / 'main'))  # src/main/ on the path
import tier  # noqa: E402 — the tiers, one home (issues/702)
import facts  # noqa: E402 - the one printer of a status's facts (issues/753)
import spell  # noqa: E402
sys.path.insert(0, str(REPO / 'src' / 'main' / 'cli' / 'browser'))  # the acquisition machinery --live reaches (issues/380)
sys.path.insert(0, str(REPO / 'src' / 'main' / 'pipeline' / 'chat-export'))  # library.py — the artifact library's owner (issues/421)
from markdown_projection import turn_seq, conv_id  # the format authority owns the parsers

# Gemini renders only the last N exchanges until scrolled; a DOM capture sitting exactly
# at the ceiling is overwhelmingly likely to be a truncated pre-walking one.
RENDER_CEILING = 10


@dataclass
class Claude:
    offline_check: str


@dataclass
class Gemini:
    """The offline findings on gemini's DOM captures: each a FAIL under the conversation it names."""
    checked: int = facts.named('DOM captures checked against their projections')
    corroboration: str = facts.phrase('none - no API capture exists, so nothing corroborates the record itself')
    placeholders: int | None = facts.named('with "[no capture" placeholder text', default=None)
    findings: dict[str, facts.Finding] | str = facts.phrase('nothing flagged')


@dataclass
class Audit:
    """The capture audit: each provider's offline standing."""
    claude: Claude | None = None
    gemini: Gemini | str | None = None


def audit_gemini(captures_dir: Path, projection_dir: Path | None = None) -> tuple[Gemini, list[str]]:
    """The offline findings on gemini's DOM captures (issues/753, issues/759), and the suspects' names."""
    # gemini has no API capture, so the DOM capture IS the record — but its projection
    # is numbered like every other conversation, so the WARN can still name it the way
    # the corpus does rather than by uuid alone.
    projected, projected_text = {}, {}
    for f in (projection_dir.glob('*.md') if projection_dir and projection_dir.is_dir() else []):
        text = f.read_text()
        cid = conv_id(text)
        if cid:
            projected[cid] = f.stem
            projected_text[cid] = text
    suspects = []
    findings: dict[str, facts.Finding] = {}
    placeholder_convs = 0
    for d in sorted(captures_dir.iterdir()):
        mds = sorted(d.glob('*.md')) if d.is_dir() else []
        if not mds:
            continue
        s = mds[0].read_text()
        humans = sum(1 for r, _ in turn_seq(s) if r == 'H')
        if humans == RENDER_CEILING:
            suspects.append((d.name, projected.get(conv_id(s) or d.name, mds[0].stem)))
        if '[no capture' in s:
            placeholder_convs += 1
    for cid, name in suspects:
        findings[f'{name} ({cid[:8]})'] = facts.Finding(
            facts.phrase('shows exactly {ceiling} human turns - the gemini page renders only the last {ceiling}, so earlier turns are likely missing from this DOM capture', ceiling=RENDER_CEILING),
            facts.Would(spell.line('browser', 'capture', provider='gemini', id=cid), {cid: 1}))
    # The capture against the rendering derived FROM it. gemini has no API, so nothing
    # else corroborates either one -- and `corpus-yoga pipeline run` rewrites the projection from
    # the capture every time, so a divergence means the two have already parted company.
    # The capture is a copy plus turn anchors, so they must agree turn for turn.
    if projected_text:
        for d in sorted(captures_dir.iterdir()):
            mds = sorted(d.glob('*.md')) if d.is_dir() else []
            if not mds:
                continue
            text = mds[0].read_text()
            cid = conv_id(text) or d.name
            if cid not in projected_text:
                findings[f'{mds[0].stem} ({cid[:8]})'] = facts.Finding(
                    facts.phrase('captured but not projected'), facts.Would(spell.line('pipeline', 'run'), {cid: 1}))
                suspects.append((cid, mds[0].stem))
                continue
            cap, proj = turn_seq(text), turn_seq(projected_text[cid])
            if len(cap) != len(proj):
                findings[f'{projected[cid]} ({cid[:8]})'] = facts.Finding(
                    facts.phrase('capture holds {captured} turns, its projection {projected} - the projection is derived from the capture, so they cannot legitimately differ',
                                   captured=len(cap), projected=len(proj)))
                suspects.append((cid, projected[cid]))
            elif any(a != b for a, b in zip(cap, proj)):
                first = next(i for i, (a, b) in enumerate(zip(cap, proj)) if a != b)
                findings[f'{projected[cid]} ({cid[:8]})'] = facts.Finding(
                    facts.phrase('capture and projection differ from turn {first} of {n} - the projection is derived from the capture, so they cannot legitimately differ',
                                   first=first + 1, n=len(cap)))
                suspects.append((cid, projected[cid]))
        unprojected = sorted(set(projected_text) -
                             {conv_id(sorted(d.glob('*.md'))[0].read_text()) or d.name
                              for d in captures_dir.iterdir()
                              if d.is_dir() and list(d.glob('*.md'))})
        for cid in unprojected:
            findings[f'{projected[cid]} ({cid[:8]})'] = facts.Finding(
                facts.phrase('projected but no capture remains - the rendering has outlived the record it was derived from'))
            suspects.append((cid, projected[cid]))

    checked = sum(1 for d in sorted(captures_dir.iterdir()) if d.is_dir() and list(d.glob('*.md')))
    return (Gemini(checked, placeholders=placeholder_convs or None, findings=findings or facts.phrase('nothing flagged')),
            [f'{n} ({c[:8]})' for c, n in suspects])


def main():
    # The one thing an unmigrated machine needs this face to say (issues/421): the
    # library's stated move — bare `corpus-yoga browser` is where a tester looks first.
    from library import migration_note
    migration_note()
    shape, found = audit(tier.DATA / 'input', tier.DATA / 'output' / 'markdown' / 'claude' / 'chat' / 'conversations')
    facts.say(shape)
    return 1 if found else 0


def audit(root: Path, api: Path, provider: str | None = None) -> tuple[Audit, bool]:
    """The audit as its shape, and whether anything actionable was found: the offline pass
    over the captures under root."""
    gemini_dom = root / 'gemini' / 'chat' / 'DOM-capture'
    suspects: list[str] = []
    out = Audit()

    # one restriction, applied wherever the audit is partitioned by provider — the
    # whole audit, so a provider named means the same thing throughout
    def want(name):
        return provider in (None, name)

    if want('claude'):
        # the absence is the report: with DOM retired there is no second render to
        # reconcile the record against, and schema validation already ran per capture
        out.claude = Claude(facts.phrase('none - the API capture is the record (DOM retired)'))

    if want('gemini') and gemini_dom.is_dir():
        # every provider's projection sits under the one corpus root, so gemini's is
        # named from it rather than guessed: api gives claude's, three levels down
        corpus_root = api.parents[2]
        out.gemini, suspects = audit_gemini(gemini_dom, corpus_root / 'gemini' / 'chat' / 'conversations')
    elif want('gemini'):
        shown = gemini_dom.relative_to(REPO) if gemini_dom.is_relative_to(REPO) else gemini_dom
        out.gemini = facts.phrase('skipped - {path} absent', path=shown)

    return out, bool(suspects)


if __name__ == '__main__':
    sys.exit(main())
