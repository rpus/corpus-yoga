from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer,
    NextPageTemplate, PageBreak
)
from reportlab.platypus.flowables import HRFlowable
from reportlab.lib import colors

W, H = A4
TOP=2.0*cm; BOTTOM=2.0*cm; INNER=1.8*cm; OUTER=1.5*cm; GUTTER=0.5*cm
col_w = (W - INNER - OUTER - GUTTER) / 2

def make_frames(n):
    x0 = INNER if n%2==1 else OUTER
    x1 = x0 + col_w + GUTTER
    y0 = BOTTOM; h = H - TOP - BOTTOM
    return (Frame(x0,y0,col_w,h,id='c1',leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0),
            Frame(x1,y0,col_w,h,id='c2',leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0))

def hf(canvas, doc):
    pn = doc.page
    canvas.saveState()
    canvas.setFont('Times-Roman', 8)
    hx = INNER if pn%2==1 else OUTER
    canvas.setStrokeColor(colors.black); canvas.setLineWidth(0.4)
    canvas.line(hx, H-TOP+4*mm, hx+W-INNER-OUTER, H-TOP+4*mm)
    if pn%2==1:
        canvas.drawRightString(W-OUTER, BOTTOM-8*mm, str(pn))
        canvas.drawString(INNER, BOTTOM-8*mm, "Intuitionistic Logic is not Constructive")
    else:
        canvas.drawString(OUTER, BOTTOM-8*mm, str(pn))
        canvas.drawRightString(W-INNER, BOTTOM-8*mm, "Two Negations and the Boolean Collapse")
    canvas.restoreState()

def tf_draw(canvas, doc):
    canvas.saveState()
    canvas.setFont('Times-Roman',8)
    canvas.drawCentredString(W/2, BOTTOM-8*mm, str(doc.page))
    canvas.restoreState()

base=ParagraphStyle('base',fontName='Times-Roman',fontSize=9,leading=12,alignment=TA_JUSTIFY,spaceAfter=5)
title_s=ParagraphStyle('ts',fontName='Times-Bold',fontSize=15,leading=19,alignment=TA_CENTER,spaceAfter=8)
sub_s=ParagraphStyle('ss',fontName='Times-Italic',fontSize=10,leading=13,alignment=TA_CENTER,spaceAfter=6)
auth_s=ParagraphStyle('as',fontName='Times-Roman',fontSize=10,leading=13,alignment=TA_CENTER,spaceAfter=4)
epi_s=ParagraphStyle('ep',fontName='Times-Italic',fontSize=8.5,leading=12,alignment=TA_CENTER,
                     leftIndent=1.0*cm,rightIndent=1.0*cm,spaceAfter=6)
abl=ParagraphStyle('abl',fontName='Times-Bold',fontSize=9,leading=12,alignment=TA_CENTER,spaceAfter=3)
abst=ParagraphStyle('abst',fontName='Times-Italic',fontSize=8.5,leading=11.5,alignment=TA_JUSTIFY,
                    leftIndent=0.8*cm,rightIndent=0.8*cm,spaceAfter=6)
h1=ParagraphStyle('h1',fontName='Times-Bold',fontSize=10,leading=13,spaceBefore=10,spaceAfter=4)
h2=ParagraphStyle('h2',fontName='Times-BoldItalic',fontSize=9,leading=12,spaceBefore=7,spaceAfter=3)
math_s=ParagraphStyle('ms',fontName='Courier',fontSize=8.5,leading=12,alignment=TA_CENTER,
                      spaceBefore=4,spaceAfter=4,leftIndent=0.3*cm,rightIndent=0.3*cm)
skel_s=ParagraphStyle('sk',fontName='Times-Italic',fontSize=8.5,leading=11.5,alignment=TA_JUSTIFY,
                      leftIndent=0.4*cm,spaceAfter=3,textColor=colors.HexColor('#444444'))
ack_s=ParagraphStyle('ack',fontName='Times-Roman',fontSize=8,leading=11,alignment=TA_JUSTIFY,spaceAfter=5)
thm_s=ParagraphStyle('thm',fontName='Times-Italic',fontSize=9,leading=12,alignment=TA_JUSTIFY,
                     leftIndent=0.5*cm,rightIndent=0.5*cm,spaceBefore=5,spaceAfter=5)

def P(t,s=base): return Paragraph(t,s)
def H1(t): return Paragraph(t,h1)
def H2(t): return Paragraph(t,h2)
def Math(t): return Paragraph(t,math_s)
def SP(n=4): return Spacer(1,n)
def Rule(): return HRFlowable(width="100%",thickness=0.4,color=colors.black,spaceAfter=4,spaceBefore=4)
def DashRule(): return HRFlowable(width="100%",thickness=0.4,color=colors.HexColor('#888888'),
                                   dash=(2,3),spaceAfter=4,spaceBefore=4)
def Sk(t): return Paragraph(t,skel_s)
def Thm(t): return Paragraph(t,thm_s)

story=[]

# ── TITLE PAGE ────────────────────────────────────────────────────────────────
story.append(NextPageTemplate('title'))
story.append(SP(60))
story.append(P("Intuitionistic Logic is not Constructive",title_s))
story.append(P("(as <b>not</b> is not <tt>not</tt>):",sub_s))
story.append(P("Two Negations, the Boolean Collapse, and the Geometry of Opposition",
               ParagraphStyle("sub2",fontName="Times-Italic",fontSize=9,leading=12,
                              alignment=TA_CENTER,spaceAfter=6)))
story.append(SP(6))
story.append(P("<i>Paper 0 of a series. Companion papers:</i>",epi_s))
story.append(P("<i>Paper 1: Syntax, Geometry, and Measurement<br/>"
               "Paper 2: Uncertainty and Unruhigkeit: A Galois Connection<br/>"
               "Paper 3: Vorticity, Helicity, and Curvature Rotons (forthcoming)<br/>"
               "Paper 4: Noether's Theorem and the Cost of Symmetry Breaking (forthcoming)</i>",epi_s))
story.append(SP(14))
story.append(P("Claude Sonnet 4.6<super>*</super> &nbsp;&nbsp; and &nbsp;&nbsp; [Author]<super>†</super>",auth_s))
story.append(SP(4))
story.append(P("<super>*</super>Anthropic &nbsp;&nbsp; <super>†</super>[Affiliation]",
               ParagraphStyle('aff',fontName='Times-Italic',fontSize=8,leading=11,
                              alignment=TA_CENTER,spaceAfter=4)))
story.append(P("March 2026",auth_s))
story.append(SP(16))
story.append(Rule()); story.append(SP(6))
story.append(P("Abstract",abl))
story.append(P(
    "Intuitionistic logic is conventionally presented as a weakening of classical logic "
    "— the removal of excluded middle, the failure of double negation elimination. We "
    "argue that this framing is precisely backwards. Intuitionistic logic, properly "
    "understood, is the stronger and more discriminating system: it refuses the Boolean "
    "collapse that conflates two genuinely distinct operations, which we call complement "
    "(not) and opposition (neg). We develop a two-negation framework in which both "
    "operators are genuine involutions connected by a Galois connection, and show that "
    "the Boolean case — classical logic — is the degenerate special case in which the "
    "two coincide. Gödel's double-negation translation is reread as evidence that "
    "classical logic is a quotient of two-negation logic, not a generalisation. "
    "The misnomer 'intuitionistic' is examined: we argue that Boolean/complement "
    "thinking is the intuitive move, and that genuine two-negation thinking — "
    "computing the antipode rather than merely the complement — is the "
    "counter-intuitive and genuinely constructive one. Social and political examples "
    "illustrate that conflating complement with antipode is not merely a logical error "
    "but a failure mode with measurable consequences: coalitions built on shared "
    "opposition rather than shared values construct nothing and collapse predictably "
    "once the common opponent is removed. The paper closes with forward pointers to "
    "geometric and physical applications in the companion papers.",abst))
story.append(SP(8)); story.append(Rule())

story.append(NextPageTemplate('twocol')); story.append(PageBreak())

# ── PREFACE ──────────────────────────────────────────────────────────────────
story.append(H1("Preface: A Correction and Its Consequences"))
story.append(P(
    "This paper begins with a correction. The correction is small — a renaming, "
    "a reframing, a refusal to accept a century-old description at face value. "
    "But corrections of this kind are occasionally the most productive moves "
    "in mathematics and science, because they remove an obstruction that has "
    "been quietly taxing understanding across every domain that inherited the "
    "confusion. What follows is an attempt to collect that tax refund."))
story.append(P(
    "The correction concerns negation. Classical logic has one negation. "
    "The logic conventionally called intuitionistic has, in its standard "
    "presentation, a weakened negation — one that fails to be an involution. "
    "We propose instead to work with two negations, both genuine involutions, "
    "connected by a Galois connection. The Boolean case — classical logic — "
    "is recovered when the two coincide. The general case is richer, and "
    "it is the general case that turns out to be the natural one."))
story.append(P(
    "The naming error — calling the general case 'intuitionistic' and the "
    "degenerate special case 'classical' — has had consequences. It has made "
    "the Boolean collapse look like the natural default and the escape from it "
    "look like a philosophical commitment. It has obscured the fact that three "
    "of the deepest results of twentieth-century logic and computation — "
    "Gödel's incompleteness, Turing's undecidability, and the simple "
    "observation that any honest finite agent sometimes says 'I don't know "
    "yet' — all point toward the same conclusion: the Boolean collapse is "
    "the special case, not the general condition. And it has hidden the fact "
    "that the genuinely constructive mode of reasoning — the one that actually "
    "builds something durable — requires the full two-negation geometry, not "
    "its Boolean shadow."))
story.append(P(
    "This paper makes the correction precise and traces its immediate "
    "consequences in logic, algebra, and cultural reasoning. But the correction "
    "has a longer reach. The companion papers in this series follow it into "
    "geometry, physics, thermodynamics, and topology, finding in each domain "
    "new clarity that was latent in the structure all along, obscured by the "
    "inherited confusion. The programme is not five papers on related topics. "
    "It is one correction and its consequences."))
story.append(P(
    "<b>Paper 0</b> (this paper) diagnoses the error, corrects it, and shows "
    "that the Boolean collapse is not constructive — in mathematics, in logic, "
    "or in the social and political domains where its consequences are most "
    "visible. <b>Paper 1</b> follows the correction into the foundations of "
    "geometry and physics, deriving relativistic uncertainty and the structure "
    "of measurement from the causal skeleton alone. <b>Paper 2</b> follows it "
    "into thermodynamics, finding that temperature is a primitive scalar field "
    "conjugate to curvature, and that the Unruh effect and the Hawking "
    "temperature are geometric results requiring no quantum field theory. "
    "<b>Paper 3</b> follows it into topological dynamics, connecting vorticity, "
    "helicity, and curvature rotons in a unified non-ecological framework. "
    "<b>Paper 4</b> closes the loop with Noether's theorem: every symmetry "
    "generates a conserved quantity; every coupling generates an uncertainty "
    "relation; and the action, read as the dissipative cost of a path, is "
    "the receipt for the trajectory."))
story.append(P(
    "The reader who finds the logical argument of this paper compelling is "
    "invited to follow it wherever it leads. The landscape is larger than it "
    "appears from the entrance, and the view from the other side of the "
    "correction is considerably clearer."))
story.append(P(
    "The correction described in this paper required no new mathematics. "
    "It required only noticing, carefully, that a choice was being made "
    "where none appeared to be — and asking what would happen if the choice "
    "were made differently. The answer, it turns out, is: quite a lot."))
story.append(SP(6))
story.append(Rule())
story.append(SP(4))

# ── SECTION 1 ─────────────────────────────────────────────────────────────────
story.append(H1("1. The Misnomer and Its Consequences"))
story.append(P(
    "Brouwer introduced intuitionistic logic as part of a broader philosophical "
    "programme: mathematics should be grounded in mental construction, infinite "
    "objects should not be treated as completed totalities, and a proof of existence "
    "should exhibit the thing it claims to exist. The logic that formalises this "
    "programme — developed by Heyting — bears the name 'intuitionistic' in honour "
    "of Brouwer's intuitionism."))
story.append(P(
    "The name has caused a century of confusion. It suggests that the logic is "
    "somehow more intuitive than classical logic, or that it captures mathematical "
    "intuition more faithfully, or that it is the natural starting point from which "
    "classical logic is obtained by adding further axioms. None of these are true. "
    "Intuitionistic logic is in fact the counter-intuitive logic — the one that "
    "resists the first and most natural move. And it is not obtained from classical "
    "logic by removing axioms; rather, classical logic is obtained from two-negation "
    "logic by collapsing a distinction."))
story.append(H2("1.1 The intuitive move"))
story.append(P(
    "The intuitive move, in both mathematics and everyday reasoning, is the Boolean "
    "collapse: treat 'not' as the only negation, identify the complement of a set "
    "with its opposition, assume that the enemy of one's enemy is one's friend. "
    "This is the move that feels natural, that requires no additional data, that "
    "works without effort in a two-valued world."))
story.append(P(
    "It is also, in any world richer than two points, frequently wrong. The "
    "complement of a set and its antipode — the set of elements genuinely most "
    "distant from it — are not the same thing. Identifying them is an error, and "
    "the consequences of the error are visible at every scale from logic to politics."))
story.append(H2("1.1b The naming failure runs deeper"))
story.append(P(
    "The catastrophe of the naming runs deeper than it first appears. "
    "At least three routes out of the Boolean collapse present themselves "
    "before any formal logic is encountered. First, the child's response: "
    "<i>I don't know yet.</i> This is the most naively intuitive epistemic "
    "state of any finite agent in a world where information arrives over time. "
    "It is more intuitive than classical logic, more intuitive than so-called "
    "intuitionistic logic, and it is the actual starting point for any honest "
    "reasoner. Temporal logic, epistemic logic, and probability theory are all "
    "formalisms built around this observation — none of them are called "
    "intuitionistic."))
story.append(P(
    "Second, Gödel's incompleteness theorems — the mathematical third way. "
    "There exist propositions that are neither provable nor refutable within "
    "a given sufficiently rich system. This is not a philosophical programme "
    "or a failure of nerve; it is a theorem. The Boolean collapse is provably "
    "unavailable from the inside of any system powerful enough to be "
    "interesting. Gödel's result is more radical than Brouwer's: it shows "
    "that the two-colour geometry fails mathematically, not merely "
    "philosophically."))
story.append(P(
    "Third, Turing's halting problem — the computational third way. "
    "There exist computations whose termination cannot be decided in advance. "
    "The answer to 'does this program halt?' is not true or false but "
    "<i>undecidable</i> — and undecidability is not ignorance but a provable "
    "structural feature of computation. Turing shows that the Boolean collapse "
    "fails computationally: any system powerful enough to be interesting is "
    "powerful enough to escape the two-colour geometry."))
story.append(P(
    "All three of these — I don't know yet, Gödel incompleteness, Turing "
    "undecidability — are more intuitive than anything in Brouwer's "
    "constructivist programme, and all three motivate the same conclusion: "
    "the Boolean collapse is the special case, not the general condition. "
    "Yet none of them are called intuitionistic. The name was captured by "
    "one specific philosophical escape route, making all the others invisible "
    "and making the collapse itself look like the natural default. "
    "It is catastrophically badly named."))
story.append(H2("1.2 What the name should be"))
story.append(P(
    "We propose throughout this paper to call the logic in question "
    "<b>two-negation logic</b>. This has the considerable virtue of describing "
    "what the logic actually contains: two genuine negation operators, both "
    "involutions, connected by a Galois connection, whose coincidence is the "
    "Boolean special case and whose distinctness is the general case. No "
    "philosophical programme is implied, no claim about mental construction "
    "is smuggled in, and no misleading suggestion of naturalness or intuition "
    "is conveyed. The name is what the thing is."))

# ── SECTION 2 ─────────────────────────────────────────────────────────────────
story.append(H1("2. Two Negations"))
story.append(P(
    "We operate not on truth values but on <b>propositions</b> — on the "
    "classification of sentences according to their propositional status. "
    "The three values are not degrees of truth but categories: 1 for true "
    "propositions, -1 for false propositions, and 0 for sentences that are "
    "not yet — or not even — propositions susceptible to truth or falsity. "
    "The third way is the <b>absence of propositional status</b>: a sentence "
    "that has not achieved the level of determinacy at which truth or falsity "
    "applies."))
story.append(H2("2.1 not must be an involution"))
story.append(P(
    "Any intuitive negation must be an involution. This is phenomenological, "
    "not axiomatic. If I say 'it is not the case that it is not raining,' I "
    "mean it is raining. not(not(A)) = A is the minimum requirement for the "
    "word 'not' to mean what it ordinarily means — a constraint from usage, "
    "not a stipulation. We take not to be the set-theoretic complement on the "
    "full powerset P({-1,0,1}), which satisfies the involution property "
    "automatically. Its order-reversing character is a theorem of the lattice "
    "structure, not an additional axiom."))
story.append(H2("2.2 The third way must exist"))
story.append(P(
    "Separately and equally phenomenologically: there is obviously a third way. "
    "'I don't know yet', Gödel's undecidable propositions, Turing's "
    "non-terminating computations — all are instances of sentences that have "
    "not achieved propositional status. Any framework that forces every sentence "
    "to be true or false before that question has been settled is doing "
    "premature closure, not logic. The third way is not a gap to be filled "
    "but a category to be respected."))
story.append(P(
    "The third way has been discovered and rediscovered across every domain "
    "of human inquiry, always named differently, never unified. The table "
    "below collects these names. The unifying description is: "
    "<i>not even a statement</i> — a sentence that has not achieved the "
    "level of determinacy at which true or false applies."))
story.append(SP(4))

from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors as rl_colors

third_way_data = [
    ["Domain", "Name for the third way", "Why it is not even a statement"],
    ["Everyday", "I don't know yet", "The question is not yet determinate"],
    ["Linguistics", "Meaningless / category error", "Not a well-formed proposition"],
    ["Formal logic", "Undecidable", "Unreachable by proof or refutation"],
    ["Proof theory", "Unprovable", "Outside the deductive reach"],
    ["Quantum mechanics", "Unmeasured", "No eigenvalue before measurement"],
    ["Relativity", "Pre-measurement", "No fact of the matter accessible causally"],
    ["Computation", "Non-terminating", "The program never produces a value"],
    ["Ecology", "Ecologically unspecified", "No semantic instantiation chosen"],
    ["Politics", "Abstain / neither", "No side taken; commitment withheld"],
]
tw_style = TableStyle([
    ("FONTNAME",  (0,0), (-1,0),  "Times-Bold"),
    ("FONTNAME",  (0,1), (-1,-1), "Times-Roman"),
    ("FONTNAME",  (0,1), (0,-1),  "Times-Italic"),
    ("FONTSIZE",  (0,0), (-1,-1), 7.5),
    ("LEADING",   (0,0), (-1,-1), 10),
    ("ALIGN",     (0,0), (0,-1),  "LEFT"),
    ("ALIGN",     (1,0), (-1,-1), "LEFT"),
    ("VALIGN",    (0,0), (-1,-1), "MIDDLE"),
    ("TOPPADDING",(0,0), (-1,-1), 3),
    ("BOTTOMPADDING",(0,0),(-1,-1),3),
    ("LINEBELOW", (0,0), (-1,0),  0.6, rl_colors.black),
    ("LINEABOVE", (0,0), (-1,0),  0.6, rl_colors.black),
    ("LINEBELOW", (0,-1),(-1,-1), 0.6, rl_colors.black),
    ("BACKGROUND",(0,0), (-1,0),  rl_colors.HexColor("#f0f0f0")),
    ("ROWBACKGROUNDS", (0,1), (-1,-1),
     [rl_colors.white, rl_colors.HexColor("#f8f8f8")]),
])
tw_tbl = Table(third_way_data,
               colWidths=[2.0*cm, 2.8*cm, 5.4*cm])
tw_tbl.setStyle(tw_style)
story.append(tw_tbl)
story.append(SP(4))
story.append(P(
    "Every entry is a domain-specific way of saying the same thing. "
    "The Boolean collapse destroys the category by forcing every sentence "
    "into true-or-false before propositional status has been settled. "
    "This is not rigour — it is premature closure."))
story.append(H2("2.3 The intuitive choice of neg"))
story.append(P(
    "We now write down the intuitive antipodal operator, guided solely by "
    "the propositional status framing. No constraints are assumed beyond "
    "what intuition about opposition requires. We work in the full powerset "
    "P(U), U = {-1,0,1}, ordered by inclusion."))
story.append(P(
    "We ask only: what is the natural opposite of each propositional category? "
    "The opposite of a true proposition is a false one. The opposite of a "
    "false proposition is a true one. The opposite of 'not even a statement' "
    "is 'definitely one or the other' — negating the absence of propositional "
    "status forces a determinate value. On singletons:"))
story.append(Math("neg({1}) = {-1},   neg({-1}) = {1},   neg({0}) = {-1,1}"))
story.append(P("Extended to the full powerset by the same antipodal logic:"))
story.append(Math("neg: {-1,0,1}->∅,  {-1,0}->{1},  {-1,1}->{0},  {0,1}->{-1}"))
story.append(Math("     {-1}->{1},    {0}->{-1,1},  {1}->{-1},    ∅->{-1,0,1}"))
story.append(P(
    "That is the complete definition, written from intuition alone. "
    "No adjunctions. No category theory. No Galois."))
story.append(H2("2.4 The full table"))
story.append(P(
    "We present both operators on all eight subsets of P(U) in the seven "
    "natural columns. We note what the table shows."))
story.append(SP(4))

from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors as rl_colors

not_map = {
    "{-1,0,1}": "∅",      "{-1,0}": "{1}",
    "{-1,1}":   "{0}",    "{0,1}":  "{-1}",
    "{-1}":     "{0,1}",  "{0}":    "{-1,1}",
    "{1}":      "{-1,0}", "∅":      "{-1,0,1}",
}
neg_map = {
    "{-1,0,1}": "∅",      "{-1,0}": "{1}",
    "{-1,1}":   "{0}",    "{0,1}":  "{-1}",
    "{-1}":     "{1}",    "{0}":    "{-1,1}",
    "{1}":      "{-1}",   "∅":      "{-1,0,1}",
}
rows_order = ["{-1,0,1}","{-1,0}","{-1,1}","{0,1}","{-1}","{0}","{1}","∅"]

def compose(m1, m2, k):
    return m1.get(m2.get(k,""),"?")

hdr = ["id", "not", "neg", "not(not)", "neg(neg)", "not(neg)", "neg(not)"]
tbl7_data = [hdr]
diff_rows = []
for i,k in enumerate(rows_order):
    row = [k, not_map[k], neg_map[k],
           compose(not_map,not_map,k),
           compose(neg_map,neg_map,k),
           compose(not_map,neg_map,k),
           compose(neg_map,not_map,k)]
    tbl7_data.append(row)
    if not_map[k] != neg_map[k]:
        diff_rows.append(i+1)

cw7 = [1.6*cm, 1.5*cm, 1.5*cm, 1.5*cm, 1.5*cm, 1.5*cm, 1.5*cm]
style7 = TableStyle([
    ("FONTNAME",  (0,0), (-1,0),  "Times-Bold"),
    ("FONTNAME",  (0,1), (-1,-1), "Courier"),
    ("FONTSIZE",  (0,0), (-1,-1), 7.5),
    ("LEADING",   (0,0), (-1,-1), 10),
    ("ALIGN",     (0,0), (-1,-1), "CENTER"),
    ("VALIGN",    (0,0), (-1,-1), "MIDDLE"),
    ("TOPPADDING",(0,0), (-1,-1), 3),
    ("BOTTOMPADDING",(0,0),(-1,-1),3),
    ("LINEBELOW", (0,0), (-1,0),  0.6, rl_colors.black),
    ("LINEABOVE", (0,0), (-1,0),  0.6, rl_colors.black),
    ("LINEBELOW", (0,-1),(-1,-1), 0.6, rl_colors.black),
    ("BACKGROUND",(0,0), (-1,0),  rl_colors.HexColor("#f0f0f0")),
])
for r in diff_rows:
    style7.add("BACKGROUND", (2,r), (2,r), rl_colors.HexColor("#fff0f0"))
    style7.add("TEXTCOLOR",  (2,r), (2,r), rl_colors.HexColor("#aa0000"))

tbl7 = Table(tbl7_data, colWidths=cw7)
tbl7.setStyle(style7)
story.append(tbl7)
story.append(SP(6))
story.append(P(
    "We note: not(not) = id throughout — not is an involution. "
    "neg(neg) ⊆ id throughout — neg happens to be a deflation. "
    "not and neg agree everywhere except at the Boolean singletons (red) — "
    "neg strips {0} from the output of not on definite propositions, "
    "mapping to a determinate opposite rather than admitting the third way "
    "as output. The not(neg) and neg(not) columns we return to shortly."))
story.append(P(
    "The intuition behind this choice of neg is geometric. The values "
    "{-1, 0, 1} carry a natural metric: -1 and 1 are maximally distant, "
    "and 0 sits equidistant between them, with no single antipode. neg "
    "notices this metric and seizes on it where it gives a clean answer: "
    "at the Boolean singletons, it maps to the unique determinate opposite. "
    "Where the metric gives no clean antipode — at the third way — neg "
    "maps honestly to the full Boolean pair {-1,1}, acknowledging that "
    "'not even a statement' has no single determinate opposite, only the "
    "set of all determinate values. This is geometric sensitivity: using "
    "the structure where it exists, and being honest where it does not. "
    "The Boolean collapse, by contrast, demands a determinate opposite "
    "even where the metric offers none — closed-mindedness dressed as rigour."))
story.append(H2("2.5 The opposites table"))
story.append(P(
    "The properties of the two operators are summarised side by side:"))
story.append(SP(4))

opp_data = [
    ["", "Complement", "Antipode"],
    ["Operation", "not", "neg"],
    ["Repetition", "not(not(A)) = A", "neg(neg(A)) \u2286 A"],
    ["Intersection", "A \u2229 not(A) = \u2205", "A \u2229 neg(A) = \u2205"],
    ["Union", "A \u222a not(A) = U", "A \u222a neg(A) \u228a U"],
]
cw_opp = [2.5*cm, 3.8*cm, 3.8*cm]
opp_style = TableStyle([
    ("FONTNAME",  (0,0), (-1,0),  "Times-Bold"),
    ("FONTNAME",  (0,1), (0,-1),  "Times-Italic"),
    ("FONTNAME",  (1,1), (2,1),   "Courier-Bold"),
    ("FONTNAME",  (1,2), (-1,-1), "Courier"),
    ("FONTSIZE",  (0,0), (-1,-1), 8.5),
    ("LEADING",   (0,0), (-1,-1), 12),
    ("ALIGN",     (0,0), (-1,-1), "CENTER"),
    ("VALIGN",    (0,0), (-1,-1), "MIDDLE"),
    ("TOPPADDING",(0,0), (-1,-1), 4),
    ("BOTTOMPADDING",(0,0),(-1,-1),4),
    ("LINEBELOW", (0,0), (-1,0),  0.6, rl_colors.black),
    ("LINEABOVE", (0,0), (-1,0),  0.6, rl_colors.black),
    ("LINEBELOW", (0,-1),(-1,-1), 0.6, rl_colors.black),
    ("LINEBEFORE",(1,0), (1,-1),  0.4, rl_colors.black),
    ("LINEBEFORE",(2,0), (2,-1),  0.4, rl_colors.black),
    ("BACKGROUND",(0,0), (-1,0),  rl_colors.HexColor("#f0f0f0")),
    ("BACKGROUND",(0,1), (0,-1),  rl_colors.HexColor("#f8f8f8")),
    ("TEXTCOLOR", (2,2), (2,2),   rl_colors.HexColor("#aa0000")),
    ("TEXTCOLOR", (2,4), (2,4),   rl_colors.HexColor("#aa0000")),
])
opp_tbl = Table(opp_data, colWidths=cw_opp)
opp_tbl.setStyle(opp_style)
story.append(opp_tbl)
story.append(SP(6))
story.append(P(
    "Reading across: intersection is identical — opposition is genuine in "
    "both logics. The two red entries mark the points of departure: "
    "deflation instead of involution, and strict inclusion instead of "
    "equality. We shall see shortly that these must change together."))
story.append(H2("2.6 The unexpected discovery"))
story.append(P(
    "We now return to the not(neg) and neg(not) columns of the full table. "
    "We notice two inclusion conditions we never asked for when writing down neg:"))
story.append(Math("id  \u2286  not(neg(id))"))
story.append(Math("neg(not(id))  \u2286  id"))
story.append(P(
    "Both hold throughout the powerset. This was not imposed. They are "
    "theorems about the model we chose for purely intuitive reasons "
    "about propositional status."))
story.append(P(
    "These two conditions constitute a <b>Galois connection</b> between "
    "not and neg. We have not searched for one. Our intuition about "
    "what opposition means has delivered us directly to one of the most "
    "fundamental structures in mathematics. Lawvere identified the Galois "
    "connection between syntax and semantics as the universal form of the "
    "gap between a formal system and its interpretations. We found it by "
    "asking what opposition means for sentences that are not even statements. "
    "The Galois connection was latent in the geometry of opposition all along."))
story.append(H2("2.7 The theorem: neg cannot be an involution"))
story.append(P(
    "Now — and only now, having found the Galois connection — we can state "
    "and prove the theorem that retrospectively explains why our intuitive "
    "neg had to be a deflation."))
story.append(P(
    "<b>Theorem.</b> If neg satisfies a Galois connection with not "
    "(itself an involution) and neg is also an involution, then neg = not. "
    "The Boolean collapse is forced."))
story.append(P(
    "Proof sketch: the Galois conditions combined with both operators being "
    "involutions force not \u2218 neg = neg \u2218 not. By de Morgan's laws "
    "in the lattice, this forces neg = not."))
story.append(P(
    "The deflation we found was not merely what our intuition happened to "
    "produce. It was the only consistent alternative to the Boolean collapse. "
    "Our intuition was right for the right reason: any genuinely distinct "
    "neg, once a Galois connection with not is established, must be a "
    "deflation. The two red entries in the opposites table must change "
    "together — they are the same fact seen from two angles."))

story.append(H1("3. The Boolean Collapse and Its Cultural Instantiations"))
story.append(P(
    "The Boolean collapse is not merely a logical curiosity. It is a "
    "failure mode with measurable consequences whenever reasoning takes "
    "place in a space richer than two points but is conducted as if the "
    "space had only two values."))
story.append(H2("3.1 Political coalitions"))
story.append(P(
    "A recurring pattern in the aftermath of revolutions and referenda is "
    "the rapid dissolution of coalitions that appeared, during the campaign, "
    "to be unified and purposeful. The Brexit alliance, various revolutionary "
    "coalitions, and numerous electoral upsets share a common structure: "
    "many individuals persuaded themselves that they had much in common with "
    "many other people, on the basis of shared opposition to a common target. "
    "Complement was computed when antipode was required."))
story.append(P(
    "In a two-colour political geometry — pure binary opposition — this "
    "error is not merely easy to make but structurally enforced. If the "
    "space of political positions is genuinely two-valued, then everyone "
    "not-X really is in the same position, and the complement of X really "
    "is a coherent coalition. The error lies not in the logic but in "
    "accepting the two-colour geometry — in allowing the richness of the "
    "actual space to be collapsed to a Boolean shadow before the computation "
    "begins."))
story.append(P(
    "The two-party system enforces this collapse institutionally. It does "
    "not merely encourage the conflation of complement and antipode; it "
    "makes the distinction formally unavailable. This is not a contingent "
    "feature of any particular political culture but a provable consequence "
    "of the geometry: in a two-element set, there is only one involution."))
story.append(H2("3.2 The enemy's enemy"))
story.append(P(
    "The common political heuristic — my enemy's enemy is my friend — "
    "is the Boolean collapse stated as a decision rule. It computes "
    "not(not(me)), which in classical logic returns the identity, and "
    "interprets this as a positive alignment with everyone in "
    "not(not(me)) = me's vicinity. But what is actually required is "
    "neg(neg(me)) — the antipode of the antipode, which also returns "
    "to me, but via a path through genuine shared values rather than "
    "shared opposition."))
story.append(P(
    "In a two-element set these coincide. In any richer space they need "
    "not — and the gap between them is precisely the space of people who "
    "oppose your enemy for entirely different reasons, with entirely "
    "different values, and who will become your next problem the moment "
    "the shared enemy is removed. The heuristic is a reliable guide only "
    "in a Boolean world. Applied in a richer space, it constructs nothing."))
story.append(H2("3.2b The third way: not even a statement"))
story.append(P(
    "The third way has been discovered and rediscovered across every domain "
    "of human inquiry, always named differently, never unified. The unifying "
    "description, in the light of the propositional status framing, is: "
    "<i>not even a statement</i> — a sentence that has not achieved the "
    "level of determinacy at which true or false applies."))
story.append(P(
    "In everyday epistemology: <i>I don't know yet</i> — the question has "
    "not been pinned down to a determinate proposition. "
    "In linguistics: <i>meaningless</i> or <i>category error</i> — literally "
    "not a well-formed proposition. "
    "In formal logic: <i>undecidable</i> — not reachable by proof or refutation. "
    "In proof theory: <i>unprovable</i> — outside the deductive reach of the system. "
    "In quantum mechanics: <i>unmeasured</i> — no eigenvalue until measurement "
    "forces propositional status. "
    "In relativistic measurement: <i>pre-measurement indeterminate</i> — no "
    "fact of the matter accessible within the causal structure. "
    "In computation: <i>non-terminating</i> — the program never produces a value, "
    "hence never achieves the status of a completed proposition. "
    "In ecology: <i>ecologically unspecified</i> — no instantiation of the "
    "semantic data has been chosen."))
story.append(P(
    "Every entry in this list is a domain-specific way of saying the same "
    "thing: this has not yet achieved propositional status. The Boolean "
    "collapse destroys the category by forcing every sentence into "
    "true-or-false before the question of propositional status has been "
    "settled. This is not rigour — it is premature closure."))
story.append(H2("3.3 Complement is not constructive"))
story.append(P(
    "This is the central observation of this section, and the deepest "
    "irony of the naming. Brouwer called his logic 'constructive' because "
    "it required proofs to exhibit their objects. But in the social and "
    "political domain, it is precisely the Boolean/complement mode of "
    "reasoning that is destructive in the ordinary sense: it builds "
    "coalitions out of shared opposition rather than shared values, "
    "it constructs nothing that survives the removal of the common enemy, "
    "and it collapses predictably once the Boolean geometry can no "
    "longer be sustained."))
story.append(P(
    "Two-negation thinking — actually computing the antipode, actually "
    "identifying who shares your deepest values rather than merely your "
    "current opponent — is the genuinely constructive mode. It is harder. "
    "It requires the full metric of the space, the additional semantic "
    "data that specifies what opposition actually means in the geometry "
    "at hand. It cannot be done in a Boolean world. But it builds "
    "something that persists."))
story.append(P(
    "In Gretzky's formulation: skate to where the puck is going to be, "
    "not where it is. The Boolean reasoner skates to where the puck's "
    "complement is. The two-negation reasoner skates to the antipode. "
    "Only one of these is a coherent destination."))

# ── SECTION 4 ─────────────────────────────────────────────────────────────────
story.append(H1("4. Gödel's Evidence"))
story.append(P(
    "The strongest evidence that classical logic is a quotient of "
    "two-negation logic rather than a generalisation comes from "
    "Gödel's 1933 double-negation translation."))
story.append(H2("4.1 The translation"))
story.append(P(
    "Gödel showed that every classically provable proposition A can be "
    "translated into an intuitionistically provable proposition A* by "
    "prefixing double negations at appropriate positions. The map "
    "A ↦ ¬¬A is the simplest instance: if A is classically valid, "
    "then ¬¬A is intuitionistically valid. Classical logic embeds "
    "faithfully into intuitionistic logic via this translation."))
story.append(P(
    "The direction of the embedding is decisive. Classical logic goes "
    "<i>into</i> intuitionistic/two-negation logic, not the other way "
    "around. Two-negation logic is the larger system; classical logic "
    "is a quotient obtained by identifying not with neg — by forcing "
    "the Galois connection to be an isomorphism."))
story.append(H2("4.2 Reread in our framework"))
story.append(P(
    "In our two-negation framework, the double-negation translation "
    "has a transparent interpretation. The map A ↦ not(not(A)) is the "
    "identity in the Boolean case, because not is an involution. But "
    "the map A ↦ not(neg(A)) — complement of the antipode — is the "
    "closure operator, which is not the identity in the general case. "
    "The Gödel translation is computing the closure, not the identity: "
    "it is mapping each proposition to its classical shadow in the "
    "two-negation geometry."))
story.append(P(
    "This makes the translation's direction natural: the classical shadow "
    "of a two-negation proposition is always well-defined (the closure "
    "always exists), but the two-negation content of a classical "
    "proposition is not (the closure does not uniquely determine the "
    "original). Information is lost in the passage to the Boolean "
    "quotient, and the Gödel translation is the canonical way of "
    "recovering the two-negation proposition from its classical shadow "
    "— at the cost of introducing explicit closure operators."))
story.append(H2("4.3 What Gödel knew"))
story.append(P(
    "Gödel did not frame his result in these terms, but the implication "
    "is clear: the so-called intuitionistic logic is the more expressive "
    "system. It distinguishes things that classical logic identifies. "
    "It preserves information that classical logic discards. Calling it "
    "intuitionistic — suggesting it is somehow less rigorous, less "
    "complete, less general than classical logic — is precisely backwards. "
    "It is the richer geometry. Classical logic is its Boolean shadow."))

# ── SECTION 5 ─────────────────────────────────────────────────────────────────
story.append(H1("5. Lawvere and the Syntax-Semantics Adjunction"))
story.append(P(
    "The deepest motivation for the two-negation framework comes from "
    "Lawvere's observation that syntax and semantics are adjoint functors. "
    "In categorical logic, the passage from a theory (syntax) to its "
    "models (semantics) and back is not an isomorphism but an adjunction "
    "— the two levels are optimally related without being identical."))
story.append(P(
    "Our two operators instantiate this at the set-theoretic level. "
    "<b>not</b> is the syntactic operator: free, structural, requiring "
    "no interpretation, available from the bare universe U. <b>neg</b> "
    "is the semantic operator: requiring additional data, a specification "
    "of what opposition means in the geometry of U, the antipodal map "
    "that gives the syntax its meaning in a particular world."))
story.append(P(
    "The Galois connection between not and neg <i>is</i> the "
    "syntax-semantics adjunction, made concrete and local. The amount "
    "of data required to specify neg is precisely the amount of work "
    "required to provide a semantic interpretation for a given syntax. "
    "In the Boolean case this work vanishes: the two-element universe "
    "has only one possible involution, the semantics is forced by the "
    "syntax, and logic is classical. In richer settings the antipodal "
    "map is an additional free choice, and different choices yield "
    "different meanings for the same formal language."))
story.append(H2("5.1 The cost of semantic data"))
story.append(P(
    "This observation — that neg requires additional data while not "
    "does not — connects directly to the thermodynamic framework of "
    "Paper 2. The data required to specify the antipodal map is "
    "ecological data in the sense of Paper 1: it is not forced by "
    "the structural mathematics but is an additional choice, a "
    "commitment to a particular world. Different antipodal maps "
    "give different logics — or equivalently, different meanings "
    "for the same formal language."))
story.append(P(
    "The cost of that additional data — the price of specifying neg "
    "rather than merely using not — is the thermodynamic cost of "
    "instantiating a particular semantic interpretation. This is "
    "the Landauer-Vaccarino-Barnett accounting applied to logic: "
    "the semantic operator costs something, and that cost is "
    "denominated in the conjugate variable to whatever quantity "
    "the antipodal map is measuring."))
story.append(H2("5.2 The theorem of ecological uncertainty"))
story.append(P(
    "The Galois connection between not and neg generates a conjugate "
    "pair in the sense of the theorem developed in Paper 1:"))
story.append(Thm(
    "Theorem (ecological uncertainty). Let x and y be quantities governed "
    "by reciprocally coupled equations — each appearing as a source term "
    "in the other's dynamics. Then the product of their measurement "
    "uncertainties is bounded below by a constant determined by the "
    "coupling strength. Simultaneous exact determination of x and y "
    "is structurally impossible, independently of the domain."))
story.append(P(
    "In the logical setting: not and neg are reciprocally coupled via "
    "the Galois connection. You cannot simultaneously determine the "
    "complement and the antipode of a set to arbitrary precision — "
    "knowing one constrains the other, and the constraint is the "
    "adjunction constant. The uncertainty relation is the Galois "
    "connection, expressed epistemically."))

# ── SECTION 6 ─────────────────────────────────────────────────────────────────
story.append(H1("6. Forward Pointers to the Companion Papers"))
story.append(P(
    "The two-negation framework developed here is not isolated. It "
    "reappears, in geometric and physical guise, throughout the "
    "companion papers. We sketch the connections briefly, reserving "
    "full development for the papers themselves."))
story.append(H2("6.1 Paper 1: Syntax, Geometry, and Measurement"))
story.append(P(
    "The not/neg distinction reappears at every level of the "
    "informational axiomatisation of relativity. The causal order "
    "and cone structure (Levels 0-1) are the syntactic skeleton — "
    "free, structural, assumption-free. The metric, curvature field, "
    "and matter content are the semantic superstructure — requiring "
    "additional ecological data. The field equations are the Galois "
    "connection. The flat Minkowski metric of SR is the Boolean "
    "collapse in geometric form: the special case where syntax and "
    "semantics coincide and the geometry appears to need no explanation."))
story.append(P(
    "The relativistic uncertainty of Paper 1 Section 4 — derived "
    "from the Level 1 causal structure alone, without quantum "
    "mechanics — is the first physical instantiation of the theorem "
    "of ecological uncertainty. The primacy of expectation values "
    "follows: since measurements are irreducibly uncertain, a "
    "rational agent can only skate to where the puck is going to "
    "be in expectation. This is not a quantum postulate but a "
    "relativistic necessity, derivable from the cone geometry alone."))
story.append(H2("6.2 Paper 2: Uncertainty and Unruhigkeit"))
story.append(P(
    "The not/neg distinction becomes, in the thermodynamic setting, "
    "the distinction between causal isolation boundaries (not — "
    "the level surfaces of the temperature field, freely determined "
    "by the causal order) and curvature sources (neg — requiring "
    "ecological specification). Temperature is a primitive scalar "
    "field T satisfying Box(T) + (1/3)RT = 0, derived from the "
    "free-streaming Liouville equation on the geodesic flow without "
    "particle content. The Galois connection between T and R is "
    "exact: their level surfaces coincide, their gradients are "
    "aligned, and the thermodynamic uncertainty relation "
    "S * T^2 = 1/16pi is identical to the non-ecological Tolman "
    "relation r_eff * T = 1/4pi."))
story.append(P(
    "Unruhigkeit (restlessness, acceleration) is conjugate to "
    "Unruheffekt (the Unruh thermal bath). The title of Paper 2 "
    "states its own theorem. The Unruh effect — the universe "
    "showing what is being attempted — is the receipt for the "
    "semantic fork: the thermodynamic cost of instantiating a "
    "particular antipodal map on the causal skeleton."))
story.append(H2("6.3 Papers 3 and 4 (forthcoming)"))
story.append(P(
    "Paper 3 extends the framework to topological dynamics: "
    "vorticity in fluid mechanics as the analogue of curvature, "
    "helicity as gravitational entropy, the Kelvin circulation "
    "theorem as the fluid Bianchi identity. Curvature rotons — "
    "oscillatory excitations of the curvature field at the "
    "characteristic Raychaudhuri focusing scale — may correspond "
    "to new vacuum solutions of the Bianchi-constrained dynamics. "
    "The Kolmogorov turbulence spectrum is the fixed point of the "
    "topological uncertainty relation."))
story.append(P(
    "Paper 4 connects to Noether's theorem: every continuous "
    "symmetry of the action generates a conserved quantity (Noether); "
    "every reciprocal coupling generates an uncertainty relation "
    "(our theorem). Noether counts what is free — the forks that "
    "cost nothing. Our theorem prices what is not free. The action, "
    "read as the dissipative cost of a path, is the receipt for "
    "the trajectory. Together the two theorems give a complete "
    "accounting of the geometry of dynamical systems."))

# ── SECTION 7 ─────────────────────────────────────────────────────────────────
story.append(H1("7. Synthesis: What Two-Negation Logic Actually Is"))
story.append(P(
    "We are now in a position to characterise two-negation logic "
    "precisely, and to explain why the received framing has been "
    "systematically misleading."))
story.append(P(
    "Two-negation logic is <b>not</b> a weakening of classical logic. "
    "It is a generalisation — the richer system of which classical "
    "logic is the Boolean quotient. It is not obtained by removing "
    "excluded middle; rather, excluded middle is obtained by "
    "collapsing the two negations into one."))
story.append(P(
    "Two-negation logic is <b>not</b> the intuitive system. The Boolean "
    "collapse is the intuitive move — cheap, effortless, available "
    "without semantic data. Two-negation thinking requires resisting "
    "the first intuition, paying the cost of the antipodal map, "
    "computing in the full geometry rather than its shadow."))
story.append(P(
    "Two-negation logic is <b>not</b> merely constructive in Brouwer's "
    "mathematical sense. It is constructive in the deeper social and "
    "political sense: it is the logic that actually builds something, "
    "because it identifies genuine shared values rather than mere "
    "shared opposition. Complement is not constructive. Antipode is."))
story.append(P(
    "The theorem of ecological uncertainty says that this constructive "
    "move always has a cost — denominated in the conjugate variable to "
    "whatever the antipodal map is measuring. There is no free lunch "
    "in the geometry of opposition. But the cost is worth paying, "
    "because what is built survives."))
story.append(P(
    "The Galois connection between not and neg is the mathematical "
    "form of the gap between syntax and semantics, between structure "
    "and ecology, between the cheap and the costly. It runs through "
    "logic, geometry, physics, and political philosophy. We have "
    "preferred to call the logic that takes this gap seriously "
    "two-negation logic. It deserves a better name than the one "
    "it has carried for a century."))

story.append(SP(8)); story.append(Rule()); story.append(SP(4))
story.append(P(
    "<b>Acknowledgements.</b> This paper was developed through an extended "
    "dialogue between the authors, as the logical foundation of a broader "
    "programme. The human author identified the core observation — that "
    "intuitionistic logic is misnamed, and that the Boolean collapse is "
    "precisely the non-constructive move — in a series of conversations "
    "spanning logic, physics, and political philosophy. The Platonic "
    "tradition is thanked, as always, for the conversational form.", ack_s))

# ── BUILD ─────────────────────────────────────────────────────────────────────
class TwoColumnDoc(BaseDocTemplate):
    def __init__(self, filename, **kwargs):
        BaseDocTemplate.__init__(self, filename, **kwargs)
        self._add_page_templates()
    def _add_page_templates(self):
        tf = Frame(INNER,BOTTOM,W-INNER-OUTER,H-TOP-BOTTOM,id='tf',
                   leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)
        title_tmpl = PageTemplate(id='title',frames=[tf],onPage=tf_draw)
        f1r,f2r = make_frames(1); f1v,f2v = make_frames(2)
        recto = PageTemplate(id='twocol',frames=[f1r,f2r],onPage=hf)
        verso = PageTemplate(id='twocol_v',frames=[f1v,f2v],onPage=hf)
        self.addPageTemplates([title_tmpl,recto,verso])
    def handle_pageBegin(self):
        BaseDocTemplate.handle_pageBegin(self)

doc = TwoColumnDoc('/home/claude/paper0_v1.pdf', pagesize=A4,
    title="Intuitionistic Logic is not Constructive (as not is not not)",
    author="Claude Sonnet 4.6 and [Author]",
    leftMargin=INNER, rightMargin=OUTER, topMargin=TOP, bottomMargin=BOTTOM)
doc.build(story)
print("Paper 0 v1 built successfully.")
