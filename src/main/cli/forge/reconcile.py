"""reconcile.py — the forge's declared merge settings against the live ones.

stdin is the live repository json (gh api repos/{owner}/{repo}); argv[1] is
src/main/cli/forge/forge.csv; argv[2] is the default branch's protection json
(gh api repos/{owner}/{repo}/branches/<branch>/protection), `{}` where the branch
is not protected, absent or empty where it was not read. One row per declared
setting, OK or DRIFT, each DRIFT carrying its own gh remedy. A row named
`protection.<field>` is the default branch's (issues/623): the forge sets a
protection whole, so every drifted protection row carries the one call that sets
every declared field. forge.sh relays the rows verbatim; the
judgment lives in the csv, never in a wrapper — and this face runs in the
venv like every .py (issues/478), never under a PATH python.
"""
import csv
import json
import sys
from pathlib import Path
import facts  # the one face a sentence is said through (issues/909)



def norm(value) -> str:
    return 'true' if value is True else 'false' if value is False else str(value)


PROTECTION = 'protection.'
OWED = ('required_status_checks', 'enforce_admins', 'required_pull_request_reviews', 'restrictions')   # the fields the forge refuses a protection without; null where undeclared


def main() -> None:
    live = json.load(sys.stdin)
    slug = live.get('full_name') or '{owner}/{repo}'
    rows = list(csv.DictReader(open(sys.argv[1])))
    read = sys.argv[2] if len(sys.argv) > 2 else ''
    protection = json.loads(read) if read else None
    declared = {row['setting'][len(PROTECTION):]: row['value'] for row in rows if row['setting'].startswith(PROTECTION)}
    fields = {**{field: 'null' for field in OWED}, **declared}
    protect = ('gh api -X PUT repos/' + slug + '/branches/' + str(live.get('default_branch')) + '/protection '
               + ' '.join(f'-F {field}={value}' for field, value in fields.items()))
    for row in rows:
        key, want = row['setting'], row['value']
        if key.startswith(PROTECTION):
            if protection is None:
                print('UNVERIFIED', key, facts.phrase("the default branch's protection was not read"), '', sep='\t')
                continue
            held = protection.get(key[len(PROTECTION):])
            got = norm(held.get('enabled')) if isinstance(held, dict) else 'unprotected'
            remedy = protect
        else:
            got = norm(live.get(key))
            remedy = 'gh api -X PATCH repos/' + slug + ' ' + ('-F' if want in ('true', 'false') else '-f') + ' ' + key + '=' + want
        if got == want:
            print('OK', key, want, '', sep='\t')
        else:
            print('DRIFT', key, facts.phrase('declared {want}, live {got}', want=want, got=got), remedy, sep='\t')


if __name__ == '__main__':
    main()
