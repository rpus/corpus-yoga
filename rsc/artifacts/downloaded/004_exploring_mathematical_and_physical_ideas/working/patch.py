with open('paper1_v4.py', 'r') as f:
    content = f.read()

old = 'and we recover classical logic. In richer spaces they come apart."))'

new = ('and we recover classical logic. In richer spaces they come apart. '
       'This distinction has immediate cultural force: in a two-colour political '
       'geometry, complement and antipode are structurally indistinguishable — '
       'not merely confused but provably identical, since a two-element set admits '
       'only one involution. The two-party system does not merely encourage the '
       'conflation of everyone opposed to one\'s opponents with everyone who shares '
       'one\'s values; it forecloses the distinction entirely. Political coalitions '
       'united only by a common opponent compute the complement when they require '
       'the antipode. Complement is broader than antipode — and the difference '
       'becomes visible, often painfully, the moment the opponent is removed and '
       'the Boolean collapse can no longer be sustained."))')

if old in content:
    content = content.replace(old, new)
    with open('paper1_v4.py', 'w') as f:
        f.write(content)
    print("Done.")
else:
    print("Not found.")