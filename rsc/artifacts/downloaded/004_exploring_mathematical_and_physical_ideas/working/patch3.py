with open('/home/claude/paper1_v4.py', 'r') as f:
    content = f.read()

old = ('and the Boolean collapse can no longer be sustained."))')

new = ('and the Boolean collapse can no longer be sustained. '
       'The common political heuristic — my enemy\'s enemy is my friend — '
       'is precisely this error stated as a decision rule: it computes the '
       'complement of the complement, which is the identity in any Boolean '
       'geometry, and mistakes it for the antipode of the antipode, which '
       'requires the full metric of the space."))')

if old in content:
    content = content.replace(old, new)
    print("Enemy's enemy added.")
else:
    print("Enemy target not found.")

old2 = ('story.append(H2("2.2 The Galois connection axioms"))')

new2 = ('story.append(P('
        '"These examples also illuminate a curious misnomer. Intuitionistic logic — '
        'named for Brouwer\'s constructivist programme — is in practice the '
        'counter-intuitive logic: it is the Boolean collapse, the conflation of '
        'complement with antipode, that feels natural and obvious. The richer '
        'geometry, in which the two negations come apart, requires actively '
        'resisting the first intuition. Gödel, whose double-negation translation '
        'showed that classical logic embeds into intuitionistic logic rather than '
        'the other way around, would likely have agreed: the so-called intuitionistic '
        'logic is the stronger and more discriminating one. We have preferred '
        'throughout to call it two-negation logic, which has the virtue of '
        'describing what it actually is."))\n'
        'story.append(H2("2.2 The Galois connection axioms"))')

if old2 in content:
    content = content.replace(old2, new2)
    print("Misnomer paragraph added.")
else:
    print("Section 2.2 target not found.")

with open('/home/claude/paper1_v4.py', 'w') as f:
    f.write(content)
print("Done.")