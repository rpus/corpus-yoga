"""unit.py - the dev gate's checks of the stage and the store: rehearsal records, units, states and atoms."""
import hashlib
import json
import sys
from pathlib import Path

from gate import (  # noqa: F401 - the gate's shared vocabulary
    REPO_ROOT,
    SRC,
    check,
)


@check(tier='code', on=['src/main/rehearsal.py', 'src/main/rehearsal.schema.json', 'src/main/corpus.py', 'src/main/tier.py', 'src/main/pipeline', 'rsc/reference/JSONSchema'], says=(
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
    sys.path.insert(0, str(SRC / 'main'))
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
    def unit(name: str, pipeline: str | None = 'chat-capture') -> corpus.Unit:
        address = Path('claude/chat/API-capture') / name
        judges = next(s for s in corpus.stores() if s.pipeline == 'chat-capture' and s.provider == 'claude').globs[0].families if pipeline else ()
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
        got = [corpus.verdict(a, record, digests['a'], main), corpus.verdict(b, record, digests['b'], main),
               corpus.verdict(a, record, {sha('f')}, main), corpus.verdict(c, record, digests['c'], main),
               corpus.verdict(d, record, digests['d'], main), corpus.verdict(e, record, set(), main),
               corpus.verdict(a, record, digests['a'], lambda pipeline, family: (sha('d'), 'v2')),   # origin/main has moved past the record
               corpus.verdict(a, record, digests['a'], lambda pipeline, family: (sha('d'), 'v0'))]   # the record is a branch's mint ahead of main
    expected = [(corpus.Judgement.VALID, f'validates at claude/apiConversation v1 (origin/main; rehearsal {stamp})'),
                (corpus.Judgement.INVALID, 'invalid at claude/apiConversation v1 - Validation error - a version is owed'),
                (corpus.Judgement.CHANGED, f'changed since rehearsal {stamp}'),
                (corpus.Judgement.UNSEEN, f'unseen by rehearsal {stamp}'),
                (corpus.Judgement.UNJUDGED, f'seen by rehearsal {stamp}, no verdict written'),
                (corpus.Judgement.NONE, 'no pipeline selects it'),
                (corpus.Judgement.SUPERSEDED, 'judged at claude/apiConversation v1; origin/main holds v2 - corpus-yoga pipeline rehearse re-judges it'),
                (corpus.Judgement.UNLICENSED, 'valid at claude/apiConversation v1 - a version of this checkout, which origin/main does not hold (v0 there)')]
    wrong = [(g, e) for g, e in zip(got, expected) if g[0] is not e[0] or not g[1].startswith(e[1])]
    refusal = got[1][2]
    at = '/'.join(('chat-capture', 'claude/apiConversation', 'v1.json'))   # the fixture's version file under rsc/schema/pipeline, which no tree holds
    if not wrong and (refusal is None or (refusal.path, refusal.reason) != (at, 'Validation error')):
        wrong = [(got[1], (corpus.Judgement.INVALID, f'a refusal as data - family, version, reason - where it is {refusal}'))]
    states = [corpus.state(a, corpus.Relation.ABSENT, j) for j in (corpus.Judgement.UNSEEN, corpus.Judgement.CHANGED, corpus.Judgement.SUPERSEDED, corpus.Judgement.NONE)]
    counted = states == ['unjudged', 'unjudged', 'unjudged', 'promotable']
    run("rehearsal: a unit's standing to the record is decidable from it", not wrong and counted,
        None if not wrong and counted else
        f'{wrong[0][0][0].value}: {wrong[0][0][1][:100]!r}, where it is {wrong[0][1][0].value}: {wrong[0][1][1]!r}' if wrong
        else f'unseen, changed, superseded and no family count as {states}, where they are unjudged, unjudged, unjudged and promotable',
        check='rehearsal.states_are_decidable')


@check(tier='code', says=('stage.export_is_one_unit',), on=['src/main/corpus.py', 'src/main/pipeline'])
def check_unit_companion(run) -> None:
    """The staged bulk export <X> is one unit, named by <X>, by the chat-export declaration
    itself: its member is data-<X>/, which promotion copies, and its record is
    manifest-<X>.json, which stays in the stage. Either alone is the same unit, unpaired,
    naming what is absent. The fixture is synthetic - one export whole, one with its
    manifest alone, one with its payload alone."""
    import tempfile
    sys.path.insert(0, str(SRC / 'main'))
    import corpus
    store = next(s for s in corpus.stores() if s.pipeline == 'chat-export')
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
    sys.path.insert(0, str(SRC / 'main'))
    import corpus
    from append_only import Relation
    state = getattr(corpus, 'state', None)
    judgement = getattr(corpus, 'Judgement', None)
    if state is None or judgement is None:
        run('stage: a unit not yet judged is counted unjudged, never held back', False,
            'src/main/corpus.py derives no state: its counts hold back whatever is not promotable',
            check='stage.states_are_told_apart')
        return
    whole = corpus.Unit(Path('a/b'), [Path('a/b')], [], [], 'prefix', 'chat-capture', 'claude')
    lacking = corpus.Unit(Path('a/c'), [Path('a/c')], [], [], 'whole', 'chat-export', None, missing=['x.json'])
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
    store = next(s for s in corpus.stores() if s.pipeline == 'chat-capture' and s.provider == 'claude')
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


@check(tier='code', on=['src/main/corpus.py', 'src/main/pipeline'], says=(
    'store.held_twice_is_found',
    'store.surplus_is_found',
    'store.unit_names_its_kind',
))
def check_store(run) -> None:
    """A unit knows what it is called, and a unit another of its kind holds whole is found: over a scratch root, a session whose log is a prefix of the same
    session's under another project is contained, a memory equal to another's is
    identical, and what differs is neither."""
    import tempfile
    sys.path.insert(0, str(SRC / 'main'))
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


@check(tier='code', on=['src/main/corpus.py', 'src/main/pipeline/chat-export/atoms.py'], says=(
    'store.export_is_held_within_a_later_one',
))
def check_export_atoms(run) -> None:
    """An earlier export is held whole within a later one by its atoms: over a
    scratch root, an export whose conversations, memories and users are all among a later
    export's is contained, and one holding a message the later lacks is not; a memory state
    the deposits hold counts for nothing the export must still hold."""
    import json as json_
    import tempfile
    sys.path.insert(0, str(SRC / 'main'))
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
