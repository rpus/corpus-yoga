"""unit.py - the dev gate's checks of the stage and the store: rehearsal records, units, states and atoms."""
import json
from pathlib import Path

from gate import (
    REPO_ROOT,
    SRC,
    check,
)


@check(tier='code', on=['src/main/rehearsal.py', 'src/main/rehearsal.schema.json', 'src/main/corpus.py', 'src/main/tier.py', 'src/main/browser', 'src/main/export', 'src/main/agent', 'rsc/reference/JSONSchema'], says=(
    'rehearsal.record_is_whole',
    'rehearsal.states_are_decidable',
))
def check_rehearsal_record(run) -> None:
    """The stage's rehearsal record is one file, whole, of what the last rehearsal saw and
    judged. Over a scratch fixture - two units the run began over, one validated
    green and one refused with its log, a third staged after it began - the record reduced
    from the extent and the scratch's verdicts validates against
    src/main/rehearsal.schema.json, holds each unit of the extent with its digests and the
    validator's output where it refused, holds nothing of the later unit, is read back as
    written, and is told apart from a directory or from what is not a record. From it a
    unit's standing is decidable: valid, invalid, changed since, unseen, seen without
    verdict, judged by no family, superseded where origin/main has moved past the version
    judged at, or unlicensed where the record's version is ahead of main's, each said with
    the stamp."""
    import tempfile
    try:
        import rehearsal
    except ImportError:
        run('rehearsal: the record is one file, whole, validating against its schema', False,
            'src/main/rehearsal.py does not exist: a rehearsal leaves stamped directories under tmp/stage/rehearsal '
            'and no record of what it saw', check='rehearsal.record_is_whole')
        run("rehearsal: a unit's standing to the record is decidable from it", False,
            'there is no record to decide from', check='rehearsal.states_are_decidable')
        return
    import corpus
    import jsonschema
    stamp, sha = '2026-10-08T000000Z', lambda c: c * 64
    schema_digest = sha('c')
    def unit(name: str, pipeline: str | None = 'browser') -> corpus.Unit:
        address = Path('claude/chat/API-capture') / name
        judges = next(s for s in corpus.stores() if s.pipeline == 'browser' and s.provider == 'claude').globs[0].families if pipeline else ()
        return corpus.Unit(address, [address], [], [], 'message-uuids', pipeline, 'claude' if pipeline else None, subject=(name,), families=judges)
    a, b, c, d, e = unit('a'), unit('b'), unit('c'), unit('d'), unit('e', None)
    digests = {'a': {sha('a')}, 'b': {sha('b')}, 'c': {sha('c')}, 'd': {sha('d')}}
    with tempfile.TemporaryDirectory() as scratch:
        root = Path(scratch)
        for name, valid in (('a', True), ('b', False)):
            log_dir = root / 'cache' / name / 'validation' / 'apiConversation'
            log_dir.mkdir(parents=True)
            (log_dir / 'v1.verdict.json').write_text(json.dumps({
                'datum': f'{name}.json', 'datum_sha256': sha(name), 'datum_bytes': 2, 'datum_lines': 1,
                'schema': 'v1.json', 'schema_sha256': schema_digest, 'version': 'v1',
                'verdict': 'valid' if valid else 'invalid', 'reason': 'Valid!' if valid else 'Validation error',
                'at': '2026-10-08T00:00:01+00:00'}))
            (log_dir / 'v1.log').write_text('2026-10-08T00:00:01+00:00\nValidation error: x is not of type string\n')
        seen = rehearsal.extent([a, b, d], lambda u: digests[u.address.name])
        record = rehearsal.reduce(stamp, 'abc1234', 0, 'a-room/claude/e2d2039d', 0, seen, [a, b, c, d],
                                  lambda u: root / 'cache' / u.address.name, corpus.family_of)
        faults = rehearsal.faults(record)
        meta = json.loads((REPO_ROOT / 'rsc' / 'reference' / 'JSONSchema' / 'draft-04' / 'schema.json').read_text())
        schema_faults = sorted(e.message for e in jsonschema.Draft4Validator(meta).iter_errors(json.loads(rehearsal.SCHEMA.read_text())))
        held = record.get('units', {})
        refused = held.get(b.address.as_posix(), {}).get('verdicts', {}).get('claude/apiConversation', {})
        path = root / 'rehearsal.json'
        rehearsal.write(record, path)
        back = rehearsal.read(path)
        (root / 'layout').mkdir()
        before = rehearsal.read(root / 'layout')
        (root / 'broken').write_text('{"stamp": "x"}')
        broken = rehearsal.read(root / 'broken')
        wants = [
            ('the schema is draft-04', not schema_faults, '; '.join(schema_faults)),
            ('the record validates', not faults, '; '.join(faults)),
            ('it holds the units the run began over and no other', sorted(held) == sorted(u.address.as_posix() for u in (a, b, d)), sorted(held)),
            ("each with its digests", held.get(a.address.as_posix(), {}).get('digests') == [sha('a')], held.get(a.address.as_posix())),
            ("a refused verdict carries the validator's output", 'Validation error: x is not of type string' in refused.get('output', ''), refused),
            ('a green verdict carries none', 'output' not in held.get(a.address.as_posix(), {}).get('verdicts', {}).get('claude/apiConversation', {'output': 1}), None),
            ('a unit the run wrote no verdict for holds none', held.get(d.address.as_posix(), {}).get('verdicts') == {}, held.get(d.address.as_posix())),
            ('it reads back as written', back == record, str(back)[:120]),
            ('a directory at its address is told apart', isinstance(before, str) and 'is a directory' in before, before),
            ('what is not a record is told apart', isinstance(broken, str) and 'is not a record' in broken, broken),
        ]
        failed = [(what, detail) for what, ok, detail in wants if not ok]
        run('rehearsal: the record is one file, whole, validating against its schema', not failed,
            None if not failed else '; '.join(f'{what}: {str(detail)[:160]}' for what, detail in failed[:3]),
            check='rehearsal.record_is_whole')
        main = lambda pipeline, family: (schema_digest, 'v1')   # noqa: E731
        judged = lambda pipeline, family, version, schema_sha256: schema_sha256   # noqa: E731
        got = [corpus.verdict(a, record, digests['a'], main, judged), corpus.verdict(b, record, digests['b'], main, judged),
               corpus.verdict(a, record, {sha('f')}, main, judged), corpus.verdict(c, record, digests['c'], main, judged),
               corpus.verdict(d, record, digests['d'], main, judged), corpus.verdict(e, record, set(), main, judged),
               corpus.verdict(a, record, digests['a'], lambda pipeline, family: (sha('d'), 'v2'), judged),   # origin/main has moved past the record
               corpus.verdict(a, record, digests['a'], lambda pipeline, family: (sha('d'), 'v0'), judged),   # the record is a branch's mint ahead of main
               corpus.verdict(a, record, digests['a'], lambda pipeline, family: (sha('e'), 'v1'),
                              lambda pipeline, family, version, schema_sha256: sha('e')),   # reworded or moved here, admitting what main's admits
               corpus.verdict(a, record, digests['a'], main, lambda pipeline, family, version, schema_sha256: None)]   # changed here since the rehearsal
    expected = [(corpus.Judgement.VALID, f'validates at claude/apiConversation v1 (origin/main; rehearsal {stamp})'),
                (corpus.Judgement.INVALID, 'invalid at claude/apiConversation v1 - Validation error - a version is owed'),
                (corpus.Judgement.CHANGED, f'changed since rehearsal {stamp}'),
                (corpus.Judgement.UNSEEN, f'unseen by rehearsal {stamp}'),
                (corpus.Judgement.UNJUDGED, f'seen by rehearsal {stamp}, no verdict written'),
                (corpus.Judgement.NONE, 'no pipeline selects it'),
                (corpus.Judgement.SUPERSEDED, 'judged at claude/apiConversation v1; origin/main holds v2'),
                (corpus.Judgement.UNLICENSED, 'valid at claude/apiConversation v1 - a version of this checkout, which origin/main does not hold (v0 there)'),
                (corpus.Judgement.VALID, f'validates at claude/apiConversation v1 (origin/main; rehearsal {stamp})'),
                (corpus.Judgement.UNJUDGED, 'the verdict at claude/apiConversation v1 is on a schema this checkout no longer holds - rehearse again')]
    wrong = [(g, e) for g, e in zip(got, expected) if g[0] is not e[0] or not g[1].startswith(e[1])]
    refusal = got[1][2]
    at = '/'.join(('browser', 'claude/apiConversation', 'v1.json'))   # the fixture's version file under rsc/schema, which no tree holds
    if not wrong and (refusal is None or (refusal.path, refusal.reason) != (at, 'Validation error')):
        wrong = [(got[1], (corpus.Judgement.INVALID, f'a refusal as data - family, version, reason - where it is {refusal}'))]
    states = [corpus.state(a, corpus.Relation.ABSENT, j) for j in (corpus.Judgement.UNSEEN, corpus.Judgement.CHANGED, corpus.Judgement.SUPERSEDED, corpus.Judgement.NONE)]
    counted = states == ['unjudged', 'unjudged', 'unjudged', 'promotable']
    run("rehearsal: a unit's standing to the record is decidable from it", not wrong and counted,
        None if not wrong and counted else
        f'{wrong[0][0][0].value}: {wrong[0][0][1][:100]!r}, where it is {wrong[0][1][0].value}: {wrong[0][1][1]!r}' if wrong
        else f'unseen, changed, superseded and no family count as {states}, where they are unjudged, unjudged, unjudged and promotable',
        check='rehearsal.states_are_decidable')


@check(tier='code', says=('stage.export_is_one_unit',), on=['src/main/corpus.py', 'src/main/browser', 'src/main/export', 'src/main/agent'])
def check_unit_companion(run) -> None:
    """The staged bulk export <X> is one unit, named by <X>, by the export declaration
    itself: its member is data-<X>/, which promotion copies, and its record is
    manifest-<X>.json, which stays in the stage. Either alone is the same unit, unpaired,
    naming what is absent. The fixture is synthetic - one export whole, one with its
    manifest alone, one with its payload alone."""
    import tempfile
    import corpus
    store = next(s for s in corpus.stores() if s.pipeline == 'export')
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        base = root / store.input
        for name in ('data-2026-01-01-whole', 'data-2026-03-03-payload'):
            (base / name).mkdir(parents=True)
            (base / name / 'conversations.json').write_text('[]')
        (base / 'manifest-2026-01-01-whole.json').write_text('{}')
        (base / 'manifest-2026-02-02-manifest.json').write_text('{}')
        got = sorted((unit.address.name, [m.name for m in unit.members],
                      [m.name for m in getattr(unit, 'record', [Path('?')])], list(unit.missing))
                     for unit in corpus.select(root, store))
        expected = [('2026-01-01-whole', ['data-2026-01-01-whole'], ['manifest-2026-01-01-whole.json'], []),
                    ('2026-02-02-manifest', [], ['manifest-2026-02-02-manifest.json'], ['data-2026-02-02-manifest/']),
                    ('2026-03-03-payload', ['data-2026-03-03-payload'], [], ['manifest-2026-03-03-payload.json'])]
        run('stage: a staged bulk export is one unit named by its star, its manifest the record that stays', got == expected,
            None if got == expected else f'selected {got}, where the units are {expected}',
            check='stage.export_is_one_unit')


@check(tier='code', on=['src/main/validation_audit.py', 'src/main/corpus.py', 'src/main/append_only.py'], says=(
    'audit.counts_what_pipelines_were_shown',
    'audit.input_changed_since_output',
    'stage.empty_selection_is_incomplete',
    'stage.recapture_names_a_full_id',
    'stage.states_are_told_apart',
))
def check_unit_state(run) -> None:
    """A staged unit is in one of seven states, and the stage's counts are of those states: promotable, held already, invalid - a family gave its verdict against it -
    would lose - its relation would cost the held copy something, which the promote, asked,
    refuses - unlicensed - valid at a version origin/main does not hold - incomplete, and
    unjudged, the state before any verdict, whose remedy is a rehearsal. No status line
    prescribes a removal: a unit that would lose is the reader's to reconcile, an incomplete
    one the janitor's; and no state of a status is refused, since a status asks for no act."""
    import corpus
    from append_only import Relation
    state = getattr(corpus, 'state', None)
    judgement = getattr(corpus, 'Judgement', None)
    if state is None or judgement is None:
        run('stage: a unit not yet judged is counted unjudged, never held back', False,
            'src/main/corpus.py derives no state: its counts hold back whatever is not promotable',
            check='stage.states_are_told_apart')
        return
    whole = corpus.Unit(Path('a/b'), [Path('a/b')], [], [], 'prefix', 'browser', 'claude')
    lacking = corpus.Unit(Path('a/c'), [Path('a/c')], [], [], 'whole', 'export', None, missing=['x.json'])
    got = [state(lacking, Relation.ABSENT, judgement.UNJUDGED), state(whole, Relation.ABSENT, judgement.UNJUDGED),
           state(whole, Relation.EXTENDS, judgement.UNLICENSED), state(whole, Relation.DIVERGED, judgement.NONE),
           state(whole, Relation.ABSENT, judgement.VALID)]
    expected = ['incomplete', 'unjudged', 'unlicensed', 'would lose', 'promotable']
    run('stage: a unit not yet judged is counted unjudged, never held back', got == expected,
        None if got == expected else f'the states read {got}, where they are {expected}',
        check='stage.states_are_told_apart')
    prescribed = [line.strip() for line in (SRC / 'main' / 'corpus.py').read_text().splitlines()
                  if '→ run: rm' in line]
    run('stage: no status line prescribes a removal', not prescribed,
        None if not prescribed else f'src/main/corpus.py prints {prescribed[0]}', check='stage.states_are_told_apart')
    # A directory a store's selection names with no file under it has no payload (issues/988): an
    # interrupted capture leaves exactly this, and it is the janitor's, never a rehearsal's
    # input - held over a planted root, since the room's stage may hold none.
    import tempfile
    store = next(s for s in corpus.stores() if s.pipeline == 'browser' and s.provider == 'claude')
    with tempfile.TemporaryDirectory() as scratch:
        root = Path(scratch)
        (root / store.input / 'empty').mkdir(parents=True)
        (root / store.input / 'full').mkdir(parents=True)
        (root / store.input / 'full' / 'full.json').write_text('{}')
        states = {u.address.name: state(u, Relation.ABSENT, judgement.UNJUDGED) for u in corpus.select(root, store)}
    ok = states.get('empty') == 'incomplete' and states.get('full') == 'unjudged'
    run('stage: a directory the selection names with no file under it is incomplete', ok,
        None if ok else f'the states read {states}, where an empty directory is incomplete and a full one unjudged',
        check='stage.empty_selection_is_incomplete')
    # A rehearsal passes over an incomplete unit and judges the rest (issues/996): the audit
    # counts as owed output only the units the pipelines were shown, so an empty directory
    # is never an input unprocessed - held over a planted root through the audit's own reader.
    import validation_audit as audit
    subjects = getattr(audit, 'input_subjects', None)
    with tempfile.TemporaryDirectory() as scratch:
        root = Path(scratch)
        (root / store.input / 'empty').mkdir(parents=True)
        (root / store.input / 'full').mkdir(parents=True)
        (root / store.input / 'full' / 'full.json').write_text('{}')
        try:
            counted = subjects(store, root) if subjects else None
        except TypeError:
            counted = None                # the reader takes no root: it counts the room's input alone
    ok = counted == ['full']
    run('stage: the audit counts only the units a rehearsal shows the pipelines', ok,
        None if ok else f'the audit counts {counted}, where the whole unit alone is owed output',
        check='audit.counts_what_pipelines_were_shown')
    # An input whose output was built from other bytes is owed a run (issues/1005): the output
    # records the digest of what it was built from, and the audit holds it to the input now -
    # over a planted input and cache, in process.
    owed = getattr(audit, 'owed_units', None)
    with tempfile.TemporaryDirectory() as scratch:
        root = Path(scratch) / 'input'; cache = Path(scratch) / 'cache'
        for name, body, recorded in (('fresh', b'{"a": 1}', None), ('stale', b'{"a": 2}', 'other bytes'), ('unprocessed', b'{"a": 3}', 'absent')):
            (root / store.input / name).mkdir(parents=True); (root / store.input / name / f'{name}.json').write_bytes(body)
            if recorded != 'absent':
                import hashlib
                (cache / name / 'validation').mkdir(parents=True)
                (cache / name / 'source.sha256').write_text((hashlib.sha256(body).hexdigest() if recorded is None else hashlib.sha256(b'other').hexdigest()) + '\n')
        found = owed(store, root, cache) if owed else None
    ok = found == {'stale': 'changed since its output', 'unprocessed': 'unprocessed'}
    run('audit: an input whose output was built from other bytes is owed a run', ok,
        None if ok else f'the audit owes {found}, where the stale and the unprocessed inputs alone are owed a run',
        check='audit.input_changed_since_output')
    # The capture an empty unit is offered again names the unit's directory as the id, and a
    # capture files under the full id (issues/990): so the offer stands only where the directory
    # is a full id of the provider's declared shape (issues/994) - a prefix-named directory, which
    # an interrupted capture of a typed prefix left, is the janitor's alone.
    recapture = getattr(corpus, 'recapture_of', None)
    with tempfile.TemporaryDirectory() as scratch:
        root = Path(scratch)
        for name in ('d11565d6', 'd11565d6-640e-465a-9aca-b77a96404d49'):
            (root / store.input / name).mkdir(parents=True)
        offered = {u.address.name: (recapture(u) if recapture else None) for u in corpus.select(root, store)}
    full = 'corpus-yoga browser capture --provider claude --id d11565d6-640e-465a-9aca-b77a96404d49'
    ok = recapture is not None and offered.get('d11565d6') is None and offered.get('d11565d6-640e-465a-9aca-b77a96404d49') == full
    run('stage: an empty unit is offered its capture again only where its directory is a full id', ok,
        None if ok else f'the offers read {offered}, where a prefix-named directory gets none and a full-id one gets {full!r}',
        check='stage.recapture_names_a_full_id')


@check(tier='code', on=['src/main/corpus.py', 'src/main/browser', 'src/main/export', 'src/main/agent'], says=(
    'store.held_twice_is_found',
    'store.surplus_is_found',
    'store.unit_names_its_kind',
))
def check_store(run) -> None:
    """A unit knows what it is called, and a unit another of its kind holds whole is found: over a scratch root, a session whose log is a prefix of the same
    session's under another project is contained, a memory equal to another's is
    identical, and what differs is neither."""
    import tempfile
    import corpus
    twice = getattr(corpus, 'held_twice', None)
    if twice is None:
        run('store: a unit another of its kind holds whole is found', False,
            'src/main/corpus.py relates a staged unit to the held one of its address and nothing else: '
            'one thing held at two addresses is found by no one', check='store.held_twice_is_found')
        return
    with tempfile.TemporaryDirectory() as scratch:
        root = Path(scratch)
        store = root / 'claude' / 'code' / 'machine-transport' / 'a-room'
        for project, session, log, note in (('one', '11111111-aaaa', b'abc\n', b'same'),
                                            ('two', '11111111-aaaa', b'abc\ndef\n', b'same'),
                                            ('three', '22222222-bbbb', b'xyz\n', b'other')):
            (store / project / 'memory').mkdir(parents=True)
            (store / project / f'{session}.jsonl').write_bytes(log)
            (store / project / 'memory' / 'note.md').write_bytes(note)
        found = corpus.units(root)
        kinds = sorted({u.kind for u in found})
        run('store: a unit is called what its selection\'s declaration calls it', kinds == ['memory', 'session'],
            None if kinds == ['memory', 'session'] else f'the kinds read {kinds}', check='store.unit_names_its_kind')
        got = [(u.address.relative_to(store.relative_to(root)).as_posix(), h.address.relative_to(store.relative_to(root)).as_posix(), how)
               for u, h, how in ((d.unit, d.holder, d.how) for d in twice(root))]
    expected = [('one/11111111-aaaa.jsonl', 'two/11111111-aaaa.jsonl', 'contained'), ('two/memory', 'one/memory', 'identical')]
    run('store: a unit another of its kind holds whole is found', got == expected,
        None if got == expected else f'held twice read {got}', check='store.held_twice_is_found')
    # a file inside a held unit that its measure does not read is surplus (issues/833): iCloud's
    # conflict copy beside a capture; a memory's every file is the mirror's, so none is
    extra = getattr(corpus, 'surplus', None)
    if extra is None:
        run('store: a file inside a held unit that its measure does not read is found', False,
            'src/main/corpus.py finds no file inside a held unit that no capture wrote', check='store.surplus_is_found')
        return
    with tempfile.TemporaryDirectory() as scratch:
        root = Path(scratch)
        capture = root / 'claude' / 'chat' / 'API-capture' / 'aaaaaaaa-0000-4000-8000-000000000000'
        capture.mkdir(parents=True)
        (capture / 'aaaaaaaa-0000-4000-8000-000000000000.json').write_text('{}')
        (capture / 'aaaaaaaa-0000-4000-8000-000000000000 2.json').write_text('{}')
        memory = root / 'claude' / 'code' / 'machine-transport' / 'a-room' / 'one' / 'memory'
        memory.mkdir(parents=True)
        (memory / 'note.md').write_text('x')
        (memory / 'note 2.md').write_text('x')
        got = sorted(rel.as_posix() for unit, rel in extra(root))
    expected = ['claude/chat/API-capture/aaaaaaaa-0000-4000-8000-000000000000/aaaaaaaa-0000-4000-8000-000000000000 2.json']
    run('store: a file inside a held unit that its measure does not read is found', got == expected,
        None if got == expected else f'surplus read {got}, where it is {expected}', check='store.surplus_is_found')


@check(tier='code', on=['src/main/corpus.py', 'src/main/export/atoms.py'], says=(
    'store.export_is_held_within_a_later_one',
))
def check_export_atoms(run) -> None:
    """An earlier export is held whole within a later one by its atoms: over a
    scratch root, an export whose conversations, memories and users are all among a later
    export's is contained, and one holding a message the later lacks is not; a memory state
    the deposits hold counts for nothing the export must still hold."""
    import json as json_
    import tempfile
    import corpus
    if 'atoms' not in corpus.MEASURE:
        run('store: an export is held whole within a later one by its atoms', False,
            'src/main/corpus.py relates two exports by the bytes of their trees alone: no earlier export is ever read as held within a later one',
            check='store.export_is_held_within_a_later_one')
        return
    with tempfile.TemporaryDirectory() as scratch:
        root = Path(scratch) / 'data' / 'input'
        bulk = root / 'claude' / 'chat' / 'bulk-export'
        account = '0fc4c1e0-4719-4e10-997a-697bf05599af'
        def export(name, convs, memory):
            d = bulk / name
            d.mkdir(parents=True)
            (d / 'conversations.json').write_text(json_.dumps(
                [{'uuid': c, 'name': c, 'summary': f's-{c}', 'chat_messages': [{'uuid': f'{c}-{i}'} for i in range(n)]} for c, n in convs]))
            (d / 'memories.json').write_text(json_.dumps({'account_uuid': account, 'note': memory}))
            (d / 'users.json').write_text(json_.dumps([{'uuid': 'u1', 'full_name': 'me'}]))
        export(f'data-{account}-1700000000-aaaaaaaa-2026-01-01-00-00-00', [('c1', 2)], 'early')
        export(f'data-{account}-1700000100-bbbbbbbb-2026-01-02-00-00-00', [('c1', 3), ('c2', 3)], 'later')
        export(f'data-{account}-1700000200-cccccccc-2026-01-03-00-00-00', [('c1', 4)], 'later')   # a message the second lacks, and lacking its c2
        deposits = Path(scratch) / 'data' / 'output' / 'memories'
        deposits.mkdir(parents=True)
        (deposits / '2026-01-01T000000Z.json').write_text(json_.dumps({'account_uuid': account, 'note': 'early'}))
        got = [(d.unit.address.name[-28:-20], d.holder.address.name[-28:-20], d.how) for d in corpus.held_twice(root)]
    expected = [('aaaaaaaa', 'bbbbbbbb', 'contained')]
    run('store: an export is held whole within a later one by its atoms', got == expected,
        None if got == expected else f'held twice read {got}', check='store.export_is_held_within_a_later_one')


@check(tier='code', says=('agent.memory_merge_judges_each_fact_alone',), on=['src/main/cli/agent'])
def check_memory_merge(run) -> None:
    """Whether a peer's copy of a memory fact differs from the local copy is decided by that
    pair alone, its links read by the facts they name: a copy that differs only in what one of
    its links is dressed as is the same fact, kept. The fixture is synthetic: one fact that
    differs, seven that link it in a chain, one the room lacks that links it, and one the peer
    extends whose room copy links it already re-dressed, extended after the bytes the room
    holds; the peer's index line for the new fact joins the room's index, and the merge leaves
    no record of itself in it (issues/1063); a second receipt of the same folder writes nothing (L1)."""
    import tempfile
    import transport
    harness = transport.adapter('claude')
    assert harness is not None, 'transport serves no claude adapter'
    def address(stem: str) -> str:
        return '/'.join(('p', 'memory', f'{stem}.md'))
    with tempfile.TemporaryDirectory() as tmp:
        sent, held = Path(tmp) / 'sent', Path(tmp) / 'held'
        sent.mkdir()
        held.mkdir()
        (sent / 'a0.md').write_text('the fact, as the peer holds it\n')
        (held / 'a0.md').write_text('the fact, as this room holds it\n')
        for i in range(1, 8):
            for root in (sent, held):
                (root / f'a{i}.md').write_text(f'follows [[a{i - 1}]]\n')
        (sent / 'b.md').write_text('new here, and follows [[a0]]\n')
        (held / 'c.md').write_text('begun [[a0.peer]]\n')
        (sent / 'c.md').write_text('begun [[a0]]\ngone on [[a0]]\n')
        (held / 'MEMORY.md').write_text('- [the fact](a0.md)\n')
        (sent / 'MEMORY.md').write_text('- [the fact](a0.md)\n- [new here](b.md)\n')
        outcomes = []
        log = transport.Log(transport.LIVE, 'did')
        for _ in range(2):
            log = transport.Log(transport.LIVE, 'did')
            try:
                harness.merge_memory(sent, held, True, 'peer', log, 'p')
                outcomes.append({key: sorted(units) for key, units in log.by.items()})
            except Exception as error:
                outcomes.append(f'{type(error).__name__}: {error}')
                break
        wrote, kept = log.key('wrote'), log.key('kept')
        chain = [address(f'a{i}') for i in range(1, 8)]
        first = {wrote: [address('MEMORY'), address('a0'), address('b'), address('c')], kept: chain}
        second = {kept: sorted([address('MEMORY'), address('a0'), address('b'), address('c'), *chain])}
        def text(name: str) -> str | None:
            return (held / name).read_text() if (held / name).is_file() else None
        written = (text('a0.peer.md'), text('b.md'), text('c.md'), text('MEMORY.md'))
        same = (outcomes == [first, second] and written == ('the fact, as the peer holds it\n', 'new here, and follows [[a0.peer]]\n',
                                                            'begun [[a0.peer]]\ngone on [[a0.peer]]\n',
                                                            '- [the fact](a0.md)\n- [the fact](a0.peer.md)\n- [new here](b.md)\n'))
        run("agent: a peer's memory fact is judged against the room's copy alone, and a second receipt writes nothing", same,
            None if same else f'the two receipts said {outcomes!r}; the twin, the new fact, the extended one and the index hold {written!r}',
            check='agent.memory_merge_judges_each_fact_alone')


@check(tier='code', says=('agent.renamed_checkout_is_one_project', 'migration.renamed_checkout_moves_once'),
       on=['src/main/cli/agent', 'rsc/naming/checkout_paths.csv', 'rsc/migration/step.sh', 'rsc/migration/1058.sh'])
def check_renamed_checkout(run) -> None:
    """A checkout's former paths, rsc/naming/checkout_paths.csv, name one project: an install
    writes a peer's project held under a former path's key under the current key, a capture
    reads a session the store holds under a former key as the one it holds, and rsc/migration/1058.sh
    brings a room's live store under the current key - bare, every step it would take and the
    halt where an entry stands under both keys; applied, the steps; again, nothing (issues/1058).
    The fixtures are synthetic: a peer's bundle and a store under temporary roots, and a
    checkout, a live store and a home of their own for the migration."""
    import os
    import shutil
    import subprocess
    import tempfile
    import transport
    harness = transport.adapter('claude')
    assert harness is not None, 'transport serves no claude adapter'
    current, former = transport._checkout_keys()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        bundle, live, outbox, held = root / 'bundle', root / 'live', root / 'outbox', root / 'held'
        (bundle / former[0]).mkdir(parents=True)
        (bundle / former[0] / 'aaaaaaaa-0000-0000-0000-000000000000.jsonl').write_text('{"a": 1}\n')
        harness.pull_all(bundle, live, True, 'peer')
        installed = sorted(p.relative_to(live).as_posix() for p in live.rglob('*.jsonl'))
        (held / former[1]).mkdir(parents=True)
        (held / former[1] / 'aaaaaaaa-0000-0000-0000-000000000000.jsonl').write_text('{"a": 1}\n')
        (live / current).mkdir(parents=True, exist_ok=True)
        if not (live / current / 'aaaaaaaa-0000-0000-0000-000000000000.jsonl').exists():   # where an install put it elsewhere, the capture still reads one live copy
            (live / current / 'aaaaaaaa-0000-0000-0000-000000000000.jsonl').write_text('{"a": 1}\n')
        log = harness.capture_all(live, outbox, held)
        restaged = sorted(p.relative_to(outbox).as_posix() for p in outbox.rglob('*.jsonl')) if outbox.is_dir() else []
        same = installed == [f'{current}/aaaaaaaa-0000-0000-0000-000000000000.jsonl'] and restaged == []
        run("agent: a peer's project under a former path's key installs under the current key, and a capture reads the store's copy under a former key",
            same, None if same else f'installed {installed}; the capture staged {restaged}, saying {log.facts()}',
            check='agent.renamed_checkout_is_one_project')
        unmoved = root / 'unmoved'
        (unmoved / former[1]).mkdir(parents=True)
        (unmoved / former[1] / 'aaaaaaaa-0000-0000-0000-000000000000.jsonl').write_text('{"a": 1}\n')
        dry = harness.pull_all(bundle, unmoved, False, 'peer')
        kept = list(dry.by) == [dry.key('kept')]
        run("agent: an install reads a live session still under a former path's key as the one the room holds, and would write nothing", kept,
            None if kept else f'the install would say {dry.facts()}', check='agent.renamed_checkout_is_one_project')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        checkout, home = root / 'checkout', root / 'home'
        for part in ('rsc/migration/step.sh', 'rsc/migration/1058.sh', 'rsc/naming/checkout_paths.csv'):
            (checkout / part).parent.mkdir(parents=True, exist_ok=True)
            if (REPO_ROOT / part).is_file():
                shutil.copy2(REPO_ROOT / part, checkout / part)
        (checkout / 'machine-name.txt').write_text('room\n')
        projects = home / 'projects'
        mount = checkout / 'ext/mnt/claude/code/machine-transport'
        mount.mkdir(parents=True)
        (mount / 'room').symlink_to(projects)
        keys = [line.split(',')[0] for line in (checkout / 'rsc/naming/checkout_paths.csv').read_text().splitlines()[1:]]
        now, *was = [''.join(c if c.isalnum() else '-' for c in str(home / k.removeprefix('~/'))) for k in keys]
        (projects / was[1] / 'memory').mkdir(parents=True)
        (projects / was[1] / 'memory' / 'MEMORY.md').write_text('the index\n')
        (projects / was[1] / 'bbbbbbbb.jsonl').write_text('{}\n')
        (projects / was[1] / '.DS_Store').write_text('')
        (projects / now).mkdir(parents=True)
        (projects / now / 'memory').symlink_to(projects / was[1] / 'memory')
        (projects / now / 'cccccccc.jsonl').write_text('{}\n')
        script = checkout / 'rsc/migration/1058.sh'
        env = {**os.environ, 'HOME': str(home)}
        def ran(*flags: str) -> subprocess.CompletedProcess:
            if not script.is_file():
                return subprocess.CompletedProcess([str(script)], 127, '', 'rsc/migration/1058.sh is absent')
            return subprocess.run([str(script), *flags], capture_output=True, text=True, env=env, timeout=60)
        bare, applied, again = ran(), ran('--apply'), ran()
        moved = sorted(p.relative_to(projects).as_posix() for p in projects.rglob('*') if not p.is_dir() or p.is_symlink())
        settled = (bare.returncode == 0 and len(bare.stdout.splitlines()) == 4 and applied.returncode == 0 and again.stdout == ''
                   and moved == [f'{now}/bbbbbbbb.jsonl', f'{now}/cccccccc.jsonl', f'{now}/memory/MEMORY.md']
                   and not (projects / now / 'memory').is_symlink())
        run('migration: rsc/migration/1058.sh brings a former key\'s folder under the current key - bare the steps, applied the moves, again nothing',
            settled, None if settled else f'bare said {bare.stdout!r} {bare.stderr!r}; applied said {applied.stdout!r} {applied.stderr!r}; '
            f'again said {again.stdout!r}; the live store holds {moved}', check='migration.renamed_checkout_moves_once')
        (projects / was[2] / 'memory').mkdir(parents=True)
        (projects / was[2] / 'memory' / 'MEMORY.md').write_text('an older index\n')
        halted = ran()
        stops = halted.returncode == 1 and 'both exist' in halted.stderr and (projects / was[2] / 'memory' / 'MEMORY.md').is_file()
        run('migration: rsc/migration/1058.sh halts, bare, where a former key\'s entry and the current key\'s both stand and the store holds no copy of it', stops,
            None if stops else f'it exits {halted.returncode}, saying {halted.stdout!r} {halted.stderr!r}', check='migration.renamed_checkout_moves_once')
        record = checkout / 'data/input/claude/code/machine-transport/room' / was[2] / 'memory'
        record.mkdir(parents=True)
        (record / 'MEMORY.md').write_text('an older index\n')
        bare_held, applied_held = ran(), ran('--apply')
        released = (bare_held.returncode == 0 and applied_held.returncode == 0 and not (projects / was[2]).exists()
                    and (record / 'MEMORY.md').is_file() and (projects / now / 'memory' / 'MEMORY.md').read_text() == 'the index\n')
        run('migration: rsc/migration/1058.sh releases a former key\'s entry the store holds byte for byte where the current key\'s stands, and halts on none',
            released, None if released else f'bare said {bare_held.stdout!r} {bare_held.stderr!r}; applied said {applied_held.stdout!r} {applied_held.stderr!r}',
            check='migration.renamed_checkout_moves_once')
    import facts
    import importlib.util
    spec = importlib.util.spec_from_file_location('migration_status', SRC / 'main' / 'cli' / 'migration' / 'migration.py')
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    import standing
    halted_facts = migration.status_facts({'rsc/migration/1058.sh': (1, ['mv a b', 'FAIL: c and d both exist'])})
    offered, found = facts.now_of(halted_facts), getattr(standing, 'failing', lambda said: None)(facts.plain(halted_facts))
    finding = offered == {} and found == {'scripts': {'rsc/migration/1058.sh': {'halted': 'c and d both exist'}}}
    run('migration: a halted script is a finding - its FAIL a fact the room gathers, and no entry of now:, which holds acts alone', finding,
        None if finding else f'now: says {offered!r}; the findings gathered are {found!r}',
        check='migration.renamed_checkout_moves_once')


@check(tier='code', says=('agent.offers_only_effective_acts', 'status.an_act_has_something_to_act_on', 'migration.merge_records_are_stripped'),
       on=['src/main/cli/agent', 'src/main/facts.py', 'rsc/migration'])
def check_effective_acts(run) -> None:
    """An act a status offers has something to act on (issues/1064): facts.would gives the act of
    what a dry run found, and none where it found nothing, and no act stands over nothing. The
    agent's pull from a peer (issues/1062) is offered so, from its dry run; the agent declares no
    undo, and rsc/migration/1063.sh strips the merge records a room's memory index holds, its
    index lines kept (issues/1063)."""
    import importlib.util
    import os
    import shutil
    import subprocess
    import tempfile
    import facts
    import transport
    would = getattr(facts, 'would', None)
    orphan = '/'.join(('tmp', 'logs', 'site', 'one'))
    built = (would('corpus-yoga logs clean', {}), would('corpus-yoga logs clean', {orphan: 2})) if callable(would) else None
    try:
        facts.Would('corpus-yoga logs clean', {})
        empty = 'an act over nothing was built'
    except (AssertionError, ValueError):
        empty = None
    effective = built is not None and built[0] is None and built[1] == facts.Would('corpus-yoga logs clean', {orphan: 2}) and empty is None
    run('status: an act is built of what a dry run found, and none stands over nothing', effective,
        None if effective else 'src/main/facts.py has no would(line, found)' if built is None else f'would gave {built!r}; {empty}',
        check='status.an_act_has_something_to_act_on')
    spec = importlib.util.spec_from_file_location('agent_status', SRC / 'main' / 'cli' / 'agent' / 'agent.py')
    assert spec is not None and spec.loader is not None
    agent = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(agent)
    offer = getattr(agent, 'pull_act', None)
    idle, busy = transport.Log(transport.LIVE, 'would'), transport.Log(transport.LIVE, 'would')
    idle.say('kept', 'p/s.jsonl', {'identical': '1 bytes'}, 'session')
    busy.say('wrote', 'p/s.jsonl', {'new': '1 bytes'}, 'session')
    said = (offer('home-room', idle), offer('home-room', busy)) if callable(offer) else None
    verbs = sorted(d.stem for d in (SRC / 'main' / 'cli' / 'agent').glob('*.json') if d.stem != 'agent')
    pulled = (said is not None and said[0] is None and isinstance(said[1], facts.Would) and said[1].line == 'corpus-yoga agent pull --all --from home-room'
              and 'pull' in verbs and 'install' not in verbs and 'demerge' not in verbs)
    run('agent: a pull from a peer is offered only where its dry run would write something, and the agent declares no install and no undo', pulled,
        None if pulled else f'src/main/cli/agent/agent.py has no pull_act(machine, log); the agent declares {verbs}' if said is None
        else f'offered {said!r}; the agent declares {verbs}', check='agent.offers_only_effective_acts')

    peer = getattr(agent, 'Peer', None)
    shown = facts.plain(peer(busy.facts(), said[1])) if peer is not None and said is not None else None
    direct = shown == facts.plain(busy.facts())
    run("agent: a peer's pull is said as its dry run's outcomes, directly under the peer's name", direct,
        None if direct else f'the peer is said as {shown!r}, where the dry run says {facts.plain(busy.facts())!r}', check='agent.offers_only_effective_acts')

    with tempfile.TemporaryDirectory() as tmp:
        checkout, projects = Path(tmp) / 'checkout', Path(tmp) / 'projects'
        for part in ('rsc/migration/step.sh', 'rsc/migration/1063.sh'):
            (checkout / part).parent.mkdir(parents=True, exist_ok=True)
            if (REPO_ROOT / part).is_file():
                shutil.copy2(REPO_ROOT / part, checkout / part)
        (checkout / 'machine-name.txt').write_text('room\n')
        mount = checkout / 'ext/mnt/claude/code/machine-transport'
        mount.mkdir(parents=True)
        (mount / 'room').symlink_to(projects)
        index = projects / '-p' / 'memory' / 'MEMORY.md'
        index.parent.mkdir(parents=True)
        index.write_text('- [mine](mine.md)\n<!-- merge:begin 2026-11-11T151001Z from=peer -->\n- [theirs](theirs.md)\n'
                         '<!-- merge:act new theirs.md sha=0 len=1 -->\n<!-- merge:end -->\n')
        script = checkout / 'rsc/migration/1063.sh'
        def ran(*flags: str) -> subprocess.CompletedProcess:
            if not script.is_file():
                return subprocess.CompletedProcess([str(script)], 127, '', 'rsc/migration/1063.sh is absent')
            return subprocess.run([str(script), *flags], capture_output=True, text=True, env={**os.environ}, timeout=60)
        bare, applied, again = ran(), ran('--apply'), ran()
        stripped = (bare.returncode == 0 and len(bare.stdout.splitlines()) == 1 and applied.returncode == 0 and again.stdout == ''
                    and index.read_text() == '- [mine](mine.md)\n- [theirs](theirs.md)\n')
        run("migration: rsc/migration/1063.sh strips the merge records a memory index holds, its index lines kept - bare the step, applied, again nothing",
            stripped, None if stripped else f'bare said {bare.stdout!r} {bare.stderr!r}; applied said {applied.stdout!r} {applied.stderr!r}; '
            f'again said {again.stdout!r}; the index holds {index.read_text()!r}', check='migration.merge_records_are_stripped')


@check(tier='code', says=('python.bytecode_stands_under_tmp_cache', 'migration.bytecode_leaves_src', 'cache.stale_bytecode_is_named'),
       on=['src/import_roots.sh', 'src/run_python_script.sh', 'corpus-yoga', 'rsc/migration', 'src/main/cli/cache', 'rsc/cache_io.csv'])
def check_bytecode(run) -> None:
    """Python's bytecode stands under tmp/cache/python, never beside the sources (issues/1052): every
    python the launcher starts is given that prefix; rsc/migration/1052.sh discards the bytecode
    a room's src already holds and retires each directory that held nothing else; and bytecode
    under the prefix whose source no longer stands is an orphan the cache names. The fixtures are
    synthetic: a checkout with a src of its own, and a prefix under a temporary root."""
    import os
    import shutil
    import subprocess
    import sys
    import tempfile
    import cache_io
    asked = subprocess.run([str(REPO_ROOT / 'src' / 'run_python_script.sh'), '-c', 'import sys; print(sys.pycache_prefix)'],
                           capture_output=True, text=True, cwd=REPO_ROOT, env={**os.environ, 'CORPUS_YOGA_VENV': sys.prefix}, timeout=60)
    prefix = (REPO_ROOT / 'tmp' / 'cache' / 'python').as_posix()
    given = asked.stdout.strip() == prefix
    run('python: every python the launcher starts keeps its bytecode under tmp/cache/python', given,
        None if given else f'sys.pycache_prefix is {asked.stdout.strip() or asked.stderr.strip()[:120]!r}, where the prefix is {prefix}',
        check='python.bytecode_stands_under_tmp_cache')

    with tempfile.TemporaryDirectory() as tmp:
        checkout = Path(tmp) / 'checkout'
        for part in ('rsc/migration/step.sh', 'rsc/migration/1052.sh'):
            (checkout / part).parent.mkdir(parents=True, exist_ok=True)
            if (REPO_ROOT / part).is_file():
                shutil.copy2(REPO_ROOT / part, checkout / part)
        def under_src(*parts: str) -> str:
            return '/'.join(('src', *parts))
        for held in (under_src('__pycache__', 'top.cpython-314.pyc'),
                     under_src('main', 'kept', '__pycache__', 'kept.cpython-314.pyc'), under_src('main', 'kept', 'kept.py'),
                     under_src('main', 'gone', '__pycache__', 'gone.cpython-314.pyc'),
                     under_src('main', 'gone', 'deeper', '__pycache__', 'deeper.cpython-314.pyc'), under_src('gen', 'made', 'made.txt')):
            (checkout / held).parent.mkdir(parents=True, exist_ok=True)
            (checkout / held).write_text('')
        script = checkout / 'rsc/migration/1052.sh'
        def ran(*flags: str) -> subprocess.CompletedProcess:
            if not script.is_file():
                return subprocess.CompletedProcess([str(script)], 127, '', 'rsc/migration/1052.sh is absent')
            return subprocess.run([str(script), *flags], capture_output=True, text=True, env={**os.environ}, timeout=60)
        bare, applied, again = ran(), ran('--apply'), ran()
        left = sorted(p.relative_to(checkout).as_posix() for p in (checkout / 'src').rglob('*'))
        cleared = (bare.returncode == 0 and len(bare.stdout.splitlines()) == 6 and applied.returncode == 0 and again.stdout == ''
                   and left == [under_src('gen'), under_src('gen', 'made'), under_src('gen', 'made', 'made.txt'),
                                under_src('main'), under_src('main', 'kept'), under_src('main', 'kept', 'kept.py')])
        run("migration: rsc/migration/1052.sh discards the bytecode under src and retires each directory that held nothing else - bare the steps, applied, again nothing",
            cleared, None if cleared else f'bare said {bare.stdout!r} {bare.stderr!r}; applied said {applied.stdout!r} {applied.stderr!r}; '
            f'again said {again.stdout!r}; src holds {left}', check='migration.bytecode_leaves_src')

    with tempfile.TemporaryDirectory() as tmp:
        source, under = Path(tmp).resolve() / 'source', Path(tmp).resolve() / 'prefix'
        source.mkdir()
        (source / 'kept.py').write_text('')
        mirror = under / source.relative_to(source.anchor)
        mirror.mkdir(parents=True)
        for name in ('kept.cpython-314.pyc', 'gone.cpython-314.pyc'):
            (mirror / name).write_text('')
        (under / 'nowhere' / 'left').mkdir(parents=True)
        (under / 'nowhere' / 'left' / 'x.cpython-314.pyc').write_text('')
        found = sorted(p.relative_to(under).as_posix() for p in cache_io.stale_bytecode(under))
    wanted = sorted([(mirror / 'gone.cpython-314.pyc').relative_to(under).as_posix(), 'nowhere'])
    named = found == wanted
    run('cache: bytecode whose source no longer stands is an orphan - a file where its directory stands, the directory where it does not', named,
        None if named else f'named {found}, where the stale are {wanted}',
        check='cache.stale_bytecode_is_named')


@check(tier='code', says=('agent.status_counts_by_kind', 'scratch.stands_under_tmp_cache', 'cache.dead_scratch_is_named'),
       on=['src/main/cli/agent', 'src/main/tier.sh', 'src/main/cli/cache', 'rsc/cache_io.csv', 'src'])
def check_screen_and_scratch(run) -> None:
    """The agent status counts what it holds by kind and names only what a reader acts on
    (issues/1004): sessions by room and provider, a pull's kept units by kind with their size, the
    units it would write by name - the per-session listing a verb of its own, list-sessions.
    A disposable file a script keeps stands under tmp/cache/scratch, named with the pid of the
    run that keeps it, through the tier's scratch_file and scratch_dir alone (issues/906), and the
    cache names an entry there whose run is gone. The fixtures are synthetic."""
    import importlib.util
    import os
    import subprocess
    import sys
    import tempfile
    import cache_io
    import transport
    spec = importlib.util.spec_from_file_location('agent_status', SRC / 'main' / 'cli' / 'agent' / 'agent.py')
    assert spec is not None and spec.loader is not None
    agent = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(agent)
    tally, summary = getattr(agent, 'tally', None), getattr(agent, 'summary', None)
    verbs = sorted(d.stem for d in (SRC / 'main' / 'cli' / 'agent').glob('*.json') if d.stem != 'agent')
    counted = tally([('local', 'claude', 1_500_000), ('local', 'claude', 500_000), ('home-room', 'claude', 2_000_000)]) if callable(tally) else None
    with tempfile.TemporaryDirectory() as tmp:
        bundle = Path(tmp)
        (bundle / 'p' / 's').mkdir(parents=True)
        (bundle / 'p' / 'memory').mkdir()
        (bundle / 'p' / 's.jsonl').write_text('x' * 10)
        (bundle / 'p' / 's' / 'f').write_text('x' * 5)
        (bundle / 'p' / 'memory' / 'a.md').write_text('x' * 3)
        log = transport.Log(transport.LIVE, 'would')
        for address in ('p/s.jsonl', 'p/s/', '/'.join(('p', 'memory', 'a.md'))):
            log.say('kept', address, {'identical': 'bytes'})
        log.say('wrote', 'p/t.jsonl', {'new': '9 bytes'})
        said = summary(log, bundle) if callable(summary) else None
    human = cache_io.human
    wanted = {log.key('wrote'): {'p/t.jsonl': {'new': '9 bytes'}},
              log.key('kept'): {'sessions': f'1, {human(10)}', 'workspaces': f'1, {human(5)}', 'memory facts': f'1, {human(3)}'}}
    same = (counted == {'local': {'claude': f'2 session(s), {human(2_000_000)}'}, 'home-room': {'claude': f'1 session(s), {human(2_000_000)}'}}
            and said == wanted and 'list-sessions' in verbs)
    run('agent: the status counts sessions by room and provider and a pull\'s kept units by kind, names what a pull would write, and list-sessions lists each session',
        same, None if same else 'src/main/cli/agent/agent.py has no tally(sized) and summary(log, bundle)' if counted is None or said is None
        else f'sessions counted as {counted!r}; the pull said as {said!r}; the agent declares {verbs}', check='agent.status_counts_by_kind')

    loose = sorted(f'{path.relative_to(REPO_ROOT)}:{number}' for path in SRC.rglob('*.sh') if path.name != 'tier.sh'
                   for number, line in enumerate(path.read_text().splitlines(), 1) if 'mktemp' in line and not line.lstrip().startswith('#'))
    with tempfile.TemporaryDirectory() as tmp:
        made = subprocess.run(['bash', '-c', f'source "{SRC}/main/tier.sh"; TMP_DIR="{tmp}"; f="$(scratch_file probe)"; d="$(scratch_dir probe)"; echo "$f"; echo "$d"; echo $$; [[ -f "$f" && -d "$d" ]]'],
                              capture_output=True, text=True, timeout=30)
        lines = made.stdout.split()
        placed = (made.returncode == 0 and len(lines) == 3 and all(line.startswith(f'{tmp}/cache/scratch/probe.{lines[2]}.') for line in lines[:2]))
    kept = not loose and placed
    run('scratch: a disposable file a script keeps stands under tmp/cache/scratch, named with its run\'s pid, through the tier\'s scratch_file and scratch_dir alone',
        kept, None if kept else f'mktemp is called at {", ".join(loose)}' if loose else f'the tier made {made.stdout!r} {made.stderr.strip()[:160]!r}',
        check='scratch.stands_under_tmp_cache')

    gone = subprocess.run([sys.executable, '-c', 'import os; print(os.getpid())'], capture_output=True, text=True, timeout=30).stdout.strip()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / f'live.{os.getpid()}.aaaaaa').write_text('')
        (root / f'left.{gone}.bbbbbb').write_text('')
        (root / 'unnamed').write_text('')
        found = sorted(p.name for p in cache_io.dead_scratch(root))
    named = found == [f'left.{gone}.bbbbbb', 'unnamed']
    run('cache: a scratch entry whose run is gone is an orphan, and one whose run lives is not', named,
        None if named else f'named {found}', check='cache.dead_scratch_is_named')


@check(tier='code', says=('command.a_moved_verb_is_a_fault', 'reference.pointer_reads_the_declared_lineage', 'migration.raise_bodies_stand_with_the_record',
                          'python.a_shebang_is_executable', 'requirements.each_is_pinned'),
       on=['src', 'rsc/migration', 'pyrightconfig.json'])
def check_sweep(run) -> None:
    """What the reading of 2026-11-12 found (issues/1069), held: a word after a declared noun that
    is another noun's verb is a spelling fault; a pointer into a reference project resolves
    against the lineage its derivation declares; a raise keeps its body beside the act's record,
    and rsc/migration/1069.sh moves a room's bodies there; a python file with a shebang is
    executable; and every requirement is pinned. The migration's fixture is synthetic."""
    import importlib
    import importlib.util
    import os
    import shutil
    import subprocess
    import tempfile
    import factoring
    import latest
    spell = importlib.import_module('spell')
    said = {text: [fault for _spelling, fault in spell.mentions(text)] for text in
            ('`corpus-yoga reference pull` holds every lineage', 'corpus-yoga reference fetch records them', 'corpus-yoga reference says what differs')}
    moved = bool(said['`corpus-yoga reference pull` holds every lineage'][0]) and not any(said['corpus-yoga reference fetch records them']) and not any(said['corpus-yoga reference says what differs'])
    run("spelling: a word after a declared noun that is another noun's verb is a fault, and prose after a noun is not", moved,
        None if moved else f'the mentions read as {said!r}', check='command.a_moved_verb_is_a_fault')

    read = getattr(latest, 'reference_file', None)
    pointed = read(factoring.SNAPSHOT_DIR) if callable(read) else latest.latest_file(factoring.SNAPSHOT_DIR)
    declared = callable(read) and pointed == factoring.WITNESS
    run('reference: a pointer into a reference project resolves against the lineage its derivation declares', declared,
        None if declared else 'src/main/latest.py has no reference_file(directory)' if not callable(read) else f'it resolves {pointed}, where the derivation declares {factoring.WITNESS}',
        check='reference.pointer_reads_the_declared_lineage')

    raise_at = importlib.util.spec_from_file_location('forge_raise', SRC / 'main' / 'cli' / 'forge' / 'raise.py')
    assert raise_at is not None and raise_at.loader is not None
    raising = importlib.util.module_from_spec(raise_at)
    raise_at.loader.exec_module(raising)
    kept = raising.RECORD.as_posix().endswith('/'.join(('tmp', 'logs', 'forge', 'raise')))
    with tempfile.TemporaryDirectory() as tmp:
        checkout = Path(tmp) / 'checkout'
        for part in ('rsc/migration/step.sh', 'rsc/migration/1069.sh'):
            (checkout / part).parent.mkdir(parents=True, exist_ok=True)
            if (REPO_ROOT / part).is_file():
                shutil.copy2(REPO_ROOT / part, checkout / part)
        old, new = checkout / 'tmp' / 'forge' / 'raise', checkout / 'tmp' / 'logs' / 'forge' / 'raise'
        old.mkdir(parents=True)
        new.mkdir(parents=True)
        (old / '2026-11-11T134619Z.md').write_text('a body\n')
        (new / '2026-11-11T134618Z.log').write_text('its record\n')
        script = checkout / 'rsc/migration/1069.sh'
        def ran(*flags: str) -> subprocess.CompletedProcess:
            if not script.is_file():
                return subprocess.CompletedProcess([str(script)], 127, '', 'rsc/migration/1069.sh is absent')
            return subprocess.run([str(script), *flags], capture_output=True, text=True, env={**os.environ}, timeout=60)
        bare, applied, again = ran(), ran('--apply'), ran()
        stands = sorted(p.name for p in new.iterdir()) if new.is_dir() else []
        moved_bodies = (bare.returncode == 0 and len(bare.stdout.splitlines()) == 2 and applied.returncode == 0 and again.stdout == ''
                        and stands == ['2026-11-11T134618Z.log', '2026-11-11T134619Z.md'] and not old.exists())
    run("migration: a raise keeps its body under tmp/logs/forge/raise, and rsc/migration/1069.sh moves a room's bodies there and retires tmp/forge/raise",
        kept and moved_bodies, None if kept and moved_bodies else f'a raise keeps its body under {raising.RECORD}; bare said {bare.stdout!r} {bare.stderr!r}; '
        f'applied said {applied.stdout!r} {applied.stderr!r}; again said {again.stdout!r}; the record holds {stands}', check='migration.raise_bodies_stand_with_the_record')

    listed = subprocess.run(['git', 'ls-files', '-s', '--', '*.py'], capture_output=True, text=True, cwd=REPO_ROOT, timeout=60).stdout.splitlines()
    idle = sorted(row.split('\t', 1)[1] for row in listed if not row.startswith('100755')
                  and (REPO_ROOT / row.split('\t', 1)[1]).is_file() and (REPO_ROOT / row.split('\t', 1)[1]).read_bytes()[:2] == b'#!')
    run('python: a python file that opens with a shebang is executable', not idle,
        None if not idle else f'{len(idle)} file(s) open with a shebang and are not executable - {", ".join(idle[:5])}', check='python.a_shebang_is_executable')

    loose = [line.strip() for line in (SRC / 'requirements.txt').read_text().splitlines() if line.strip() and not line.startswith('#') and '==' not in line]
    run('requirements: every requirement is pinned', not loose,
        None if not loose else f'src/requirements.txt leaves unpinned: {", ".join(loose)}', check='requirements.each_is_pinned')
