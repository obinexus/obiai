import fs from "node:fs/promises";
import { createReadStream } from "node:fs";
import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));

export const ROOT = path.resolve(scriptDir, "..");
export const DOCS_DIR = path.join(ROOT, "docs");
export const SOURCE_DIR = path.join(DOCS_DIR, "source");
export const PUBLIC_DIR = path.join(DOCS_DIR, "public");
export const ARCHIVE_DIR = path.join(DOCS_DIR, "archive");
export const PUBLIC_ASSETS_DIR = path.join(PUBLIC_DIR, "assets");
export const PUBLIC_PDF_DIR = path.join(PUBLIC_DIR, "pdf");
export const PUBLIC_SOURCE_HTML_DIR = path.join(PUBLIC_DIR, "source-html");
export const BASE_URL = "https://obinexus.github.io/obi/";
export const OBI_DEFINITION =
  "an ontological and Bayesian reasoning infrastructure for uncertainty-aware robotic and humanitarian systems.";

export const REQUIRED_SOURCE_DIRS = [
  "tex",
  "bib",
  "md",
  "pdf",
  "txt",
  "html",
  "assets",
].map((name) => path.join(SOURCE_DIR, name));

export const REQUIRED_OUTPUTS = [
  "pyproject.toml",
  "package.json",
  "README.md",
  ".circleci/config.yml",
  ".github/workflows/publish.yml",
  "nw/package.json",
  "docs/source/README.md",
  "docs/public/index.html",
  "docs/public/papers.html",
  "docs/public/bibliography.html",
  "docs/public/search.json",
  "docs/public/sitemap.xml",
  "docs/public/robots.txt",
  "docs/public/manifest.json",
  "docs/public/assets/obi.css",
  "docs/public/assets/obi.js",
];

export async function ensureDocumentationLayout() {
  const dirs = [
    SOURCE_DIR,
    PUBLIC_DIR,
    PUBLIC_ASSETS_DIR,
    PUBLIC_PDF_DIR,
    PUBLIC_SOURCE_HTML_DIR,
    ARCHIVE_DIR,
    ...REQUIRED_SOURCE_DIRS,
  ];
  for (const dir of dirs) {
    await fs.mkdir(dir, { recursive: true });
  }
}

export async function cleanPublicDocs() {
  const resolvedPublic = path.resolve(PUBLIC_DIR);
  const resolvedDocs = path.resolve(DOCS_DIR);
  if (!isInside(resolvedPublic, resolvedDocs)) {
    throw new Error(`Refusing to clean outside docs: ${resolvedPublic}`);
  }
  await fs.mkdir(PUBLIC_DIR, { recursive: true });
  const entries = await fs.readdir(PUBLIC_DIR, { withFileTypes: true });
  for (const entry of entries) {
    const target = path.join(PUBLIC_DIR, entry.name);
    if (!isInside(path.resolve(target), resolvedPublic)) {
      throw new Error(`Refusing to remove unsafe path: ${target}`);
    }
    await fs.rm(target, { recursive: true, force: true });
  }
  await fs.mkdir(PUBLIC_ASSETS_DIR, { recursive: true });
}

export function isInside(candidate, parent) {
  const relative = path.relative(parent, candidate);
  return relative === "" || (!relative.startsWith("..") && !path.isAbsolute(relative));
}

export async function listFiles(dir, extensions = null) {
  const found = [];
  async function walk(current) {
    let entries = [];
    try {
      entries = await fs.readdir(current, { withFileTypes: true });
    } catch (error) {
      if (error.code === "ENOENT") return;
      throw error;
    }
    for (const entry of entries) {
      const fullPath = path.join(current, entry.name);
      if (entry.isDirectory()) {
        await walk(fullPath);
      } else if (
        !extensions ||
        extensions.includes(path.extname(entry.name).toLowerCase())
      ) {
        found.push(fullPath);
      }
    }
  }
  await walk(dir);
  return found.sort((a, b) => a.localeCompare(b));
}

export async function copySourceAssets() {
  const sourceAssets = path.join(SOURCE_DIR, "assets");
  const assets = await listFiles(sourceAssets);
  for (const asset of assets) {
    const relative = path.relative(sourceAssets, asset);
    const destination = path.join(PUBLIC_ASSETS_DIR, relative);
    await fs.mkdir(path.dirname(destination), { recursive: true });
    await fs.copyFile(asset, destination);
  }
}

export async function copySourcePdfs() {
  const sourcePdfs = path.join(SOURCE_DIR, "pdf");
  const pdfs = await listFiles(sourcePdfs, [".pdf"]);
  for (const pdf of pdfs) {
    const relative = path.relative(sourcePdfs, pdf);
    const destination = path.join(PUBLIC_PDF_DIR, relative);
    await fs.mkdir(path.dirname(destination), { recursive: true });
    await fs.copyFile(pdf, destination);
  }
}

export async function copySourceHtml() {
  const sourceHtml = path.join(SOURCE_DIR, "html");
  const files = await listFiles(sourceHtml);
  for (const file of files) {
    const relative = path.relative(sourceHtml, file);
    const destination = path.join(PUBLIC_SOURCE_HTML_DIR, relative);
    await fs.mkdir(path.dirname(destination), { recursive: true });
    await fs.copyFile(file, destination);
  }
}

export function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

export function stripHtml(value) {
  return String(value ?? "")
    .replace(/<script[\s\S]*?<\/script>/gi, " ")
    .replace(/<style[\s\S]*?<\/style>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

export function slugify(value, fallback = "document") {
  const slug = String(value ?? "")
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/&/g, " and ")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 96);
  return slug || fallback;
}

export function uniqueSlug(baseSlug, usedSlugs) {
  let candidate = baseSlug;
  let index = 2;
  while (usedSlugs.has(candidate)) {
    candidate = `${baseSlug}-${index}`;
    index += 1;
  }
  usedSlugs.add(candidate);
  return candidate;
}

export function titleFromPath(filePath) {
  return path
    .basename(filePath, path.extname(filePath))
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export function relativePublicPath(filePath) {
  return path.relative(PUBLIC_DIR, filePath).replaceAll(path.sep, "/");
}

export function rootPrefixFor(publicRelativePath) {
  const depth = publicRelativePath.split("/").length - 1;
  return depth === 0 ? "" : "../".repeat(depth);
}

export function pageUrl(publicRelativePath) {
  return new URL(publicRelativePath.replace(/index\.html$/, ""), BASE_URL).href;
}

export function excerpt(value, length = 220) {
  const text = String(value ?? "").replace(/\s+/g, " ").trim();
  if (text.length <= length) return text;
  return `${text.slice(0, length - 1).trim()}...`;
}

export function parseFrontMatter(markdown) {
  if (!markdown.startsWith("---")) {
    return { data: {}, content: markdown };
  }
  const end = markdown.indexOf("\n---", 3);
  if (end === -1) {
    return { data: {}, content: markdown };
  }
  const raw = markdown.slice(3, end).trim();
  const data = {};
  for (const line of raw.split(/\r?\n/)) {
    const match = line.match(/^([A-Za-z0-9_-]+):\s*(.*)$/);
    if (match) {
      data[match[1]] = match[2].replace(/^["']|["']$/g, "");
    }
  }
  return { data, content: markdown.slice(end + 4).trimStart() };
}

export function inlineMarkdown(value) {
  const code = [];
  let html = escapeHtml(value).replace(/`([^`]+)`/g, (_match, inner) => {
    code.push(`<code>${inner}</code>`);
    return `@@CODE${code.length - 1}@@`;
  });
  html = html
    .replace(
      /!\[([^\]]*)\]\(([^)\s]+)(?:\s+&quot;([^&]*)&quot;)?\)/g,
      '<img src="$2" alt="$1" loading="lazy">',
    )
    .replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (match, label, href) => {
      const isLinkTarget =
        /^(https?:|mailto:|#|\.{0,2}\/)/i.test(href) ||
        /^[A-Za-z0-9_-]+[/.]/.test(href);
      return isLinkTarget ? `<a href="${href}">${label}</a>` : match;
    })
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\*([^*]+)\*/g, "<em>$1</em>");
  return html.replace(/@@CODE(\d+)@@/g, (_match, index) => code[Number(index)]);
}

export function markdownToHtml(markdown) {
  const { data, content } = parseFrontMatter(markdown);
  const lines = content.replace(/\r\n?/g, "\n").split("\n");
  const html = [];
  let paragraph = [];
  let list = null;
  let codeFence = null;
  const toc = [];

  function closeParagraph() {
    if (paragraph.length > 0) {
      html.push(`<p>${inlineMarkdown(paragraph.join(" "))}</p>`);
      paragraph = [];
    }
  }

  function closeList() {
    if (list) {
      html.push(`</${list}>`);
      list = null;
    }
  }

  for (const rawLine of lines) {
    const line = rawLine.trimEnd();
    const fenceMatch = line.match(/^```([A-Za-z0-9_-]*)\s*$/);
    if (fenceMatch) {
      if (codeFence) {
        html.push(
          `<pre><code class="language-${escapeHtml(codeFence.language)}">${escapeHtml(
            codeFence.lines.join("\n"),
          )}</code></pre>`,
        );
        codeFence = null;
      } else {
        closeParagraph();
        closeList();
        codeFence = { language: fenceMatch[1] || "text", lines: [] };
      }
      continue;
    }
    if (codeFence) {
      codeFence.lines.push(rawLine);
      continue;
    }

    if (line.trim() === "") {
      closeParagraph();
      closeList();
      continue;
    }

    const heading = line.match(/^(#{1,4})\s+(.+)$/);
    if (heading) {
      closeParagraph();
      closeList();
      const level = heading[1].length + 1;
      const title = heading[2].trim();
      const id = slugify(title);
      toc.push({ level, title, id });
      html.push(`<h${level} id="${id}">${inlineMarkdown(title)}</h${level}>`);
      continue;
    }

    const ordered = line.match(/^\d+\.\s+(.+)$/);
    const unordered = line.match(/^[-*]\s+(.+)$/);
    if (ordered || unordered) {
      closeParagraph();
      const type = ordered ? "ol" : "ul";
      if (list && list !== type) closeList();
      if (!list) {
        list = type;
        html.push(`<${type}>`);
      }
      html.push(`<li>${inlineMarkdown((ordered || unordered)[1])}</li>`);
      continue;
    }

    if (line.trimStart().startsWith(">")) {
      closeParagraph();
      closeList();
      html.push(`<blockquote>${inlineMarkdown(line.replace(/^>\s?/, ""))}</blockquote>`);
      continue;
    }

    paragraph.push(line.trim());
  }

  closeParagraph();
  closeList();
  if (codeFence) {
    html.push(`<pre><code>${escapeHtml(codeFence.lines.join("\n"))}</code></pre>`);
  }

  return { html: html.join("\n"), toc, data };
}

export function cleanTranscriptText(raw) {
  return String(raw ?? "")
    .replace(/\r\n?/g, "\n")
    .replace(/\b\d{1,2}:\d{2,}(?:\s*(?:minute|minutes|second|seconds|,|\d|s))*\s*/gi, " ")
    .replace(/\b\d+\s*(?:minute|minutes|second|seconds)\b/gi, " ")
    .replace(/[ \t]+/g, " ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

export function textToHtml(raw, title) {
  const cleaned = cleanTranscriptText(raw);
  const chunks = cleaned
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean);
  const sections = [];
  const groupSize = 12;

  sections.push(`<section id="source-note">`);
  sections.push(`<h2>Source Note</h2>`);
  sections.push(
    `<p>This page preserves a cleaned text source for ${escapeHtml(
      title,
    )}. Audio timestamps and transcript artifacts are reduced so the material can be searched and read as documentation.</p>`,
  );
  sections.push(`</section>`);

  for (let index = 0; index < chunks.length; index += groupSize) {
    const group = chunks.slice(index, index + groupSize);
    const id = `source-segment-${Math.floor(index / groupSize) + 1}`;
    sections.push(`<section id="${id}">`);
    sections.push(`<h2>Source Segment ${Math.floor(index / groupSize) + 1}</h2>`);
    for (const paragraph of group) {
      sections.push(`<p>${escapeHtml(paragraph)}</p>`);
    }
    sections.push(`</section>`);
  }

  const toc = extractHeadings(sections.join("\n"));
  return { html: sections.join("\n"), toc, text: cleaned };
}

export function parseBibTeX(raw) {
  const entries = [];
  const source = String(raw ?? "");
  let index = 0;
  while (index < source.length) {
    const at = source.indexOf("@", index);
    if (at === -1) break;
    const typeMatch = source.slice(at + 1).match(/^([A-Za-z]+)\s*\{/);
    if (!typeMatch) {
      index = at + 1;
      continue;
    }
    const type = typeMatch[1].toLowerCase();
    const open = at + 1 + typeMatch[0].lastIndexOf("{");
    let depth = 0;
    let close = -1;
    for (let cursor = open; cursor < source.length; cursor += 1) {
      const char = source[cursor];
      if (char === "{") depth += 1;
      if (char === "}") depth -= 1;
      if (depth === 0) {
        close = cursor;
        break;
      }
    }
    if (close === -1) break;

    const body = source.slice(open + 1, close);
    const comma = body.indexOf(",");
    if (comma !== -1) {
      const key = body.slice(0, comma).trim();
      const fieldsRaw = body.slice(comma + 1);
      const fields = {};
      const fieldPattern =
        /([A-Za-z][A-Za-z0-9_-]*)\s*=\s*(\{(?:[^{}]|\{[^{}]*\})*\}|"[^"]*"|[^,\n]+)\s*,?/g;
      let fieldMatch;
      while ((fieldMatch = fieldPattern.exec(fieldsRaw))) {
        fields[fieldMatch[1].toLowerCase()] = cleanBibValue(fieldMatch[2]);
      }
      entries.push({ type, key, fields });
    }
    index = close + 1;
  }
  return entries;
}

function cleanBibValue(value) {
  return String(value ?? "")
    .trim()
    .replace(/^["{]+|["}]+$/g, "")
    .replace(/[{}]/g, "")
    .replace(/\s+/g, " ");
}

export function bibliographyEntryHtml(entry) {
  const { fields } = entry;
  const title = fields.title || entry.key;
  const author = fields.author || "Unknown author";
  const year = fields.year || "n.d.";
  const venue = fields.journal || fields.booktitle || fields.publisher || fields.school || "";
  const doi = fields.doi
    ? ` <a href="https://doi.org/${escapeHtml(fields.doi)}">doi:${escapeHtml(fields.doi)}</a>`
    : "";
  return [
    `<li id="bib-${slugify(entry.key)}" class="bibliography-entry">`,
    `<strong>${escapeHtml(title)}</strong>`,
    `<span>${escapeHtml(author)} (${escapeHtml(year)}). ${escapeHtml(venue)}${doi}</span>`,
    `<code>${escapeHtml(entry.key)}</code>`,
    `</li>`,
  ].join("");
}

export function citationHtml(keys, bibliographyMap, currentRootPrefix = "") {
  return keys
    .split(",")
    .map((key) => key.trim())
    .filter(Boolean)
    .map((key) => {
      if (bibliographyMap.has(key)) {
        return `<a class="citation" href="${currentRootPrefix}bibliography.html#bib-${slugify(
          key,
        )}">[${escapeHtml(key)}]</a>`;
      }
      return `<span class="citation unresolved" title="Unresolved citation">[${escapeHtml(
        key,
      )}]</span>`;
    })
    .join(" ");
}

export function texToHtml(raw, bibliographyMap = new Map(), currentRootPrefix = "") {
  let source = String(raw ?? "").replace(/\r\n?/g, "\n");
  source = source.replace(/(^|[^\\])%.*/g, "$1");

  const title = matchTexCommand(source, "title");
  const author = matchTexCommand(source, "author");
  const date = matchTexCommand(source, "date");

  source = source
    .replace(/\\documentclass(?:\[[^\]]*\])?\{[^}]+\}/g, "")
    .replace(/\\usepackage(?:\[[^\]]*\])?\{[^}]+\}/g, "")
    .replace(/\\(?:title|author|date)\{[^}]*\}/g, "")
    .replace(/\\begin\{document\}|\\end\{document\}/g, "")
    .replace(/\\maketitle/g, "");

  const preserved = [];
  const keep = (html) => {
    const token = `@@OBI_KEEP_${preserved.length}@@`;
    preserved.push(html);
    return token;
  };

  source = source
    .replace(/\\begin\{abstract\}([\s\S]*?)\\end\{abstract\}/g, (_match, body) =>
      keep(`<section id="abstract"><h2>Abstract</h2><p>${inlineTex(body, bibliographyMap, currentRootPrefix)}</p></section>`),
    )
    .replace(/\\begin\{equation\}([\s\S]*?)\\end\{equation\}/g, (_match, body) =>
      keep(`<div class="math-block">\\[${escapeHtml(body.trim())}\\]</div>`),
    )
    .replace(/\\begin\{align\}([\s\S]*?)\\end\{align\}/g, (_match, body) =>
      keep(`<div class="math-block">\\[\\begin{align}${escapeHtml(body.trim())}\\end{align}\\]</div>`),
    )
    .replace(/\\\[([\s\S]*?)\\\]/g, (_match, body) =>
      keep(`<div class="math-block">\\[${escapeHtml(body.trim())}\\]</div>`),
    )
    .replace(/\\\(([\s\S]*?)\\\)/g, (_match, body) =>
      keep(`<span class="math-inline">\\(${escapeHtml(body.trim())}\\)</span>`),
    )
    .replace(/\\begin\{itemize\}([\s\S]*?)\\end\{itemize\}/g, (_match, body) =>
      keep(texListToHtml(body, "ul", bibliographyMap, currentRootPrefix)),
    )
    .replace(/\\begin\{enumerate\}([\s\S]*?)\\end\{enumerate\}/g, (_match, body) =>
      keep(texListToHtml(body, "ol", bibliographyMap, currentRootPrefix)),
    );

  const html = [];
  if (title) {
    html.push(`<section id="paper-metadata"><h2>Paper Metadata</h2>`);
    html.push(`<dl class="metadata-list">`);
    html.push(`<div><dt>Title</dt><dd>${escapeHtml(title)}</dd></div>`);
    if (author) html.push(`<div><dt>Author</dt><dd>${escapeHtml(author)}</dd></div>`);
    if (date) html.push(`<div><dt>Date</dt><dd>${escapeHtml(date)}</dd></div>`);
    html.push(`</dl></section>`);
  }

  for (const block of source.split(/\n{2,}/)) {
    const trimmed = block.trim();
    if (!trimmed) continue;
    const section = trimmed.match(/^\\section\{([^}]+)\}/);
    const subsection = trimmed.match(/^\\subsection\{([^}]+)\}/);
    const subsubsection = trimmed.match(/^\\subsubsection\{([^}]+)\}/);
    const paragraph = trimmed.match(/^\\paragraph\{([^}]+)\}/);
    const heading = section || subsection || subsubsection || paragraph;
    if (heading) {
      const level = section ? 2 : subsection ? 3 : subsubsection ? 4 : 5;
      const headingText = heading[1].trim();
      html.push(
        `<h${level} id="${slugify(headingText)}">${escapeHtml(headingText)}</h${level}>`,
      );
      const rest = trimmed.slice(heading[0].length).trim();
      if (rest) {
        html.push(`<p>${inlineTex(rest, bibliographyMap, currentRootPrefix)}</p>`);
      }
      continue;
    }
    if (/^@@OBI_KEEP_\d+@@$/.test(trimmed)) {
      html.push(trimmed);
      continue;
    }
    html.push(`<p>${inlineTex(trimmed, bibliographyMap, currentRootPrefix)}</p>`);
  }

  let output = html.join("\n");
  output = output.replace(/@@OBI_KEEP_(\d+)@@/g, (_match, idx) => preserved[Number(idx)]);
  return { html: output, toc: extractHeadings(output), metadata: { title, author, date } };
}

function matchTexCommand(source, command) {
  const pattern = new RegExp(`\\\\${command}\\{([^}]*)\\}`);
  return source.match(pattern)?.[1]?.trim() || "";
}

function texListToHtml(body, type, bibliographyMap, currentRootPrefix) {
  const items = body
    .split(/\\item/g)
    .map((item) => item.trim())
    .filter(Boolean)
    .map((item) => `<li>${inlineTex(item, bibliographyMap, currentRootPrefix)}</li>`)
    .join("");
  return `<${type}>${items}</${type}>`;
}

function inlineTex(value, bibliographyMap, currentRootPrefix) {
  let html = escapeHtml(value)
    .replace(/\\textbf\{([^}]+)\}/g, "<strong>$1</strong>")
    .replace(/\\textit\{([^}]+)\}/g, "<em>$1</em>")
    .replace(/\\emph\{([^}]+)\}/g, "<em>$1</em>")
    .replace(/\\label\{([^}]+)\}/g, '<span class="anchor-label" id="label-$1"></span>')
    .replace(/\\ref\{([^}]+)\}/g, '<a href="#label-$1">$1</a>');

  html = html.replace(/\\cite[pt]?\{([^}]+)\}/g, (_match, keys) =>
    citationHtml(keys, bibliographyMap, currentRootPrefix),
  );
  return html.replace(/\s+/g, " ").trim();
}

export function extractHeadings(html) {
  const headings = [];
  const pattern = /<h([2-4])\s+id="([^"]+)">([\s\S]*?)<\/h\1>/g;
  let match;
  while ((match = pattern.exec(html))) {
    headings.push({
      level: Number(match[1]),
      id: match[2],
      title: stripHtml(match[3]),
    });
  }
  return headings;
}

export function layout({
  title,
  description,
  body,
  toc = [],
  active = "index",
  publicPath = "index.html",
  pageType = "TechArticle",
}) {
  const prefix = rootPrefixFor(publicPath);
  const canonical = pageUrl(publicPath);
  const nav = [
    ["index", "index.html", "Overview"],
    ["papers", "papers.html", "Papers"],
    ["bibliography", "bibliography.html", "Bibliography"],
  ]
    .map(
      ([key, href, label]) =>
        `<a href="${prefix}${href}" class="${key === active ? "active" : ""}">${label}</a>`,
    )
    .join("");

  const tocHtml =
    toc.length > 0
      ? toc
          .map(
            (item) =>
              `<a class="toc-level-${item.level}" href="#${escapeHtml(item.id)}">${escapeHtml(
                item.title,
              )}</a>`,
          )
          .join("")
      : `<span class="toc-empty">No page sections</span>`;

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": pageType,
    name: title,
    description,
    isPartOf: {
      "@type": "WebSite",
      name: "OBI Documentation",
      url: BASE_URL,
    },
    author: {
      "@type": "Person",
      name: "Nnamdi Michael Okpala",
    },
  };

  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${escapeHtml(title)} | OBI Documentation</title>
  <meta name="description" content="${escapeHtml(description)}">
  <link rel="canonical" href="${escapeHtml(canonical)}">
  <meta property="og:title" content="${escapeHtml(title)}">
  <meta property="og:description" content="${escapeHtml(description)}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="${escapeHtml(canonical)}">
  <meta property="og:site_name" content="OBI Documentation">
  <meta name="twitter:card" content="summary">
  <meta name="twitter:title" content="${escapeHtml(title)}">
  <meta name="twitter:description" content="${escapeHtml(description)}">
  <link rel="manifest" href="${prefix}manifest.json">
  <link rel="stylesheet" href="${prefix}assets/obi.css">
  <script>
    window.MathJax = { tex: { inlineMath: [["\\\\(", "\\\\)"]], displayMath: [["\\\\[", "\\\\]"]] } };
    window.OBI_SEARCH_URL = "${prefix}search.json";
  </script>
  <script async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
  <script type="application/ld+json">${JSON.stringify(jsonLd)}</script>
</head>
<body>
  <a class="skip-link" href="#content">Skip to content</a>
  <header class="site-header">
    <div class="brand">
      <a href="${prefix}index.html" aria-label="OBI Documentation home">
        <span class="brand-mark">OBI</span>
        <span>
          <strong>Ontological Bayesian Intelligence</strong>
          <small>OBINexus documentation</small>
        </span>
      </a>
    </div>
    <button class="nav-toggle" type="button" aria-expanded="false" aria-controls="site-nav">Menu</button>
    <nav id="site-nav" class="site-nav" aria-label="Primary navigation">${nav}</nav>
  </header>
  <div class="doc-shell">
    <aside class="doc-sidebar">
      <search class="search-panel">
        <label for="site-search">Search documentation</label>
        <input id="site-search" type="search" placeholder="Search OBI docs" autocomplete="off">
        <div id="search-results" class="search-results" role="listbox" aria-label="Search results"></div>
      </search>
      <nav class="toc" aria-label="Table of contents">
        <h2>On This Page</h2>
        ${tocHtml}
      </nav>
    </aside>
    <main id="content" class="content" tabindex="-1">
      <article class="doc-article">
        <header class="article-header">
          <p class="eyebrow">OBINexus / OBI</p>
          <h1>${escapeHtml(title)}</h1>
          <p>${escapeHtml(description)}</p>
        </header>
        ${body}
      </article>
    </main>
  </div>
  <footer class="site-footer">
    <p>OBI is ${escapeHtml(OBI_DEFINITION)}</p>
    <p>Generated as static HTML for local serving, NW.js desktop viewing, and GitHub Pages publishing.</p>
  </footer>
  <script src="${prefix}assets/obi.js" defer></script>
</body>
</html>`;
}

export function section(id, title, content) {
  return `<section id="${id}">
  <h2>${escapeHtml(title)}</h2>
  ${content}
</section>`;
}

export function overviewPageBody(sourceDocs = []) {
  const sourceList =
    sourceDocs.length > 0
      ? `<ul>${sourceDocs
          .map(
            (doc) =>
              `<li><a href="${escapeHtml(doc.href)}">${escapeHtml(doc.title)}</a> <span>${escapeHtml(
                doc.kind.toUpperCase(),
              )}</span></li>`,
          )
          .join("")}</ul>`
      : "<p>No source documents have been indexed yet.</p>";

  return [
    section(
      "what-is-obi",
      "What is OBI?",
      `<p>OBI means Ontological Bayesian Intelligence. It is ${escapeHtml(
        OBI_DEFINITION,
      )}</p><p>Its documentation focuses on semantic graphs, Bayesian inference, stochastic models, uncertainty, and reasoning infrastructure for real-world assistance systems.</p>`,
    ),
    section(
      "why-uncertainty-matters",
      "Why uncertainty matters",
      `<p>Human-facing and robotic systems rarely receive complete information. OBI treats incomplete evidence, conflicting signals, and probabilistic confidence as first-class inputs instead of forcing every question into a brittle yes/no state.</p>`,
    ),
    section(
      "ontologies-as-semantic-graphs",
      "Ontologies as semantic graphs",
      `<p>Ontologies are used as structured semantic graphs: nodes represent concepts, states, events, or actors, while edges describe relationships and interpretations. Coloring, partitioning, and labeling can expose different semantic roles inside the same knowledge structure.</p>`,
    ),
    section(
      "bayesian-reasoning",
      "Bayesian reasoning",
      `<p>Bayesian reasoning gives OBI a way to update belief under evidence. Probabilities are not decorative metadata; they express how strongly the system can support a claim given available observations and prior structure.</p>`,
    ),
    section(
      "stochastic-subject-matter",
      "Stochastic subject matter",
      `<p>Some subject matter varies over time, context, or observer. OBI preserves this stochastic character so the system can normalize, compare, and reason over distributions without pretending uncertain material is perfectly stable.</p>`,
    ),
    section(
      "top-down-and-bottom-up-reasoning",
      "Top-down and bottom-up reasoning",
      `<p>Top-down reasoning starts from a model, ontology, or hypothesis and tests observations against it. Bottom-up reasoning starts from evidence and builds toward structure. OBI needs both directions because real systems must diagnose, explain, and adapt.</p>`,
    ),
    section(
      "semantic-drift-and-data-drift",
      "Semantic drift and data drift",
      `<p>Data drift changes observed distributions. Semantic drift changes the meaning or interpretation of concepts. OBI documentation keeps both visible because robust reasoning has to notice when evidence changes and when the language around evidence changes.</p>`,
    ),
    section(
      "filter-flash-reasoning-cycle",
      "Filter/flash reasoning cycle",
      `<p>The filter/flash cycle separates careful constraint checking from rapid hypothesis formation. A filter phase can remove unsafe or unsupported interpretations, while a flash phase can propose candidate explanations for further validation.</p>`,
    ),
    section(
      "obi-for-robotics",
      "OBI for robotics",
      `<p>For robotics, OBI frames sensors, commands, environment state, and safety checks as uncertainty-aware reasoning inputs. The goal is infrastructure that helps machines act with contextual awareness while remaining inspectable by humans.</p>`,
    ),
    section(
      "humanitarian-real-world-systems",
      "Humanitarian real-world systems",
      `<p>OBI is oriented toward assistance systems that operate in messy real conditions: healthcare, safety-critical environments, accessibility, field support, and other humanitarian settings where uncertainty and ethics cannot be ignored.</p>`,
    ),
    section(
      "what-obi-is-not",
      "What OBI is not",
      `<p>OBI should not be described as conscious AI. It is not a claim of machine consciousness, sentience, or personhood. It is a reasoning infrastructure for uncertainty-aware robotic and humanitarian systems.</p>`,
    ),
    section(
      "glossary",
      "Glossary",
      `<dl class="glossary">
        <div><dt>Ontology</dt><dd>A structured representation of concepts and relationships in a domain.</dd></div>
        <div><dt>Bayesian inference</dt><dd>A method for updating belief when new evidence appears.</dd></div>
        <div><dt>Semantic graph</dt><dd>A graph whose nodes and edges carry interpretable meaning.</dd></div>
        <div><dt>Stochastic</dt><dd>Having probabilistic variation that can be modeled but not predicted perfectly.</dd></div>
        <div><dt>Data drift</dt><dd>A change in the observed data distribution over time.</dd></div>
        <div><dt>Semantic drift</dt><dd>A change in the meaning or usage of concepts over time or context.</dd></div>
      </dl>`,
    ),
    section("source-documents", "Source documents", sourceList),
  ].join("\n");
}

export function papersPageBody(documents, archives) {
  const docItems =
    documents.length > 0
      ? documents
          .map(
            (doc) =>
              `<li><a href="${escapeHtml(doc.href)}">${escapeHtml(doc.title)}</a><span>${escapeHtml(
                doc.kind.toUpperCase(),
              )}</span><p>${escapeHtml(doc.summary)}</p></li>`,
          )
          .join("")
      : `<li><span>No generated source pages yet.</span></li>`;
  const archiveItems =
    archives.length > 0
      ? archives
          .map(
            (archive) =>
              `<li><span>${escapeHtml(archive.title)}</span>${
                archive.htmlHref
                  ? `<a href="${escapeHtml(archive.htmlHref)}">HTML view</a>`
                  : ""
              }<code>${escapeHtml(
                archive.fileName,
              )}</code></li>`,
          )
          .join("")
      : `<li><span>No archived bundles found.</span></li>`;
  const extractedIndex = archives.some((archive) => archive.extractedIndexHref)
    ? `<p><a href="source-html/index.html">Open extracted archive and PDF HTML index</a>. These pages are generated under <code>docs/source/html</code> and copied into <code>docs/public/source-html</code> during the docs build.</p>`
    : "";

  return [
    section(
      "generated-source-pages",
      "Generated Source Pages",
      `<p>These pages are converted from material under <code>docs/source</code>. They are static, searchable, and share the same layout as the rest of the documentation.</p><ul class="document-list">${docItems}</ul>`,
    ),
    section(
      "archived-research-bundles",
      "Archived Research Bundles",
      `<p>ZIP bundles are preserved in <code>docs/archive</code>. Run <code>npm run docs:populate</code> to extract them into Markdown and Pandoc-compatible HTML views.</p>${extractedIndex}<ul class="archive-list">${archiveItems}</ul>`,
    ),
  ].join("\n");
}

export function bibliographyPageBody(entries) {
  if (entries.length === 0) {
    return section(
      "bibliography",
      "Bibliography",
      `<p>No BibTeX entries were found in <code>docs/source/bib</code>. Add <code>.bib</code> files there and run <code>npm run docs:build</code> to regenerate this page and <code>bibliography.json</code>.</p>`,
    );
  }
  return section(
    "bibliography",
    "Bibliography",
    `<ol class="bibliography-list">${entries.map(bibliographyEntryHtml).join("\n")}</ol>`,
  );
}

export async function writeTextFile(filePath, contents) {
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  await fs.writeFile(filePath, contents, "utf8");
}

export async function readTextFile(filePath) {
  return fs.readFile(filePath, "utf8");
}

export async function readBibEntries() {
  const bibFiles = await listFiles(path.join(SOURCE_DIR, "bib"), [".bib"]);
  const entries = [];
  for (const file of bibFiles) {
    const raw = await readTextFile(file);
    for (const entry of parseBibTeX(raw)) {
      entries.push({ ...entry, sourceFile: path.relative(ROOT, file).replaceAll(path.sep, "/") });
    }
  }
  entries.sort((a, b) => {
    const aYear = a.fields.year || "";
    const bYear = b.fields.year || "";
    return bYear.localeCompare(aYear) || a.key.localeCompare(b.key);
  });
  return entries;
}

export async function buildDocumentation() {
  await ensureDocumentationLayout();
  await cleanPublicDocs();
  await copySourceAssets();
  await copySourcePdfs();
  await copySourceHtml();
  await writeTextFile(path.join(PUBLIC_ASSETS_DIR, "obi.css"), cssAsset());
  await writeTextFile(path.join(PUBLIC_ASSETS_DIR, "obi.js"), jsAsset());

  const bibliographyEntries = await readBibEntries();
  const bibliographyMap = new Map(bibliographyEntries.map((entry) => [entry.key, entry]));
  const generatedDocuments = await buildSourcePages(bibliographyMap);
  const archives = await archiveMetadata();

  await writeStandardPages(generatedDocuments, archives, bibliographyEntries);
  await writeSearchIndex(generatedDocuments, bibliographyEntries);
  await writeSitemap(generatedDocuments);
  await writeRobots();
  await writeManifest();

  return {
    generatedDocuments,
    bibliographyEntries,
    archives,
  };
}

export async function buildSourcePages(bibliographyMap) {
  const sourceFiles = [
    ...(await listFiles(path.join(SOURCE_DIR, "txt"), [".txt"])),
    ...(await listFiles(path.join(SOURCE_DIR, "md"), [".md", ".markdown"])),
    ...(await listFiles(path.join(SOURCE_DIR, "tex"), [".tex"])),
  ];
  const documents = [];
  const usedSlugs = new Set();
  for (const file of sourceFiles) {
    const extension = path.extname(file).toLowerCase();
    const raw = await readTextFile(file);
    const title = titleFromPath(file);
    const slug = uniqueSlug(slugify(path.basename(file, extension)), usedSlugs);
    const publicPath = `sources/${slug}.html`;
    const outputPath = path.join(PUBLIC_DIR, publicPath);
    const prefix = rootPrefixFor(publicPath);
    let converted;
    let kind = extension.slice(1);

    if (extension === ".txt") {
      converted = textToHtml(raw, title);
    } else if (extension === ".tex") {
      converted = texToHtml(raw, bibliographyMap, prefix);
    } else {
      converted = markdownToHtml(raw);
      if (converted.data.title) {
        converted.title = converted.data.title;
      }
    }

    const pageTitle = converted.title || converted.metadata?.title || title;
    const summary = excerpt(stripHtml(converted.html || raw), 260);
    const html = layout({
      title: pageTitle,
      description: summary || `Converted ${kind.toUpperCase()} source document for OBI.`,
      body: converted.html,
      toc: converted.toc?.length ? converted.toc : extractHeadings(converted.html),
      active: "papers",
      publicPath,
      pageType: "ScholarlyArticle",
    });
    await writeTextFile(outputPath, html);
    documents.push({
      title: pageTitle,
      href: publicPath,
      publicPath,
      kind,
      summary,
      sourcePath: path.relative(ROOT, file).replaceAll(path.sep, "/"),
      text: cleanTranscriptText(raw),
    });
  }
  return documents.sort((a, b) => a.title.localeCompare(b.title));
}

async function writeStandardPages(documents, archives, bibliographyEntries) {
  const overviewBody = overviewPageBody(
    documents.map((document) => ({
      ...document,
      href: document.href,
    })),
  );
  await writeTextFile(
    path.join(PUBLIC_DIR, "index.html"),
    layout({
      title: "OBI Documentation",
      description: `OBI is ${OBI_DEFINITION}`,
      body: overviewBody,
      toc: extractHeadings(overviewBody),
      active: "index",
      publicPath: "index.html",
      pageType: "WebPage",
    }),
  );

  const papersBody = papersPageBody(documents, archives);
  await writeTextFile(
    path.join(PUBLIC_DIR, "papers.html"),
    layout({
      title: "Papers and Source Documents",
      description: "Converted source documents and archived OBI research bundles.",
      body: papersBody,
      toc: extractHeadings(papersBody),
      active: "papers",
      publicPath: "papers.html",
      pageType: "CollectionPage",
    }),
  );

  const bibliographyBody = bibliographyPageBody(bibliographyEntries);
  await writeTextFile(
    path.join(PUBLIC_DIR, "bibliography.html"),
    layout({
      title: "Bibliography",
      description: "BibTeX references for OBI documentation.",
      body: bibliographyBody,
      toc: extractHeadings(bibliographyBody),
      active: "bibliography",
      publicPath: "bibliography.html",
      pageType: "CollectionPage",
    }),
  );

  await writeTextFile(
    path.join(PUBLIC_DIR, "bibliography.json"),
    `${JSON.stringify(bibliographyEntries, null, 2)}\n`,
  );
}

export async function writeSearchIndex(documents = null, bibliographyEntries = null) {
  let records;
  if (documents) {
    records = [
      {
        title: "OBI Documentation",
        href: "index.html",
        kind: "page",
        summary: `OBI is ${OBI_DEFINITION}`,
        text: stripHtml(overviewPageBody(documents)),
      },
      {
        title: "Papers and Source Documents",
        href: "papers.html",
        kind: "page",
        summary: "Converted source documents and archived OBI research bundles.",
        text: stripHtml(papersPageBody(documents, [])),
      },
      {
        title: "Bibliography",
        href: "bibliography.html",
        kind: "page",
        summary: "BibTeX references for OBI documentation.",
        text: bibliographyEntries
          ? bibliographyEntries
              .map((entry) => `${entry.key} ${Object.values(entry.fields).join(" ")}`)
              .join(" ")
          : "",
      },
      ...documents.map((document) => ({
        title: document.title,
        href: document.href,
        kind: document.kind,
        summary: document.summary,
        text: document.text,
        sourcePath: document.sourcePath,
      })),
    ];
  } else {
    records = await searchIndexFromPublicHtml();
  }
  await writeTextFile(path.join(PUBLIC_DIR, "search.json"), `${JSON.stringify(records, null, 2)}\n`);
  return records;
}

export async function searchIndexFromPublicHtml() {
  const htmlFiles = (await listFiles(PUBLIC_DIR, [".html"])).filter(
    (file) => !file.includes(`${path.sep}node_modules${path.sep}`),
  );
  const records = [];
  for (const file of htmlFiles) {
    const html = await readTextFile(file);
    const title = stripHtml(html.match(/<h1[^>]*>([\s\S]*?)<\/h1>/)?.[1] || titleFromPath(file));
    const text = stripHtml(html);
    const href = relativePublicPath(file);
    records.push({
      title,
      href,
      kind: "html",
      summary: excerpt(text),
      text,
    });
  }
  await writeTextFile(path.join(PUBLIC_DIR, "search.json"), `${JSON.stringify(records, null, 2)}\n`);
  return records;
}

async function archiveMetadata() {
  const archiveFiles = await listFiles(ARCHIVE_DIR, [".zip"]);
  const sourceHtmlIndex = path.join(PUBLIC_SOURCE_HTML_DIR, "index.html");
  const extractedIndexHref = (await fileExists(sourceHtmlIndex)) ? "source-html/index.html" : null;
  return Promise.all(
    archiveFiles.map(async (file) => {
      const slug = slugify(path.basename(file, path.extname(file)));
      const archiveHtml = path.join(PUBLIC_SOURCE_HTML_DIR, "archive", `${slug}.html`);
      return {
        title: titleFromPath(file),
        fileName: path.basename(file),
        path: path.relative(ROOT, file).replaceAll(path.sep, "/"),
        htmlHref: (await fileExists(archiveHtml)) ? `source-html/archive/${slug}.html` : null,
        extractedIndexHref,
      };
    }),
  );
}

async function fileExists(filePath) {
  try {
    const stat = await fs.stat(filePath);
    return stat.isFile();
  } catch {
    return false;
  }
}

async function writeSitemap(documents) {
  const pages = ["index.html", "papers.html", "bibliography.html", ...documents.map((doc) => doc.href)];
  const urls = pages
    .map(
      (page) => `  <url>
    <loc>${escapeHtml(pageUrl(page))}</loc>
  </url>`,
    )
    .join("\n");
  await writeTextFile(
    path.join(PUBLIC_DIR, "sitemap.xml"),
    `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls}
</urlset>
`,
  );
}

async function writeRobots() {
  await writeTextFile(
    path.join(PUBLIC_DIR, "robots.txt"),
    `User-agent: *
Allow: /

Sitemap: ${BASE_URL}sitemap.xml
`,
  );
}

async function writeManifest() {
  const manifest = {
    name: "OBI Documentation",
    short_name: "OBI Docs",
    description: `OBI is ${OBI_DEFINITION}`,
    start_url: "index.html",
    display: "standalone",
    background_color: "#f7f8f5",
    theme_color: "#161819",
    icons: [],
  };
  await writeTextFile(path.join(PUBLIC_DIR, "manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`);
}

export async function validateDocumentation() {
  const missing = [];
  for (const relative of REQUIRED_OUTPUTS) {
    const fullPath = path.join(ROOT, relative);
    try {
      const stat = await fs.stat(fullPath);
      if (!stat.isFile()) missing.push(relative);
    } catch {
      missing.push(relative);
    }
  }

  const jsonFiles = [
    "docs/public/search.json",
    "docs/public/bibliography.json",
    "docs/public/manifest.json",
  ];
  const invalidJson = [];
  for (const relative of jsonFiles) {
    try {
      JSON.parse(await readTextFile(path.join(ROOT, relative)));
    } catch (error) {
      invalidJson.push(`${relative}: ${error.message}`);
    }
  }

  const htmlFiles = ["index.html", "papers.html", "bibliography.html"];
  const missingSemantics = [];
  for (const relative of htmlFiles) {
    const html = await readTextFile(path.join(PUBLIC_DIR, relative));
    for (const tag of ["header", "nav", "main", "article", "section", "footer"]) {
      if (!html.includes(`<${tag}`)) {
        missingSemantics.push(`${relative} lacks <${tag}>`);
      }
    }
  }

  return {
    ok: missing.length === 0 && invalidJson.length === 0 && missingSemantics.length === 0,
    missing,
    invalidJson,
    missingSemantics,
  };
}

export async function servePublicDocs({ host = "127.0.0.1", port = 4173 } = {}) {
  await ensureDocumentationLayout();
  const server = http.createServer(async (request, response) => {
    const url = new URL(request.url || "/", `http://${host}:${port}`);
    let requestPath = decodeURIComponent(url.pathname);
    if (requestPath === "/") requestPath = "/index.html";
    const target = path.resolve(PUBLIC_DIR, `.${requestPath}`);

    if (!isInside(target, path.resolve(PUBLIC_DIR))) {
      response.writeHead(403, { "Content-Type": "text/plain; charset=utf-8" });
      response.end("Forbidden");
      return;
    }

    try {
      const stat = await fs.stat(target);
      if (stat.isDirectory()) {
        response.writeHead(302, { Location: `${url.pathname.replace(/\/$/, "")}/index.html` });
        response.end();
        return;
      }
      response.writeHead(200, { "Content-Type": contentType(target) });
      createReadStream(target).pipe(response);
    } catch {
      response.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
      response.end("Not found");
    }
  });

  return new Promise((resolve, reject) => {
    function tryListen(candidatePort, attemptsLeft) {
      server.once("error", (error) => {
        if (error.code === "EADDRINUSE" && attemptsLeft > 0) {
          tryListen(candidatePort + 1, attemptsLeft - 1);
          return;
        }
        reject(error);
      });
      server.listen(candidatePort, host, () => {
        resolve({
          server,
          host,
          port: candidatePort,
          url: `http://${host}:${candidatePort}/`,
        });
      });
    }
    tryListen(port, 20);
  });
}

function contentType(filePath) {
  const extension = path.extname(filePath).toLowerCase();
  return (
    {
      ".html": "text/html; charset=utf-8",
      ".css": "text/css; charset=utf-8",
      ".js": "text/javascript; charset=utf-8",
      ".json": "application/json; charset=utf-8",
      ".xml": "application/xml; charset=utf-8",
      ".txt": "text/plain; charset=utf-8",
      ".svg": "image/svg+xml",
      ".png": "image/png",
      ".jpg": "image/jpeg",
      ".jpeg": "image/jpeg",
      ".gif": "image/gif",
      ".webp": "image/webp",
      ".pdf": "application/pdf",
    }[extension] || "application/octet-stream"
  );
}

export function cssAsset() {
  return `:root {
  --obi-bg: #f7f8f5;
  --obi-surface: #ffffff;
  --obi-text: #202321;
  --obi-muted: #626962;
  --obi-accent: #147d7e;
  --obi-accent-strong: #0f5f60;
  --obi-header: #161819;
  --obi-header-text: #f5f7f2;
  --obi-border: #d9ddd4;
  --obi-code-bg: #eef1eb;
  --obi-warning: #9b5d10;
  --obi-radius: 8px;
  --obi-max-width: 1180px;
  --obi-shadow: 0 16px 36px rgba(22, 24, 25, 0.08);
}

* {
  box-sizing: border-box;
}

html {
  scroll-behavior: smooth;
}

body {
  margin: 0;
  background: var(--obi-bg);
  color: var(--obi-text);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  line-height: 1.65;
}

a {
  color: var(--obi-accent-strong);
  text-decoration-thickness: 0.08em;
  text-underline-offset: 0.18em;
}

a:hover,
a:focus {
  color: #0b4b4c;
}

.skip-link {
  position: absolute;
  left: 1rem;
  top: 0.75rem;
  z-index: 5;
  transform: translateY(-200%);
  background: var(--obi-surface);
  color: var(--obi-text);
  border: 2px solid var(--obi-accent);
  border-radius: var(--obi-radius);
  padding: 0.5rem 0.75rem;
}

.skip-link:focus {
  transform: translateY(0);
}

.site-header {
  position: sticky;
  top: 0;
  z-index: 4;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  min-height: 72px;
  padding: 0.85rem clamp(1rem, 3vw, 2rem);
  background: var(--obi-header);
  color: var(--obi-header-text);
  border-bottom: 4px solid var(--obi-accent);
}

.brand a {
  display: inline-flex;
  align-items: center;
  gap: 0.8rem;
  color: inherit;
  text-decoration: none;
}

.brand-mark {
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  border: 1px solid rgba(255, 255, 255, 0.28);
  border-radius: var(--obi-radius);
  color: #ffffff;
  background: #1f3f3f;
  font-weight: 800;
}

.brand strong,
.brand small {
  display: block;
}

.brand strong {
  font-size: 1rem;
}

.brand small {
  color: #cfd6cf;
  font-size: 0.82rem;
}

.site-nav {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.site-nav a,
.nav-toggle {
  color: var(--obi-header-text);
  border-radius: var(--obi-radius);
  padding: 0.55rem 0.75rem;
  text-decoration: none;
}

.site-nav a.active,
.site-nav a:hover,
.site-nav a:focus,
.nav-toggle:hover,
.nav-toggle:focus {
  background: rgba(255, 255, 255, 0.12);
}

.nav-toggle {
  display: none;
  border: 1px solid rgba(255, 255, 255, 0.24);
  background: transparent;
  font: inherit;
}

.doc-shell {
  display: grid;
  grid-template-columns: minmax(240px, 300px) minmax(0, 1fr);
  gap: clamp(1rem, 3vw, 2rem);
  max-width: var(--obi-max-width);
  margin: 0 auto;
  padding: clamp(1rem, 3vw, 2rem);
}

.doc-sidebar {
  align-self: start;
  position: sticky;
  top: 96px;
  display: grid;
  gap: 1rem;
}

.search-panel,
.toc {
  background: var(--obi-surface);
  border: 1px solid var(--obi-border);
  border-radius: var(--obi-radius);
  padding: 1rem;
  box-shadow: var(--obi-shadow);
}

.search-panel label,
.toc h2 {
  display: block;
  margin: 0 0 0.6rem;
  color: var(--obi-muted);
  font-size: 0.8rem;
  font-weight: 700;
  text-transform: uppercase;
}

.search-panel input {
  width: 100%;
  min-height: 42px;
  border: 1px solid var(--obi-border);
  border-radius: var(--obi-radius);
  padding: 0.55rem 0.65rem;
  color: var(--obi-text);
  background: #fbfcf9;
  font: inherit;
}

.search-panel input:focus {
  outline: 3px solid rgba(20, 125, 126, 0.18);
  border-color: var(--obi-accent);
}

.search-results {
  display: grid;
  gap: 0.4rem;
  margin-top: 0.65rem;
}

.search-result {
  display: block;
  border: 1px solid var(--obi-border);
  border-radius: var(--obi-radius);
  padding: 0.55rem;
  background: #fbfcf9;
  color: inherit;
  text-decoration: none;
}

.search-result strong,
.search-result span {
  display: block;
}

.search-result span {
  color: var(--obi-muted);
  font-size: 0.84rem;
}

.toc {
  max-height: calc(100vh - 220px);
  overflow: auto;
}

.toc a,
.toc-empty {
  display: block;
  border-left: 3px solid transparent;
  padding: 0.35rem 0.45rem;
  color: var(--obi-muted);
  text-decoration: none;
  font-size: 0.92rem;
}

.toc a.active {
  border-left-color: var(--obi-accent);
  color: var(--obi-text);
  background: #eef6f4;
}

.toc-level-3 {
  margin-left: 0.75rem;
}

.toc-level-4 {
  margin-left: 1.5rem;
}

.content {
  min-width: 0;
}

.doc-article {
  background: var(--obi-surface);
  border: 1px solid var(--obi-border);
  border-radius: var(--obi-radius);
  padding: clamp(1.25rem, 4vw, 3rem);
  box-shadow: var(--obi-shadow);
}

.article-header {
  border-bottom: 1px solid var(--obi-border);
  margin-bottom: 2rem;
  padding-bottom: 1.25rem;
}

.eyebrow {
  margin: 0 0 0.35rem;
  color: var(--obi-accent-strong);
  font-size: 0.82rem;
  font-weight: 800;
  text-transform: uppercase;
}

h1,
h2,
h3,
h4,
h5 {
  color: #1d211d;
  line-height: 1.25;
}

h1 {
  max-width: 13ch;
  margin: 0 0 0.75rem;
  font-size: clamp(2rem, 6vw, 4.35rem);
}

h2 {
  margin: 2rem 0 0.75rem;
  font-size: clamp(1.35rem, 3vw, 2rem);
}

h3 {
  margin: 1.5rem 0 0.55rem;
  font-size: 1.22rem;
}

p,
li,
dd {
  max-width: 76ch;
}

.doc-article img {
  display: block;
  max-width: 100%;
  height: auto;
  border: 1px solid var(--obi-border);
  border-radius: var(--obi-radius);
  background: #fbfcf9;
}

.doc-article p > img:only-child {
  margin: 1rem 0;
}

section {
  scroll-margin-top: 96px;
}

code,
pre {
  font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace;
}

code {
  border-radius: 5px;
  background: var(--obi-code-bg);
  padding: 0.12rem 0.25rem;
  font-size: 0.93em;
}

pre {
  position: relative;
  overflow: auto;
  border: 1px solid var(--obi-border);
  border-radius: var(--obi-radius);
  background: #20251f;
  color: #f7fbf2;
  padding: 1rem;
}

pre code {
  background: transparent;
  padding: 0;
}

.copy-code {
  position: absolute;
  right: 0.6rem;
  top: 0.6rem;
  border: 1px solid rgba(255, 255, 255, 0.28);
  border-radius: var(--obi-radius);
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
  padding: 0.25rem 0.5rem;
}

.math-block {
  overflow: auto;
  border-left: 4px solid var(--obi-accent);
  background: #f0f5f2;
  padding: 0.75rem 1rem;
}

.citation.unresolved {
  color: var(--obi-warning);
  font-weight: 700;
}

.glossary,
.metadata-list {
  display: grid;
  gap: 0.75rem;
}

.glossary div,
.metadata-list div {
  border-left: 4px solid var(--obi-accent);
  padding-left: 0.85rem;
}

dt {
  font-weight: 800;
}

dd {
  margin: 0.15rem 0 0;
}

.document-list,
.archive-list,
.bibliography-list {
  display: grid;
  gap: 0.75rem;
  padding-left: 1.25rem;
}

.document-list li,
.archive-list li,
.bibliography-entry {
  padding: 0.2rem 0;
}

.document-list span,
.archive-list code,
.bibliography-entry code {
  display: inline-block;
  margin-left: 0.4rem;
  color: var(--obi-muted);
}

.bibliography-entry strong,
.bibliography-entry span,
.bibliography-entry code {
  display: block;
  margin-left: 0;
}

.site-footer {
  max-width: var(--obi-max-width);
  margin: 0 auto;
  padding: 1rem clamp(1rem, 3vw, 2rem) 2rem;
  color: var(--obi-muted);
  font-size: 0.92rem;
}

@media (max-width: 840px) {
  .site-header {
    align-items: flex-start;
    flex-wrap: wrap;
  }

  .nav-toggle {
    display: inline-flex;
  }

  .site-nav {
    display: none;
    width: 100%;
    flex-direction: column;
    align-items: stretch;
  }

  .site-nav.open {
    display: flex;
  }

  .doc-shell {
    grid-template-columns: 1fr;
  }

  .doc-sidebar {
    position: static;
  }

  .toc {
    max-height: none;
  }

  h1 {
    max-width: 100%;
    font-size: 2.25rem;
  }
}
`;
}

export function jsAsset() {
  return `(function () {
  var searchInput = document.getElementById("site-search");
  var searchResults = document.getElementById("search-results");
  var navToggle = document.querySelector(".nav-toggle");
  var siteNav = document.getElementById("site-nav");
  var searchIndex = [];

  if (navToggle && siteNav) {
    navToggle.addEventListener("click", function () {
      var isOpen = siteNav.classList.toggle("open");
      navToggle.setAttribute("aria-expanded", String(isOpen));
    });
  }

  document.querySelectorAll("pre").forEach(function (block) {
    var button = document.createElement("button");
    button.type = "button";
    button.className = "copy-code";
    button.textContent = "Copy";
    button.addEventListener("click", function () {
      var code = block.querySelector("code");
      if (!code) return;
      navigator.clipboard.writeText(code.textContent || "").then(function () {
        button.textContent = "Copied";
        window.setTimeout(function () {
          button.textContent = "Copy";
        }, 1400);
      });
    });
    block.appendChild(button);
  });

  if (searchInput && searchResults) {
    fetch(window.OBI_SEARCH_URL || "search.json")
      .then(function (response) {
        return response.ok ? response.json() : [];
      })
      .then(function (records) {
        searchIndex = Array.isArray(records) ? records : [];
      })
      .catch(function () {
        searchIndex = [];
      });

    searchInput.addEventListener("input", function () {
      var query = searchInput.value.trim().toLowerCase();
      if (query.length < 2) {
        searchResults.innerHTML = "";
        return;
      }
      var terms = query.split(/\\s+/).filter(Boolean);
      var results = searchIndex
        .map(function (record) {
          var haystack = [record.title, record.summary, record.text, record.kind]
            .join(" ")
            .toLowerCase();
          var score = terms.reduce(function (total, term) {
            return total + (haystack.includes(term) ? 1 : 0);
          }, 0);
          return Object.assign({ score: score }, record);
        })
        .filter(function (record) {
          return record.score > 0;
        })
        .sort(function (a, b) {
          return b.score - a.score || a.title.localeCompare(b.title);
        })
        .slice(0, 8);

      searchResults.innerHTML = results
        .map(function (record, index) {
          return '<a class="search-result" role="option" id="search-result-' +
            index +
            '" href="' +
            record.href +
            '"><strong>' +
            escapeHtml(record.title) +
            "</strong><span>" +
            escapeHtml(record.summary || record.kind || "") +
            "</span></a>";
        })
        .join("");
    });

    searchInput.addEventListener("keydown", function (event) {
      if (event.key !== "ArrowDown") return;
      var first = searchResults.querySelector("a");
      if (first) {
        event.preventDefault();
        first.focus();
      }
    });
  }

  var tocLinks = Array.prototype.slice.call(document.querySelectorAll(".toc a[href^='#']"));
  var sections = tocLinks
    .map(function (link) {
      var target = document.querySelector(link.getAttribute("href"));
      return target ? { link: link, target: target } : null;
    })
    .filter(Boolean);

  if ("IntersectionObserver" in window && sections.length > 0) {
    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          sections.forEach(function (item) {
            item.link.classList.toggle("active", item.target === entry.target);
          });
        });
      },
      { rootMargin: "-20% 0px -70% 0px", threshold: 0.01 },
    );
    sections.forEach(function (item) {
      observer.observe(item.target);
    });
  }

  function escapeHtml(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }
})();`;
}
