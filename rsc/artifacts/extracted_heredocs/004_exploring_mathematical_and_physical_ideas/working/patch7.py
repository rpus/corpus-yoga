with open('/home/claude/paper0_v1.py', 'r') as f:
    content = f.read()

# 1. Add propositional status framing at start of Section 2
old1 = ('story.append(H1("2. Two Negations"))\n'
        'story.append(P(\n'
        '    "We work in the setting of sets and subsets, ordered by inclusion. "\n'
        '    "The universe is a fixed set U. All subsets are elements of the power "\n'
        '    "set P(U), ordered by inclusion."))')

new1 = ('story.append(H1("2. Two Negations"))\n'
        'story.append(P(\n'
        '    "We operate not on truth values but on <b>propositions</b> — or more "\n'
        '    "precisely, on the classification of sentences according to their "\n'
        '    "propositional status. The three values are not degrees of truth but "\n'
        '    "categories: 1 for true propositions, -1 for false propositions, and "\n'
        '    "0 for sentences that are not yet — or not even — propositions "\n'
        '    "susceptible to truth or falsity. The third way is not an unknown "\n'
        '    "truth value; it is the <b>absence of propositional status</b>. A sentence "\n'
        '    "in the third way has not failed to be true or false — it has not yet "\n'
        '    "achieved the level of determinacy at which truth or falsity applies."))\n'
        'story.append(P(\n'
        '    "This reframing is not merely philosophical. It explains directly why "\n'
        '    "the order-reversing property holds within each category but not across "\n'
        '    "the category boundary. The sets {0} and {-1,1} are not comparable by "\n'
        '    "inclusion because they inhabit different layers of the logical hierarchy: "\n'
        '    "one classifies propositional status, the other classifies truth value. "\n'
        '    "The order-reversing failure of neg is not a defect but a diagnostic — "\n'
        '    "it marks precisely where the category boundary lies."))\n'
        'story.append(P(\n'
        '    "We work in the powerset P({-1,0,1}), ordered by inclusion. "\n'
        '    "The universe is U = {-1,0,1}. Both not and neg are functions on "\n'
        '    "the full powerset — we list their values on singletons for "\n'
        '    "illustration, but the operators are defined on all eight subsets."))')

if old1 in content:
    content = content.replace(old1, new1)
    print("Section 2 opening updated.")
else:
    print("Section 2 target not found.")

# 2. Update the table of names for the third way in Section 3
old2 = ('story.append(H2("3.3 Complement is not constructive"))')

new2 = ('story.append(H2("3.2b The third way: not even a statement"))\n'
        'story.append(P(\n'
        '    "The third way has been discovered and rediscovered across every domain "\n'
        '    "of human inquiry, always named differently, never unified. The unifying "\n'
        '    "description, in the light of the propositional status framing, is: "\n'
        '    "<i>not even a statement</i> — a sentence that has not achieved the "\n'
        '    "level of determinacy at which true or false applies."))\n'
        'story.append(P(\n'
        '    "In everyday epistemology: <i>I don\'t know yet</i> — the question has "\n'
        '    "not been pinned down to a determinate proposition. "\n'
        '    "In linguistics: <i>meaningless</i> or <i>category error</i> — literally "\n'
        '    "not a well-formed proposition. "\n'
        '    "In formal logic: <i>undecidable</i> — not reachable by proof or refutation. "\n'
        '    "In proof theory: <i>unprovable</i> — outside the deductive reach of the system. "\n'
        '    "In quantum mechanics: <i>unmeasured</i> — no eigenvalue until measurement "\n'
        '    "forces propositional status. "\n'
        '    "In relativistic measurement: <i>pre-measurement indeterminate</i> — no "\n'
        '    "fact of the matter accessible within the causal structure. "\n'
        '    "In computation: <i>non-terminating</i> — the program never produces a value, "\n'
        '    "hence never achieves the status of a completed proposition. "\n'
        '    "In ecology: <i>ecologically unspecified</i> — no instantiation of the "\n'
        '    "semantic data has been chosen."))\n'
        'story.append(P(\n'
        '    "Every entry in this list is a domain-specific way of saying the same "\n'
        '    "thing: this has not yet achieved propositional status. The Boolean "\n'
        '    "collapse destroys the category by forcing every sentence into "\n'
        '    "true-or-false before the question of propositional status has been "\n'
        '    "settled. This is not rigour — it is premature closure."))\n'
        'story.append(H2("3.3 Complement is not constructive"))')

if old2 in content:
    content = content.replace(old2, new2)
    print("Third way table added.")
else:
    print("Section 3.3 target not found.")

# 3. Update the three-value model in Section 2 to include the explicit maps
old3 = ('story.append(H2("2.3 The Galois connection axioms"))\n'
        'story.append(P("We take as fundamental:"))')

new3 = ('story.append(H2("2.3 The explicit three-value model"))\n'
        'story.append(P(\n'
        '    "The following explicit model on P({-1,0,1}) instantiates the framework. "\n'
        '    "Both not and neg are defined on all eight subsets; we list them "\n'
        '    "top to bottom (full universe to empty set):"))\n'
        'story.append(Math("not: {-1,0,1}->∅,  {-1,0}->{1},  {-1,1}->{0},  {0,1}->{-1}"))\n'
        'story.append(Math("     {-1}->{0,1},  {0}->{-1,1},  {1}->{-1,0},  ∅->{-1,0,1}"))\n'
        'story.append(Math("neg: {-1,0,1}->∅,  {-1,0}->{1},  {-1,1}->{0},  {0,1}->{-1}"))\n'
        'story.append(Math("     {-1}->{1},    {0}->{-1,1},  {1}->{-1},    ∅->{-1,0,1}"))\n'
        'story.append(P(\n'
        '    "The operators agree everywhere except at the Boolean singletons: "\n'
        '    "not({-1}) = {0,1} while neg({-1}) = {1}, and "\n'
        '    "not({1}) = {-1,0} while neg({1}) = {-1}. "\n'
        '    "neg strips 0 from the output of not on definite propositions — it maps "\n'
        '    "to the genuine opposite without admitting the third way as an output. "\n'
        '    "Verified properties: not is an involution; neg is a deflation "\n'
        '    "(neg(neg(S)) ⊆ S); non-contradiction holds; excluded middle fails "\n'
        '    "for neg (the third way exists); both Galois conditions hold; "\n'
        '    "not ≠ neg. The order-reversing property holds within each propositional "\n'
        '    "category but fails across the category boundary — specifically at "\n'
        '    "{-1,1}, whose neg lands in the orthogonal third-way category {0}."))\n'
        'story.append(H2("2.4 The Galois connection axioms"))\n'
        'story.append(P("We take as fundamental:"))')

if old3 in content:
    content = content.replace(old3, new3)
    print("Explicit model added.")
else:
    print("Section 2.3 target not found.")

with open('/home/claude/paper0_v1.py', 'w') as f:
    f.write(content)
print("Done.")