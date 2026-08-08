#!/usr/bin/env python
"""
Add the export name as a tooltip (title attribute) to the engagement timeline heading.

Usage:
  update_export_tooltip.py <html_file> <export_name>
"""

import re
import sys

path, name = sys.argv[1], sys.argv[2]

with open(path) as f:
    html = f.read()

result = re.sub(
    r'(<h2\b[^>]*)>(Engagement timeline</h2>)',
    lambda m: f'{m.group(1)} title="{name}">{m.group(2)}',
    html
)

with open(path, 'w') as f:
    f.write(result)
