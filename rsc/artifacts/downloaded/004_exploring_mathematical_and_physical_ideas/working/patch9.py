with open('/home/claude/paper0_v1.py', 'r') as f:
    content = f.read()

# Replace the Galois connection axioms section with the correct lean axioms
old = ('story.append(H2("2.4 The Galois connection axioms"))\n'
       'story.append(P("We take as fundamental:"))\n'
       'story.append(Math("A  ⊆  not(neg(A))"))\n'
       'story.append(Math("neg(not(A))  ⊆  A"))\n'
       'story.append(P(\n'
       '    "The first: nothing is its own antipode — no element is maximally distant "\n'
       '    "from the set it belongs to. The second: the antipode of the complement "\n'
       '    "is already inside A — the deepest interior of A in the antipodal sense "\n'
       '    "is contained in A. These two axioms are not independent: given that both "\n'
       '    "operators are order-reversing involutions, each implies the other. "\n'
       '    "Together they express precisely that not and neg form a "\n'
       '    "<b>Galois connection</b> — neg is the right adjoint of not in the "\n'
       '    "poset P(U) ordered by inclusion."))')

new = ('story.append(H2("2.4 Axioms for neg"))\n'
       'story.append(P(\n'
       '    "The axioms for neg are lean and motivated directly by the propositional "\n'
       '    "status framing. We do not stipulate order-reversal — for not, it is a "\n'
       '    "theorem derivable from the complement structure; for neg, it may or may "\n'
       '    "not hold depending on the model, and its failure is diagnostic rather "\n'
       '    "than pathological."))\n'
       'story.append(P("<b>Axiom 1 — Deflation:</b>"))\n'
       'story.append(Math("neg(neg(A))  ⊆  A"))\n'
       'story.append(P(\n'
       '    "Applying the antipodal map twice returns something smaller than or equal "\n'
       '    "to where you started. neg is not an involution — that would force the "\n'
       '    "Boolean collapse (see theorem below). The deflation measures how far "\n'
       '    "neg is from being an involution, which is how far the space is from "\n'
       '    "being Boolean."))\n'
       'story.append(P("<b>Axiom 2 — Non-contradiction:</b>"))\n'
       'story.append(Math("A  ∩  neg(A)  =  ∅"))\n'
       'story.append(P(\n'
       '    "Nothing is its own antipode. Opposition is genuine — a proposition and "\n'
       '    "its opposite cannot coexist. This is the minimum requirement for neg to "\n'
       '    "mean what opposition ordinarily means."))\n'
       'story.append(P("<b>Axiom 3 — The third way (necessary):</b>"))\n'
       'story.append(Math("A  ∪  neg(A)  ⊊  U  for some A"))\n'
       'story.append(P(\n'
       '    "This is the axiomatic commitment that distinguishes two-negation logic "\n'
       '    "from the Boolean collapse. The third way is not an accidental gap — it "\n'
       '    "is stipulated. Any model in which A ∪ neg(A) = U for all A is the "\n'
       '    "Boolean collapse and is explicitly excluded. Opposition is incomplete: "\n'
       '    "not every sentence has a determinate opposite, because not every "\n'
       '    "sentence has achieved propositional status."))\n'
       'story.append(P("<b>Axiom 4 — The Galois connection with not:</b>"))\n'
       'story.append(Math("A  ⊆  not(neg(A))"))\n'
       'story.append(Math("neg(not(A))  ⊆  A"))\n'
       'story.append(P(\n'
       '    "The first: a proposition lies outside the antipode of its own antipodal "\n'
       '    "neighbourhood. The second: the antipode of the complement is already "\n'
       '    "inside A. Together these connect neg to not in the precise sense of a "\n'
       '    "Galois connection — neg is the right adjoint of not in the poset P(U) "\n'
       '    "ordered by inclusion. Note that these axioms, combined with Axiom 1, "\n'
       '    "are not independent — each Galois condition implies the other given "\n'
       '    "the deflation. The connection is the formal expression of the "\n'
       '    "syntax-semantics adjunction: not is syntactic and free, neg is "\n'
       '    "semantic and costly."))\n'
       'story.append(H2("2.5 The Boolean collapse theorem"))\n'
       'story.append(P(\n'
       '    "<b>Theorem.</b> There cannot exist two distinct operators, both satisfying "\n'
       '    "the Galois connection axioms, with not an involution and neg also an "\n'
       '    "involution. If neg is an involution, the Galois connection forces "\n'
       '    "neg = not — the Boolean collapse. Equivalently: if neg is an involution, "\n'
       '    "then A ∪ neg(A) = U for all A, violating Axiom 3."))\n'
       'story.append(P(\n'
       '    "This theorem gives Axiom 3 its teeth. Without it, the Boolean collapse "\n'
       '    "is merely a special case. With it, the Boolean collapse is provably "\n'
       '    "excluded from the general framework — it requires dropping Axiom 3, "\n'
       '    "not merely specialising parameters. The two psychopathies identified "\n'
       '    "in Section 3 are now precisely the two ways of violating the axioms: "\n'
       '    "asserting neg = not (dropping the distinctness that Axiom 3 requires), "\n'
       '    "or asserting neg is an involution (which the theorem shows forces the "\n'
       '    "same collapse)."))')

if old in content:
    content = content.replace(old, new)
    print("Axioms section replaced.")
else:
    print("Axioms section not found.")
    idx = content.find("2.4 The Galois connection axioms")
    print(repr(content[idx-50:idx+100]))

# Fix the Boolean collapse section which referred to order-reversal
old2 = ('story.append(H2("2.5 Structural consequences"))\n'
        'story.append(P(\n'
        '    "The compositions not ∘ neg and neg ∘ not become, respectively, a "\n'
        '    "closure operator and an interior operator on P(U). Their difference — "\n'
        '    "the gap between closure and interior — is the boundary in the "\n'
        '    "topological sense: the region where the two negations fail to agree, "\n'
        '    "the locus of genuine logical indeterminacy. In the Boolean case this "\n'
        '    "boundary is empty. In richer spaces it is where the interesting "\n'
        '    "content lives."))')

new2 = ('story.append(H2("2.6 Structural consequences"))\n'
        'story.append(P(\n'
        '    "The compositions not ∘ neg and neg ∘ not become, respectively, a "\n'
        '    "closure operator and an interior operator on P(U). Their difference — "\n'
        '    "the gap between closure and interior — is the boundary in the "\n'
        '    "topological sense: the region where the two negations fail to agree, "\n'
        '    "the locus of genuine logical indeterminacy. In the Boolean case this "\n'
        '    "boundary is empty — Axiom 3 is violated and the third way disappears. "\n'
        '    "In the general case it is where the interesting content lives."))\n'
        'story.append(P(\n'
        '    "Order-reversal for not is a theorem, not an axiom: it follows from "\n'
        '    "the complement structure of the powerset lattice. For neg, order-reversal "\n'
        '    "holds within each propositional category but fails across the category "\n'
        '    "boundary — specifically where neg maps a Boolean set to the third-way "\n'
        '    "category. This failure is not a defect but a theorem about the model: "\n'
        '    "it marks precisely where the propositional status boundary lies, and "\n'
        '    "where the Boolean order has no jurisdiction."))')

if old2 in content:
    content = content.replace(old2, new2)
    print("Structural consequences updated.")
else:
    print("Structural consequences not found.")

with open('/home/claude/paper0_v1.py', 'w') as f:
    f.write(content)
print("Done.")