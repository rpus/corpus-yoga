const {
  Document, Packer, Paragraph, TextRun, HeadingLevel,
  AlignmentType, LevelFormat, BorderStyle
} = require('docx');
const fs = require('fs');

function p(text, opts = {}) {
  return new Paragraph({
    spacing: { after: opts.after ?? 200 },
    indent: opts.indent ? { left: 720, right: 720 } : undefined,
    children: [new TextRun({
      text,
      font: "Arial",
      size: 24,
      italics: opts.italic ?? false,
      bold: opts.bold ?? false,
      color: opts.color ?? undefined
    })]
  });
}

function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    children: [new TextRun(text)]
  });
}

function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    children: [new TextRun(text)]
  });
}

function rule() {
  return new Paragraph({
    spacing: { before: 80, after: 80 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: "cccccc", space: 1 } },
    children: [new TextRun({ text: " ", size: 24 })]
  });
}

const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 24 } } },
    paragraphStyles: [
      {
        id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 36, bold: true, font: "Arial", color: "1a1a2e" },
        paragraph: { spacing: { before: 400, after: 200 }, outlineLevel: 0 }
      },
      {
        id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: "Arial", color: "2c3e7a" },
        paragraph: { spacing: { before: 280, after: 140 }, outlineLevel: 1 }
      },
    ]
  },
  numbering: {
    config: [{
      reference: "bullets",
      levels: [{
        level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 360 } } }
      }]
    }]
  },
  sections: [{
    properties: {
      page: {
        size: { width: 11906, height: 16838 },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
      }
    },
    children: [

      // Title block
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 480, after: 120 },
        children: [new TextRun({ text: "6: The First Perfect Number", bold: true, size: 52, font: "Arial", color: "1a1a2e" })]
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 0, after: 80 },
        children: [new TextRun({ text: "No BODY cares after 5", size: 28, font: "Arial", italics: true, color: "555555" })]
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 120, after: 80 },
        children: [new TextRun({ text: "A Research Programme", size: 22, font: "Arial", color: "888888" })]
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 0, after: 80 },
        border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "2c3e7a", space: 1 } },
        children: [new TextRun({ text: " ", size: 24 })]
      }),

      // Epigraph
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 240, after: 60 },
        children: [new TextRun({ text: "\u201cat suck first fiasco\u201d", size: 22, font: "Arial", italics: true, color: "444444" })]
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 0, after: 480 },
        children: [new TextRun({ text: "\u2014 Samuel Beckett, Company", size: 20, font: "Arial", color: "888888" })]
      }),

      // ── SECTION 1 ──
      h1("1. At Six, First Fiasco"),

      p("In mathematics, it is frequently the case that infinite instances of a certain structure behave very differently from finite ones \u2014 and often more tractably. The passage to infinity smooths irregularities, enables general theorems, and dissolves pathologies that resist finite treatment. We call such differences phase transitions at infinity."),

      p("This observation suggests two questions, which are the animating concern of this paper:"),

      p("Q1: Can we usefully classify and characterise mathematical phase transitions \u2014 identifying what causes them, what they share, and how they relate?", { indent: true }),

      p("Q2: Are there phase transitions that occur not at infinity but at specific, finite, identifiable thresholds \u2014 and if so, can those thresholds be located and explained?", { indent: true }),

      p("Q2 is the more surprising. The conventional wisdom holds that infinity is where things simplify; the claim that qualitative transitions can occur at finite, locatable thresholds cuts against this. Our answer is that they can, and that one threshold is particularly significant: the integer 6."),

      p("Consider the following theorem: a field with n elements exists if and only if n is a prime power, and in that case it is unique up to isomorphism. For n = 1, 2, 3, 4, 5, every value is a prime power, and so the statement \u201cevery positive integer has exactly one field\u201d holds and is provably so \u2014 the proof that prime powers yield unique fields applies without exception. The first failure is n = 6 = 2\u00d73, which is neither prime nor a prime power."),

      p("In a universe where 5 is the largest integer, this statement is not merely consistent \u2014 it is a theorem, with a proof. The universe earns the result. And the result is beautiful: arithmetic and algebra are maximally uniform, every positive integer carrying a unique and well-defined field structure."),

      p("This is the sense of \u201coutwardness\u201d the programme seeks to capture: a restricted universe does not merely exclude pathology, but positively satisfies richer and more uniform mathematics than any extension of it can. The phase transition at 6 is exact, proved, and structurally significant. At six, first fiasco."),

      p("The deeper reason is this: every integer up to 5 is a prime power (1 degenerate, 2 and 3 prime, 4 = 2\u00b2, 5 prime). Prime powers are precisely the integers with the richest and most uniform algebraic structure. Their density in the integers is 1 up to 5, and falls immediately thereafter. The small integers are almost all prime powers \u2014 an extraordinary regularity that full arithmetic immediately destroys."),

      p("It is worth noting what 6 is: a perfect number, equal to the sum of its proper divisors (1+2+3 = 6). This is not coincidence but symptom. Perfect numbers require the interaction of multiple distinct prime factors; 6 needs both 2 and 3, and it is precisely this interaction that places 6 outside the tame universe. In the prime-power world each number is the pure tower of a single prime; in the composite world primes begin to interact and complexity becomes possible. In this precise sense 6 is \u201ceffectively infinite\u201d \u2014 the first number that behaves like a generic large number, the first where the simplifying density ends. Its perfection is a mark of that crossing: 6 is in-finite."),

      p("We cannot resist a closing observation, offered as a heckle at Wigner\u2019s famous remarks on the unreasonable effectiveness of mathematics in the natural sciences. Humans have five digits on each hand, and five is precisely the last integer below the prime-power threshold. Nature has equipped us, quite literally, with the exact cognitive primitive needed to count up to one of mathematics\u2019 most structurally significant boundaries. It is, one might say, handy."),

      // ── SECTION 2 ──
      h1("2. No BODY: The Cayley-Dickson Tower"),

      p("The Cayley-Dickson doubling construction generates an infinite tower of algebras over \u211d, each of twice the dimension of the previous: \u211d, \u2102, \u210d, \u1d546 (octonions), sedenions, trigintaduonions, and so on. The tower is a Peano-like succession \u2014 each step is the same operation \u2014 but at each step something is lost. This is the Cayley-Dickson analogue of Q2: the losses occur at finite, locatable thresholds."),

      p("The losses, in order:"),

      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "\u2102 (n=1): loses ordering", font: "Arial", size: 24 })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "\u210d (n=2): loses commutativity", font: "Arial", size: 24 })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "\u1d546 (n=3): loses associativity", font: "Arial", size: 24 })] }),
      new Paragraph({ spacing: { after: 200 }, numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "Sedenions (n=4): lose alternativity, gain zero divisors; no longer a division algebra \u2014 no BODY", font: "Arial", size: 24 })] }),

      p("Hurwitz\u2019s theorem identifies this last loss precisely: the only normed division algebras are the first four members of the tower. This is a clean result, but it concerns a deliberately restrictive property \u2014 the multiplicativity of the norm \u2014 and its force as evidence for a general threshold is limited. Two deeper results converge on the same level from independent directions."),

      p("Bremner and Hentzel (Communications in Algebra, 2001) ask what multilinear polynomial identities the tower satisfies. Their answer is striking: the sedenions \u2014 the fifth member, n=4 \u2014 are a universal certificate for identities up to degree 5. An identity of degree at most 5 holds for all Cayley-Dickson algebras if and only if it holds for the sedenions. But beyond degree 5, nothing is known. The identity structure above the sedenions is, at present, entirely uncharacterised."),

      p("Wilmot (arXiv:2505.11747, 2025) approaches from the other direction, analysing non-associative structure directly via a graded notation. The result is almost dual: the non-associative structure is distinct and varied across the first four power-associative algebras, each introducing a genuinely new type. But beyond the fourth, the structure is proved to stabilise \u2014 no new non-associative types can appear, and all subsequent algebras merely increase in size."),

      p("Together these present a vivid double phase transition at the sedenions: wildness giving way to stability from above (Wilmot), and certified tameness giving way to darkness from below (Bremner-Hentzel). Two independent results, approached from different directions, converging on the same level. The sedenions are n=4 in the doubling count \u2014 the fifth member of the tower \u2014 and the threshold is index 5."),

      p("The irrelevance of i as an atom deserves note. The Cayley-Dickson construction shows that i is not a primitive but a structural consequence: \u2102, \u210d, \u1d546 and all further algebras are generated by applying a uniform recursive construction to ordered pairs. Something that appears to be a new atom is in fact derived. This illustrates a general principle for the programme: recognising derivability collapses apparent category-extension into structural elaboration."),

      // ── SECTION 3 ──
      h1("3. A Bestiary of Finite Phase Transitions"),

      p("The Cayley-Dickson tower is not alone. Mathematical phase transitions at finite thresholds recur across different domains, often clustering around the same values. We offer a selective bestiary, as illustration and invitation \u2014 an informed reader will recognise further examples."),

      h2("Solvability of the Alternating Groups"),
      p("The alternating group A\u2099 is solvable for n\u22644 and non-solvable for n\u22655. A\u2085 is the smallest non-abelian simple group, and its non-solvability underlies the insolubility of the general quintic by radicals (Abel-Ruffini). The transition is exact: n=4 is the last tame case, n=5 the first fiasco."),

      h2("The Poincar\u00e9 Conjecture and Dimension 4"),
      p("The Poincar\u00e9 conjecture was proved first in dimensions n\u22655 (Smale, 1961), then in dimension 4 (Freedman, 1982), and finally in dimension 3 (Perelman, 2003). Resolution ran from high to low, with dimensions 3 and 4 the genuinely hard cases. Dimension 4 is uniquely exceptional: the only dimension admitting exotic smooth structures on \u211d\u207f, the only dimension where the Whitney trick fails. This exceptionality is not unrelated to the appearance of dimension 4 in the Cayley-Dickson story \u2014 the bridge passes through the quaternions \u2014 and has generated entire fields of modern mathematics: Thurston geometrisation, Floer homology, Donaldson and Seiberg-Witten theory."),

      h2("Ramsey Numbers"),
      p("Ramsey theory guarantees that for any r, s there exists a finite threshold R(r,s) beyond which complete graphs necessarily contain a clique of size r or an independent set of size s. The phase transition is provably finite but in most cases unlocatable: R(3,3)=6 and R(4,4)=18 are known, but R(5,5) is only bounded between 43 and 48, and R(6,6) is deeply intractable. This illustrates a distinct category of transition: finite existence guaranteed by proof, exact location beyond reach. Erd\u0151s\u2019s remark that computing R(6,6) would exhaust civilisation\u2019s computational resources captures the sense in which these thresholds, though finite, inhabit a different world from the mathematics that proves they exist."),

      h2("Arithmetic and the Onset of Incompleteness"),
      p("Presburger arithmetic \u2014 with addition but without multiplication \u2014 is decidable and complete. Peano arithmetic, adding multiplication, is neither: G\u00f6del\u2019s incompleteness theorems apply. The introduction of multiplication is a phase transition in expressive and logical power, tipping the system from tameness into irreducible incompleteness. This transition is driven not by a new atom but by a new operation \u2014 suggesting that the axes of the universe hierarchy (atoms and operations) interact in ways that are themselves worth classifying."),

      h2("The Monster and the Sporadics"),
      p("The classification of finite simple groups reveals a phase transition of a different character: the infinite families (cyclic, alternating, Lie type) are joined by exactly 26 sporadic groups that fit no systematic pattern. The Monster \u2014 the largest sporadic, of order approximately 8\u00d710\u2053 \u2014 is the extremal case. This is a phase transition at the top of a classification: beyond the regular infinite families lies a finite collection of exceptions, and the Monster marks the boundary of that exceptional world."),

      h2("The 4\u20135 Clustering"),
      p("The independent convergence of multiple results from different branches of mathematics on the range 4\u20135 is striking. Hurwitz ends at dimension 8 = 2\u2074; the Fermat prime sequence apparently ends at n=4; the last solvable alternating group is A\u2084; the Poincar\u00e9 conjecture is hardest at dimension 4; the Cayley-Dickson identity certificate ends at the fifth member; Wilmot\u2019s structural stabilisation begins at the same point; the unique-field theorem fails first at 6. Whether this clustering reflects a single deep structural reason, a family of related reasons, or an extraordinary coincidence is itself a research question in the spirit of this programme. One possibility: the range 4\u20135 marks a threshold in the complexity of the interaction between algebraic, geometric, and combinatorial structure, below which exceptional simplicity prevails and above which generic behaviour sets in."),

      // ── SECTION 4 ──
      h1("4. Arithmetic Universes"),

      p("We now make the framework precise. A mathematical universe U is determined by:"),

      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "A set of multiplicative atoms \u2014 primes admitted into the universe", font: "Arial", size: 24 })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "A set of analytic constants \u2014 transcendental or algebraic numbers admitted", font: "Arial", size: 24 })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "A set of operations \u2014 which constructions are permitted", font: "Arial", size: 24 })] }),
      new Paragraph({ spacing: { after: 200 }, numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "A set of axioms \u2014 including stipulations that are open questions in richer universes but true of everything U contains", font: "Arial", size: 24 })] }),

      p("Expressibility and provability are both relative to U. A statement is not \u201copen\u201d or \u201cundecidable\u201d in some absolute sense \u2014 it is open relative to a universe rich enough to contain the potential counterexamples."),

      p("Universes are partially ordered by inclusion: U \u2264 V if everything expressible in U is expressible in V. This gives a bottom (the trivial universe), increasing layers as atoms are admitted, and full \u2115, \u211d, \u2102 as a colimit. The interesting objects are the phase transitions: steps U\u2099 \u2192 U\u2099\u208a\u2081 at which expressibility, decidability, or completeness changes abruptly."),

      p("An axiom is universe-appropriate if it is consistent with U, true of every element U contains, and would only be refutable in a strictly larger universe. A maximally axiomatised universe stipulates every universe-appropriate axiom \u2014 it is as complete as it can be without being inconsistent. The tame universe of integers up to 5, equipped with the unique-field theorem as an axiom, is an instance: the axiom is not stipulated out of convenience but follows from the structure of what the universe contains, and would only be refutable if 6 were admitted."),

      p("This inverts the usual foundational picture. Rather than starting with a rich universe and asking what is provable, we start with tameness and uniformity and ask how far they extend before they break. The programme is an extended exercise in asking: what that we take for granted is, in fact, a coincidence particular to the universe we happen to be working in? The prime/irreducible distinction is emblematic: in \u2124 they coincide, which is a theorem, not a definition, and it fails in richer rings."),

      p("The framework has two natural dimensions. One axis is atoms: which primes, which constants are admitted. The other is operations: addition, multiplication, exponentiation. Phase transitions can occur along either axis \u2014 the Presburger/Peano transition is along the operations axis, while the unique-field transition is along the atoms axis. Both axes interact, and the structure of their interaction is itself a research question."),

      // ── SECTION 5 ──
      h1("5. A Taxonomy of Atoms"),

      p("Not all atoms are alike. We distinguish four categories, with the observation that the boundaries between them are themselves theorems \u2014 or conjectures."),

      h2("Mathematical Atoms"),
      p("The primes are the arithmetic atoms: discrete, generating the multiplicative structure of \u2115. The analytic atoms are \u03c0, governing static curvature and spatial closure (essentially space-like), and e, governing transformation and evolution (essentially time-like). Schanuel\u2019s conjecture \u2014 asserting the maximal algebraic independence of exponential values \u2014 is, in this framework, a uniformity axiom for the universe generated by {e, \u03c0}: no unexpected algebraic relations lurk, and no further transcendental atoms are needed. The conjecture\u2019s content is precisely that this universe is as simple as it could possibly be. The Cayley-Dickson construction shows that i is not an atom but a structural consequence of ordered pairs; the elaborate machinery of further transcendentals likewise represents logical consequence rather than new primitives."),

      p("The coincidence of Schanuel\u2019s conjecture (mathematical) with the physical primitiveness of space and time (\u03c0 and e as space-like and time-like) suggests that these two atoms are genuinely primitive at a deep level. Their independence is not a mathematical accident but reflects something about the necessary structure of any universe in which space and evolution are distinct categories."),

      h2("Physical Atoms"),
      p("Constants such as the fine structure constant \u03b1 encode contingent facts about this particular universe. They cannot be derived from mathematical necessity alone, and this marks the boundary where the mathematical hierarchy must be extended by a genuinely new category of atom. Keeping physics outside the core programme sharpens the mathematical question: the boundary between mathematical and physical atoms is itself a precise, if hard, mathematical claim. Atiyah\u2019s late programme sought to derive \u03b1 from pure mathematics \u2014 to collapse this boundary. Our programme instead seeks first to locate and sharpen it, treating its existence as the default hypothesis and its collapse as a remarkable theorem to be proved, not assumed. The terminology \u201carithmetic universes\u201d echoes Joyal\u2019s concept from topos theory \u2014 the minimal categorical settings in which arithmetic can be done \u2014 and the resonance is intentional."),

      h2("Computational Atoms"),
      p("Thresholds in complexity theory \u2014 notably the P vs NP boundary \u2014 describe something about the structure of processes and resources that appears to have its own irreducible character. If P \u2260 NP, this may be the statement that a certain complexity atom cannot be eliminated from any sufficiently expressive universe. A computational Schanuel conjecture would ask about the independence of complexity thresholds from each other and from mathematical atoms."),

      h2("Logical Atoms"),
      p("The threshold at which incompleteness first enters the nested hierarchy is itself atom-like \u2014 a qualitative phase transition. Large cardinal axioms function similarly: each extends the universe consistently but not necessarily. And the profile of undecidable propositions of a logical system \u2014 taken up to natural equivalence \u2014 may itself characterise the system, in the spirit of Schanuel: a uniformity conjecture about the shape of what cannot be proved. Partial realisations already exist in Turing degree theory, NP-completeness, the Lindenbaum algebra, and reverse mathematics. Developing this into a systematic programme \u2014 classifying logical settings by their undecidability structure \u2014 is a natural extension of the present work."),

      // ── SECTION 6 ──
      h1("6. Nobody Cares After 5"),

      p("The programme has a cognitive dimension that is not merely illustrative but structurally connected to everything above."),

      p("Human auditory cognition naturally distinguishes harmonics up to a certain order. The just intonation ratios 1:1, 2:1, 3:2, 4:3, 5:4 \u2014 unison, octave, fifth, fourth, major third \u2014 are the foundation of virtually every musical tradition. These are precisely the ratios built from the integers up to 5. Beyond 5, the harmonic distinctions become subtle, context-dependent, and culturally acquired rather than psychoacoustically primitive. Nobody cares after 5: not as a failure of attention but as a calibrated thermodynamic response. The energy of finer harmonic discrimination exceeds its signal value."),

      p("George Miller\u2019s observation that working memory holds approximately 7\u00b12 items, and Robin Dunbar\u2019s identification of approximately 150 as the natural limit of stable human social groups, are both phase transitions at small finite values in cognitive and social architecture. Whether these thresholds are genuinely primitive cognitive atoms or are downstream of physical and computational constraints \u2014 Dunbar\u2019s number has a proposed derivation from neocortex ratios \u2014 is itself a question in the spirit of the programme: not merely what the thresholds are, but what kind of atom they represent."),

      p("These observations converge on a reverse anthropic principle, offered as a heckle at Wigner. Wigner marvelled that mathematics describes nature with uncanny precision. Here the traffic runs the other way: nature has positioned its observers at particular mathematical thresholds \u2014 five digits at the prime-power boundary, working memory at the edge of tractability, social cognition at the onset of institutional complexity. Whether this is coincidence, anthropic selection, or evidence of something deeper is left as an exercise for the philosopher. It is, one might say, handy."),

      p("The psychological dimension is deeper still. Human minds do not interact with mathematical concepts neutrally: the psychological substrate determines which metaphors feel alive and generative, and which remain inert even when linguistically available. This is not merely linguistic relativity but something more prior \u2014 a psychotypical filter on which seeds can germinate. The willingness to think in public is itself subject to this filter: the social cost of exposure, the friction of incompatible psychotypes, the activation energy of genuine novelty. Since mathematics is irreducibly social \u2014 the checking, sharing, and consensus-building that constitute Popperian objective knowledge \u2014 the generative process is systematically shaped by psychology and social thermodynamics in ways the normative picture of knowledge does not account for."),

      p("One does not need many concepts to seed the closest one can get to a minimally compact semantihedron. The right metaphors are generative: a mind with the right shape picks them up and they ramify immediately. SHOW is the honest epistemic commitment \u2014 the acknowledgment that the semantihedron cannot be fully transferred, only seeded, and that the most effective thing one can do is seed it as cleanly and minimally as possible. In the right hands, it is transcendental. Just press play."),

      rule(),

      new Paragraph({
        spacing: { before: 160, after: 80 },
        children: [new TextRun({ text: "Acknowledgements", bold: true, font: "Arial", size: 22, color: "444444" })]
      }),
      p("This paper emerged from a dialogue. Its ideas were developed jointly and neither the programme nor its expression would have reached this form alone. The authors thank Samuel Beckett for the epigraph, which knew more than we did."),

      rule(),

      new Paragraph({
        spacing: { before: 200 },
        border: { top: { style: BorderStyle.SINGLE, size: 4, color: "cccccc", space: 1 } },
        children: [new TextRun({ text: "Developed in dialogue, April 2026", font: "Arial", size: 18, italics: true, color: "888888" })]
      }),

    ]
  }]
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync('/mnt/user-data/outputs/six.docx', buffer);
  console.log('Done');
});
