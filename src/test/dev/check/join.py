"""join.py - the dev gate's checks of the cross-family model: the join, its kinds and the table it obliges."""
import csv
import json
import re

from gate import (  # noqa: F401 - the gate's shared vocabulary
    REPO_ROOT,
    RSC_MODEL,
    _admits_instance_pointer,
    _check_csv_pointers,
    check,
    model_curation,
)


@check(tier='schema', on=['rsc/schema', 'rsc/model'], says=(
    'model.join_kind_declared',
    'model.join_pointers_valid',
))
def check_schema_join(run):
    join = RSC_MODEL / 'model_join.csv'
    if not join.exists():
        run('schema model_join.csv exists', False, check='model.join_pointers_valid')
        return
    kinds_table = RSC_MODEL / 'model_join_kinds.csv'
    declared_kinds = {r['kind'] for r in csv.DictReader(kinds_table.open())}
    unknown = [f'row {i}: {r["relationship"]!r}'
               for i, r in enumerate(csv.DictReader(join.open()), 2)
               if r['relationship'] not in declared_kinds]
    run('model_join: every relationship names a declared kind (rsc/model/model_join_kinds.csv)',
        not unknown, '; '.join(unknown[:4]) if unknown else None,
        check='model.join_kind_declared')
    fails: list[str] = []
    # One grammar, one base: every cell is a versioned family dir relative to the
    # repo root ('rsc/schema/pipeline/chat-export/claude/conversations#…', 'rsc/reference/mcp#…'),
    # resolved against its latest version or lineage (src/main/latest.py). No per-column
    # tribal knowledge to resolve a cell.
    _check_csv_pointers(join,
                        model_curation.JOIN_PATH_COLUMNS,
                        {c: REPO_ROOT for c in model_curation.JOIN_PATH_COLUMNS},
                        fails)
    run('schema model_join.csv: all pointers valid', not fails,
        '\n    '.join(fails[:5]) if fails else None, check='model.join_pointers_valid')


@check(tier='schema', says=('model.join_family_grammar',), on=['rsc/schema', 'rsc/model'])
def check_model_join_versions(run):
    """The versioned columns must use the de-versioned grammar — a family dir per
    cell ('<pipeline>/<family>#/definitions/…'), never a vN.json pin. A pinned cell
    would churn on every mint, and its bare filename names neither the family nor
    its pipeline, so a search for the family's references would miss it. check_schema_join resolves family dirs against
    their latest version, so currency is enforced by resolution, not by rewriting."""
    join = RSC_MODEL / 'model_join.csv'
    if not join.exists():
        return
    pins: list[str] = []
    with join.open() as fh:
        for i, row in enumerate(csv.DictReader(fh), 2):
            for col in model_curation.JOIN_PATH_COLUMNS:
                file_part = (row.get(col) or '').strip().partition('#')[0]
                if re.search(r'v\d+\.json$', file_part):
                    pins.append(f'row {i} {col}: {file_part}')
    run('model_join: de-versioned pointer grammar (family dirs, no vN.json pins)',
        not pins,
        '\n    '.join(pins[:5]) if pins else None, check='model.join_family_grammar')


@check(tier='schema', says=('model.table_valid',), on=['rsc/model'])
def check_model_table(run) -> None:
    """rsc/model/model.json is the table of documented shared types - a name, its
    description, its occurrences by family - and rsc/model/model.schema.json is
    the row shape (draft-04) every reader of the table relies on: the table
    validates against it, so a malformed entry fails by name."""
    import jsonschema
    table, schema = RSC_MODEL / 'model.json', RSC_MODEL / 'model.schema.json'
    validator = jsonschema.Draft4Validator(json.loads(schema.read_text()))
    errors = sorted(validator.iter_errors(json.loads(table.read_text())), key=lambda e: list(e.path))
    detail = None
    if errors:
        first = errors[0]
        detail = (f'{table.relative_to(REPO_ROOT)} #/{"/".join(str(x) for x in first.path)}: {first.message[:160]}'
                  + (f' ({len(errors)} errors)' if len(errors) > 1 else ''))
    run(f'model: {table.relative_to(REPO_ROOT)} validates against {schema.relative_to(REPO_ROOT)}', not errors, detail,
        check='model.table_valid')


@check(tier='schema', on=['rsc/schema', 'rsc/model', 'src'], says=(
    'model.occurrence_family_grammar',
    'model.occurrence_pointers_resolve',
    'model.occurrences_cover_edges',
))
def check_model_occurrences(run):
    """model.json's occurrence paths obey the de-versioned family-dir grammar
    model_join.csv earned (check_model_join_versions) and RESOLVE:
    each occurrences key is '<pipeline>/<family>' and each instance pointer must resolve against the
    family's LATEST version by walking the schema's structure. A mint that
    renames a documented field fails here, the model_join review prompt; one
    that keeps it costs nothing."""
    doc = json.loads((RSC_MODEL / 'model.json').read_text())
    fams = model_curation.latest_versions()
    pins, bad = [], []
    for tname, entry in doc.items():
        for key, pointers in entry.get('occurrences', {}).items():
            if re.search(r'v\d+\.json$', key.partition('#')[0]):
                pins.append(f'{tname}: {key}')
                continue
            latest = fams.get(key)
            if latest is None:
                bad.append(f'{tname}: no such family dir: {key}')
                continue
            schema = json.loads(latest.read_text())
            for ptr in pointers:
                if not _admits_instance_pointer(schema, ptr):
                    bad.append(f'{tname}: {key} {ptr} does not resolve against {latest.name}')
    run('model: occurrences use family-dir grammar (no vN.json pins)', not pins,
        '\n    '.join(pins[:5]) if pins else None, check='model.occurrence_family_grammar')
    run('model: occurrence pointers resolve against latest versions', not bad,
        '\n    '.join(bad[:5]) if bad else None, check='model.occurrence_pointers_resolve')
    # Completeness (issues/19 follow-up, the foolproof-index fix, user + reading-room):
    # grounds() needs one family to match, so a type can be documented with a
    # dressing missing and still ground — model.json would then answer "where does
    # this type occur" incompletely, the non-foolproof grep the account-uuid thread
    # exposed. Every DATA family a grounding edge asserts must be an occurrence, so
    # the index is the complete, reliable answer the four-dressing schemas cannot be.
    gaps = model_curation.coverage_gaps()
    run('model: documented types occur completely (occurrences cover their edges\' data families)',
        not gaps,
        '\n    '.join(f'{n}: grounding edge asserts {", ".join(f)} — not in occurrences'
                      for n, f in list(gaps.items())[:5]) if gaps else None, check='model.occurrences_cover_edges')


@check(tier='schema', on=['rsc/schema', 'rsc/model', 'src'], says=(
    'model.documented_type_grounded',
    'model.shared_type_disposed',
))
def check_model_obligations(run) -> None:
    """The blocking half of model.json's curate discipline, BOTH directions of the one
    grounding relation (model_curation.grounds — by containing-definition name,
    or by property trail for inline field types whose semantic name no schema
    definition can supply, e.g. UserUUID's account uuid):

    - edge→doc: every model_join edge whose relationship kind asserts ONE
      shared type (identical, snake_cased) is grounded by a documented entry or
      covered by a rejection in rsc/model/model_rejected.txt. One check per
      distinct shared type, so a regression names what it broke.
    - doc→edge: every documented type is grounded by >=1 obligating edge — no
      orphan documentation.

    Together: model.json documents exactly the shared types model_join asserts,
    minus rejections. GATES (schema tier): an edge is a human-asserted
    identity, and an undocumented asserted identity — or a documented type no
    edge asserts — is a defect, not a queue. The raw name scan is `corpus-yoga
    model`'s FAIL pointed at model_join, since a name_collision is a
    false friend no scan can tell from a shared type."""
    queue = model_curation.edge_queue()
    for names, rows in sorted(model_curation.shared_types().items(),
                              key=lambda kv: sorted(kv[0])):
        pending = queue.get(names)
        run(f'model: shared type disposed: {"/".join(sorted(names))}', not pending,
            None if not pending else
            f'model_join row(s) {", ".join(map(str, pending))} assert one shared type: '
            'document it in rsc/model/model.json or reject it in rsc/model/model_rejected.txt', check='model.shared_type_disposed')
    orphans = set(model_curation.orphan_entries())
    for name in sorted(model_curation.documented()):
        run(f'model: documented type grounded: {name}', name not in orphans,
            None if name not in orphans else
            'no model_join edge asserts this type: curate the asserting edge '
            '(relationship identical | snake_cased), or retire the entry', check='model.documented_type_grounded')


@check(tier='schema', says=('model.identity_holds',))
def check_model_identity(run) -> None:
    """Identity-class model_join edges hold at their families' latest versions: a one-sided mint that breaks an
    identical/snake_cased edge reds the dev gate until the edge is re-judged
    or the identity restored. Hermetic — schemas only, no corpus."""
    violations = model_curation.identity_violations()
    run('model: identity edges hold at latest', not violations,
        None if not violations else
        '; '.join(f'row {line} ({kind}): {cells}' for line, kind, cells in violations)
        + ' — re-judge the relationship kind (rsc/model/model_join_kinds.csv) '
          'or restore the identity in the schemas', check='model.identity_holds')
