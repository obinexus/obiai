import path from "node:path";
import { pathToFileURL } from "node:url";
import {
  ROOT,
  SOURCE_DIR,
  texToHtml,
  readBibEntries,
  readTextFile,
  layout,
  rootPrefixFor,
  slugify,
  titleFromPath,
  writeTextFile,
  PUBLIC_DIR,
} from "./docs-lib.mjs";

const files = process.argv.slice(2);

if (files.length === 0) {
  console.log("Usage: node scripts/convert-tex.mjs docs/source/tex/paper.tex");
  process.exit(0);
}

const bibliography = await readBibEntries();
const bibliographyMap = new Map(bibliography.map((entry) => [entry.key, entry]));

for (const input of files) {
  const file = path.resolve(ROOT, input);
  const raw = await readTextFile(file);
  const slug = slugify(path.basename(file, path.extname(file)));
  const publicPath = `sources/${slug}.html`;
  const converted = texToHtml(raw, bibliographyMap, rootPrefixFor(publicPath));
  const title = converted.metadata.title || titleFromPath(file);
  await writeTextFile(
    path.join(PUBLIC_DIR, publicPath),
    layout({
      title,
      description: `Converted LaTeX source from ${path.relative(SOURCE_DIR, file)}`,
      body: converted.html,
      toc: converted.toc,
      active: "papers",
      publicPath,
      pageType: "ScholarlyArticle",
    }),
  );
  console.log(`Converted ${pathToFileURL(file).href} -> ${publicPath}`);
}
