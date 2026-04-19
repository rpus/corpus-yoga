import json, sys

def pretty_table(json_str):
    data = json.loads(json_str)
    cols = data['columns']
    rows = data['rows']

    def cell_str(v):
        return json.dumps(v, ensure_ascii=False)

    col_widths = [len(json.dumps(c)) for c in cols]
    for row in rows:
        for i, v in enumerate(row):
            col_widths[i] = max(col_widths[i], len(cell_str(v)))

    padded_headers = [json.dumps(c).ljust(col_widths[i]) for i, c in enumerate(cols)]
    columns_line = '  [' + ', '.join(padded_headers) + ']'

    padded_rows = []
    for row in rows:
        cells = []
        for i, v in enumerate(row):
            s = cell_str(v)
            cells.append(s.rjust(col_widths[i]) if isinstance(v, (int, float)) else s.ljust(col_widths[i]))
        padded_rows.append('  [' + ', '.join(cells) + ']')

    return (
        '{"columns":\n' +
        columns_line + ',\n' +
        '"rows":[\n' +
        ',\n'.join(padded_rows) + '\n' +
        ']}'
    )

# Usage: python3 pretty_tables.py input.json
# Or pipe: cat input.json | python3 pretty_tables.py
if __name__ == '__main__':
    src = open(sys.argv[1]).read() if len(sys.argv) > 1 else sys.stdin.read()
    print(pretty_table(src.strip()))
