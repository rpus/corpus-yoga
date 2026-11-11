"""schema.py - the dev gate's checks of the schema families: layout, validity, versions, changelogs and verdict records."""
import json
from pathlib import Path

from gate import (
    DIAGNOSTIC_NAMES,
    PIPELINES,
    REPO_ROOT,
    RSC_SCHEMA,
    SRC,
    SRC_TEST_DIAGNOSTICS,
    _call_many,
    _diag_detail,
    _schema_families,
    _sorted_versions,
    check,
)
from latest import latest_file
import provider


@check(tier='schema', on=['rsc/schema', 'src/main', 'rsc/provider'], says=(
    'schema.family_mirrors_writer',
    'schema.pipeline_schema_placed',
))
def check_schema_layout(run) -> None:
    """A family's address under rsc/schema is its writer's under src/main, then the
    provider's name where the family's instances are one provider's, then the family: strip the family, strip a segment that is a row of rsc/provider/providers.csv,
    strip a leading `derived` - a tier of the schema tree alone, marking a family derived from
    upstream's schema rather than authored, whose writer is no tier of the code (issues/1047) -
    and what remains is a directory under src/main or nothing. Every pipeline's declared
    schema sits under rsc/schema/<pipeline>, at exactly one address."""
    providers = set(provider.provider_names())
    families = _schema_families()
    for key, d in sorted(families.items()):
        parts = key.split('/')[:-1]
        if parts and parts[-1] in providers:
            parts = parts[:-1]
        if parts[:1] == ['derived']:
            parts = parts[1:]
        writer = SRC / 'main' / '/'.join(parts) if parts else SRC / 'main'
        run(f'{key}: address mirrors its writer', writer.is_dir(),
            None if writer.is_dir() else
            f'src/main/{"/".join(parts)} is no directory - the family sits where no code writes against it; '
            f'git mv it under its writer\'s path (rsc/schema/WORKFLOW.md)',
            check='schema.family_mirrors_writer')
    for name, pipeline in sorted(PIPELINES.items()):
        for schema in pipeline.schemas:
            placed = f'{name}/{schema}' in families
            run(f'pipeline: {name}: {schema} sits under rsc/schema/{name}', placed,
                None if placed else
                f'no family at rsc/schema/{name}/{schema} - the pipeline declares a schema '
                f'that is not at its address',
                check='schema.pipeline_schema_placed')


@check(tier='schema', says=('schema.valid_json_with_schema',), on=['rsc/schema'])
def check_schema_validity(run) -> None:
    """Every version of every schema family parses and declares $schema — a property
    of the committed schema artifacts, not of any pipeline."""
    for schema_name, schema_dir in sorted(_schema_families().items()):
        for path in _sorted_versions(schema_dir):
            v = path.stem
            try:
                schema = json.loads(path.read_text())
                run(f'{schema_name}: valid JSON + $schema: {v}', '$schema' in schema,
                    'Missing $schema field' if '$schema' not in schema else None, check='schema.valid_json_with_schema')
            except json.JSONDecodeError as e:
                run(f'{schema_name}: valid JSON: {v}', False, str(e), check='schema.valid_json_with_schema')


@check(tier='schema', on=['rsc/schema', 'rsc/reference/JSONSchema'], says=(
    'schema.valid_against_meta_schema',
))
def check_schema_meta_validity(run) -> None:
    """Every house schema - each family's latest version -
    validates against the committed draft-04 meta-schema
    (rsc/reference/JSONSchema/draft-04/schema.json), the dialect every one of them
    declares, held as repo data: a property of the committed artifacts."""
    import jsonschema
    meta_path = REPO_ROOT / 'rsc' / 'reference' / 'JSONSchema' / 'draft-04' / 'schema.json'
    if not meta_path.is_file():
        run('schema: the draft-04 meta-schema is committed', False,
            f'{meta_path.relative_to(REPO_ROOT)} is absent', check='schema.valid_against_meta_schema')
        return
    validator = jsonschema.Draft4Validator(json.loads(meta_path.read_text()))
    targets = [(f'{name}: {latest.stem}', latest)
               for name, d in sorted(_schema_families().items()) if (latest := latest_file(d))]
    for label, path in targets:
        errors = sorted(validator.iter_errors(json.loads(path.read_text())), key=lambda e: list(e.path))
        detail = None
        if errors:
            first = errors[0]
            detail = (f'{path.relative_to(REPO_ROOT)} #/{"/".join(str(x) for x in first.path)}: {first.message[:160]}'
                      + (f' (+{len(errors) - 1} more)' if len(errors) > 1 else ''))
        run(f'{label}: valid against the draft-04 meta-schema', not errors, detail,
            check='schema.valid_against_meta_schema')


@check(tier='schema', says=('schema.single_version',), on=['rsc/schema'])
def check_schema_single_version(run) -> None:
    """Every schema family holds exactly one version file - the latest is the schema
    and the rest history: a mint renames the file in place, and a second
    v*.json beside it is a mint made as a copy beside its predecessor."""
    for schema_name, schema_dir in sorted(_schema_families().items()):
        versions = _sorted_versions(schema_dir)
        extra = [p.name for p in versions[:-1]]
        run(f'{schema_name}: one version file', not extra,
            None if not extra else
            f'{schema_dir.relative_to(REPO_ROOT)} also holds {", ".join(extra)} - the latest is the '
            f'schema and the rest history: git rm the rest (their narrative stays in the CHANGELOG)',
            check='schema.single_version')


@check(tier='schema', says=('schema.changelog_narrative', 'schema.changelog_no_todo'), on=['rsc/schema'])
def check_schema_changelogs(run) -> None:
    """Every schema family's CHANGELOG narrates every version, and no version carries
    TODO descriptions — properties of the committed artifacts, not of any pipeline.
    (Whether each version is registered in the validation matrix is the data gate's
    concern: corpus-yoga pipeline audit.)"""
    for schema_name, schema_dir in sorted(_schema_families().items()):
        changelog = schema_dir / 'CHANGELOG.md'
        changelog_text = changelog.read_text() if changelog.exists() else ''
        for path in _sorted_versions(schema_dir):
            v = path.stem
            run(f'{schema_name}: changelog_narrative: {v}',
                f'## {v}' in changelog_text,
                f'Add a ## {v} section to {changelog.relative_to(REPO_ROOT)}'
                if f'## {v}' not in changelog_text else None, check='schema.changelog_narrative')
            schema_text = path.read_text()
            run(f'{schema_name}: no_todo: {v}',
                '"TODO' not in schema_text,
                f'Replace TODO descriptions in {path.relative_to(REPO_ROOT)}'
                if '"TODO' in schema_text else None, check='schema.changelog_no_todo')


@check(tier='schema', says=('schema.has_versions', *DIAGNOSTIC_NAMES), on=['rsc/schema'])
def check_versioned_schema_diagnostics(run):
    all_diagnostics = sorted(SRC_TEST_DIAGNOSTICS.glob('*.py'))
    schema_skips    = {RSC_SCHEMA / p.name / family: skips
                       for p in PIPELINES.values() for family, skips in p.diagnostic_skip.items()}

    schema_dirs = _schema_families()
    # One jobs list across every family, one _call_many: a per-family dispatch
    # drains the pool at each family boundary, idling workers on every family's
    # tail (issues/472). The report below walks the families in this same enumeration
    # order, so the committed log cannot differ from the per-family loop's (L2).
    # A family's job count is None when it has no versions (reported as its own
    # failure) - an empty count means every diagnostic was skipped: report nothing.
    families = []
    jobs = []
    for schema_name in sorted(schema_dirs):
        schema_dir  = schema_dirs[schema_name]
        skip        = schema_skips.get(schema_dir, frozenset())
        # the latest version is the schema, the rest history (issues/557): diagnostics
        # judge the version that judges data; validity and the changelog still
        # hold every version, so the history stays parseable and narrated
        versions    = _sorted_versions(schema_dir)[-1:] if schema_dir else []
        diagnostics = [s for s in all_diagnostics if s.stem not in skip]
        if not versions:
            families.append((schema_name, schema_dir, None))
            continue
        family_jobs = [(script, version) for version in versions for script in diagnostics]
        families.append((schema_name, schema_dir, len(family_jobs)))
        jobs.extend(family_jobs)
    results = _call_many(jobs)
    cursor = 0
    for schema_name, schema_dir, count in families:
        run(f'{schema_name}: has versions', count is not None,
            None if count is not None else f'{schema_dir.relative_to(REPO_ROOT) if schema_dir else schema_name} has no v*.json files',
            check='schema.has_versions')
        if count is None:
            continue
        for (script, version), (passed, output) in zip(jobs[cursor:cursor + count],
                                                       results[cursor:cursor + count]):
            run(f'{schema_name}: {script.stem}: {version.stem}', passed,
                _diag_detail(output) if not passed else None, check=script.stem)
        cursor += count


@check(tier='code', on=['src/main/validate.py', 'src/test'], says=(
    'validate.undeclared_type_names_the_union',
))
def check_validate_verdict(run) -> None:
    """A verdict on a record whose discriminator no alternative admits names the union and
    the declared set, never an alternative chosen by the count of its faults."""
    import importlib
    import tempfile
    validate = importlib.import_module('validate')
    schema = {'$schema': 'http://json-schema.org/draft-04/schema#', 'type': 'array', 'items': {'$ref': '#/definitions/Record'},
              'definitions': {
                  'Record': {'oneOf': [{'$ref': '#/definitions/A'}, {'$ref': '#/definitions/B'}]},
                  'A': {'type': 'object', 'properties': {'type': {'enum': ['a']}, 'x': {}}, 'required': ['type', 'x'], 'additionalProperties': False},
                  'B': {'type': 'object', 'properties': {'type': {'enum': ['b']}, 'y': {}, 'z': {}}, 'required': ['type', 'y', 'z'], 'additionalProperties': False},
                  'T': {'type': 'object', 'properties': {'type': {'enum': ['t']}, 'content': {'type': 'array', 'items': {'$ref': '#/definitions/ContentBlock'}}},
                        'required': ['type', 'content'], 'additionalProperties': False},
                  'ContentBlock': {'oneOf': [{'$ref': '#/definitions/X'}, {'$ref': '#/definitions/Y'}]},
                  'X': {'type': 'object', 'properties': {'type': {'enum': ['x']}}, 'required': ['type'], 'additionalProperties': False},
                  'Y': {'type': 'object', 'properties': {'type': {'enum': ['y']}}, 'required': ['type'], 'additionalProperties': False},
                  'S': {'type': 'object', 'properties': {'category': {}}, 'required': ['category'], 'additionalProperties': False}}}
    schema['definitions']['Record']['oneOf'].append({'$ref': '#/definitions/T'})
    schema['definitions']['T']['properties']['stop'] = {'oneOf': [{'type': 'null'}, {'$ref': '#/definitions/S'}]}
    with tempfile.TemporaryDirectory() as scratch:
        s, d = Path(scratch) / 'schema.json', Path(scratch) / 'data.json'
        s.write_text(json.dumps(schema))
        d.write_text(json.dumps([{'type': 'c'}]))
        undeclared = validate.validate(str(d), str(s))
        d.write_text(json.dumps([{'type': 'b', 'y': 1}]))
        malformed = validate.validate(str(d), str(s))
        d.write_text(json.dumps([{'type': 't', 'content': [{'type': 'z'}]}]))
        nested = validate.validate(str(d), str(s))
        d.write_text(json.dumps([{'type': 't', 'content': [], 'stop': 'x'}]))
        unmatched = validate.validate(str(d), str(s))
    union = (undeclared[0] == "Validation error: type: 'c' is not a type the union declares - declared: ['a', 'b', 't']"
             and undeclared[1] == "Path: [0, 'type']" and undeclared[2] == 'Schema path: #/definitions/Record')
    run('validate: a record of a type no alternative declares is judged by the union, naming the declared set', union,
        None if union else f'the verdict read {undeclared}', check='validate.undeclared_type_names_the_union')
    selected = malformed[2] == 'Schema path: #/definitions/B' and "'z' is a required property" in malformed[0]
    run('validate: a record whose type one alternative declares is judged within that alternative', selected,
        None if selected else f'the verdict read {malformed}', check='validate.undeclared_type_names_the_union')
    # the reviewer's case (home-room, 2026-10-16, on pull/900): a record of a declared type
    # carrying a nested block of an undeclared type is judged at the nested union, never at
    # the record's by the accident that every discriminator is spelled type
    inner = (nested[0] == "Validation error: content/type: 'z' is not a type the union declares - declared: ['x', 'y']"
             and nested[1] == "Path: [0, 'content', 0, 'type']" and nested[2] == 'Schema path: #/definitions/ContentBlock')
    run('validate: a declared record carrying an undeclared nested type is judged at the nested union', inner,
        None if inner else f'the verdict read {nested}', check='validate.undeclared_type_names_the_union')
    # the reviewer's fourth case (home-room, 2026-10-16, on pull/900): a union whose
    # alternatives carry no discriminator - null or an object - given a value neither admits
    # is judged by the union naming its alternatives, never by the alternative with the
    # fewest faults, which no record and no schema selects
    none = (unmatched[0] == "Validation error: stop: matches none of: null, S" and unmatched[1] == "Path: [0, 'stop']"
            and unmatched[2] == 'Schema path: #/definitions/T/properties/stop')
    run('validate: a value no alternative of an undiscriminated union admits is judged by the union naming them', none,
        None if none else f'the verdict read {unmatched}', check='validate.undeclared_type_names_the_union')


@check(tier='code', on=['src/validation_matrix.py', 'src/main/validation_verdict.py', 'src/main/validate_versions.py', 'src/main/corpus.py'], says=(
    'validation.verdict_is_record',
))
def check_verdict_record(run) -> None:
    """A verdict is read from its record, never from the log's text: a red log whose
    inspection dumps a datum that carries the validator's own word must read red. The
    fixture is synthetic - a datum directory with one family, its latest version, a log
    that says 'Validation error' and then 'Valid!' inside the dumped instance, and beside
    it the record that says invalid; a log with no record is no row."""
    import tempfile
    from validation_matrix import rows_from_records
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        schema_root = root / 'rsc' / 'schema' / 'browser'
        (schema_root / 'claude' / 'apiConversation').mkdir(parents=True)
        (schema_root / 'claude' / 'apiConversation' / 'v1.json').write_text('{}')
        datum = root / 'tmp' / 'cache' / 'browser' / 'claude' / 'datum'
        log_dir = datum / 'validation' / 'apiConversation'
        log_dir.mkdir(parents=True)
        (log_dir / 'v1.log').write_text('2026-09-27T00:00:00+00:00\n'
                                         'datum.json: 3 lines, 40 bytes · sha256 aa\n'
                                         'v1.json: 2 bytes · sha256 bb\n'
                                         'Validation error: Additional properties are not allowed\n'
                                         '--- instance ---\n'
                                         "{\"text\": \"the validator ends with print('Valid!')\"}\n")
        rows = rows_from_records(datum, schema_root)
        run('validation: a log without a record is no row, whatever its text says', not rows,
            None if not rows else f'read {rows} from the log text alone', check='validation.verdict_is_record')
        (log_dir / 'v1.verdict.json').write_text('{"datum": "datum.json", "datum_sha256": "aa", "datum_bytes": 40, '
                                                  '"datum_lines": 3, "schema": "v1.json", "schema_sha256": "bb", '
                                                  '"version": "v1", "verdict": "invalid", "reason": "Validation error", '
                                                  '"at": "2026-09-27T00:00:00+00:00"}\n')
        rows = rows_from_records(datum, schema_root)
        got = rows.get(('apiConversation', '', 'v1'), ('?', 0))[0]
        run("validation: a red record reads red though the log's dumped instance says Valid!", got == '✗',
            None if got == '✗' else f'read {got} - the verdict came from the text, not the record', check='validation.verdict_is_record')


@check(tier='code', on=['src/main/cli/pipeline/tail.py', 'src/main/validate_versions.py', 'src/main/validate.py', 'src/main/validation_verdict.py'], says=(
    'pipeline.failing_is_keyed_by_datum',
    'validation.fail_atom_names_the_fault',
))
def check_failing_record(run) -> None:
    """A failing stage's record names each refused datum by its id with the fault beneath: the tail keys atoms by their subject, datums refused for one fault share
    one key, and no line is a placeholder; a validation's FAIL atom carries the fault's
    path, rule, schema node and log, and no line of it is cut with an ellipsis or an
    arrow."""
    import contextlib
    import importlib
    import io
    import tempfile
    tail = importlib.import_module('pipeline.tail')
    a, b = 'e2d2039d-b1e5-4691-99f9-f0629d13e243', '0a1b2c3d-0000-4000-8000-000000000000'
    rows = [('agent', f'FAIL: {a}: does not validate at latest v23'), ('agent', '  path: /11165/toolUseResult'),
            ('agent', '  log: v23.log'), ('agent', f'FAIL: {b}: does not validate at latest v23'),
            ('agent', '  path: /11165/toolUseResult'), ('agent', '  log: v23.log'),
            ('corpus', f'FAIL: {a}: agent/claude/session does not validate at latest v23 - a version is owed')]
    want = {'agent': {f'{a}, {b}': {'does not validate at latest v23': {'path': '/11165/toolUseResult', 'log': 'v23.log'}}},
            'corpus': {a: 'agent/claude/session does not validate at latest v23 - a version is owed'}}
    got = tail.grouped(rows)
    run('pipeline: the failing record keys each refused datum by its id, one key for one fault, the fault beneath', got == want,
        None if got == want else f'grouped as {got!r}', check='pipeline.failing_is_keyed_by_datum')
    validate_versions = importlib.import_module('validate_versions')
    with tempfile.TemporaryDirectory() as scratch:
        root = Path(scratch)
        schema_dir = root / 'schema'
        schema_dir.mkdir()
        (schema_dir / 'v1.json').write_text(json.dumps({'type': 'object', 'properties': {'turn': {'type': ['string', 'object']}}}))
        datum = root / 'datum.json'
        datum.write_text(json.dumps({'turn': [{'type': 'text', 'text': 'x' * 200}]}))
        log_dir = root / 'validation'
        said = io.StringIO()
        with contextlib.redirect_stdout(said):
            validate_versions.validate_versions(str(datum), str(schema_dir), str(log_dir), 'datum')
        lines = [line.strip() for line in said.getvalue().splitlines()]
        record = json.loads((log_dir / 'v1.verdict.json').read_text())
    beneath = {line.split(': ', 1)[0]: line.split(': ', 1)[1] for line in lines[1:] if ': ' in line}
    ok = (bool(lines) and lines[0] == 'FAIL: datum: does not validate at latest v1' and beneath.get('path') == '/turn'
          and beneath.get('schema') == '/properties/turn' and str(beneath.get('rule', '')).startswith('type ')
          and str(beneath.get('log', '')).endswith('v1.log') and not any(mark in said.getvalue() for mark in ('\u2026', '\u2192', '\u2014'))
          and record.get('path') == '/turn' and record.get('schema_path') == '/properties/turn')
    run('validation: a FAIL atom names the fault - its path, rule, schema node and log - and no line of it is cut or arrowed', ok,
        None if ok else f'printed {said.getvalue()!r}; the record holds {sorted(record)}', check='validation.fail_atom_names_the_fault')
