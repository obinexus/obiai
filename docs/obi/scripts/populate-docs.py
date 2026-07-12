#!/usr/bin/env python3
"""Populate OBI source Markdown and HTML from archives and PDFs.

The script is intentionally conservative:
- ZIP files are extracted under docs/source/archive only.
- Generated Markdown is written under docs/source/md.
- Generated browsable HTML is written under docs/source/html.
- PDF text extraction uses pdfplumber or pypdf when available.
- Pandoc is used when present for LaTeX/Markdown conversion fidelity.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
ARCHIVE_DIR = DOCS / "archive"
SOURCE = DOCS / "source"
SOURCE_ARCHIVE = SOURCE / "archive"
SOURCE_PDF = SOURCE / "pdf"
SOURCE_MD = SOURCE / "md"
SOURCE_HTML = SOURCE / "html"
SOURCE_ASSETS = SOURCE / "assets"

ARCHIVE_MD = SOURCE_MD / "archive"
PDF_MD = SOURCE_MD / "pdf"
ARCHIVE_HTML = SOURCE_HTML / "archive"
PDF_HTML = SOURCE_HTML / "pdf"
HTML_ASSETS = SOURCE_HTML / "assets"

TEXT_EXTENSIONS = {".txt", ".psc"}
MARKDOWN_EXTENSIONS = {".md", ".markdown"}
TEX_EXTENSIONS = {".tex", ".latex"}
PDF_EXTENSIONS = {".pdf"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
CONVERTIBLE_EXTENSIONS = (
    TEXT_EXTENSIONS | MARKDOWN_EXTENSIONS | TEX_EXTENSIONS | PDF_EXTENSIONS | IMAGE_EXTENSIONS
)


@dataclass
class GeneratedPage:
    title: str
    slug: str
    kind: str
    markdown_path: Path
    html_path: Path
    source_path: Path
    warnings: list[str]


def slugify(value: str, fallback: str = "document") -> str:
    slug = (
        value.lower()
        .replace("&", " and ")
        .replace("+", " plus ")
        .replace("@", " at ")
    )
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return (slug[:120].strip("-") or fallback)


def unique_slug(base_slug: str, used: set[str]) -> str:
    candidate = base_slug
    index = 2
    while candidate in used:
        candidate = f"{base_slug}-{index}"
        index += 1
    used.add(candidate)
    return candidate


def title_from_name(value: str) -> str:
    stem = Path(value).stem
    title = re.sub(r"[_-]+", " ", stem)
    title = re.sub(r"\s+", " ", title).strip()
    return title or stem or "Untitled"


def read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(errors="replace")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def clean_generated_dirs() -> None:
    for path in [SOURCE_ARCHIVE, ARCHIVE_MD, PDF_MD, SOURCE_HTML, SOURCE_ASSETS / "archive"]:
        if path.exists():
            resolved = path.resolve()
            if SOURCE.resolve() not in [resolved, *resolved.parents]:
                raise RuntimeError(f"Refusing to remove path outside docs/source: {path}")
            shutil.rmtree(path)


def ensure_dirs() -> None:
    for path in [
        SOURCE_ARCHIVE,
        SOURCE_PDF,
        SOURCE_MD,
        SOURCE_HTML,
        ARCHIVE_MD,
        PDF_MD,
        ARCHIVE_HTML,
        PDF_HTML,
        HTML_ASSETS,
        SOURCE_ASSETS,
    ]:
        path.mkdir(parents=True, exist_ok=True)


def is_safe_member(member_name: str) -> bool:
    normalized = member_name.replace("\\", "/")
    return not (
        normalized.startswith("/")
        or normalized.startswith("../")
        or "/../" in normalized
        or re.match(r"^[A-Za-z]:", normalized)
    )


def safe_member_path(destination: Path, member_name: str) -> Path:
    if not is_safe_member(member_name):
        raise ValueError(f"Unsafe ZIP member path: {member_name}")
    safe_parts = [
        sanitize_path_part(part)
        for part in member_name.replace("\\", "/").split("/")
        if part and part not in {".", ".."}
    ]
    target = destination.joinpath(*safe_parts)
    resolved_destination = destination.resolve()
    resolved_target = target.resolve()
    if resolved_destination not in [resolved_target, *resolved_target.parents]:
        raise ValueError(f"ZIP member escaped destination: {member_name}")
    return target


def sanitize_path_part(part: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", part).strip().rstrip(".")
    return cleaned or "item"


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    for index in range(2, 10_000):
        candidate = path.with_name(f"{stem}-{index}{suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Could not allocate unique path for {path}")


def extract_zip(zip_path: Path, destination: Path) -> list[Path]:
    extracted: list[Path] = []
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            if member.is_dir():
                safe_member_path(destination, member.filename).mkdir(parents=True, exist_ok=True)
                continue
            target = unique_path(safe_member_path(destination, member.filename))
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)
            extracted.append(target)
    return extracted


def extract_archives() -> list[Path]:
    extracted_roots: list[Path] = []
    for zip_path in sorted(ARCHIVE_DIR.glob("*.zip")):
        root = SOURCE_ARCHIVE / slugify(zip_path.stem)
        extracted_roots.append(root)
        extract_zip(zip_path, root)

    nested_zips = sorted(SOURCE_ARCHIVE.rglob("*.zip"))
    for nested_zip in nested_zips:
        destination = nested_zip.with_suffix("")
        extract_zip(nested_zip, destination)
    return extracted_roots


def has_convertible_content(directory: Path) -> bool:
    return any(
        file.is_file()
        and file.suffix.lower() in CONVERTIBLE_EXTENSIONS
        and "__MACOSX" not in file.parts
        for file in directory.iterdir()
    )


def content_directories() -> list[Path]:
    dirs = [
        directory
        for directory in SOURCE_ARCHIVE.rglob("*")
        if directory.is_dir() and has_convertible_content(directory)
    ]
    if has_convertible_content(SOURCE_ARCHIVE):
        dirs.append(SOURCE_ARCHIVE)
    return sorted(set(dirs), key=lambda item: item.as_posix())


def command_available(name: str) -> bool:
    return shutil.which(name) is not None


def run_pandoc(
    args: list[str],
    cwd: Path | None = None,
    input_text: str | None = None,
) -> tuple[bool, str]:
    if not command_available("pandoc"):
        return False, "pandoc is not available"
    try:
        result = subprocess.run(
            ["pandoc", *args],
            cwd=str(cwd) if cwd else None,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            input=input_text,
        )
    except OSError as error:
        return False, str(error)
    if result.returncode != 0:
        return False, result.stderr.strip() or result.stdout.strip()
    return True, result.stdout


def latex_to_markdown(path: Path) -> tuple[str, list[str]]:
    success, output = run_pandoc(
        [
            "--from=latex",
            "--to=gfm+tex_math_dollars",
            "--wrap=none",
            f"--resource-path={path.parent}",
            str(path),
        ],
        cwd=path.parent,
    )
    if success:
        return output.strip(), []
    raw = read_text(path)
    return f"```latex\n{raw.strip()}\n```", [f"Pandoc could not convert {path.name}: {output}"]


def import_pdf_extractors():
    try:
        import pdfplumber  # type: ignore

        return "pdfplumber", pdfplumber
    except Exception:
        pass
    try:
        import pypdf  # type: ignore

        return "pypdf", pypdf
    except Exception:
        return None, None


def pdf_to_markdown(path: Path) -> tuple[str, list[str]]:
    extractor_name, extractor = import_pdf_extractors()
    warnings: list[str] = []
    if extractor_name == "pdfplumber":
        parts = []
        with extractor.open(path) as pdf:
            for index, page in enumerate(pdf.pages, start=1):
                text = (page.extract_text() or "").strip()
                if text:
                    parts.append(f"## Page {index}\n\n{text}")
        return "\n\n".join(parts).strip(), warnings
    if extractor_name == "pypdf":
        reader = extractor.PdfReader(str(path))
        parts = []
        for index, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if text:
                parts.append(f"## Page {index}\n\n{text}")
        return "\n\n".join(parts).strip(), warnings
    warnings.append(
        "PDF text extraction requires pdfplumber or pypdf. Install the docs extras or use the bundled Codex Python runtime."
    )
    return "", warnings


def text_to_markdown(path: Path) -> str:
    raw = read_text(path).strip()
    if path.name.lower().endswith(".psc.txt"):
        title = title_from_name(path.name.replace(".psc", ""))
        return f"## {title}\n\n{raw}"
    return raw


def copy_image_for_html(image: Path, page_slug: str) -> str:
    destination = HTML_ASSETS / page_slug / image.name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(image, destination)
    return f"../assets/{page_slug}/{image.name}"


def copy_image_for_public_assets(image: Path, page_slug: str) -> str:
    destination = SOURCE_ASSETS / "archive" / page_slug / image.name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(image, destination)
    return f"../assets/archive/{page_slug}/{image.name}"


def file_to_markdown(path: Path, page_slug: str) -> tuple[str, list[str]]:
    suffix = path.suffix.lower()
    warnings: list[str] = []
    if suffix in MARKDOWN_EXTENSIONS:
        return read_text(path).strip(), warnings
    if suffix in TEX_EXTENSIONS:
        return latex_to_markdown(path)
    if suffix in PDF_EXTENSIONS:
        return pdf_to_markdown(path)
    if suffix in IMAGE_EXTENSIONS:
        copy_image_for_html(path, page_slug)
        public_src = copy_image_for_public_assets(path, page_slug)
        alt = title_from_name(path.name)
        return f"![{alt}]({public_src})", warnings
    return text_to_markdown(path), warnings


def front_matter(title: str, values: dict[str, str]) -> str:
    lines = ["---", f'title: "{title}"']
    for key, value in values.items():
        safe = str(value).replace('"', '\\"')
        lines.append(f'{key}: "{safe}"')
    lines.append("---")
    return "\n".join(lines)


def build_archive_markdown(directory: Path, page_slug: str) -> tuple[str, list[str]]:
    relative = directory.relative_to(SOURCE_ARCHIVE)
    title = title_from_name(relative.name)
    warnings: list[str] = []
    files = [
        file
        for file in sorted(directory.iterdir(), key=lambda item: item.name.lower())
        if file.is_file() and file.suffix.lower() in CONVERTIBLE_EXTENSIONS
    ]
    source_archive = relative.parts[0] if relative.parts else directory.name
    sections = [
        front_matter(
            title,
            {
                "kind": "archive",
                "source_archive": source_archive,
                "source_folder": relative.as_posix(),
            },
        ),
        "",
        f"# {title}",
        "",
        f"Source folder: `{relative.as_posix()}`",
        "",
        "## Extracted Files",
        "",
    ]
    for file in files:
        sections.append(f"- `{file.name}`")
    sections.append("")

    for file in files:
        if file.suffix.lower() == ".zip":
            continue
        sections.extend([f"## {title_from_name(file.name)}", ""])
        body, file_warnings = file_to_markdown(file, page_slug)
        warnings.extend(file_warnings)
        if body:
            sections.extend([body, ""])
        else:
            sections.extend([f"No extractable text was found in `{file.name}`.", ""])
    return "\n".join(sections).strip() + "\n", warnings


def strip_front_matter(markdown: str) -> str:
    if not markdown.startswith("---"):
        return markdown
    match = re.match(r"^---\s*\n.*?\n---\s*\n", markdown, flags=re.DOTALL)
    if not match:
        return markdown
    return markdown[match.end() :]


def markdown_to_html(markdown: str, title: str, page_slug: str) -> tuple[str, list[str]]:
    warnings: list[str] = []
    markdown_body = strip_front_matter(markdown)
    try:
        import markdown as markdown_lib  # type: ignore

        body = markdown_lib.markdown(
            markdown_body,
            extensions=["extra", "toc", "tables", "fenced_code", "sane_lists", "attr_list"],
            output_format="html5",
        )
    except Exception as error:
        success, output = run_pandoc(
            [
                "--from=gfm+tex_math_dollars",
                "--to=html5",
                "--wrap=none",
            ],
            input_text=markdown_body,
        )
        if success:
            body = output
        else:
            warnings.append(f"Python-Markdown unavailable and Pandoc fallback failed: {error}; {output}")
            body = f"<pre>{html.escape(markdown_body)}</pre>"
    return wrap_html(title, body, page_slug), warnings


def markdown_file_to_html(markdown_path: Path, html_path: Path, title: str, page_slug: str) -> list[str]:
    markdown = read_text(markdown_path)
    html_doc, warnings = markdown_to_html(markdown, title, page_slug)
    write_text(html_path, html_doc)
    return warnings


def wrap_html(title: str, body: str, page_slug: str) -> str:
    escaped_title = html.escape(title)
    index_href = "../index.html" if "/" in page_slug else "index.html"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escaped_title} | OBI Source HTML</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f7f8f5;
      --surface: #ffffff;
      --text: #202321;
      --muted: #626962;
      --accent: #147d7e;
      --border: #d9ddd4;
      --code: #eef1eb;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.65;
    }}
    header, main, footer {{ max-width: 1060px; margin: 0 auto; padding: 1.25rem; }}
    header {{ border-bottom: 4px solid var(--accent); background: #161819; color: #f5f7f2; max-width: none; }}
    header > div {{ max-width: 1060px; margin: 0 auto; }}
    a {{ color: #0f5f60; }}
    header a {{ color: inherit; }}
    main {{ background: var(--surface); border: 1px solid var(--border); border-radius: 8px; margin-top: 1.25rem; }}
    h1, h2, h3 {{ line-height: 1.25; }}
    h1 {{ margin-top: 0; font-size: clamp(2rem, 5vw, 3.5rem); }}
    p, li {{ max-width: 78ch; }}
    img {{ max-width: 100%; height: auto; border: 1px solid var(--border); border-radius: 8px; }}
    pre {{ overflow: auto; background: #20251f; color: #f7fbf2; padding: 1rem; border-radius: 8px; }}
    code {{ background: var(--code); padding: 0.12rem 0.25rem; border-radius: 5px; }}
    pre code {{ background: transparent; padding: 0; }}
    table {{ border-collapse: collapse; width: 100%; display: block; overflow-x: auto; }}
    th, td {{ border: 1px solid var(--border); padding: 0.45rem 0.6rem; text-align: left; }}
    blockquote {{ border-left: 4px solid var(--accent); margin-left: 0; padding-left: 1rem; color: var(--muted); }}
    .skip-link {{ position: absolute; left: 1rem; top: 0.75rem; transform: translateY(-200%); }}
    .skip-link:focus {{ transform: translateY(0); background: var(--surface); color: var(--text); padding: 0.5rem; }}
  </style>
  <script>
    window.MathJax = {{ tex: {{ inlineMath: [["\\\\(", "\\\\)"], ["$", "$"]], displayMath: [["\\\\[", "\\\\]"], ["$$", "$$"]] }} }};
  </script>
  <script async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
</head>
<body>
  <a class="skip-link" href="#content">Skip to content</a>
  <header>
    <div>
      <a href="{index_href}">OBI Source HTML</a>
      <h1>{escaped_title}</h1>
      <p>Generated from Markdown with Python tooling and Pandoc-compatible source preservation.</p>
    </div>
  </header>
  <main id="content" tabindex="-1">
    {body}
  </main>
  <footer>
    <p>Generated artifact: <code>{html.escape(page_slug)}</code></p>
  </footer>
</body>
</html>
"""


def build_archive_pages() -> list[GeneratedPage]:
    pages: list[GeneratedPage] = []
    used_slugs: set[str] = set()
    for directory in content_directories():
        relative = directory.relative_to(SOURCE_ARCHIVE)
        page_slug = unique_slug(slugify(relative.as_posix()), used_slugs)
        markdown, warnings = build_archive_markdown(directory, page_slug)
        title = title_from_name(directory.name)
        markdown_path = ARCHIVE_MD / f"{page_slug}.md"
        html_path = ARCHIVE_HTML / f"{page_slug}.html"
        write_text(markdown_path, markdown)

        html_markdown = markdown.replace(
            f"](../assets/archive/{page_slug}/",
            f"](../assets/{page_slug}/",
        )
        temp_html_markdown = ARCHIVE_MD / f".{page_slug}.source-html.md"
        write_text(temp_html_markdown, html_markdown)
        warnings.extend(markdown_file_to_html(temp_html_markdown, html_path, title, f"archive/{page_slug}"))
        temp_html_markdown.unlink(missing_ok=True)
        pages.append(
            GeneratedPage(
                title=title,
                slug=page_slug,
                kind="archive",
                markdown_path=markdown_path,
                html_path=html_path,
                source_path=directory,
                warnings=warnings,
            )
        )
    return pages


def build_pdf_pages() -> list[GeneratedPage]:
    pages: list[GeneratedPage] = []
    used_slugs: set[str] = set()
    for pdf in sorted(SOURCE_PDF.glob("*.pdf")):
        title = title_from_name(pdf.name)
        slug = unique_slug(slugify(pdf.stem), used_slugs)
        body, warnings = pdf_to_markdown(pdf)
        public_pdf_href = f"../pdf/{quote(pdf.name)}"
        source_pdf_href = f"../../pdf/{quote(pdf.name)}"
        markdown = "\n".join(
            [
                front_matter(
                    title,
                    {
                        "kind": "pdf",
                        "source_pdf": pdf.name,
                    },
                ),
                "",
                f"# {title}",
                "",
                f"Original PDF: [{pdf.name}]({public_pdf_href})",
                "",
                body or "No extractable text was found in this PDF.",
                "",
            ]
        )
        markdown_path = PDF_MD / f"{slug}.md"
        html_path = PDF_HTML / f"{slug}.html"
        write_text(markdown_path, markdown)

        html_markdown = markdown.replace(f"]({public_pdf_href})", f"]({source_pdf_href})")
        temp_html_markdown = PDF_MD / f".{slug}.source-html.md"
        write_text(temp_html_markdown, html_markdown)
        warnings.extend(markdown_file_to_html(temp_html_markdown, html_path, title, f"pdf/{slug}"))
        temp_html_markdown.unlink(missing_ok=True)

        pages.append(
            GeneratedPage(
                title=title,
                slug=slug,
                kind="pdf",
                markdown_path=markdown_path,
                html_path=html_path,
                source_path=pdf,
                warnings=warnings,
            )
        )
    return pages


def detect_toolchain() -> dict[str, object]:
    tools = {
        "python": sys.executable,
        "pandoc": shutil.which("pandoc"),
        "pdflatex": shutil.which("pdflatex"),
        "xelatex": shutil.which("xelatex"),
        "lualatex": shutil.which("lualatex"),
        "bibtex": shutil.which("bibtex"),
    }
    extractor_name, _extractor = import_pdf_extractors()
    return {
        "tools": tools,
        "pdf_extractor": extractor_name,
        "python_markdown": module_available("markdown"),
    }


def module_available(name: str) -> bool:
    try:
        __import__(name)
        return True
    except Exception:
        return False


def write_index(pages: Iterable[GeneratedPage], toolchain: dict[str, object]) -> None:
    pages = sorted(pages, key=lambda page: (page.kind, page.title.lower()))
    items = "\n".join(
        f'<li><a href="{html.escape(page.kind)}/{html.escape(page.slug)}.html">{html.escape(page.title)}</a> '
        f'<span>{html.escape(page.kind)}</span></li>'
        for page in pages
    )
    tool_rows = "\n".join(
        f"<tr><th>{html.escape(key)}</th><td>{html.escape(str(value or 'not found'))}</td></tr>"
        for key, value in toolchain["tools"].items()
    )
    body = f"""
<h2>Generated Pages</h2>
<p>These HTML pages are generated from extracted ZIP folders and source PDFs. Serve this folder with <code>python scripts/serve-source-html.py</code> or <code>python -m http.server 8000 -d docs/source</code> and open <code>/html/</code>.</p>
<ul>{items}</ul>
<h2>Toolchain</h2>
<table>
  <tbody>
    {tool_rows}
    <tr><th>PDF extractor</th><td>{html.escape(str(toolchain["pdf_extractor"] or "not found"))}</td></tr>
    <tr><th>Python-Markdown</th><td>{html.escape(str(toolchain["python_markdown"]))}</td></tr>
  </tbody>
</table>
<p>Pandoc is preferred for LaTeX-to-Markdown conversion. MiKTeX or another LaTeX distribution is optional for future PDF compilation, but HTML generation does not require a TeX engine.</p>
"""
    write_text(SOURCE_HTML / "index.html", wrap_html("OBI Extracted Source Index", body, "index"))


def write_report(pages: Iterable[GeneratedPage], toolchain: dict[str, object]) -> None:
    report = {
        "page_count": 0,
        "pages": [],
        "toolchain": toolchain,
    }
    for page in pages:
        report["page_count"] += 1
        report["pages"].append(
            {
                "title": page.title,
                "kind": page.kind,
                "slug": page.slug,
                "markdown": page.markdown_path.relative_to(ROOT).as_posix(),
                "html": page.html_path.relative_to(ROOT).as_posix(),
                "source": page.source_path.relative_to(ROOT).as_posix()
                if ROOT in [page.source_path.resolve(), *page.source_path.resolve().parents]
                else str(page.source_path),
                "warnings": page.warnings,
            }
        )
    write_text(SOURCE_HTML / "manifest.json", json.dumps(report, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-clean", action="store_true", help="Keep previously generated extraction outputs.")
    parser.add_argument("--skip-archives", action="store_true", help="Do not extract docs/archive ZIP files.")
    parser.add_argument("--skip-pdfs", action="store_true", help="Do not convert docs/source/pdf files.")
    args = parser.parse_args()

    if not args.no_clean:
        clean_generated_dirs()
    ensure_dirs()

    pages: list[GeneratedPage] = []
    if not args.skip_archives:
        extract_archives()
        pages.extend(build_archive_pages())
    if not args.skip_pdfs:
        pages.extend(build_pdf_pages())

    toolchain = detect_toolchain()
    write_index(pages, toolchain)
    write_report(pages, toolchain)

    warnings = [warning for page in pages for warning in page.warnings]
    print(
        f"Generated {len(pages)} pages into {SOURCE_HTML.relative_to(ROOT).as_posix()} "
        f"and Markdown into {SOURCE_MD.relative_to(ROOT).as_posix()}."
    )
    if warnings:
        print(f"Completed with {len(warnings)} warning(s). See docs/source/html/manifest.json.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
