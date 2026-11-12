"""upstream.py - the dev gate's checks of what arrives from outside: grammars, references and the mcp schema."""
import csv
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

from gate import (
    REPO_ROOT,
    check,
)
from latest import lineages
import send
import tier
import grammar as grammar_module
import extraction
import face
import factoring


def grammar_reading(project) -> dict | None:
    """What antlr4 generates from the project now, run under the grammar noun's declaration,
    whose send the tool's first use is; None where the send is refused."""
    held = os.environ.get(tier.DECLARATION)
    os.environ[tier.DECLARATION] = send.dispatched('src/main/cli/grammar/grammar.json')
    try:
        return grammar_module.generated(project)
    except send.SendRefused:
        return None
    finally:
        if held is None:
            os.environ.pop(tier.DECLARATION)
        else:
            os.environ[tier.DECLARATION] = held


@check(tier='schema', on=['rsc/rpus/grammar', 'src/main/grammar', 'src/gen/grammar'], says=(
    'grammar.parser_current',
))
def check_grammar(run) -> None:
    """Every parser under src/gen/grammar/<project>/ (machine-local, gitignored) is
    present and, where the tool is present, what antlr4 generates from
    rsc/rpus/grammar/<project>/ now. Absence fails by name - the mcp checks
    need the parser, and corpus-yoga status satisfy generates it. The
    currency half needs the tool (antlr4 from antlr4-tools in the venv, java), whose
    first use fetches the tool jar, a send: CORPUS_YOGA_NO_SEND=1 skips that half and so does
    a machine without the tool - the label is CONSTANT and the result passes on
    presence alone, as mcp.reproducible does, so the report is byte-identical
    everywhere."""
    for project in grammar_module.projects():
        have = grammar_module.held(project)
        ok, detail = bool(have), None
        if not have:
            detail = (f'src/gen/grammar/{project.name} is absent - corpus-yoga grammar generate generates it from '
                      f'rsc/rpus/grammar/{project.name} (corpus-yoga status satisfy does so with the rest)')
        elif grammar_module.tool() and (want := grammar_reading(project)) is not None:
            differing = sorted(n for n in set(have) | set(want) if have.get(n) != want.get(n))
            ok = not differing
            detail = None if ok else (f'src/gen/grammar/{project.name}: {", ".join(differing)} differ from what '
                                      f'antlr4 {grammar_module.TOOL_VERSION} generates - corpus-yoga grammar generate regenerates')
        run(f'grammar: {project.name}: the parser is generated and what its grammar generates', ok, detail,
            check='grammar.parser_current')


@check(tier='schema', on=['rsc/reference'], says=(
    'reference.lineage_changelog',
    'reference.lineage_declared',
    'reference.provenance_declared',
    'reference.verbatim',
))
def check_reference(run) -> None:
    """Every upstream reference artefact under rsc/reference is what its
    project's provenance.csv pins, hermetically: the committed bytes hash to the
    pinned SHA256; every lineage directory is declared and every declared lineage
    held; and every lineage's CHANGELOG.md carries a section per pin its rows name.
    Currency against upstream is not held here - `corpus-yoga reference fetch` records
    what upstream publishes, and `corpus-yoga reference` reads that record."""
    root = REPO_ROOT / 'rsc' / 'reference'
    for project in sorted(p for p in root.iterdir() if p.is_dir()):
        name = project.name
        provenance = project / 'provenance.csv'
        rows = list(csv.DictReader(provenance.open(newline=''))) if provenance.is_file() else []
        run(f'reference: {name}: provenance.csv pins its files', bool(rows),
            None if rows else f'add {provenance.relative_to(REPO_ROOT)} (lineage, file, url, pin, sha256)',
            check='reference.provenance_declared')
        held = [d.name for d in lineages(project)]
        declared = sorted({r['lineage'] for r in rows})
        undeclared = [d for d in held if d not in declared]
        unheld = [d for d in declared if d not in held]
        run(f'reference: {name}: every lineage directory is declared and every declared lineage held',
            not undeclared and not unheld,
            None if not undeclared and not unheld else
            '; '.join([f'{project.relative_to(REPO_ROOT)}/{d} has no provenance.csv row' for d in undeclared]
                      + [f'provenance.csv names {d} but {project.relative_to(REPO_ROOT)}/{d}/schema.json is absent - '
                         'corpus-yoga reference fetch records it under tmp/reference/fetch, and a commit copies it in' for d in unheld]),
            check='reference.lineage_declared')
        for row in rows:
            path = project / row['lineage'] / row['file']
            rel = path.relative_to(REPO_ROOT)
            local = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
            run(f'reference: {rel} verbatim (bytes hash to the pinned SHA256)', local == row['sha256'],
                None if local == row['sha256'] else
                (f'{rel} is absent - corpus-yoga reference fetch records it under tmp/reference/fetch, and a commit copies it in' if local is None else
                 f'{rel} hashes {local}, provenance.csv pins {row["sha256"]} - the committed file is not the pinned upstream file'),
                check='reference.verbatim')
        for lineage in declared:
            changelog = project / lineage / 'CHANGELOG.md'
            text = changelog.read_text() if changelog.is_file() else ''
            missing = sorted({r['pin'] for r in rows if r['lineage'] == lineage and f'## {r["pin"]}' not in text})
            run(f'reference: {name}/{lineage}: changelog carries a section per pin', changelog.is_file() and not missing,
                None if changelog.is_file() and not missing else
                (f'{changelog.relative_to(REPO_ROOT)} is absent' if not changelog.is_file() else
                 f'{changelog.relative_to(REPO_ROOT)} has no section ' + ', '.join(f'`## {pin}`' for pin in missing)),
                check='reference.lineage_changelog')


@check(tier='schema', on=['rsc/reference/mcp', 'rsc/schema/mcp', 'src/main/mcp', 'src/gen/grammar'], says=(
    'mcp.faces_derivable',
    'mcp.factoring_agrees',
    'mcp.factoring_current',
    'mcp.lineages_parse',
))
def check_mcp_factoring(run) -> None:
    """The house MCP factoring is a committed derivation: the latest
    rsc/schema/mcp/<lineage>/mcpMessage version must be byte-identical to what
    corpus-yoga mcp derive generates from the committed schema.ts and the family's
    tables (mcp.factoring_current), and every definition of upstream's schema.json -
    the witness, never a source - must equal its house counterpart flattened and
    normalized, the declared additions set back (mcp.factoring_agrees); every held
    lineage's schema.ts must parse (mcp.lineages_parse)."""
    target = factoring.latest_version(factoring.FAMILY_DIR)
    if not target:
        run('mcp: rsc/schema/mcp/<lineage>/mcpMessage has a version', False,
            'corpus-yoga mcp derive derives v1.json', check='mcp.factoring_current')
        return
    rel = target.relative_to(REPO_ROOT)
    try:
        wanted = factoring.current_text()
    except AssertionError as e:
        run(f'mcp: {target.stem} derivable from the snapshot', False, str(e), check='mcp.factoring_current')
        return
    have = target.read_text()
    run(f'mcp: {target.stem} current with the snapshot', have == wanted,
        None if have == wanted else
        f'{rel} differs from what schema.ts generates - corpus-yoga mcp derive prints the diff and mints the next version; write its changelog section and commit',
        check='mcp.factoring_current')
    _, snap = factoring.snapshot()
    bad = factoring.disagreements(json.loads(have), snap, factoring.additions(), factoring.generated().constants)
    run(f'mcp: {target.stem} flattens to the snapshot', not bad,
        '\n    '.join(bad[:5]) if bad else None, check='mcp.factoring_agrees')
    import jsonschema
    meta = json.loads((REPO_ROOT / 'rsc' / 'reference' / 'JSONSchema' / 'draft-04' / 'schema.json').read_text())
    for which in face.FACES:
        detail = None
        try:
            derived = face.face(json.loads(have), which)
            errors = sorted(jsonschema.Draft4Validator(meta).iter_errors(derived), key=lambda e: list(e.path))
            if errors:
                detail = f'{which} face: #/{"/".join(str(x) for x in errors[0].path)}: {errors[0].message[:160]}'
        except (factoring.Conflict, AssertionError, KeyError) as e:
            detail = f'{which} face: cannot derive from {rel} ({e})'
        run(f'mcp: the {which} face derives from {target.stem} and is valid draft-04', detail is None, detail, check='mcp.faces_derivable')
    for lineage in lineages(factoring.SNAPSHOT_DIR):
        ts = lineage / 'schema.ts'
        rel = ts.relative_to(REPO_ROOT)
        detail = None
        try:
            extraction.parsed(ts.read_text(), str(rel))
        except (extraction.ParseRefused, extraction.ParserAbsent) as refused:
            detail = str(refused)
        run(f'mcp: {rel} parses through the house TypeScript grammar', detail is None, detail, check='mcp.lineages_parse')


@check(tier='schema', says=('mcp.reproducible',), on=['rsc/reference/mcp', 'src/main/mcp'])
def check_mcp_reproducible(run) -> None:
    """The mcp snapshot's schema.json is what upstream's own generator makes of the
    committed schema.ts: src/main/mcp/reproduce.sh fetches upstream at the
    pinned commit, runs its generator unchanged in a node container and diffs the
    result against the committed file. Two sends (a git fetch, a docker run), so
    CORPUS_YOGA_NO_SEND=1 skips it - and so does a machine whose docker daemon is not
    reachable: the label is CONSTANT and the result passes when the run did not
    happen, as check_reference's currency probes do, so the committed report is
    byte-identical on a machine that cannot run it."""
    script = REPO_ROOT / 'src' / 'main' / 'mcp' / 'reproduce.sh'
    docker = shutil.which('docker')
    daemon = bool(docker) and subprocess.run([docker, 'info'], capture_output=True).returncode == 0
    ok, detail = True, None
    if daemon:
        # A git hook exports GIT_DIR and its kin; stripped here as well as in the script,
        # so the protection does not depend on any script the gate runs remembering it. The
        # script runs under the declaration whose sends it makes, and a refused send is a skip.
        env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        env[tier.DECLARATION] = send.dispatched('src/main/cli/mcp/reproduce.json')
        proc = subprocess.run([str(script)], capture_output=True, text=True, cwd=REPO_ROOT, env=env)
        ok = proc.returncode in (0, send.REFUSED_STATUS)
        if not ok:
            lines = [l for l in (proc.stdout + proc.stderr).splitlines() if l.strip()]
            detail = '\n    '.join(lines[-12:])
    run("mcp: schema.json reproduces from schema.ts through upstream's generator", ok, detail,
        check='mcp.reproducible')


@check(tier='schema', on=['rsc/reference', 'rsc/schema/mcp', 'src/main/mcp', 'src/main/reference', 'src/main/cli/reference', 'src/main/derivation.schema.json'], says=(
    'mcp.derivation_declared',
    'mcp.upstream_as_fetched_is_judged',
    'reference.status_reads_its_fetch',
))
def check_upstream_chain(run) -> None:
    """The mcp derivation is declared in one file, src/main/mcp/derivation.json - the lineage it
    reads, the parser it needs, the family and cache it writes, its witness and its arbiter
    (issues/1053) - and the family stands at the lineage's address, its latest changelog section
    naming the upstream commit (issues/1055). Upstream reaches a room by `corpus-yoga reference
    fetch`, into tmp/reference/fetch; the reference's status reads that record and sends nothing,
    and the mcp status judges upstream's schema.json as fetched against the committed version
    (issues/1054). The fixtures are synthetic: a project and a fetch record under a temporary root."""
    import importlib.util
    import tempfile
    import jsonschema
    def loaded(name: str, path: Path):
        spec = importlib.util.spec_from_file_location(name, path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    declared_at, schema_at = REPO_ROOT / 'src/main/mcp/derivation.json', REPO_ROOT / 'src/main/derivation.schema.json'
    why = None
    if not declared_at.is_file() or not schema_at.is_file():
        why = f'{"src/main/mcp/derivation.json" if not declared_at.is_file() else "src/main/derivation.schema.json"} is absent'
    else:
        declared = json.loads(declared_at.read_text())
        errors = sorted(jsonschema.Draft4Validator(json.loads(schema_at.read_text())).iter_errors(declared), key=lambda e: list(e.path))
        lineage = declared.get('lineage', '')
        def at(path: str) -> Path:
            return REPO_ROOT / path.replace('<lineage>', lineage)
        family = at(declared.get('writes', [''])[0])
        latest = factoring.latest_version(family) if family.is_dir() else None
        section = ''
        if latest is not None:
            text = (family / 'CHANGELOG.md').read_text()
            section = text.split(f'## {latest.stem}', 1)[-1].split('\n## ', 1)[0] if f'## {latest.stem}' in text else ''
        why = (f'#/{"/".join(str(x) for x in errors[0].path)}: {errors[0].message[:160]}' if errors
               else f'{declared["reads"]} is no file at lineage {lineage}' if not at(declared['reads']).is_file()
               else f'{declared["witness"]} is no file at lineage {lineage}' if not at(declared['witness']).is_file()
               else f'{family.relative_to(REPO_ROOT)} holds no version' if latest is None
               else f'the derivation writes {factoring.FAMILY_DIR.relative_to(REPO_ROOT)}, where the declaration says {family.relative_to(REPO_ROOT)}' if factoring.FAMILY_DIR != family
               else f'the derivation reads {factoring.schema_ts().relative_to(REPO_ROOT)}, where the declaration says {at(declared["reads"]).relative_to(REPO_ROOT)}' if factoring.schema_ts() != at(declared['reads'])
               else f'the changelog section of {latest.stem} does not name the upstream commit {factoring.provenance()["commit"]}' if factoring.provenance()['commit'] not in section
               else None)
    run('mcp: the derivation is declared in src/main/mcp/derivation.json, and reads, writes and is recorded as it declares', why is None, why,
        check='mcp.derivation_declared')

    reference = loaded('reference_noun', REPO_ROOT / 'src/main/reference/reference.py')
    read = getattr(reference, 'drift', None)
    verbs = sorted(d.stem for d in (REPO_ROOT / 'src/main/cli/reference').glob('*.json') if d.stem != 'reference')
    sends = json.loads((REPO_ROOT / 'src/main/cli/reference/reference.json').read_text()).get('sends')
    with tempfile.TemporaryDirectory() as tmp:
        project, fetched = Path(tmp) / 'held' / 'p', Path(tmp) / 'fetch' / 'p'
        project.mkdir(parents=True)
        fetched.mkdir(parents=True)
        header = '"lineage","file","url","pin","sha256"\n'
        (project / 'provenance.csv').write_text(header + '"2026-01-01","schema.json","u","a","aaaa"\n')
        unfetched = read(project, fetched) if callable(read) else 'no drift(project, fetched)'
        (fetched / 'fetched.csv').write_text(header + '"2026-01-01","schema.json","u","b","bbbb"\n"2026-02-02","schema.json","u","c","cccc"\n')
        found = read(project, fetched) if callable(read) else None
    same = (callable(read) and unfetched is None and found == {'2026-01-01/schema.json': 'drifted - upstream hashes bbbb, provenance.csv pins aaaa',
                                                               '2026-02-02/schema.json': 'missing'}
            and verbs == ['fetch'] and not sends)
    run("reference: its status reads what the last fetch recorded against provenance.csv, and sends nothing; fetch is its one verb", same,
        None if same else 'src/main/reference/reference.py has no drift(project, fetched)' if not callable(read)
        else f'unfetched reads {unfetched!r}; fetched reads {found!r}; the verbs are {verbs}; the status declares sends {sorted(sends or {})}',
        check='reference.status_reads_its_fetch')

    mcp = loaded('mcp_noun', REPO_ROOT / 'src/main/mcp/mcp.py')
    judge = getattr(mcp, 'as_fetched', None)
    target = factoring.latest_version(factoring.FAMILY_DIR)
    judged = None
    if callable(judge) and target is not None:
        have, (_path, witness) = json.loads(target.read_text()), factoring.snapshot()
        moved = json.loads(json.dumps(witness))
        holder = next(key for key in ('definitions', '$defs') if key in moved)
        name = sorted(moved[holder])[0]
        moved[holder][name] = {'type': 'string', 'description': 'changed upstream'}
        with tempfile.TemporaryDirectory() as tmp:
            agreeing, differing = Path(tmp) / 'agreeing.json', Path(tmp) / 'differing.json'
            agreeing.write_text(json.dumps(witness))
            differing.write_text(json.dumps(moved))
            judged = (judge(have, agreeing), judge(have, differing))
    held = judged is not None and isinstance(judged[0], str) and getattr(judged[1], 'FAIL', None) is not None
    run("mcp: upstream's schema.json as fetched is judged against the committed version - agreeing, or a finding", held,
        None if held else 'src/main/mcp/mcp.py has no as_fetched(have, path)' if not callable(judge) else f'judged {judged!r}'[:300],
        check='mcp.upstream_as_fetched_is_judged')
