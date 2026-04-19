# Syntax, Geometry, and Measurement — Paper Sources

## Files

| File | Description |
|------|-------------|
| `paper1_v5.py` | Paper 1: Syntax, Geometry, and Measurement (v5) |
| `paper2_v4.py` | Paper 2: Uncertainty and Unruhigkeit (v4) |
| `Dockerfile` | Reproducible build environment |
| `build.sh` | Build script |

---

## Option A — Docker (recommended, fully reproducible)

### Prerequisites
- Docker installed and running

### Steps

```bash
# 1. Place all four files in a directory, e.g. ~/papers/
mkdir ~/papers
cp paper1_v5.py paper2_v4.py Dockerfile build.sh ~/papers/
cd ~/papers

# 2. Build the Docker image
docker build -t papers .

# 3. Run the build (PDFs appear in ~/papers/output/)
docker run --rm -v $(pwd)/output:/papers/output papers

# 4. Find your PDFs
ls output/
# paper1_v5.pdf
# paper2_v4.pdf
```

---

## Option B — Local Python (simpler, slightly less reproducible)

### Prerequisites
- Python 3.9 or later
- pip

### Steps

```bash
# 1. Install reportlab
pip install reportlab

# 2. Build Paper 1
python paper1_v5.py
# -> paper1_v4.pdf  (rename as desired)

# 3. Build Paper 2
python paper2_v4.py
# -> paper2_v4.pdf
```

---

## Editing the papers

Each paper is a single self-contained Python script using ReportLab's
Platypus framework. The structure is straightforward:

- **Styles** are defined near the top (base, h1, h2, math_s, etc.)
- **Content** is built as a `story` list of flowables
- Helper functions: `P(text)` for paragraphs, `H1/H2(text)` for headings,
  `Math(text)` for centred Courier math, `Boxed(text)` for key results,
  `SP(n)` for vertical space, `Rule()` for horizontal rules
- The `TwoColumnDoc` class at the bottom handles page layout

### Adding a paragraph
```python
story.append(P("Your text here, with <b>bold</b> and <i>italic</i> supported."))
```

### Adding a display equation
```python
story.append(Math("□T  +  (1/3) R T  =  0"))
```

### Adding a boxed result
```python
story.append(Boxed("r_eff · T  =  1 / 4π"))
```

### Adding a section
```python
story.append(H1("N. Section Title"))
story.append(H2("N.M Subsection Title"))
```

---

## Version history

### Paper 1
- v1: Initial six sections + postscript
- v2: Section 7 (ecological contingency, world-building, cost of a fork)
- v3: Updated abstract; postscript expanded
- v4: Section 6.6 (intelligence footnote — no von Neumann architecture)
- v5: Section 6.7 (theorem of ecological uncertainty; token/context corollary)

### Paper 2
- v1: Sections 1-5 complete; Sections 6-9 as skeletons
- v2: Section 2.3 (tensor inventory); Section 9 updated; Paper 3 forward reference
- v3: Section 10 (Gauss, Planck length, fundamental constants as fixed points)
- v4: Section 1.1 (Hilbert's sixth problem); Section 4.4 (four-current conservation)

---

## Dependencies

```
reportlab==4.2.2
```

No other dependencies. All layout, typesetting, and mathematics rendering
is handled by ReportLab's built-in Platypus framework using standard
PostScript fonts (Times-Roman, Times-Bold, Times-Italic, Courier).

Note: Mathematical notation is rendered in Courier with Unicode characters
where available. For full LaTeX-quality typesetting, the content can be
straightforwardly transcribed to LaTeX using the Python scripts as a
structured outline.

---

## Planned papers

- **Paper 3**: Vorticity, Helicity, and Curvature Rotons
  (topological thermodynamics of the geodesic flow)
- **Paper 4**: Noether's Theorem and the Cost of Symmetry Breaking
  (action as dissipative path cost; Noether prices what is free,
  our theorem prices what is not)
