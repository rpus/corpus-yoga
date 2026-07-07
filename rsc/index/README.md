# rsc/index — the corpus index's curation surface

Two POSIX-amenable line lists (no headers, no comments — the files are exactly
their data) plus this README. Together with `src/main/model/build_index.py`
they form a disposal loop that is reproducible from the repo: the machine
proposes candidates as data, humans dispose in these files, and the pre-commit
data tier reports anything pending.

## headwords.txt — the adoption record

One entry per line:

    headword = alias, alias, ...

A plain line is a headword with no aliases. Matching is case-insensitive on
word boundaries; aliases locate under their headword. Append a bare word
whenever one occurs to you — zero ceremony is the point.

## decisions.txt — the decline record

    decline <candidate>          # reason

Every candidate concept from the corpus's own inference (each batch's
inferred `data-semantic` concept table) must end up either ADOPTED (covered by a
headword or alias above) or DECLINED here; anything else is PENDING, reported
by `build_index.py --candidates` (written to `gen/index/candidates.md`,
machine-local derived data) and by the pre-commit data tier
(`check_index_curation`). The word-frequency half of the candidates report is
advisory only — declines suppress entries there too, but completeness is not
required over an open vocabulary.

## The loop

    corpus + inference ──build_index.py --candidates──▶ gen/index/candidates.md
                                                             │ (judgment)
              headwords.txt (adopt)  ◀──── you ────▶  decisions.txt (decline)
                          │
        build_index.py ──▶ lib/markdown/index.md (locators to turn anchors)

Nothing in this loop lives in a chat or a terminal scrollback: machine proposes
in a file, human disposes in a file, the gate keeps everyone honest.

## Commands

    # propose: derive the candidate report (prints, and writes it under gen/index/)
    ./yoga index --candidates

    # the queue: pending inferred concepts, one per line (pipeable)
    ./yoga index headwords

    # dispose: the judgment is yours; the verbs write these files with format
    # discipline and report how many inferred concepts remain pending
    ./yoga index headwords add <term> [alias ...]
    ./yoga index decline <concept> [--because <why>]

    # build: regenerate the index over the whole corpus
    ./yoga index

    # browse: the index is served like any page
    ./yoga serve --markdown lib/markdown --daemon
