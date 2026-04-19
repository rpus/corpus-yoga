#!/usr/bin/env python
# Reads JSON from a file (argv[1]) or stdin, writes aligned table JSON to stdout.
import json, sys

def fmt_aligned(header, rows, depth):
    pad = '  ' * depth
    inner = pad + '  '
    all_rows = [header] + rows
    n = max((len(r) for r in all_rows), default=0)
    widths = [max(len(json.dumps(r[i])) for r in all_rows if i < len(r)) for i in range(n)]

    def fmt_row(row):
        cells = []
        for i, v in enumerate(row):
            s = json.dumps(v)
            if i < len(row) - 1:
                s = s.rjust(widths[i]) if isinstance(v, int) else s.ljust(widths[i])
            cells.append(s)
        return '[' + ', '.join(cells) + ']'

    rows_body = ('[]' if not rows else
                 '[\n' + ',\n'.join(inner + '  ' + fmt_row(r) for r in rows) + '\n' + inner + ']')
    return fmt_row, rows_body

def fmt_data_table(header, rows, depth, note=None):
    pad = '  ' * depth
    inner = pad + '  '
    fmt_row, rows_body = fmt_aligned(header, rows, depth)
    note_line = f',\n{inner}"note": {json.dumps(note)}' if note is not None else ''
    return (f'{{\n'
            f'{inner}"columns":\n'
            f'{inner}  {fmt_row(header)},\n'
            f'{inner}"rows": {rows_body}'
            f'{note_line}\n'
            f'{pad}}}')

def fmt(obj, depth=0):
    pad = '  ' * depth
    if isinstance(obj, dict):
        if 'columns' in obj and 'rows' in obj:
            return fmt_data_table(obj['columns'], obj['rows'], depth, obj.get('note'))
        parts = [f'{pad}  {json.dumps(k)}: {fmt(v, depth + 1)}' for k, v in obj.items()]
        return '{\n' + ',\n'.join(parts) + '\n' + pad + '}'
    elif isinstance(obj, list):
        if not obj:
            return '[]'
        if all(isinstance(x, list) for x in obj):
            return '[\n' + ',\n'.join(pad + '  ' + json.dumps(x) for x in obj) + '\n' + pad + ']'
        return json.dumps(obj)
    return json.dumps(obj)

src = open(sys.argv[1]) if len(sys.argv) > 1 else sys.stdin
print(fmt(json.load(src)))
