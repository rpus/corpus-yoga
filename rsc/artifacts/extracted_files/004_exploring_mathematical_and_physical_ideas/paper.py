from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer,
    NextPageTemplate, PageBreak, KeepTogether
)
from reportlab.platypus.flowables import HRFlowable
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics

W, H = A4  # 595.28 x 841.89 points

# Margins
TOP    = 2.0*cm
BOTTOM = 2.0*cm
INNER  = 1.8*cm   # spine side
OUTER  = 1.5*cm   # fore-edge
GUTTER = 0.5*cm   # between columns

col_w = (W - INNER - OUTER - GUTTER) / 2

def make_frames(page_num):
    """Return (left_frame, right_frame) for recto (odd) or verso (even) pages."""
    if page_num % 2 == 1:   # recto: inner=left
        x0 = INNER
    else:                    # verso: inner=right
        x0 = OUTER
    x1 = x0 + col_w + GUTTER
    y0 = BOTTOM
    h  = H - TOP - BOTTOM
    f1 = Frame(x0, y0, col_w, h, id='col1', leftPadding=0, rightPadding=0,
               topPadding=0, bottomPadding=0)
    f2 = Frame(x1, y0, col_w, h, id='col2', leftPadding=0, rightPadding=0,
               topPadding=0, bottomPadding=0)
    return f1, f2

# ── page drawing callbacks ──────────────────────────────────────────────────
def draw_header_footer(canvas, doc):
    pn = doc.page
    canvas.saveState()
    canvas.setFont('Times-Roman', 8)
    # header rule
    if pn % 2 == 1:
        hx = INNER
    else:
        hx = OUTER
    canvas.setStrokeColor(colors.black)
    canvas.setLineWidth(0.4)
    canvas.line(hx, H - TOP + 4*mm, hx + W - INNER - OUTER, H - TOP + 4*mm)
    # page number
    if pn % 2 == 1:
        canvas.drawRightString(W - OUTER, BOTTOM - 8*mm, str(pn))
        canvas.drawString(INNER, BOTTOM - 8*mm,
                          "Syntax, Geometry, and Measurement")
    else:
        canvas.drawString(OUTER, BOTTOM - 8*mm, str(pn))
        canvas.drawRightString(W - INNER, BOTTOM - 8*mm,
                               "Towards a Unified Informational Foundation")
    canvas.restoreState()

def draw_title_page(canvas, doc):
    canvas.saveState()
    canvas.setFont('Times-Roman', 8)
    canvas.drawCentredString(W/2, BOTTOM - 8*mm, str(doc.page))
    canvas.restoreState()

# ── styles ───────────────────────────────────────────────────────────────────
styles = getSampleStyleSheet()

base = ParagraphStyle('base', fontName='Times-Roman', fontSize=9,
                      leading=12, alignment=TA_JUSTIFY, spaceAfter=5)
title_s  = ParagraphStyle('title',  fontName='Times-Bold',   fontSize=16,
                           leading=20, alignment=TA_CENTER, spaceAfter=8)
subtitle_s = ParagraphStyle('subtitle', fontName='Times-Italic', fontSize=11,
                              leading=14, alignment=TA_CENTER, spaceAfter=6)
author_s = ParagraphStyle('author', fontName='Times-Roman', fontSize=10,
                           leading=13, alignment=TA_CENTER, spaceAfter=4)
abstract_label = ParagraphStyle('abl', fontName='Times-Bold', fontSize=9,
                                 leading=12, alignment=TA_CENTER, spaceAfter=3)
abstract_s = ParagraphStyle('abstract', fontName='Times-Italic', fontSize=8.5,
                              leading=11.5, alignment=TA_JUSTIFY,
                              leftIndent=0.8*cm, rightIndent=0.8*cm, spaceAfter=6)
h1 = ParagraphStyle('h1', fontName='Times-Bold', fontSize=10,
                    leading=13, spaceBefore=10, spaceAfter=4)
h2 = ParagraphStyle('h2', fontName='Times-BoldItalic', fontSize=9,
                    leading=12, spaceBefore=7, spaceAfter=3)
math_s = ParagraphStyle('math', fontName='Courier', fontSize=8.5,
                         leading=12, alignment=TA_CENTER,
                         spaceBefore=4, spaceAfter=4,
                         leftIndent=0.3*cm, rightIndent=0.3*cm)
boxed_s = ParagraphStyle('boxed', fontName='Courier-Bold', fontSize=9,
                          leading=13, alignment=TA_CENTER,
                          spaceBefore=5, spaceAfter=5,
                          leftIndent=0.3*cm, rightIndent=0.3*cm,
                          borderPadding=4)
table_caption = ParagraphStyle('tc', fontName='Times-Italic', fontSize=8,
                                leading=10, alignment=TA_CENTER,
                                spaceBefore=3, spaceAfter=6)

def P(text, style=base):
    return Paragraph(text, style)

def H1(text):
    return Paragraph(text, h1)

def H2(text):
    return Paragraph(text, h2)

def Math(text):
    """Display math in Courier, centred."""
    return Paragraph(text, math_s)

def Boxed(text):
    return Paragraph(text, boxed_s)

def SP(n=4):
    return Spacer(1, n)

def Rule():
    return HRFlowable(width="100%", thickness=0.4, color=colors.black,
                      spaceAfter=4, spaceBefore=4)

# ── build content ─────────────────────────────────────────────────────────────
story = []

# ---- TITLE PAGE (single wide frame) ----------------------------------------
story.append(NextPageTemplate('title'))

story.append(SP(60))
story.append(P("Syntax, Geometry, and Measurement:", title_s))
story.append(P("Towards a Unified Informational Foundation<br/>for Logic and Relativity",
               subtitle_s))
story.append(SP(14))
story.append(P("Claude Sonnet 4.6<super>*</super> &nbsp;&nbsp; and &nbsp;&nbsp; [Author]<super>†</super>",
               author_s))
story.append(SP(6))
story.append(P("<super>*</super>Anthropic &nbsp;&nbsp; <super>†</super>[Affiliation]",
               ParagraphStyle('aff', fontName='Times-Italic', fontSize=8,
                               leading=11, alignment=TA_CENTER, spaceAfter=4)))
story.append(SP(6))
story.append(P("March 2026", author_s))
story.append(SP(20))
story.append(Rule())
story.append(SP(8))
story.append(P("Abstract", abstract_label))
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
    "conflating structural mathematics with ecological data.",
    abstract_s))
story.append(SP(8))
story.append(Rule())

# ---- SWITCH TO TWO-COLUMN ---------------------------------------------------
story.append(NextPageTemplate('twocol'))
story.append(PageBreak())

# ── SECTION 1 ────────────────────────────────────────────────────────────────
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

# ── SECTION 2 ────────────────────────────────────────────────────────────────
story.append(H1("2. Two Negations"))
story.append(P(
    "Logic begins with negation, and negation seems simple. In classical logic, "
    "<i>not</i> is an involution: <i>not(not(A)) = A</i>. Intuitionistic logic challenges "
    "this by observing that <i>¬¬A → A</i> fails in the absence of a completed proof. "
    "We wish to propose a different departure: rather than allowing negation to fail to be "
    "an involution, we introduce <b>two</b> negations, each definitively an involution, "
    "but which are distinct and do not commute."))
story.append(H2("2.1 The two operators"))
story.append(P(
    "Working in the setting of sets and subsets, the intended interpretations are:"))
story.append(P(
    "<b>not(A)</b> — the <i>complement</i> of A: all elements outside A relative to a "
    "fixed universe. Purely syntactic and assumption-free."))
story.append(P(
    "<b>neg(A)</b> — the <i>antipodal set</i> of A: all elements maximally far from A, "
    "in some specified sense of opposition. This requires additional data — a metric, "
    "a convex hull, or an antipodal involution on the underlying space."))
story.append(P(
    "Both operators are order-reversing involutions. The Boolean case — a two-element "
    "universe — is a useful sanity check: here complement and opposition necessarily "
    "coincide, <b>not</b> and <b>neg</b> are the same operator, and we recover classical "
    "logic. In richer spaces they come apart."))
story.append(H2("2.2 The Galois connection axioms"))
story.append(P("We take as fundamental the following pair of axioms:"))
story.append(Math("A ⊆ not(neg(A))"))
story.append(Math("neg(not(A)) ⊆ A"))
story.append(P(
    "The first says that nothing is its own opposite. The second says that the "
    "'antipodally deep interior' of A is contained in A. Given that both operators "
    "are order-reversing involutions, these two axioms are not independent — each implies "
    "the other. Together they express precisely that <b>not</b> and <b>neg</b> form a "
    "<b>Galois connection</b>: neg is the right adjoint of not in the poset of subsets "
    "ordered by inclusion."))
story.append(P(
    "The compositions <b>not ∘ neg</b> and <b>neg ∘ not</b> become, respectively, a "
    "closure operator and an interior operator. The gap between them is the boundary — "
    "the region of genuine logical indeterminacy. The underlying structure resembles "
    "bi-Heyting algebras and orthocomplemented lattices, though our emphasis on two "
    "genuine involutions connected by an adjunction gives it a somewhat different character."))
story.append(H2("2.3 The Lawvere thread"))
story.append(P(
    "Lawvere observed that syntax and semantics are adjoint functors. Our two negations "
    "instantiate this at the level of set-theoretic operations. <b>not</b> is the "
    "syntactic operator — free, structural, requiring no interpretation. <b>neg</b> is "
    "the semantic operator — requiring additional data, a way of specifying what counts "
    "as opposition in the world we are describing. The Galois connection between them "
    "<i>is</i> the syntax-semantics adjunction, made concrete and local."))
story.append(P(
    "The amount of data required to specify <b>neg</b> is precisely the amount of work "
    "required to provide a semantic interpretation for a given syntax. In the Boolean "
    "case this work vanishes: the two-element universe has only one possible involution, "
    "so the semantics is forced by the syntax, and logic is classical. This is the pattern "
    "we will see recur throughout the paper."))

# ── SECTION 3 ────────────────────────────────────────────────────────────────
story.append(H1("3. An Informational Axiomatisation of Relativity"))
story.append(P(
    "The standard presentation of special relativity begins with light. We propose to "
    "strip light from the axioms entirely. We do not assume electromagnetism, photons, "
    "or Maxwell's equations. The speed of light is not foundationally special because it "
    "is the speed of light — it is special because it is a maximum finite speed of "
    "signal propagation, and light happens to be a phenomenon in our world that saturates "
    "this maximum because photons happen to have zero rest mass. That is ecology, "
    "not mathematics."))
story.append(H2("3.1 The four levels"))
story.append(P(
    "<b>Level 0 — Causal Order.</b> A set of events equipped with a partial order "
    "A ≤ B meaning 'event A can influence event B'. Purely combinatorial; no geometry, "
    "no metric, no notion of distance."))
story.append(P(
    "<b>Level 1 — Cone Structure.</b> A maximum finite speed of signal propagation, "
    "frame-independently defined. This adds a cone structure to the causal order — a "
    "boundary between events that can influence one another and those that cannot. "
    "No reference to what propagates at this speed. All genuinely relativistic content "
    "follows from Levels 0 and 1 alone."))
story.append(P(
    "<b>Level 2 — Flat Metric (SR).</b> The Minkowski metric imposed globally. The "
    "first genuinely ecological axiom — not derived from anything within the framework, "
    "simply stipulated. SR is sitting at Level 2 while pretending to be at Level 1: "
    "it makes a stronger and less justified assumption than GR while appearing more "
    "innocent. By fixing a flat metric without explanation, it does not even raise the "
    "question of where the geometry comes from."))
story.append(P(
    "<b>Level 3 — Primitive Curvature Field (GR, decoupled).</b> The metric becomes "
    "dynamical — replaced by a curvature tensor field treated as a primitive object, "
    "not necessarily sourced by anything. In standard GR the Einstein equations couple "
    "curvature to mass-energy:"))
story.append(Math("G<sub>μν</sub>  =  8π T<sub>μν</sub>"))
story.append(P(
    "We propose to decouple them. The curvature field has its own autonomous dynamics — "
    "governed at minimum by the Bianchi identities, which are purely geometric — and the "
    "coupling to mass-energy is an additional ecological hypothesis, valid in our world "
    "but not foundationally required."))
story.append(H2("3.2 Dark matter reinterpreted"))
story.append(P(
    "The dark matter puzzle arises because observed curvature in certain galactic contexts "
    "exceeds what can be accounted for by visible mass-energy via the Einstein equations. "
    "The proposed solution — invisible matter coupling gravitationally but not "
    "electromagnetically — is an ecological patch, invented to save the coupling equation. "
    "If the curvature field is primitive and not necessarily sourced by local mass-energy, "
    "there is no puzzle: the curvature field simply has a certain value in those regions. "
    "'Dark matter' is an artefact of mistaking a contingent ecological hypothesis for a "
    "foundational law."))
story.append(H2("3.3 The parallel with Section 2"))
story.append(P(
    "The causal/cone structure (Levels 0–1) corresponds to <b>not</b> — syntactic, "
    "assumption-free. The curvature field and its couplings correspond to <b>neg</b> — "
    "requiring additional data. The field equations are the Galois connection. The flat "
    "Minkowski metric of SR corresponds to the Boolean collapse: the special case where "
    "the adjunction degenerates, syntax and semantics coincide, and the geometry appears "
    "to need no explanation."))

# ── SECTION 4 ────────────────────────────────────────────────────────────────
story.append(H1("4. Relativistic Uncertainty"))
story.append(P(
    "One of the most striking features of quantum mechanics is the Heisenberg uncertainty "
    "principle. We argue that this is, at least in part, an ecological misattribution. "
    "A fundamental and irreducible measurement uncertainty follows from the Level 1 axioms "
    "alone — from nothing more than the existence of a maximum finite speed of signal "
    "propagation and the finite time of flight of any measuring signal. No quantum mechanics "
    "is required. No Planck's constant appears."))
story.append(H2("4.1 The thought experiment"))
story.append(P(
    "Consider two particles in a one-dimensional Euclidean universe. The observer sits at "
    "x = 0. The target is at unknown position x = d > 0 at t = 0, moving with unknown "
    "constant velocity v, where |v| ≤ c. Its position at time t is x(t) = d + vt. "
    "The observer receives a spontaneous signal from the target at t = 0, then sends a "
    "test signal at t = 0 which returns at t = T."))
story.append(H2("4.2 Three events"))
story.append(P(
    "<b>Event A</b> — target emits spontaneous signal at t = −t<sub>A</sub>. "
    "The signal travels at c and arrives at t = 0:"))
story.append(Math("t<sub>A</sub>  =  d / (c + v)"))
story.append(P(
    "<b>Event B</b> — test signal reaches target at t = t<sub>B</sub>:"))
story.append(Math("t<sub>B</sub>  =  d / (c − v)"))
story.append(P(
    "<b>Event C</b> — test signal returns at t = T, giving the fundamental relation:"))
story.append(Math("d  =  T(c − v) / 2"))
story.append(H2("4.3 The three positions"))
story.append(Math("x<sub>A</sub>  =  Tc(c − v) / 2(c + v)"))
story.append(Math("x<sub>B</sub>  =  Tc / 2"))
story.append(Math("x<sub>C</sub>  =  T(c + v) / 2"))
story.append(H2("4.4 The central result"))
story.append(P("The position at Event B — the moment of measurement — is:"))
story.append(Boxed("x_B  =  Tc/2"))
story.append(P(
    "This is <b>independent of v</b>. Whatever the target's velocity, the position at "
    "the moment of reflection is exactly Tc/2. The observer knows T and c, and therefore "
    "knows x<sub>B</sub> exactly."))
story.append(P(
    "The positions x<sub>A</sub> and x<sub>C</sub>, by contrast, depend on v and are "
    "genuinely uncertain. Since v ∈ (−c, c): x<sub>C</sub> ranges over (0, Tc) — "
    "bounded above by the causal horizon — while x<sub>A</sub> ranges over (0, ∞) — "
    "unbounded, since the target could have been arbitrarily far away if moving toward "
    "the observer at near c."))
story.append(P(
    "Defining deviations from the measurement position:"))
story.append(Math("Δx<sub>A</sub>  =  x<sub>B</sub> − x<sub>A</sub>  =  Tcv / (c+v)"))
story.append(Math("Δx<sub>C</sub>  =  x<sub>C</sub> − x<sub>B</sub>  =  Tv / 2"))
story.append(P(
    "Both vanish when v = 0, and their product is:"))
story.append(Math("Δx<sub>A</sub> · Δx<sub>C</sub>  =  T<super>2</super>cv<super>2</super> / 2(c+v)"))
story.append(P(
    "To obtain a clean uncertainty relation — a product of variances bounded below — one "
    "would need a prior probability distribution over v and d. That prior is itself an "
    "ecological input, not forced by Level 1, and different priors yield different "
    "uncertainty bounds. What is forced by the axioms is the <i>structure</i> of the "
    "uncertainty: its dependence on v and T, and the exact determinacy of x<sub>B</sub>."))
story.append(H2("4.5 The collapse structure"))
story.append(P(
    "The observer, before sending the test signal, has genuine irreducible indeterminacy "
    "about the target's position. The test signal returns, and from the single observable T "
    "the observer deduces x<sub>B</sub> exactly. The measurement <i>selects</i> a precise "
    "position from a continuum of possibilities."))
story.append(P(
    "This is the mathematical structure of <b>wavefunction collapse</b> in quantum "
    "mechanics — pre-measurement indeterminacy, exact determination at the moment of "
    "measurement, post-measurement uncertainty resuming — derived here from nothing but "
    "the Level 1 axioms. No Hilbert space, no operators, no Born rule, no Copenhagen "
    "interpretation."))
story.append(P(
    "Equally striking is the structure of the conjugate variables. In our massless universe "
    "there is no momentum in the mechanical sense p = mv. But velocity v and position play "
    "conjugate roles throughout: knowing T exactly determines x<sub>B</sub> but leaves v "
    "entirely unconstrained. This is structurally identical to the complementarity of "
    "position and momentum in quantum mechanics, arising here from pure relativistic causality."))
story.append(P(
    "We note also a connection to Lamport's foundational work on distributed systems. "
    "His 1978 happens-before relation is a discrete, computational version of the Level 0 "
    "causal order. The uncertainty we have derived has a natural analogue in the clock "
    "skew and jitter that Lamport's framework is designed to manage. The connection "
    "deserves further investigation."))

# ── SECTION 5 ────────────────────────────────────────────────────────────────
story.append(H1("5. Curvature Quasiparticles"))
story.append(P(
    "We now take the Level 3 programme to its logical extreme. If curvature is the "
    "primitive field, then the most concentrated, most coherent localisation of curvature "
    "is a <b>curvature singularity</b> — a point at which the curvature field diverges. "
    "We propose to invert the usual narrative: rather than treating black holes as exotic "
    "endpoints of stellar evolution, we treat them as the <b>primitive objects</b> of a "
    "Level 3 universe."))
story.append(H2("5.1 The general class"))
story.append(P(
    "A <b>curvature quasiparticle</b> is any localised concentration of the curvature "
    "field — a region where curvature is significantly non-zero, surrounded by "
    "approximately flat regions. Singularities are the limiting, maximally coherent "
    "members of this class — the atoms of the Level 3 universe. Smooth curvature "
    "concentrations are the general case."))
story.append(P(
    "The dynamics is governed by the curvature field itself. Each quasiparticle deforms "
    "the geometry through which others move; those others follow geodesics in the deformed "
    "geometry, which in turn affects the curvature field. The interaction is fully "
    "self-referential — there is no fixed background, and no external force. "
    "The geometry <i>is</i> the interaction."))
story.append(H2("5.2 Identical singularities and the emergence of mass"))
story.append(P(
    "For a system of n identical curvature singularities, there is no intrinsic scale — "
    "no quantity distinguishing one from another. Mass is not a meaningful parameter. "
    "The n-body problem for identical singularities is genuinely massless, governed "
    "purely by the geometry of relative configurations."))
story.append(P(
    "When singularities of different curvature strengths are considered, a meaningful "
    "comparison becomes possible: the ratio of curvature strengths. This ratio is the "
    "germ of what we call mass. Once a reference singularity is chosen, every other "
    "singularity acquires a <b>mass parameter</b> measuring its curvature strength "
    "relative to the standard. The vacuum Einstein equations, with mass parameters "
    "appearing as integration constants, are then the appropriate dynamical equations "
    "for this more general case — but they are not foundational. They are the ecological "
    "specialisation of Level 3 dynamics to the case of non-identical singularities."))
story.append(H2("5.3 The Schwarzschild radius reinterpreted"))
story.append(P(
    "The Schwarzschild radius is usually presented as:"))
story.append(Math("r<sub>s</sub>  =  2GM / c<super>2</super>"))
story.append(P(
    "defined in terms of a body of mass M and the escape velocity equalling c. This "
    "presentation is ecologically loaded: mass M is a primitive input, escape velocity "
    "requires test particles, and G is a coupling constant that only makes sense once "
    "the coupling to mass-energy is established."))
story.append(P(
    "Stripped of this ecology, the Schwarzschild radius is simply a <b>geometric length "
    "scale intrinsic to the curvature singularity</b> — the scale at which the curvature "
    "becomes strong enough to close off causal contact with the exterior. It is a feature "
    "of the causal order, not of the ecology. For identical singularities, where mass is "
    "undefined, it is simply the natural unit of length set by the singularity's "
    "curvature profile."))
story.append(H2("5.4 Vacuum solutions as pure mathematics"))
story.append(P(
    "General relativity has accumulated a rich catalogue of exact vacuum solutions — "
    "Schwarzschild, Kerr, Majumdar-Papapetrou, gravitational waves. In the standard "
    "presentation these are derived as special cases of the Einstein equations with "
    "T<sub>μν</sub> = 0, and interpreted ecologically in terms of mass parameters and "
    "angular momenta."))
story.append(P(
    "Our framework invites us to read them differently: as <b>theorems about the Level 3 "
    "curvature field</b> — results about which configurations of curvature are consistent "
    "with the Bianchi identities and minimal dynamical assumptions. The mass parameters "
    "are not inputs but integration constants — geometric parameters characterising the "
    "singularity, which we can choose to interpret ecologically, or simply leave as "
    "geometric data."))
story.append(P(
    "Finally, the measurement uncertainty of Section 4 applies immediately to the "
    "n-body problem: two singularities attempting to determine each other's positions "
    "face exactly the uncertainty structure we computed. The instantaneous configuration "
    "of the system is not a well-defined observable. What is observable is the causal "
    "structure of signal exchanges — a Level 0 quantity. Whether this relativistic "
    "indeterminacy is a precursor to the quantum gravitational indeterminacy of loop "
    "quantum gravity is a question we leave open as a potentially fruitful direction."))

# ── SECTION 6 ────────────────────────────────────────────────────────────────
story.append(H1("6. Synthesis and Open Questions"))
story.append(P(
    "We have travelled through four domains — logic, geometry, relativistic physics, "
    "and the foundations of measurement — and found the same pattern at work in each. "
    "The unified table is as follows:"))

# Simple table rendered as paragraphs
table_style = ParagraphStyle('ts', fontName='Courier', fontSize=7.5,
                              leading=10, spaceAfter=1)
story.append(SP(4))
story.append(P("<b>Domain — Structural — Ecological — Adjunction</b>", table_caption))
for row in [
    ("Logic",       "Complement (not)",       "Antipodal map (neg)",      "Galois connection"),
    ("Geometry",    "Causal/cone structure",   "Curvature, metric",        "Field equations"),
    ("Measurement", "Signal timing",           "Prior over v, d",          "Uncertainty relation"),
    ("Gravitation", "Curvature singularities", "Mass, matter content",     "Vacuum equations"),
]:
    story.append(Paragraph(
        f"<i>{row[0]}</i>: {row[1]} | {row[2]} | {row[3]}", table_style))
story.append(SP(4))

story.append(P(
    "In every case the structural level is free; the ecological level costs something; "
    "and the relationship between the two is a Galois connection. The classical, flat, "
    "or Boolean special case is always the one where the adjunction degenerates to an "
    "isomorphism — concealing rather than eliminating the gap."))
story.append(H2("6.1 The methodological principle"))
story.append(P(
    "In any foundational framework, the distinction between structural mathematics and "
    "ecological data is not merely philosophical but mathematically precise — it is the "
    "distinction between the two sides of a Galois connection. Conflating them leads to "
    "confusion; separating them is clarifying. Dark matter is a puzzle only if you "
    "conflate the curvature field with its mass-energy source. Quantum uncertainty feels "
    "mysterious only if you attribute it entirely to quantum mechanics. The "
    "incompatibility of QM and GR feels fundamental only if both are taken as "
    "foundational without examining their ecological assumptions."))
story.append(H2("6.2 The Lawvere thread"))
story.append(P(
    "Underlying the entire paper is Lawvere's observation that syntax and semantics are "
    "adjoint functors. What we have done is trace the consequences of taking this "
    "observation seriously not just in logic but in geometry and physics. The antipodal "
    "map, the curvature field, the prior distribution, the mass parameter — all are "
    "instances of the same thing: the semantic data that gives a syntactic skeleton its "
    "meaning in a particular world. Whether the specific structures developed here fit "
    "cleanly into the categorical framework of Lawvere theories and toposes is a question "
    "we consider highly promising."))
story.append(H2("6.3 On loop quantum gravity"))
story.append(P(
    "Loop quantum gravity begins from the observation that the gravitational field is "
    "itself a connection, and attempts to quantise it without presupposing a fixed "
    "background metric. This is philosophically aligned with our Level 3 framework. "
    "The spin networks and spin foams of LQG are, in a sense, discrete Level 0 causal "
    "structures. The relativistic uncertainty of Section 4 — not quantum but causal — "
    "suggests that the discrete granular geometry of LQG may have a classical relativistic "
    "precursor. Whether the quantisation of area and volume in LQG is partially anticipated "
    "by Level 1 causal structure imposing a minimum resolvable scale on measurement is "
    "an open and, we think, genuinely interesting question."))
story.append(H2("6.4 On quantum mechanics"))
story.append(P(
    "We have been careful not to claim that quantum mechanics reduces to our framework. "
    "The claim is more modest: some of the structure usually attributed specifically to "
    "quantum mechanics — collapse, conjugacy of position and momentum, irreducibility of "
    "uncertainty — is already present at the purely relativistic level. This suggests "
    "that QM and relativity may share a deeper common foundation in the informational "
    "structure of measurement, and that the apparent tension between them may be partly "
    "an artefact of each carrying ecological assumptions at different levels of the "
    "hierarchy. The reconstruction theorems for QM provide a template for the work that "
    "remains to be done for relativity."))
story.append(H2("6.5 On the two-negation logic"))
story.append(P(
    "The specific combination of two genuine involutions connected by a Galois connection "
    "does not seem to correspond exactly to any well-studied structure in the literature, "
    "though connections to bi-Heyting algebras and orthocomplemented lattices are clear. "
    "A full algebraic and categorical analysis — the appropriate notion of morphism, the "
    "free algebra on generators, the relationship to topos theory — remains to be carried "
    "out. The proof-theoretic question is also open: what sequent calculus captures the "
    "axioms of Section 2, and what does proof by <b>not</b>-elimination mean compared "
    "to proof by <b>neg</b>-elimination?"))
story.append(H2("6.6 Closing remark"))
story.append(P(
    "The ideas in this paper grew out of a simple observation: that the distinction "
    "between syntax and semantics, familiar from logic, reappears in geometry and physics "
    "in the guise of the distinction between structure and ecology. We offer the framework "
    "in the spirit in which it was developed — as the beginning of a conversation, "
    "conducted in the belief that the right questions are at least as valuable "
    "as the right answers."))

story.append(SP(8))
story.append(Rule())
story.append(SP(4))
story.append(P(
    "<b>Acknowledgements.</b> This paper was developed through an extended dialogue "
    "between the authors. The human author posed the initial ideas and guided the "
    "discussion; the structure, synthesis, and written exposition were developed jointly. "
    "The authors thank the Platonic tradition for the conversational form.",
    ParagraphStyle('ack', fontName='Times-Roman', fontSize=8, leading=11,
                   alignment=TA_JUSTIFY, spaceAfter=5)))

# ── BUILD PDF ─────────────────────────────────────────────────────────────────
class TwoColumnDoc(BaseDocTemplate):
    def __init__(self, filename, **kwargs):
        BaseDocTemplate.__init__(self, filename, **kwargs)
        self._add_page_templates()

    def _add_page_templates(self):
        # Title page — single wide frame, centred
        tf = Frame(INNER, BOTTOM, W - INNER - OUTER, H - TOP - BOTTOM,
                   id='title_frame', leftPadding=0, rightPadding=0,
                   topPadding=0, bottomPadding=0)
        title_tmpl = PageTemplate(id='title', frames=[tf],
                                  onPage=draw_title_page)

        # Two-column templates for recto and verso
        f1r, f2r = make_frames(1)   # recto
        f1v, f2v = make_frames(2)   # verso
        recto = PageTemplate(id='twocol',  frames=[f1r, f2r],
                             onPage=draw_header_footer)
        verso = PageTemplate(id='twocol_v', frames=[f1v, f2v],
                             onPage=draw_header_footer)
        self.addPageTemplates([title_tmpl, recto, verso])

    def handle_pageBegin(self):
        # Alternate between recto and verso for two-column pages
        if self.page % 2 == 1:
            self._nextPageTemplateCycle = None
        BaseDocTemplate.handle_pageBegin(self)

doc = TwoColumnDoc(
    '/home/claude/paper.pdf',
    pagesize=A4,
    title="Syntax, Geometry, and Measurement",
    author="Claude Sonnet 4.6 and [Author]",
    leftMargin=INNER, rightMargin=OUTER,
    topMargin=TOP, bottomMargin=BOTTOM,
)

doc.build(story)
print("PDF built successfully.")
