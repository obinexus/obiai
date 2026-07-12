# OBI Source Documentation

This folder contains source material for the OBI documentation build. Generated files are written to `docs/public`; do not edit generated HTML by hand.

## Where Files Go

- Put LaTeX papers in `docs/source/tex`.
- Put BibTeX files in `docs/source/bib`.
- Put Markdown notes in `docs/source/md`.
- Put PDFs in `docs/source/pdf`.
- Put plain text transcripts or notes in `docs/source/txt`.
- Put images, diagrams, and other web assets in `docs/source/assets`.
- Generated archive/PDF HTML is written to `docs/source/html`.
- Extracted ZIP contents are written to `docs/source/archive`.
- Put older research ZIP bundles in `docs/archive`.

## Build

```powershell
npm run docs:populate
npm run docs:build
```

The populate step extracts ZIP bundles, converts extracted files and source PDFs into Markdown, and writes standalone Pandoc-compatible HTML views. The build creates static HTML, `search.json`, `bibliography.html`, `bibliography.json`, `sitemap.xml`, `robots.txt`, `manifest.json`, copied source PDFs, copied source HTML, and the shared CSS/JavaScript assets.

## Serve Locally

```powershell
npm run docs:serve
npm run docs:serve:html
```

The local server starts at `http://127.0.0.1:4173/` by default and automatically tries the next available port if needed.

The source HTML server starts at `http://127.0.0.1:8000/html/` and serves `docs/source` so generated HTML pages can link back to source PDFs.

## Add a New Paper

1. Add the `.tex` file to `docs/source/tex`.
2. Add references to a `.bib` file in `docs/source/bib`.
3. Put any images in `docs/source/assets`.
4. Run `npm run docs:build`.
5. Run `npm run docs:validate`.

## Citations

The LaTeX converter resolves `\cite{}`, `\citep{}`, and `\citet{}` keys against BibTeX entries found in `docs/source/bib`. Resolved citations link to `bibliography.html`. Missing keys are shown as unresolved but do not fail the build.

## MathJax

Inline math written as `\( ... \)` and display math written as `\[ ... \]`, `equation`, or `align` environments is preserved as TeX and rendered in HTML through MathJax.

## Pandoc and PDF Extraction

`scripts/populate-docs.py` prefers Pandoc for LaTeX conversion, Python Markdown for Markdown rendering, and `pdfplumber` or `pypdf` for PDF text extraction. Install the Python docs extra with `pip install -e .[docs]` for the complete local toolchain. MiKTeX is optional for future PDF compilation and is not required for HTML generation.

## Source Preservation

The build reads from `docs/source` and `docs/archive`. It cleans only generated files under `docs/public`, so original source material remains preserved.
