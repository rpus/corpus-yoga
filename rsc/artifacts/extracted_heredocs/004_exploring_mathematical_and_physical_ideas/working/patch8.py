with open('/home/claude/paper0_v1.py', 'r') as f:
    content = f.read()

# Fix title in title page
old1 = 'story.append(P("Intuitionistic Logic is not (not!) Constructive:",title_s))'
new1 = 'story.append(P("Intuitionistic Logic is not Constructive",title_s))'

# Fix subtitle
old2 = 'story.append(P("Two Negations, the Boolean Collapse, and the Geometry of Opposition",sub_s))'
new2 = ('story.append(P("(as <b>not</b> is not <tt>not</tt>):",sub_s))\n'
        'story.append(P("Two Negations, the Boolean Collapse, and the Geometry of Opposition",\n'
        '               ParagraphStyle("sub2",fontName="Times-Italic",fontSize=9,leading=12,\n'
        '                              alignment=TA_CENTER,spaceAfter=6)))')

# Fix header
old3 = '"Intuitionistic Logic is not (not!) Constructive"'
new3 = '"Intuitionistic Logic is not Constructive"'

# Fix doc title metadata
old4 = 'title="Intuitionistic Logic is not (not!) Constructive"'
new4 = 'title="Intuitionistic Logic is not Constructive (as not is not not)"'

for old, new, label in [
    (old1, new1, "title page"),
    (old2, new2, "subtitle"),
    (old3, new3, "header"),
    (old4, new4, "metadata"),
]:
    if old in content:
        content = content.replace(old, new)
        print(f"Fixed: {label}")
    else:
        print(f"Not found: {label}")

with open('/home/claude/paper0_v1.py', 'w') as f:
    f.write(content)
print("Done.")