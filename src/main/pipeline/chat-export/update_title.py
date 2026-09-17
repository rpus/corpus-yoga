#!/usr/bin/env python
"""
Update the HTML <title> to reflect the conversation corpus date range and count.

Usage:
  update_title.py <html_file> <conversations_json>
"""

import json
import re
import sys
from datetime import datetime

path, conv_path = sys.argv[1], sys.argv[2]

with open(conv_path) as f:
    data = json.load(f)

dates = sorted(c['created_at'] for c in data)
t0, t1 = (datetime.fromisoformat(d.replace('Z', '+00:00')) for d in (dates[0], dates[-1]))
count = len(data)

if t0.year == t1.year:
    date_range = (t0.strftime('%B %Y') if t0.month == t1.month
                  else f"{t0.strftime('%B')}–{t1.strftime('%B %Y')}")
else:
    date_range = f"{t0.strftime('%B %Y')}–{t1.strftime('%B %Y')}"

title = f'Conversation corpus — {count} chats, {date_range}'

with open(path) as f:
    html = f.read()

with open(path, 'w') as f:
    f.write(re.sub(r'<title>.*?</title>', f'<title>{title}</title>', html))

print(f'  title: {title}')
