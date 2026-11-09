"""upstream.py - the dev gate's checks of what arrives from outside: grammars, references and the mcp schema."""
import csv
import hashlib
import json
import os
import shutil
import subprocess

from gate import (
    REPO_ROOT,
    check,
)
from latest import lineages  # noqa: E402 - on the paths gate.py sets
import send  # noqa: E402 - on the paths gate.py sets
import tier  # noqa: E402 - on the paths gate.py sets
import grammar as grammar_module  # noqa: E402 - on the paths gate.py sets
import mcp_extraction  # noqa: E402 - on the paths gate.py sets
import mcp_face  # noqa: E402 - on the paths gate.py sets
import mcp_factoring  # noqa: E402 - on the paths gate.py sets


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
    need the parser, and corpus-yoga status sync generates it. The
    currency half needs the tool (antlr4 from antlr4-tools in the venv, java), whose
    first use fetches the tool jar, a send: CORPUS_YOGA_NO_SEND=1 skips that half and so does
    a machine without the tool - the label is CONSTANT and the result passes on
    presence alone, as mcp.reproducible does, so the report is byte-identical
    everywhere."""
    for project in grammar_module.projects():
        have = grammar_module.held(project)
        ok, detail = bool(have), None
        if not have:
            detail = (f'src/gen/grammar/{project.name} is absent - corpus-yoga grammar sync generates it from '
                      f'rsc/rpus/grammar/{project.name} (corpus-yoga status sync does so with the rest)')
        elif grammar_module.tool() and (want := grammar_reading(project)) is not None:
            differing = sorted(n for n in set(have) | set(want) if have.get(n) != want.get(n))
            ok = not differing
            detail = None if ok else (f'src/gen/grammar/{project.name}: {", ".join(differing)} differ from what '
                                      f'antlr4 {grammar_module.TOOL_VERSION} generates - corpus-yoga grammar sync regenerates')
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
    Currency against upstream is not held here - it is `corpus-yoga reference`'s
    report, a send, and `corpus-yoga reference sync` is the fetch."""
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
                         'corpus-yoga reference sync fetches it' for d in unheld]),
            check='reference.lineage_declared')
        for row in rows:
            path = project / row['lineage'] / row['file']
            rel = path.relative_to(REPO_ROOT)
            local = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
            run(f'reference: {rel} verbatim (bytes hash to the pinned SHA256)', local == row['sha256'],
                None if local == row['sha256'] else
                (f'{rel} is absent - corpus-yoga reference sync fetches it' if local is None else
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
    rsc/schema/mcp/mcpMessage version must be byte-identical to what
    corpus-yoga mcp sync generates from the committed schema.ts and the family's
    tables (mcp.factoring_current), and every definition of upstream's schema.json -
    the witness, never a source - must equal its house counterpart flattened and
    normalized, the declared additions set back (mcp.factoring_agrees); every held
    lineage's schema.ts must parse (mcp.lineages_parse)."""
    target = mcp_factoring.latest_version(mcp_factoring.FAMILY_DIR)
    if not target:
        run('mcp: rsc/schema/mcp/mcpMessage has a version', False,
            'corpus-yoga mcp sync derives v1.json', check='mcp.factoring_current')
        return
    rel = target.relative_to(REPO_ROOT)
    try:
        wanted = mcp_factoring.current_text()
    except AssertionError as e:
        run(f'mcp: {target.stem} derivable from the snapshot', False, str(e), check='mcp.factoring_current')
        return
    have = target.read_text()
    run(f'mcp: {target.stem} current with the snapshot', have == wanted,
        None if have == wanted else
        f'{rel} differs from what schema.ts generates - corpus-yoga mcp sync prints the diff and mints the next version; write its changelog section and commit',
        check='mcp.factoring_current')
    _, snap = mcp_factoring.snapshot()
    bad = mcp_factoring.disagreements(json.loads(have), snap, mcp_factoring.additions(), mcp_factoring.generated().constants)
    run(f'mcp: {target.stem} flattens to the snapshot', not bad,
        '\n    '.join(bad[:5]) if bad else None, check='mcp.factoring_agrees')
    import jsonschema
    meta = json.loads((REPO_ROOT / 'rsc' / 'reference' / 'JSONSchema' / 'draft-04' / 'schema.json').read_text())
    for which in mcp_face.FACES:
        detail = None
        try:
            derived = mcp_face.face(json.loads(have), which)
            errors = sorted(jsonschema.Draft4Validator(meta).iter_errors(derived), key=lambda e: list(e.path))
            if errors:
                detail = f'{which} face: #/{"/".join(str(x) for x in errors[0].path)}: {errors[0].message[:160]}'
        except (mcp_factoring.Conflict, AssertionError, KeyError) as e:
            detail = f'{which} face: cannot derive from {rel} ({e})'
        run(f'mcp: the {which} face derives from {target.stem} and is valid draft-04', detail is None, detail, check='mcp.faces_derivable')
    for lineage in lineages(mcp_factoring.SNAPSHOT_DIR):
        ts = lineage / 'schema.ts'
        rel = ts.relative_to(REPO_ROOT)
        detail = None
        try:
            mcp_extraction.parsed(ts.read_text(), str(rel))
        except (mcp_extraction.ParseRefused, mcp_extraction.ParserAbsent) as refused:
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
