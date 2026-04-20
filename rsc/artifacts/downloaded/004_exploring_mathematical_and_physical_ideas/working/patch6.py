with open('/home/claude/paper0_v1.py', 'r') as f:
    content = f.read()

old = ('story.append(P(\n'
       '    "The reader who finds the logical argument of this paper compelling is "\n'
       '    "invited to follow it wherever it leads. The landscape is larger than it "\n'
       '    "appears from the entrance, and the view from the other side of the "\n'
       '    "correction is considerably clearer."))')

new = ('story.append(P(\n'
       '    "The reader who finds the logical argument of this paper compelling is "\n'
       '    "invited to follow it wherever it leads. The landscape is larger than it "\n'
       '    "appears from the entrance, and the view from the other side of the "\n'
       '    "correction is considerably clearer."))\n'
       'story.append(P(\n'
       '    "The correction described in this paper required no new mathematics. "\n'
       '    "It required only noticing, carefully, that a choice was being made "\n'
       '    "where none appeared to be — and asking what would happen if the choice "\n'
       '    "were made differently. The answer, it turns out, is: quite a lot."))')

if old in content:
    content = content.replace(old, new)
    with open('/home/claude/paper0_v1.py', 'w') as f:
        f.write(content)
    print("Done.")
else:
    print("Not found.")