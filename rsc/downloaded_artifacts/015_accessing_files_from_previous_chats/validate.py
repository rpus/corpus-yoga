# brew install python
# python3 -m venv ~/venvs/general

'''
source ~/venvs/general/bin/activate
# pip install jsonschema

for f in *.json; do python "../Yoga/src/validate.py" "$f" "../Yoga/rsc/schema/${f%.json}.json" > "../Yoga/gen/validation/${f%.json}.txt"; done

python ../Yoga/src/validate.py conversations.json ../Yoga/rsc/schema/conversations.json > ../Yoga/gen/validation/conversations.txt
# Path: [1, 'chat_messages', 1, 'content', 0]
# jq 'getpath([1,"chat_messages",1,"content",0])' conversations.json
deactivate
'''

import os
import sys
import json
import jsonschema
import datetime

def load_and_report(path):
    size = os.path.getsize(path)
    with open(path) as f:
        lines = f.readlines()
    data = json.loads(''.join(lines))
    print(f'{path}: {len(lines):,} lines, {size:,} bytes')
    return data

if len(sys.argv) != 3:
    print(f'Usage: python {sys.argv[0]} <data.json> <schema.json>')
    sys.exit(1)

print(f'{datetime.datetime.now().isoformat(timespec="seconds")}')

data   = load_and_report(sys.argv[1])
schema = load_and_report(sys.argv[2])

try:
    jsonschema.Draft4Validator(schema).validate(data)
    print('Valid!')
except jsonschema.ValidationError as e:
    print(f'Validation error: {e.message}')
    print(f'Path: {list(e.absolute_path)}')
except jsonschema.SchemaError as e:
    print(f'Schema error: {e.message}')
