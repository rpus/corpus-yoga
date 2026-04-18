"""
Three-value logic: powerset model enumeration.
Universe U = {-1, 0, 1}
Powerset P(U) has 8 elements, ordered top to bottom (by inclusion, descending).
We define candidate not and neg functions on P(U) and check properties.
"""

from itertools import chain, combinations

# Universe
U_list = [-1, 0, 1]
U = frozenset(U_list)

# Generate powerset, ordered top to bottom (descending by size, then lex)
def powerset(s):
    s = list(s)
    return list(chain.from_iterable(combinations(s, r) for r in range(len(s)+1)))

all_sets = [frozenset(s) for s in powerset(U_list)]
# Order: descending by size, then by sorted tuple for consistency
all_sets.sort(key=lambda s: (-len(s), sorted(s)))

def fmt(s):
    """Format a frozenset for display."""
    if not s:
        return "∅"
    return "{" + ",".join(str(x) for x in sorted(s)) + "}"

def subset(a, b):
    """Check a ⊆ b."""
    return a <= b

# ── Define candidate operators ────────────────────────────────────────────────

# not: full set-theoretic complement in U
def op_not(s):
    return U - s

# neg candidates to explore:

# neg_A: full complement (same as not) — the Boolean collapse
def neg_A(s):
    return U - s

# neg_B: "antipodal" — maps each set to U minus s, but with 0 treated specially
# Specifically: neg maps s to the complement of s in {-1,1} union,
# plus {0} if 0 was NOT in s, minus {0} if 0 was in s.
# i.e. neg "flips" the Boolean content and also flips membership of 0.
def neg_B(s):
    bool_part = frozenset({-1,1}) - s  # complement of Boolean content
    zero_part = frozenset({0}) if 0 not in s else frozenset()
    return bool_part | zero_part

# neg_C: antipodal on values, 0 maps to full Boolean pair
# Singletons: {-1}->{0,1}, {0}->{-1,1}, {1}->{-1,0}
# Extended by: neg(S) = union of neg of singletons? No — let's define via complement
# neg_C: complement in U (same as not) for non-zero sets,
# but for sets containing only 0, map to {-1,1}
# Actually let's try: neg(S) = U \ S for all S (same as not — neg_A)
# and neg_D: the "pointwise antipodal" extension
# neg({x}) = U \ {x} for singletons, extended as:
# neg(S) = intersection of neg({x}) for x in S
def neg_D(s):
    if not s:
        return U
    result = U
    for x in s:
        result = result & (U - frozenset({x}))
    return result

# neg_E: union extension of pointwise antipodal
# neg(S) = union of neg({x}) for x in S = union of (U\{x}) for x in S
def neg_E(s):
    if not s:
        return U
    result = frozenset()
    for x in s:
        result = result | (U - frozenset({x}))
    return result

# neg_F: complement restricted — neg(S) = (U\S) but 0 always excluded from neg output
# i.e. neg only takes values in {-1,1}
def neg_F(s):
    return (U - s) - frozenset({0})

# ── Property checkers ─────────────────────────────────────────────────────────

def check_involution(op, name, sets):
    return all(op(op(s)) == s for s in sets)

def check_deflation(op, name, sets):
    return all(subset(op(op(s)), s) for s in sets)

def check_order_reversing(op, name, sets):
    for a in sets:
        for b in sets:
            if subset(a, b):
                if not subset(op(b), op(a)):
                    return False
    return True

def check_noncontradiction(op_not, op_neg, sets):
    return all((s & op_neg(s)) == frozenset() for s in sets)

def check_excluded_middle(op_not, op_neg, sets):
    return all((s | op_neg(s)) == U for s in sets)

def check_galois_1(op_not, op_neg, sets):
    # A ⊆ not(neg(A))
    return all(subset(s, op_not(op_neg(s))) for s in sets)

def check_galois_2(op_not, op_neg, sets):
    # neg(not(A)) ⊆ A
    return all(subset(op_neg(op_not(s)), s) for s in sets)

# ── Print table ───────────────────────────────────────────────────────────────

def print_table(neg, neg_name):
    print(f"\n{'='*80}")
    print(f"neg = {neg_name}")
    print(f"{'='*80}")
    
    # Header
    cols = ["id", "not(id)", "neg(id)", "not(not)", "neg(neg)", "not(neg)", "neg(not)"]
    col_w = 12
    print("".join(c.ljust(col_w) for c in cols))
    print("-" * (col_w * len(cols)))
    
    for s in all_sets:
        n = op_not(s)
        g = neg(s)
        nn = op_not(op_not(s))
        gg = neg(neg(s))
        ng = op_not(neg(s))
        gn = neg(op_not(s))
        
        row = [fmt(s), fmt(n), fmt(g), fmt(nn), fmt(gg), fmt(ng), fmt(gn)]
        
        # Mark deflation violations
        deflation_ok = subset(gg, s)
        row[4] = fmt(gg) + ("" if deflation_ok else "!")
        
        print("".join(r.ljust(col_w) for r in row))
    
    print()
    
    # Property checks
    props = [
        ("not is involution",      check_involution(op_not, "not", all_sets)),
        ("neg is involution",      check_involution(neg, "neg", all_sets)),
        ("neg is deflation",       check_deflation(neg, "neg", all_sets)),
        ("not order-reversing",    check_order_reversing(op_not, "not", all_sets)),
        ("neg order-reversing",    check_order_reversing(neg, "neg", all_sets)),
        ("non-contradiction",      check_noncontradiction(op_not, neg, all_sets)),
        ("excluded middle (neg)",  check_excluded_middle(op_not, neg, all_sets)),
        ("Galois 1: S⊆not(neg(S))",check_galois_1(op_not, neg, all_sets)),
        ("Galois 2: neg(not(S))⊆S",check_galois_2(op_not, neg, all_sets)),
    ]
    
    for name, result in props:
        tick = "✓" if result else "✗"
        print(f"  {tick} {name}")

# ── Run all candidates ────────────────────────────────────────────────────────

candidates = [
    (neg_A, "Full complement (= not): Boolean collapse"),
    (neg_B, "Flip Boolean + flip 0 membership"),
    (neg_D, "Intersection of pointwise antipodals"),
    (neg_E, "Union of pointwise antipodals"),
    (neg_F, "Complement restricted to {-1,1}"),
]

print("THREE-VALUE POWERSET MODEL")
print(f"Universe U = {fmt(U)}")
print(f"\nnot(S) = U \\ S  (full complement, always)\n")
print("Powerset elements (top to bottom):")
for s in all_sets:
    print(f"  {fmt(s)}")

for neg, name in candidates:
    print_table(neg, name)
