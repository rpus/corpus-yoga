"""
reply_shape.py - the shape the indexing capture asks the API to return for a table, the table it
reads back, and why a stored reading fails its family (issues/1161).

    reply_shape.py schema <family> <columns-json> [<column>=<json-schema>]...
        the schema sent as output_config.format's: {"rows": [{<column>: ..., ...}, ...]}, each column
        the family's own - its row's item at the column's place, in the family's latest version -
        keeping only what structured outputs accept; a column asked for otherwise than it is
        stored is given its shape as <column>=<json-schema>
    reply_shape.py table <columns-json>
        the reply on stdin, {"rows": [{...}, ...]}, as the {"columns", "rows"} table the capture writes
    reply_shape.py fault <file> <schema>
        where the stored file first fails the schema, its column named: rows/0/count fails type
        "integer", holding a string
"""
import json
import sys
from pathlib import Path
import tier  # the repository root, which corpus-yoga hands every run (issues/1173)

REPO = tier.REPO

KEPT = ('type', 'enum', 'const', 'description')   # what structured outputs accept of a column's schema; the family judges the rest after


def latest(family: str) -> Path:
    versions = sorted((REPO / 'rsc' / 'schema' / 'indexing' / family).glob('v*.json'), key=lambda p: int(p.stem[1:]))
    if not versions:
        sys.exit(f'reply_shape: no version of the indexing family {family}')
    return versions[-1]


def resolve(node: dict, schema: dict) -> dict:
    while '$ref' in node:
        node = schema['definitions'][node['$ref'].rsplit('/', 1)[-1]]
    return node


def row_items(schema: dict) -> list:
    """The row's items, in column order: the items of the array the table's rows hold."""
    for definition in schema['definitions'].values():
        rows = definition.get('properties', {}).get('rows')
        if rows and 'columns' in definition.get('properties', {}):
            return resolve(rows['items'], schema)['items']
    sys.exit('reply_shape: the family defines no table of columns and rows')


def shape(family: str, columns: list[str], given: dict[str, dict]) -> dict:
    schema = json.loads(latest(family).read_text())
    items = row_items(schema)
    properties = {}
    for place, column in enumerate(columns):
        if column in given:
            properties[column] = given[column]
        else:
            properties[column] = {k: v for k, v in resolve(items[place], schema).items() if k in KEPT}
    return {'type': 'object', 'additionalProperties': False, 'required': ['rows'],
            'properties': {'rows': {'type': 'array', 'items': {'type': 'object', 'additionalProperties': False,
                                                               'required': columns, 'properties': properties}}}}


def fault(file: str, schema_file: str) -> str:
    import validate   # the repository's one validator
    found = validate.fault(file, schema_file)
    if found is None:
        return 'nothing'
    steps = list(found['steps'])
    columns = json.loads(Path(file).read_text()).get('columns', [])
    if len(steps) >= 3 and steps[0] == 'rows' and isinstance(steps[2], int) and steps[2] < len(columns):
        steps[2] = columns[steps[2]]
    said = '/'.join(str(step) for step in steps) or 'the root'
    if found['rule']:
        said += f' fails {found["rule"]}'
    return f'{said}, holding {found["holds"]}' if found.get('holds') else said


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[0] == 'schema':
        given = {}
        for word in argv[3:]:
            column, _, said = word.partition('=')
            given[column] = json.loads(said)
        print(json.dumps(shape(argv[1], json.loads(argv[2]), given)))
        return 0
    if len(argv) == 2 and argv[0] == 'table':
        columns = json.loads(argv[1])
        reply = json.load(sys.stdin)
        print(json.dumps({'columns': columns, 'rows': [[row[column] for column in columns] for row in reply['rows']]}))
        return 0
    if len(argv) == 3 and argv[0] == 'fault':
        print(fault(argv[1], argv[2]))
        return 0
    print(f'usage: {Path(__file__).resolve().relative_to(tier.REPO)} schema <family> <columns-json> [<column>=<json-schema>]... | table <columns-json> | fault <file> <schema>', file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
