# docs/

**Purpose:** Write-ups, diagrams, and the ACM report drafts for both course deliverables.

---

## Structure

```
docs/
├── paper/
│   ├── acmart.cls                    # ACM LaTeX class file (download from acm.org)
│   ├── ACM-Reference-Format.bst      # ACM bibliography style
│   ├── refs.bib                      # Shared bibliography (BibTeX format)
│   │
│   ├── milestone/
│   │   ├── milestone.tex             # Milestone Report LaTeX source
│   │   └── figures/                  # Any figures for the milestone
│   │
│   └── final/
│       ├── final.tex                 # Final Report LaTeX source
│       └── figures/                  # Charts from data/evaluation/ for the final paper
│
└── diagrams/
    ├── system_overview.png           # High-level diagram of the full pipeline
    ├── attack_taxonomy.png           # Visual of the attack classification scheme
    └── placement_schemes.png         # Diagram of the three placement strategies
```

---

## Deliverable Requirements

### Milestone Report — Due November 4, 2026
- **Length:** ≤ 4 pages (not counting references)
- **Format:** ACM 2-column proceedings template
- **Required sections (in order):**
  1. **Problem Statement** — what we're studying and why pipeline attacks matter
  2. **Technique** — how our approach works (taxonomy → operators → placement → engine)
  3. **Initial Results** — preliminary output from the first vertical slice (at least one working mutant and one PipelineSave result)
  4. **Initial Discussion** — what we observe so far; what's uncertain; what's next
  5. **Work Distribution** — who did what and roughly how many hours each person spent

### Final Report — Due December 10, 2026
- **Length:** 6–8 pages + as many pages as needed for references
- **Format:** ACM 2-column proceedings template
- **Required sections (in order):**
  1. Abstract
  2. Introduction
  3. Problem Statement
  4. Related Work
  5. Technique
  6. Evaluation
  7. Discussion
  8. Work Distribution
  9. Conclusion
  10. References

---

## Section Ownership

| Section | Owner |
|---|---|
| Abstract | Daniel (written last, after all other sections exist) |
| Introduction | Rejoice |
| Problem Statement | Rejoice |
| Related Work | Debora |
| Technique | David (structure) + all members (each writes their own subsection) |
| Evaluation | Daniel (tables/figures) + Debora (missed-mutant analysis) + David (breakdown by scheme/difficulty) |
| Discussion | Debora |
| Work Distribution | All (each person writes their own entry) |
| Conclusion | Rejoice |
| References | All (add citations as you write your sections) |

**Internal deadline: December 8** — complete draft due for group review before final submission.

---

## Getting the ACM Template

1. Go to [acm.org/publications/proceedings-template](https://www.acm.org/publications/proceedings-template)
2. Download the LaTeX template package
3. Copy `acmart.cls` and `ACM-Reference-Format.bst` into `docs/paper/`

### Compiling the Paper

**Recommended: Use Overleaf** — no local LaTeX install needed, and multiple people can edit at the same time.

1. Create a new Overleaf project
2. Upload the contents of `docs/paper/` (the `.cls`, `.bst`, `.bib`, and `.tex` files)
3. Share the edit link in Discord

**Local LaTeX (alternative):**
```bash
cd docs/paper/milestone
pdflatex milestone.tex
bibtex milestone
pdflatex milestone.tex
pdflatex milestone.tex   # Run twice to resolve cross-references
```

---

## Managing Citations

We use BibTeX. To add a citation:

1. Find the paper on [Google Scholar](https://scholar.google.com)
2. Click the `"` (cite) button → **BibTeX** → copy the entry
3. Paste it into `docs/paper/refs.bib`
4. In the `.tex` file, cite it with `\cite{authorYearKeyword}`

Alternatively, use [Zotero](https://www.zotero.org/) to manage your citations and export to BibTeX — it auto-generates the `.bib` entry for any paper.

---

## Diagrams

The `diagrams/` folder holds visual figures that explain the system. These are included in both reports. When you create a diagram (in any tool — draw.io, Lucidchart, PowerPoint, etc.), export it as a `.png` or `.pdf` and save it here so everyone can use it in the LaTeX files.
