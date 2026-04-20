const { Document, Packer, Paragraph, TextRun, AlignmentType } = require('docx');
const fs = require('fs');

const doc = new Document({
  styles: {
    default: {
      document: { run: { font: "Georgia", size: 24 } }
    }
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1440, right: 1620, bottom: 1440, left: 1620 }
      }
    },
    children: [

      // Title
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 0, after: 200 },
        children: [new TextRun({ text: "An Information-Theoretic Reading of the List Type", bold: true, size: 28, font: "Georgia" })]
      }),

      // Subtitle / genre marker
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 0, after: 480 },
        children: [new TextRun({ text: "A Pearl", italics: true, size: 22, font: "Georgia", color: "555555" })]
      }),

      // Section: The algebra
      new Paragraph({
        spacing: { before: 0, after: 200 },
        children: [new TextRun({ text: "The List Type as a Geometric Series", bold: true, font: "Georgia", size: 24 })]
      }),

      new Paragraph({
        spacing: { before: 0, after: 240 },
        alignment: AlignmentType.BOTH,
        children: [new TextRun({
          text: "A list over a type A may be defined by the union of all finite products: List(A) = 1 + A + A\u00B2 + A\u00B3 + \u22EF. This is a geometric series in A, and by the standard identity for such series, it contracts to the closed form:",
          font: "Georgia"
        })]
      }),

      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 120, after: 120 },
        children: [new TextRun({ text: "List(A)  =  1 / (1 \u2212 A)", bold: true, font: "Georgia", size: 26 })]
      }),

      new Paragraph({
        spacing: { before: 120, after: 360 },
        alignment: AlignmentType.BOTH,
        children: [new TextRun({
          text: "This is not merely a formal trick. Each step of the equivalence carries meaning, and reading it carefully \u2014 attending to how each symbol is naturally pronounced \u2014 yields a small constellation of insights.",
          font: "Georgia"
        })]
      }),

      // Section: Pronouncing the operators
      new Paragraph({
        spacing: { before: 0, after: 200 },
        children: [new TextRun({ text: "Pronouncing the Operators", bold: true, font: "Georgia", size: 24 })]
      }),

      new Paragraph({
        spacing: { before: 0, after: 200 },
        alignment: AlignmentType.BOTH,
        children: [new TextRun({
          text: "The operators of type algebra have natural readings. Addition (+) is \u201Cor\u201D: a disjoint choice between alternatives. Multiplication (\u00D7) is \u201Cand\u201D: the simultaneous holding of two things. Their respective identities follow: 0, the empty type, is \u201Cimpossibly\u201D \u2014 the choice that offers nothing; and 1, the unit type, is \u201Ctrivially\u201D \u2014 the conjunction that adds no information.",
          font: "Georgia"
        })]
      }),

      new Paragraph({
        spacing: { before: 0, after: 200 },
        alignment: AlignmentType.BOTH,
        children: [new TextRun({
          text: "Inverses must invert. Division (/) is therefore \u201Cregardless of\u201D or \u201Cignoring differences in\u201D \u2014 the dissolution of a simultaneous distinction (as in \u211D/\u2124: the reals, regardless of integer part). And subtraction (\u2212) inverts disjunction: \u201Cwithout distinguishing\u201D or \u201Cpretending indifference between\u201D.",
          font: "Georgia"
        })]
      }),

      new Paragraph({
        spacing: { before: 0, after: 360 },
        alignment: AlignmentType.BOTH,
        children: [new TextRun({
          text: "Under these readings, 1/(1\u2212A) becomes: \u201Cthe trivial, regardless of pretending-A-indistinguishable-from-the-trivial.\u201D Equated to the series \u2014 \u201Ca list is nothing, or one thing, or two things, \u2026\u201D \u2014 the tautology crystallises: the whole is nothing but the iterated overcoming of its own lack.",
          font: "Georgia",
          italics: false
        })]
      }),

      // Section: Information theory
      new Paragraph({
        spacing: { before: 0, after: 200 },
        children: [new TextRun({ text: "The Radius of Convergence as a Logical Boundary", bold: true, font: "Georgia", size: 24 })]
      }),

      new Paragraph({
        spacing: { before: 0, after: 200 },
        alignment: AlignmentType.BOTH,
        children: [new TextRun({
          text: "The geometric series converges only when |A| < 1. This analytic condition is not imported from complex analysis by accident \u2014 it is the condition that A carry genuine information. To construct a random instance of a type is to perform a probabilistic event; |A| is therefore literally the probability of that event, constrained by construction to [0, 1].",
          font: "Georgia"
        })]
      }),

      new Paragraph({
        spacing: { before: 0, after: 200 },
        alignment: AlignmentType.BOTH,
        children: [new TextRun({
          text: "The boundary cases are instructive. When |A| = 0, A is the empty type \u2014 \u201Cimpossibly\u201D \u2014 and List(A) = 1: there is exactly one list of impossible things, namely the empty list. Vacuous truth is well-behaved. When |A| = 1, A is the unit type \u2014 \u201Ctrivially\u201D \u2014 and the series diverges: List(1) = 1 + 1 + 1 + \u22EF. A list of tautologies is not a list; it is an explosion of undifferentiated sameness.",
          font: "Georgia"
        })]
      }),

      new Paragraph({
        spacing: { before: 0, after: 200 },
        alignment: AlignmentType.BOTH,
        children: [new TextRun({
          text: "Shannon makes this precise. The information content of an event of probability p is \u2212log p. The convergence condition |A| < 1 is therefore precisely \u2212log|A| > 0: A must carry positive information. The series \u2014 and with it the well-foundedness of the list type \u2014 converges if and only if each element says something.",
          font: "Georgia"
        })]
      }),

      new Paragraph({
        spacing: { before: 0, after: 480 },
        alignment: AlignmentType.BOTH,
        children: [new TextRun({
          text: "The analytic boundary and the logical boundary coincide: the list construction is well-behaved precisely in the space between impossibility and triviality, between bot and top, between 0 and 1. The radius of convergence was always a logical condition dressed in analytic clothing. The mathematics knew before we did.",
          font: "Georgia",
          italics: true
        })]
      }),

      // Closing em-dash separator
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 0, after: 360 },
        children: [new TextRun({ text: "\u2014", font: "Georgia", color: "888888" })]
      }),

      // Coda
      new Paragraph({
        spacing: { before: 0, after: 0 },
        alignment: AlignmentType.BOTH,
        children: [new TextRun({
          text: "That the same object \u2014 a humble list \u2014 simultaneously encodes a tautology about lack and overcoming, a probabilistic constraint on informativeness, and the logical gap between the impossible and the trivial, is not a coincidence. It is a small instance of the general fact that structure, once found, ramifies everywhere. All is metaphor; the metaphors are load-bearing.",
          font: "Georgia",
          italics: true
        })]
      }),

    ]
  }]
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync('/mnt/user-data/outputs/list_type_pearl.docx', buf);
  console.log('Done');
});
