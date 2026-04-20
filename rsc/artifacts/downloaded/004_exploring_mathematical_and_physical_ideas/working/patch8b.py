with open('/home/claude/paper0_v1.py', 'r') as f:
    content = f.read()

old = '    title="Intuitionistic Logic is not Constructive",'
new = '    title="Intuitionistic Logic is not Constructive (as not is not not)",'

if old in content:
    content = content.replace(old, new)
    print("Metadata fixed.")
else:
    print("Not found.")

with open('/home/claude/paper0_v1.py', 'w') as f:
    f.write(content)