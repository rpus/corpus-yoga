#!/usr/bin/env python
"""
Replace an inlined JSON block in an HTML file.

Looks for <!-- key.json:begin/end --> markers first; falls back to matching
the <script id="key"> tag directly (for sections without markers).

Usage:
  inject.py <html_file> <key> <json_file>
"""

import re
import sys

path, key, json_path = sys.argv[1], sys.argv[2], sys.argv[3]

with open(json_path) as f:
    content = f.read()
with open(path) as f:
    html = f.read()

begin = f'  <!-- {key}.json:begin -->'
end   = f'  <!-- {key}.json:end -->'

if begin in html:
    result = re.sub(
        re.escape(begin) + r'.*?' + re.escape(end),
        lambda _: (f'  <!-- {key}.json:begin -->\n'
                   f'  <script id="{key}" type="application/json">\n'
                   + content +
                   f'\n  </script>\n'
                   f'  <!-- {key}.json:end -->'),
        html, flags=re.DOTALL)
else:
    result = re.sub(
        r'(<script id="' + re.escape(key) + r'"[^>]*>).*?(</script>)',
        lambda m: m.group(1) + '\n' + content + '\n  ' + m.group(2),
        html, flags=re.DOTALL)

with open(path, 'w') as f:
    f.write(result)
