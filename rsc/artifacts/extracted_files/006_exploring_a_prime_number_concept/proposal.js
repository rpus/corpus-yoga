const {
  Document, Packer, Paragraph, TextRun, HeadingLevel,
  AlignmentType, LevelFormat, BorderStyle
} = require('docx');
const fs = require('fs');

const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 24 } } },
    paragraphStyles: [
      {
        id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 36, bold: true, font: "Arial", color: "1a1a2e" },
        paragraph: { spacing: { before: 360, after: 180 }, outlineLevel: 0 }
      },
      {
        id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: "Arial", color: "2c3e7a" },
        paragraph: { spacing: { before: 280, after: 140 }, outlineLevel: 1 }
      },
      {
        id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, italics: true, font: "Arial", color: "444444" },
        paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 2 }
      },
    ]
  },
  numbering: {
    config: [
      {
        reference: "bullets",
        levels: [{
          level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } }
        }]
      },
      {
        reference: "subbullets",
        levels: [{
          level: 0, format: LevelFormat.BULLET, text: "\u25e6", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 1080, hanging: 360 } } }
        }]
      }
    ]
  },
  sections: [{
    properties: {
      page: {
        size: { width: 11906, height: 16838 },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
      }
    },
    children: [

      // Title
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 480, after: 120 },
        children: [new TextRun({ text: "Arithmetic Universes Built from Finite Atoms", bold: true, size: 48, font: "Arial", color: "1a1a2e" })]
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 0, after: 80 },
        children: [new TextRun({ text: "A Research Programme Sketch", size: 28, font: "Arial", italics: true, color: "555555" })]
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 0, after: 600 },
        border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "2c3e7a", space: 1 } },
        children: [new TextRun({ text: " ", size: 24 })]
      }),

      // 1. Motivation
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("1. Motivation")] }),
      new Paragraph({
        spacing: { after: 200 },
        children: [new TextRun({
          text: "The first five Fermat numbers are prime. Whether any further Fermat numbers are prime is unknown, and it is conceivable that this question is undecidable within standard arithmetic. This observation — one instance of a broader phenomenon — prompts a foundational question:",
          font: "Arial", size: 24
        })]
      }),
      new Paragraph({
        spacing: { before: 160, after: 160 },
        indent: { left: 720, right: 720 },
        children: [new TextRun({
          text: "Is there a revised sense of \"integer\", or a restricted mathematical universe, in which such questions do not merely become solved, but become absent — because the objects that would witness their failure lie outside the universe entirely?",
          font: "Arial", size: 24, italics: true
        })]
      }),
      new Paragraph({
        spacing: { after: 200 },
        children: [new TextRun({
          text: "Note that the Fermat prime example is purely illustrative: what matters is not that the Fermat numbers are prime, but that there exist statements of the form \"this sequence has exactly N members satisfying some property\" which may be independent of our axioms, and which only become expressible once the universe is rich enough to contain the relevant objects.",
          font: "Arial", size: 24
        })]
      }),

      // 2. Core Idea
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("2. The Core Idea")] }),
      new Paragraph({
        spacing: { after: 200 },
        children: [new TextRun({
          text: "We propose studying a hierarchy of mathematical universes, each parametrised by a set of admitted atoms. The guiding intuition is:",
          font: "Arial", size: 24
        })]
      }),
      new Paragraph({
        spacing: { before: 160, after: 160 },
        indent: { left: 720, right: 720 },
        children: [new TextRun({
          text: "Build mathematics upward from the smallest defensible set of atoms. Stipulate as axioms whatever is consistent and true of everything the universe contains — even if those stipulations would be refutable in a richer universe. Study both the structure that emerges and the thresholds at which tameness breaks down.",
          font: "Arial", size: 24, italics: true
        })]
      }),
      new Paragraph({
        spacing: { after: 160 },
        children: [new TextRun({
          text: "This inverts the usual foundational picture. Rather than starting with a rich universe and asking what is provable, we start with tameness and uniformity, and ask how far they can be extended before they break.",
          font: "Arial", size: 24
        })]
      }),
      new Paragraph({
        spacing: { after: 100 },
        children: [new TextRun({ text: "An axiom is called universe-appropriate if:", font: "Arial", size: 24 })]
      }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "it is consistent with the universe U,", font: "Arial", size: 24 })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "it is true of every element U actually contains, and", font: "Arial", size: 24 })] }),
      new Paragraph({
        spacing: { after: 200 },
        numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "it would only be refutable in a strictly larger universe.", font: "Arial", size: 24 })]
      }),
      new Paragraph({
        spacing: { after: 200 },
        children: [new TextRun({
          text: "A maximally axiomatised universe is one in which every universe-appropriate axiom has been stipulated. Such universes are, in a precise sense, as complete as they can be without being inconsistent.",
          font: "Arial", size: 24
        })]
      }),

      // 3. Structure of the Hierarchy
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("3. Structure of the Hierarchy")] }),
      new Paragraph({
        spacing: { after: 200 },
        children: [new TextRun({
          text: "Universes are partially ordered by inclusion: U \u2264 V if everything expressible in U is expressible in V. This yields:",
          font: "Arial", size: 24
        })]
      }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "A bottom — the minimal universe with no primes and no constants, essentially trivial arithmetic.", font: "Arial", size: 24 })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "Increasing layers as primes and constants are admitted.", font: "Arial", size: 24 })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "Full \u2115, \u211d, \u2102 etc. as a colimit of the entire system.", font: "Arial", size: 24 })] }),
      new Paragraph({
        spacing: { before: 160, after: 200 },
        numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "Phase transitions — qualitatively significant steps where expressibility, decidability, or completeness changes abruptly.", font: "Arial", size: 24 })]
      }),
      new Paragraph({
        spacing: { after: 200 },
        children: [new TextRun({
          text: "We are particularly interested in finite and nested chains U\u2080 \u2282 U\u2081 \u2282 U\u2082 \u2282 \u22ef, where each U\u2099 is generated by the first n primes (or first n atoms of a given type). Such chains provide a narrative of emergence: one can watch structure and pathology arrive, one atom at a time.",
          font: "Arial", size: 24
        })]
      }),
      new Paragraph({
        spacing: { after: 200 },
        children: [new TextRun({
          text: "Infinite sets of atoms may simultaneously be more tractable — in the same way that proving a theorem for all n is often easier than for a specific large n. Both perspectives are valuable.",
          font: "Arial", size: 24
        })]
      }),

      // 4. Taxonomy of Atoms
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("4. A Taxonomy of Atoms")] }),
      new Paragraph({
        spacing: { after: 160 },
        children: [new TextRun({
          text: "An atom of category X is a primitive necessary and sufficient to make a certain class of statements expressible, and not constructible from atoms of other categories without importing the ideas of category X. The category boundaries are themselves theorems — or conjectures. We distinguish four main categories.",
          font: "Arial", size: 24
        })]
      }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("4.1 Arithmetic Atoms")] }),
      new Paragraph({
        spacing: { after: 200 },
        children: [new TextRun({
          text: "The primes. Discrete, generating the multiplicative structure of \u2115. The hierarchy of universes built from finite sets of primes is the most concrete instantiation of the programme.",
          font: "Arial", size: 24
        })]
      }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("4.2 Analytic Atoms")] }),
      new Paragraph({
        spacing: { after: 160 },
        children: [new TextRun({
          text: "Two atoms appear sufficient and necessary at the analytic level:",
          font: "Arial", size: 24
        })]
      }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "\u03c0, governing static curvature and spatial closure — essentially space-like.", font: "Arial", size: 24 })] }),
      new Paragraph({
        spacing: { after: 160 },
        numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "e, governing transformation, growth, and evolution — essentially time-like.", font: "Arial", size: 24 })]
      }),
      new Paragraph({
        spacing: { after: 160 },
        children: [new TextRun({
          text: "Schanuel's conjecture — which asserts the maximal algebraic independence of exponential values — can be read, within this framework, as a uniformity axiom for the universe generated by {e, \u03c0}: no unexpected algebraic relations lurk between its elements, and no further transcendental atoms are needed. The conjecture's content is precisely that this universe is as simple as it could possibly be.",
          font: "Arial", size: 24
        })]
      }),
      new Paragraph({
        spacing: { after: 160 },
        children: [new TextRun({
          text: "The Cayley-Dickson construction (doubling) shows that i is not a primitive atom but a structural consequence: \u2102, \u210d, \u1d546 etc. are generated by applying a uniform recursive construction to ordered pairs. This illustrates a general principle: something that appears to be a new atom may be a derived construction, and recognising this collapses apparent category-extension into structural elaboration.",
          font: "Arial", size: 24
        })]
      }),
      new Paragraph({
        spacing: { after: 200 },
        children: [new TextRun({
          text: "The coincidence of Schanuel's conjecture (mathematical) with the physical primitiveness of space and time (e and \u03c0 as space-like and time-like respectively) suggests that these two atoms are genuinely primitive at a deep level — not merely conventional choices. It also suggests that the elaborate machinery for constructing further transcendentals represents logical consequence rather than genuine new atoms: those numbers exist in the universe once e and \u03c0 are admitted, but need not be reached for as primitives.",
          font: "Arial", size: 24
        })]
      }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("4.3 Physical Atoms")] }),
      new Paragraph({
        spacing: { after: 200 },
        children: [new TextRun({
          text: "Constants such as the fine structure constant \u03b1 encode contingent facts about this particular universe. They cannot be derived from mathematical necessity alone. This marks the boundary where the mathematical universe hierarchy must be extended by a new category of atom — a physical one. A physical analogue of Schanuel's conjecture would ask about the algebraic independence of physical constants from each other and from mathematical atoms. Crucially, keeping physics outside the core programme sharpens the mathematical question: the boundary between mathematical and physical atoms is itself a precise (if hard) mathematical claim.",
          font: "Arial", size: 24
        })]
      }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("4.4 Computational Atoms")] }),
      new Paragraph({
        spacing: { after: 200 },
        children: [new TextRun({
          text: "Thresholds in complexity theory — notably the P vs NP boundary — are neither physical contingencies nor straightforwardly mathematical in the sense of \u03c0. They describe something about the structure of processes and resources that appears to have its own irreducible character. If P \u2260 NP, this may be the statement that a certain complexity atom cannot be eliminated from any sufficiently expressive universe.",
          font: "Arial", size: 24
        })]
      }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("4.5 Logical/Metamathematical Atoms")] }),
      new Paragraph({
        spacing: { after: 200 },
        children: [new TextRun({
          text: "The threshold at which incompleteness first enters the nested hierarchy is itself atom-like — a qualitative phase transition. Large cardinal axioms function similarly: each extends the universe consistently (as far as we know) but not necessarily, making new statements expressible or provable. The point in the hierarchy where G\u00f6del-type phenomena first appear is a central object of study in this programme.",
          font: "Arial", size: 24
        })]
      }),

      // 5. Key Questions
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("5. Key Questions")] }),
      new Paragraph({
        spacing: { after: 120 },
        children: [new TextRun({ text: "The programme generates the following families of questions:", font: "Arial", size: 24 })]
      }),

      new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun("Expressibility thresholds")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "At which transition U\u2099 \u2192 U\u2099\u208a\u2081 does a given problem or statement first become expressible?", font: "Arial", size: 24 })] }),
      new Paragraph({
        spacing: { after: 160 },
        numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "At which transition does it first become undecidable or incomplete?", font: "Arial", size: 24 })]
      }),

      new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun("Tameness and uniformity")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "Which universes in the hierarchy are complete, decidable, or uniform in precise senses?", font: "Arial", size: 24 })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "What is the last tame universe before wild behaviour enters?", font: "Arial", size: 24 })] }),
      new Paragraph({
        spacing: { after: 160 },
        numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "Are there phase transitions that are qualitatively more significant than others?", font: "Arial", size: 24 })]
      }),

      new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun("Parsimony of atoms")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "Which proposed atoms are genuinely primitive, and which are derived constructions?", font: "Arial", size: 24 })] }),
      new Paragraph({
        spacing: { after: 160 },
        numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "Is the universe generated by a small number of primes together with e and \u03c0 surprisingly complete?", font: "Arial", size: 24 })]
      }),

      new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun("Category boundaries")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "Can \u03b1 be constructed from mathematical atoms, or does it necessarily require physical primitives?", font: "Arial", size: 24 })] }),
      new Paragraph({
        spacing: { after: 200 },
        numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "Are the four categories of atom exhaustive, and are their boundaries provably sharp?", font: "Arial", size: 24 })]
      }),

      // 6. Connections
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("6. Connections to Existing Mathematics")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "Reverse mathematics: identifies which axioms are needed for theorems; this programme asks which universes (in the richer sense of admitted atoms) are needed.", font: "Arial", size: 24 })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "Presburger arithmetic: addition only, no multiplication — decidable and complete, illustrating how restricting operations tames a universe.", font: "Arial", size: 24 })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "S-integers and S-units: the arithmetic of numbers whose prime factors lie in a fixed finite set S — a studied object that partially instantiates the arithmetic-atom side of the programme.", font: "Arial", size: 24 })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "Nonstandard models of arithmetic: provide a rigorous setting in which \"a universe where 5 is large enough\" can be made precise.", font: "Arial", size: 24 })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "Schanuel's conjecture: a uniformity axiom for the analytic universe — the claim that {e, \u03c0} is as algebraically independent as possible, with no further transcendental atoms required.", font: "Arial", size: 24 })] }),
      new Paragraph({
        spacing: { after: 200 },
        numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "Feasibilism and ultrafinitism: philosophical positions that motivate asking where the last tame universe lies and whether there is a largest meaningful universe at all.", font: "Arial", size: 24 })]
      }),

      // 7. A Note on Methodology
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("7. A Note on Methodology")] }),
      new Paragraph({
        spacing: { after: 160 },
        children: [new TextRun({
          text: "The programme is deliberately parsimonious. It asks, at each step: is this atom genuinely necessary, or can it be derived? It favours small, concrete, finitely-generated universes as starting points, growing outward only when forced. It is suspicious of complexity — not because complexity is uninteresting, but because unexpected simplicity is more informative.",
          font: "Arial", size: 24
        })]
      }),
      new Paragraph({
        spacing: { after: 160 },
        children: [new TextRun({
          text: "The joke that \"the fingers of one hand might suffice to generate a psychologically rich mathematical universe\" captures the spirit: not a claim that five primes are literally enough, but that starting with what fits in the hand — what is fully graspable — and asking how far that takes us, is the right way to understand where richness comes from and where pathology enters.",
          font: "Arial", size: 24
        })]
      }),
      new Paragraph({
        spacing: { after: 200 },
        children: [new TextRun({
          text: "The prime/irreducible distinction is emblematic of the programme's ethos: most people conflate them because in the familiar universe (\u2124) they coincide. But this coincidence is a theorem, not a definition, and it fails in richer rings. The programme is an extended exercise in asking: what else that we take for granted is, in fact, a coincidence particular to the universe we happen to be working in?",
          font: "Arial", size: 24
        })]
      }),

      // Footer rule
      new Paragraph({
        spacing: { before: 400 },
        border: { top: { style: BorderStyle.SINGLE, size: 4, color: "cccccc", space: 1 } },
        children: [new TextRun({ text: "Research programme sketch — developed in dialogue, March 2026", font: "Arial", size: 18, italics: true, color: "888888" })]
      }),

    ]
  }]
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync('/mnt/user-data/outputs/arithmetic_universes.docx', buffer);
  console.log('Done');
});
