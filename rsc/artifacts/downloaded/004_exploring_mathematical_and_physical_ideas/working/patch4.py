with open('/home/claude/paper0_v1.py', 'r') as f:
    content = f.read()

old = ('story.append(H2("1.2 What the name should be"))')

new = ('story.append(H2("1.1b The naming failure runs deeper"))\n'
       'story.append(P(\n'
       '    "The catastrophe of the naming runs deeper than it first appears. "\n'
       '    "At least three routes out of the Boolean collapse present themselves "\n'
       '    "before any formal logic is encountered. First, the child\'s response: "\n'
       '    "<i>I don\'t know yet.</i> This is the most naively intuitive epistemic "\n'
       '    "state of any finite agent in a world where information arrives over time. "\n'
       '    "It is more intuitive than classical logic, more intuitive than so-called "\n'
       '    "intuitionistic logic, and it is the actual starting point for any honest "\n'
       '    "reasoner. Temporal logic, epistemic logic, and probability theory are all "\n'
       '    "formalisms built around this observation — none of them are called "\n'
       '    "intuitionistic."))\n'
       'story.append(P(\n'
       '    "Second, Gödel\'s incompleteness theorems — the mathematical third way. "\n'
       '    "There exist propositions that are neither provable nor refutable within "\n'
       '    "a given sufficiently rich system. This is not a philosophical programme "\n'
       '    "or a failure of nerve; it is a theorem. The Boolean collapse is provably "\n'
       '    "unavailable from the inside of any system powerful enough to be "\n'
       '    "interesting. Gödel\'s result is more radical than Brouwer\'s: it shows "\n'
       '    "that the two-colour geometry fails mathematically, not merely "\n'
       '    "philosophically."))\n'
       'story.append(P(\n'
       '    "Third, Turing\'s halting problem — the computational third way. "\n'
       '    "There exist computations whose termination cannot be decided in advance. "\n'
       '    "The answer to \'does this program halt?\' is not true or false but "\n'
       '    "<i>undecidable</i> — and undecidability is not ignorance but a provable "\n'
       '    "structural feature of computation. Turing shows that the Boolean collapse "\n'
       '    "fails computationally: any system powerful enough to be interesting is "\n'
       '    "powerful enough to escape the two-colour geometry."))\n'
       'story.append(P(\n'
       '    "All three of these — I don\'t know yet, Gödel incompleteness, Turing "\n'
       '    "undecidability — are more intuitive than anything in Brouwer\'s "\n'
       '    "constructivist programme, and all three motivate the same conclusion: "\n'
       '    "the Boolean collapse is the special case, not the general condition. "\n'
       '    "Yet none of them are called intuitionistic. The name was captured by "\n'
       '    "one specific philosophical escape route, making all the others invisible "\n'
       '    "and making the collapse itself look like the natural default. "\n'
       '    "It is catastrophically badly named."))\n'
       'story.append(H2("1.2 What the name should be"))')

if old in content:
    content = content.replace(old, new)
    with open('/home/claude/paper0_v1.py', 'w') as f:
        f.write(content)
    print("Done.")
else:
    print("Not found.")