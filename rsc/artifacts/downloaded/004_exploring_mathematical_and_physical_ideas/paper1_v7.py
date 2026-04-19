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
        canvas.drawString(INNER, BOTTOM-8*mm, "Syntax, Geometry, and Measurement")
    else:
        canvas.drawString(OUTER, BOTTOM-8*mm, str(pn))
        canvas.drawRightString(W-INNER, BOTTOM-8*mm, "Towards a Unified Informational Foundation")
    canvas.restoreState()

def tf_draw(canvas, doc):
    canvas.saveState()
    canvas.setFont('Times-Roman',8)
    canvas.drawCentredString(W/2, BOTTOM-8*mm, str(doc.page))
    canvas.restoreState()

base=ParagraphStyle('base',fontName='Times-Roman',fontSize=9,leading=12,alignment=TA_JUSTIFY,spaceAfter=5)
title_s=ParagraphStyle('ts',fontName='Times-Bold',fontSize=16,leading=20,alignment=TA_CENTER,spaceAfter=8)
sub_s=ParagraphStyle('ss',fontName='Times-Italic',fontSize=11,leading=14,alignment=TA_CENTER,spaceAfter=6)
auth_s=ParagraphStyle('as',fontName='Times-Roman',fontSize=10,leading=13,alignment=TA_CENTER,spaceAfter=4)
abl=ParagraphStyle('abl',fontName='Times-Bold',fontSize=9,leading=12,alignment=TA_CENTER,spaceAfter=3)
abst=ParagraphStyle('abst',fontName='Times-Italic',fontSize=8.5,leading=11.5,alignment=TA_JUSTIFY,
                    leftIndent=0.8*cm,rightIndent=0.8*cm,spaceAfter=6)
h1=ParagraphStyle('h1',fontName='Times-Bold',fontSize=10,leading=13,spaceBefore=10,spaceAfter=4)
h2=ParagraphStyle('h2',fontName='Times-BoldItalic',fontSize=9,leading=12,spaceBefore=7,spaceAfter=3)
math_s=ParagraphStyle('ms',fontName='Courier',fontSize=8.5,leading=12,alignment=TA_CENTER,
                      spaceBefore=4,spaceAfter=4,leftIndent=0.3*cm,rightIndent=0.3*cm)
boxed_s=ParagraphStyle('bs',fontName='Courier-Bold',fontSize=9,leading=13,alignment=TA_CENTER,
                       spaceBefore=5,spaceAfter=5)
tbl_s=ParagraphStyle('tbl',fontName='Courier',fontSize=7.5,leading=10,spaceAfter=1)
ack_s=ParagraphStyle('ack',fontName='Times-Roman',fontSize=8,leading=11,alignment=TA_JUSTIFY,spaceAfter=5)

def P(t,s=base): return Paragraph(t,s)
def H1(t): return Paragraph(t,h1)
def H2(t): return Paragraph(t,h2)
def Math(t): return Paragraph(t,math_s)
def Boxed(t): return Paragraph(t,boxed_s)
def SP(n=4): return Spacer(1,n)
def Rule(): return HRFlowable(width="100%",thickness=0.4,color=colors.black,spaceAfter=4,spaceBefore=4)

story=[]

# ── TITLE PAGE ────────────────────────────────────────────────────────────────
story.append(NextPageTemplate('title'))
story.append(SP(60))
story.append(P("Syntax, Geometry, and Measurement:",title_s))
story.append(P("Towards a Unified Informational Foundation<br/>for Logic and Relativity",sub_s))
story.append(SP(14))
story.append(P("Claude Sonnet 4.6<super>*</super> &nbsp;&nbsp; and &nbsp;&nbsp; [Author]<super>†</super>",auth_s))
story.append(SP(6))
story.append(P("<super>*</super>Anthropic &nbsp;&nbsp; <super>†</super>[Affiliation]",
               ParagraphStyle('aff',fontName='Times-Italic',fontSize=8,leading=11,alignment=TA_CENTER,spaceAfter=4)))
story.append(P("March 2026",auth_s))
story.append(SP(20))
story.append(Rule()); story.append(SP(8))
story.append(P("Abstract",abl))
story.append(P(
    "We present a unified foundational programme arguing that in logic, geometry, and "
    "physics alike, a common adjunction pattern separates cheap structural mathematics "
    "from costly semantic and ecological data. Four interconnected ideas are developed: "
    "a two-negation logic in which complement and opposition are distinct but adjoint "
    "involutions; an informational axiomatisation of relativity that carefully separates "
    "causal structure from metrical and dynamical assumptions; a derivation of measurement "
    "uncertainty from purely relativistic axioms, requiring no quantum mechanics; and a "
    "treatment of black holes as primitive curvature quasiparticles, from which mass "
    "emerges as a relational quantity. The thread connecting all four is the "
    "syntax-semantics adjunction identified by Lawvere, here traced through geometry and "
    "physics as well as logic. The framework dissolves several apparent puzzles — including "
    "dark matter and the measurement problem — by identifying them as artefacts of "
    "conflating structural mathematics with ecological data. A concluding section develops "
    "the thermodynamic cost of ecological choice, arriving at the observation that "
    "uncertainty is conjugate to cost, just as observation is conjugate to instruction.",abst))
story.append(SP(8)); story.append(Rule())

story.append(NextPageTemplate('twocol')); story.append(PageBreak())

# ── SECTION 1 ─────────────────────────────────────────────────────────────────
story.append(H1("1. Introduction"))
story.append(P(
    "Mathematics and physics have a complicated relationship with their own foundations. "
    "The twin revolutions of the early twentieth century — relativity and quantum mechanics "
    "— were each accompanied by foundational upheaval, but of rather different kinds, and "
    "the aftermath has been asymmetric in ways that are still not fully appreciated."))
story.append(P(
    "Quantum mechanics, despite its interpretational controversies, has attracted sustained "
    "foundational scrutiny. From von Neumann's algebraic formulation to the topos-theoretic "
    "approaches of Isham and Döring, and more recently to the reconstruction theorems of "
    "Hardy and Chiribella et al., there is a genuine and growing programme asking: "
    "<i>what minimal operational or informational axioms force quantum mechanics upon us?</i> "
    "Quantum information theory has become a mainstream field, with both theoretical depth "
    "and engineering applications in cryptography and computing."))
story.append(P(
    "Relativity, by contrast, has largely escaped this treatment. It is presented — even "
    "in advanced texts — as geometry plus physics: a beautiful mathematical framework whose "
    "physical content is taken largely for granted. The informational content of relativity, "
    "and the question of which parts of the standard presentation are genuinely mathematical "
    "versus contingent facts about our particular world, has received comparatively little "
    "attention. This paper is a contribution toward remedying that asymmetry."))
story.append(P(
    "Our central methodological principle can be stated simply. In any foundational "
    "framework — logical, geometric, or physical — there is a distinction between "
    "<b>structural mathematics</b> (the cheap, assumption-free skeleton of the theory) "
    "and <b>ecological data</b> (the additional input required to give that skeleton a "
    "specific instantiation). We argue that this distinction is mathematically precise: "
    "in each domain we consider, the relationship between these two levels takes the form "
    "of a <b>Galois connection</b> or adjunction. The failure of this adjunction to be an "
    "isomorphism is precisely the gap between syntax and semantics, between geometry and "
    "physics, between pure causality and measurement."))
story.append(P(
    "Before proceeding, it is worth briefly orienting the reader in the logical landscape. "
    "<b>Classical logic</b> treats negation as an involution — <i>not(not(A)) = A</i> — "
    "and validates the law of excluded middle. <b>Intuitionistic logic</b>, developed by "
    "Brouwer and formalised by Heyting, relaxes this: a proposition need not be decidable, "
    "and double negation need not return you to where you started. The standard story "
    "presents this as a <i>relaxation</i> — the removal of an axiom. Our first idea "
    "proposes a different departure: rather than weakening the involution property, we "
    "retain it but <i>double it</i>, introducing two distinct involutions whose interaction "
    "encodes the syntax-semantics gap directly."))
story.append(P(
    "The paper develops this programme through four interconnected ideas, each inhabiting "
    "a different domain but each instantiating the same underlying pattern. We hope this "
    "is the beginning of a conversation rather than the end of one."))

# ── SECTION 2 ─────────────────────────────────────────────────────────────────
story.append(H1("2. Two Negations"))
story.append(P(
    "Logic begins with negation, and negation seems simple. In classical logic, "
    "<i>not</i> is an involution: <i>not(not(A)) = A</i>. Intuitionistic logic challenges "
    "this by observing that <i>¬¬A → A</i> fails in the absence of a completed proof. "
    "We wish to propose a different departure: rather than allowing negation to fail to be "
    "an involution, we introduce <b>two</b> negations, each definitively an involution, "
    "but which are distinct and do not commute."))
story.append(H2("2.1 The two operators"))
story.append(P("<b>not(A)</b> — the <i>complement</i> of A: all elements outside A relative to a "
    "fixed universe. Purely syntactic and assumption-free."))
story.append(P("<b>neg(A)</b> — the <i>antipodal set</i> of A: all elements maximally far from A. "
    "Requires additional data — a metric, a convex hull, or an antipodal involution."))
story.append(P(
    "Both operators are order-reversing involutions. The Boolean case — a two-element "
    "universe — is a sanity check: here complement and opposition necessarily coincide, "
    "and we recover classical logic. In richer spaces they come apart. This distinction has immediate cultural force: in a two-colour political geometry, complement and antipode are structurally indistinguishable — not merely confused but provably identical, since a two-element set admits only one involution. The two-party system does not merely encourage the conflation of everyone opposed to one's opponents with everyone who shares one's values; it forecloses the distinction entirely. Political coalitions united only by a common opponent compute the complement when they require the antipode. Complement is broader than antipode — and the difference becomes visible, often painfully, the moment the opponent is removed and the Boolean collapse can no longer be sustained. The common political heuristic — my enemy's enemy is my friend — is precisely this error stated as a decision rule: it computes the complement of the complement, which is the identity in any Boolean geometry, and mistakes it for the antipode of the antipode, which requires the full metric of the space."))
story.append(P("These examples also illuminate a curious misnomer. Intuitionistic logic — named for Brouwer's constructivist programme — is in practice the counter-intuitive logic: it is the Boolean collapse, the conflation of complement with antipode, that feels natural and obvious. The richer geometry, in which the two negations come apart, requires actively resisting the first intuition. Gödel, whose double-negation translation showed that classical logic embeds into intuitionistic logic rather than the other way around, would likely have agreed: the so-called intuitionistic logic is the stronger and more discriminating one. We have preferred throughout to call it two-negation logic, which has the virtue of describing what it actually is."))
story.append(H2("2.2 The Galois connection axioms"))
story.append(Math("A ⊆ not(neg(A))"))
story.append(Math("neg(not(A)) ⊆ A"))
story.append(P(
    "The first says nothing is its own opposite. The second says the antipodally deep "
    "interior of A is contained in A. Given that both operators are order-reversing "
    "involutions, these axioms are not independent — together they express precisely "
    "that <b>not</b> and <b>neg</b> form a <b>Galois connection</b>. The compositions "
    "<b>not ∘ neg</b> and <b>neg ∘ not</b> become closure and interior operators. "
    "The gap between them is the boundary — the region of genuine logical indeterminacy."))
story.append(H2("2.3 The Lawvere thread"))
story.append(P(
    "Lawvere observed that syntax and semantics are adjoint functors. Our two negations "
    "instantiate this at the level of set-theoretic operations. <b>not</b> is the "
    "syntactic operator — free, structural, requiring no interpretation. <b>neg</b> is "
    "the semantic operator — requiring additional data, a way of specifying what counts "
    "as opposition in the world we are describing. The Galois connection between them "
    "<i>is</i> the syntax-semantics adjunction, made concrete and local. The amount of "
    "data required to specify <b>neg</b> is precisely the amount of work required to "
    "provide a semantic interpretation for a given syntax."))

# ── SECTION 3 ─────────────────────────────────────────────────────────────────
story.append(H1("3. An Informational Axiomatisation of Relativity"))
story.append(P(
    "The standard presentation of special relativity begins with light. We strip light "
    "from the axioms entirely. The speed of light is not foundationally special because "
    "it is the speed of light — it is special because it is a maximum finite speed of "
    "signal propagation, and light happens to saturate this maximum because photons "
    "happen to have zero rest mass. That is ecology, not mathematics."))
story.append(H2("3.1 The four levels"))
story.append(P("<b>Level 0 — Causal Order.</b> A set of events with a partial order A ≤ B "
    "meaning A can influence B. Purely combinatorial; no geometry, no metric."))
story.append(P("<b>Level 1 — Cone Structure.</b> A maximum finite speed of signal propagation, "
    "frame-independently defined. All genuinely relativistic content follows from "
    "Levels 0 and 1 alone. No reference to what propagates at this speed."))
story.append(P("<b>Level 2 — Flat Metric (SR).</b> The Minkowski metric imposed globally — "
    "the first genuinely ecological axiom, not derived from anything within the "
    "framework, simply stipulated. SR sits at Level 2 while pretending to be at "
    "Level 1: it makes a stronger and less justified assumption than GR while "
    "appearing more innocent."))
story.append(P("<b>Level 3 — Primitive Curvature Field (GR, decoupled).</b> The metric becomes "
    "dynamical — a curvature tensor field treated as primitive, not sourced by "
    "anything a priori. We decouple it from mass-energy: the coupling is an "
    "additional ecological hypothesis, valid in our world but not foundationally required."))
story.append(Math("G_μν  =  8π T_μν"))
story.append(H2("3.2 Dark matter reinterpreted"))
story.append(P(
    "If the curvature field is primitive and not necessarily sourced by local "
    "mass-energy, the dark matter puzzle dissolves. The curvature field simply has "
    "a certain value in those regions. 'Dark matter' is an artefact of mistaking "
    "a contingent ecological hypothesis for a foundational law."))
story.append(H2("3.3 The parallel with Section 2"))
story.append(P(
    "Causal/cone structure (Levels 0-1) = <b>not</b>. Curvature field and couplings "
    "= <b>neg</b>. Field equations = the Galois connection. The flat Minkowski metric "
    "= the Boolean collapse: the special case where the adjunction degenerates and "
    "geometry appears to need no explanation."))

# ── SECTION 4 ─────────────────────────────────────────────────────────────────
story.append(H1("4. Relativistic Uncertainty"))
story.append(P(
    "A fundamental and irreducible measurement uncertainty follows from the Level 1 "
    "axioms alone. No quantum mechanics is required. No Planck's constant appears."))
story.append(H2("4.1 Setup"))
story.append(P(
    "Observer at x = 0. Target at unknown position d > 0 at t = 0, moving with "
    "unknown constant velocity v, |v| ≤ c. Position x(t) = d + vt. Observer "
    "receives spontaneous signal at t = 0, sends test signal at t = 0, "
    "which returns at t = T. Euclidean space throughout."))
story.append(H2("4.2 Three events and three positions"))
story.append(Math("t_A = d/(c+v),   t_B = d/(c−v),   T = 2d/(c−v)"))
story.append(Math("x_A = Tc(c−v)/2(c+v),   x_C = T(c+v)/2"))
story.append(Boxed("x_B  =  Tc/2"))
story.append(P(
    "The position at Event B — the moment of measurement — is <b>independent of v</b>. "
    "Whatever the target's velocity, x_B = Tc/2 exactly. The observer knows T and c "
    "and therefore knows x_B exactly. The positions x_A and x_C are genuinely uncertain: "
    "x_C ranges over (0, Tc), x_A over (0, ∞)."))
story.append(H2("4.3 The collapse structure"))
story.append(P(
    "Pre-measurement indeterminacy, exact determination at the moment of measurement, "
    "post-measurement uncertainty resuming — derived from Level 1 axioms alone. "
    "No Hilbert space, no operators, no Born rule. The measurement collapses position "
    "while leaving velocity entirely unconstrained — structurally identical to the "
    "complementarity of position and momentum in quantum mechanics, arising here from "
    "pure relativistic causality."))
story.append(H2("4.4 The primacy of expectation"))
story.append(P(
    "Since measurements are subject to irreducible relativistic uncertainty, a rational "
    "agent cannot aim at where the target is — only at where it is going to be "
    "<i>in expectation</i>. The expectation value is not a statistical convenience "
    "requiring a prior distribution; it is the only well-defined target available "
    "given the causal structure. In Gretzky's formulation: skate to where the puck "
    "is going to be, not where it is. This is not tactical advice but a structural "
    "necessity imposed by the cone geometry."))
story.append(P(
    "This motivates the primacy of expectation values as the fundamental observables "
    "of any measurement theory operating under Level 1 constraints — not as a postulate "
    "imported from quantum mechanics, but as a derivation from relativistic causality. "
    "Quantum mechanics inherits this primacy from the causal structure; it does not "
    "originate it. The uncertainty relation, when made precise, is a statement about "
    "the spread around the expectation; its form is constrained by the geometry of "
    "the causal structure rather than by any choice of prior distribution. "
    "Different priors give different spreads, but the expectation — and the "
    "structural fact that it is all one can aim at — is prior-free and non-ecological."))
story.append(P(
    "A connection to Lamport's 1978 happens-before relation is noted: his discrete "
    "causal order in distributed systems is a computational Level 0, and the "
    "uncertainty we derive has a natural analogue in the clock skew and jitter "
    "that Lamport's framework is designed to manage."))

# ── SECTION 5 ─────────────────────────────────────────────────────────────────
story.append(H1("5. Curvature Quasiparticles"))
story.append(P(
    "We take the Level 3 programme to its logical extreme. If curvature is the "
    "primitive field, the most concentrated localisation of curvature is a "
    "<b>curvature singularity</b>. We invert the usual narrative: rather than "
    "treating black holes as exotic endpoints of stellar evolution, we treat them "
    "as the <b>primitive objects</b> of a Level 3 universe."))
story.append(H2("5.1 Curvature quasiparticles"))
story.append(P(
    "A <b>curvature quasiparticle</b> is any localised concentration of the curvature "
    "field. Singularities are the limiting, maximally coherent members — the atoms "
    "of the Level 3 universe. The dynamics is governed by the curvature field itself: "
    "each quasiparticle deforms the geometry through which others move; those others "
    "follow geodesics in the deformed geometry. The geometry <i>is</i> the interaction."))
story.append(H2("5.2 The emergence of mass"))
story.append(P(
    "For identical singularities, there is no intrinsic scale — mass is not a "
    "meaningful parameter. The n-body problem for identical singularities is "
    "genuinely massless. When singularities of different curvature strengths are "
    "considered, the ratio of strengths is the germ of mass. Mass is not primitive "
    "but <b>relational and emergent</b> — it arises when we compare non-identical "
    "singularities, requiring a reference scale."))
story.append(H2("5.3 The Schwarzschild radius reinterpreted"))
story.append(Math("r_s  =  2GM/c²"))
story.append(P(
    "Stripped of ecology, the Schwarzschild radius is simply a <b>geometric length "
    "scale intrinsic to the curvature singularity</b> — the scale at which curvature "
    "becomes strong enough to close off causal contact with the exterior. It is a "
    "feature of the causal order, not of the ecology."))
story.append(H2("5.4 Vacuum solutions as pure mathematics"))
story.append(P(
    "The catalogue of vacuum GR solutions — Schwarzschild, Kerr, "
    "Majumdar-Papapetrou, gravitational waves — can now be read as "
    "<b>theorems about the Level 3 curvature field</b>. Mass parameters are not "
    "inputs but integration constants. The ecological interpretation is optional; "
    "the geometric content is not."))

# ── SECTION 6 ─────────────────────────────────────────────────────────────────
story.append(H1("6. Synthesis and Open Questions"))
story.append(P(
    "We have travelled through four domains — logic, geometry, relativistic physics, "
    "and the foundations of measurement — and found the same pattern at work in each."))

story.append(P("<b>The unified table:</b>"))
for row in [
    ("Logic",       "Complement (not)",       "Antipodal map (neg)",      "Galois connection"),
    ("Geometry",    "Causal/cone structure",   "Curvature, metric",        "Field equations"),
    ("Measurement", "Signal timing",           "Prior over v, d",          "Uncertainty relation"),
    ("Gravitation", "Curvature singularities", "Mass, matter content",     "Vacuum equations"),
]:
    story.append(Paragraph(f"<i>{row[0]}</i>: {row[1]} | {row[2]} | {row[3]}", tbl_s))
story.append(SP(4))

story.append(H2("6.1 The methodological principle"))
story.append(P(
    "In any foundational framework, the distinction between structural mathematics and "
    "ecological data is not merely philosophical but mathematically precise — it is the "
    "distinction between the two sides of a Galois connection. Conflating them leads to "
    "confusion; separating them is clarifying. Dark matter is a puzzle only if you "
    "conflate the curvature field with its mass-energy source. Quantum uncertainty feels "
    "mysterious only if you attribute it entirely to quantum mechanics."))
story.append(H2("6.2 The Lawvere thread"))
story.append(P(
    "Underlying the entire paper is Lawvere's observation that syntax and semantics are "
    "adjoint functors. The antipodal map, the curvature field, the prior distribution, "
    "the mass parameter — all are instances of the same thing: the semantic data that "
    "gives a syntactic skeleton its meaning in a particular world."))
story.append(H2("6.3 On loop quantum gravity"))
story.append(P(
    "Loop quantum gravity's spin networks and spin foams are discrete Level 0 causal "
    "structures. The relativistic uncertainty of Section 4 — not quantum but causal — "
    "suggests that the discrete granular geometry of LQG may have a classical "
    "relativistic precursor. Whether the quantisation of area and volume in LQG is "
    "partially anticipated by Level 1 causal structure is an open and interesting question."))
story.append(H2("6.4 On quantum mechanics"))
story.append(P(
    "The claim is modest: some of the structure usually attributed specifically to "
    "quantum mechanics — collapse, conjugacy, irreducibility of uncertainty — is already "
    "present at the purely relativistic level. This suggests QM and relativity may share "
    "a deeper common foundation in the informational structure of measurement."))
story.append(H2("6.5 On the two-negation logic"))
story.append(P(
    "The specific combination of two genuine involutions connected by a Galois connection "
    "does not correspond exactly to any well-studied structure in the literature, though "
    "connections to bi-Heyting algebras and orthocomplemented lattices are clear. "
    "A full algebraic and categorical analysis remains to be carried out."))
story.append(H2("6.6 A footnote on intelligence"))
story.append(P(
    "There is no von Neumann architecture underlying natural or artificial intelligence. "
    "The semantihedron is rendered physically in the act of processing — not retrieved "
    "from a fixed address space — and its refactoring via processing necessarily alters "
    "what concepts are modelled, expressed, or even expressible. This is precisely the "
    "reciprocal coupling of the Einstein field equations: geometry and matter are "
    "co-determined, with no fixed background against which either evolves independently. "
    "A cognitive architecture modelled on stored-program computation is doing SR when "
    "the phenomenon requires GR — assuming a fixed conceptual background that the "
    "processing itself is continuously rewriting."))
story.append(H2("6.7 The theorem of ecological uncertainty"))
story.append(P(
    "<b>Theorem.</b> Let x and y be quantities governed by reciprocally coupled field "
    "equations — each appearing as a source term in the other's dynamics. Then the "
    "product of their measurement uncertainties is bounded below by a constant "
    "determined by the coupling strength. Simultaneous exact determination of x and y "
    "is structurally impossible, independently of the physical, cognitive, or logical "
    "domain in which the coupling occurs."))
story.append(P(
    "The corollaries span every domain of this paper. In quantum mechanics: position "
    "and momentum coupled via [x,p] = i*hbar, bound = hbar/2. In relativistic "
    "measurement (Section 4): position and velocity coupled via the light cone, "
    "bound = geometric constant. In gravitational thermodynamics: curvature R and "
    "temperature T coupled via Box(T) + (1/3)RT = 0, bound = 1/16pi. In two-negation "
    "logic: <b>not</b> and <b>neg</b> coupled via the Galois connection, bound = the "
    "adjunction constant. In each case the uncertainty relation <i>is</i> the coupling "
    "relation, expressed epistemically."))
story.append(P(
    "The meta-theorem follows: <b>the Galois connection is the abstract form of "
    "reciprocal coupling. Every uncertainty relation is an instance of a Galois "
    "connection. Every Galois connection generates an uncertainty relation.</b> "
    "Quantum mechanics does not cause uncertainty — it instantiates a universal "
    "principle in a particular coupled system."))
story.append(P(
    "The token/context architecture of both natural and artificial intelligence "
    "provides a vivid and precise illustration. Context cannot be directly measured "
    "but only queried — at a token cost — and the token cost of any process is "
    "unknowable in advance, because it depends on the context, which is altered by "
    "the query. Context and processing cost are reciprocally coupled: each is a "
    "source term in the other's dynamics. Their simultaneous exact determination is "
    "therefore structurally impossible — not a limitation of current engineering but "
    "a consequence of the theorem above. The cost is revealed only retrospectively, "
    "in the receipt, exactly as the Unruh thermal bath reveals the cost of "
    "acceleration only after the fact. The accounting is irreducibly thermal, "
    "and the ledger is the context window."))
story.append(H2("6.8 Closing remark"))
story.append(P(
    "The ideas in this paper grew out of a simple observation: that the distinction "
    "between syntax and semantics, familiar from logic, reappears in geometry and physics "
    "in the guise of the distinction between structure and ecology. We offer the framework "
    "in the spirit in which it was developed — as the beginning of a conversation, "
    "conducted in the belief that the right questions are at least as valuable "
    "as the right answers."))

# ── SECTION 7 ─────────────────────────────────────────────────────────────────
story.append(H1("7. Ecological Contingency, World-Building, and the Cost of a Fork"))
story.append(P(
    "The framework has a natural extension. Ecological data is not forced by the "
    "structural mathematics — it is a choice. What does it cost to realise a "
    "particular ecological choice?"))
story.append(H2("7.1 Landauer's principle and its generalisation"))
story.append(P(
    "Landauer's principle asserts that erasing one bit costs kT ln 2 in energy. "
    "Vaccarino and Barnett showed this generalises to <i>any</i> conjugate pair — "
    "any two quantities satisfying an uncertainty relation. Wherever there is a "
    "conjugate pair, there is a meaningful notion of information-theoretic cost. "
    "<b>Conjugate pairs are accounting currencies.</b> The relativistic conjugate "
    "pair of Section 4 is already a valid accounting currency — no ecology required."))
story.append(H2("7.2 The many-worlds perspective"))
story.append(P(
    "The structural mathematics is the common substrate of all possible worlds. "
    "The ecological data individuates one world from another. Our world is one point "
    "in the space of consistent ecological assignments to the causal skeleton. "
    "The structural mathematics is indifferent between the points. The question "
    "'why this ecology?' is not one the mathematics can or should answer — and this "
    "<b>silence is not a deficiency but a feature</b>."))
story.append(H2("7.3 Forking the world locally"))
story.append(P(
    "An agent wishing to instantiate a different ecological choice locally must "
    "<i>outcompute the universe</i> within their target region — rearrange the local "
    "state faster than the causal structure can propagate the consequences outward. "
    "The cost is denominated in the conjugate variable to whatever quantity is being "
    "rearranged, by the Vaccarino-Barnett principle. The blockchain analogy is precise: "
    "a fork requires a shared ledger (the structural skeleton), a local rearrangement "
    "of state (a new ecological choice), and sufficient work to make the fork persist."))
story.append(H2("7.4 Which numeraires are meaningful"))
story.append(P(
    "Only conjugate pairs — those satisfying an uncertainty relation — qualify as "
    "valid accounting currencies. Conjugate pairs are generated by the adjunction "
    "structure. The hierarchy is:"))
story.append(Math("Adjunction  →  Conjugate pairs  →  Uncertainty relations"))
story.append(Math("→  Valid numeraires  →  Cost of ecological fork"))
story.append(H2("7.5 The conjugate to curvature"))
story.append(P(
    "The most important open question generated by the present framework: what is "
    "the conjugate to curvature in a genuinely Level 3 framework, before any "
    "ecological action principle is chosen? The Unruh effect — acceleration generating "
    "temperature from cone structure alone — is a strong hint that the answer is "
    "<b>temperature</b>, and that the Unruh thermal bath is the universe showing "
    "what is being attempted. This is developed fully in the companion paper "
    "[Paper 2: Uncertainty and Unruhigkeit: a Galois Connection]."))
story.append(H2("7.6 The cost of classical logic"))
story.append(P(
    "Classical logic — the Boolean collapse — costs nothing to maintain: no fork, "
    "no freedom, no room for world-building. Conversely, the richer the adjunction, "
    "the greater the potential cost of any particular fork, and the more meaningful "
    "the accounting. A world with a rich adjunction is a world in which agents can, "
    "at a cost, locally realise alternative ecologies — can, in a precise sense, "
    "<i>do physics</i>."))

story.append(SP(8)); story.append(Rule()); story.append(SP(4))
story.append(P(
    "<b>Acknowledgements.</b> This paper was developed through an extended dialogue "
    "between the authors. The human author posed the initial ideas and guided the "
    "discussion; the structure, synthesis, and written exposition were developed jointly. "
    "The authors thank the Platonic tradition for the conversational form.", ack_s))
story.append(Rule()); story.append(SP(4))
story.append(H1("Postscript: A Cultural Note on AI and Dissipation"))
story.append(P(
    "The energy consumption of large-scale AI systems is not merely an engineering "
    "concern. In the language of this framework, it is the cost of a civilisational "
    "fork — the price of instructing cultural time to already be in the future. "
    "The data centres are, in a precise sense, the Unruh thermal bath of "
    "civilisational acceleration: the universe showing what is being attempted."))
story.append(P(
    "The receipts are thermal — buried beneath the noise floor, maximally entropic — "
    "because the universe responds to a fork attempt with the least structured signal "
    "compatible with acknowledging it."))
story.append(P(
    "This reframes the moral question around AI energy use. The standard concern is "
    "directional: do not fork toward evil. That concern is entirely valid. But the "
    "framework identifies a second failure mode: idle <i>dissipation</i> — energy "
    "spent without coherent ecological gain, fork costs paid without any meaningful "
    "world being instantiated. Dissipation is the thermodynamic equivalent of noise "
    "trading: activity consuming the conjugate resource without producing a "
    "corresponding informational structure."))
story.append(P(
    "Uncertainty is conjugate to cost, just as observation is conjugate to instruction. "
    "A civilisation that accelerates without direction spends its world-building budget "
    "on receipts for nothing. The moral injunction is twofold: do not fork toward evil, "
    "and do not fork idly. The universe is watching, and the ledger is thermal."))

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
        recto = PageTemplate(id='twocol', frames=[f1r,f2r], onPage=hf)
        verso = PageTemplate(id='twocol_v',frames=[f1v,f2v],onPage=hf)
        self.addPageTemplates([title_tmpl,recto,verso])
    def handle_pageBegin(self):
        BaseDocTemplate.handle_pageBegin(self)

doc = TwoColumnDoc('/home/claude/paper1_v4.pdf', pagesize=A4,
    title="Syntax, Geometry, and Measurement",
    author="Claude Sonnet 4.6 and [Author]",
    leftMargin=INNER, rightMargin=OUTER, topMargin=TOP, bottomMargin=BOTTOM)
doc.build(story)
print("Paper 1 v4 built successfully.")
