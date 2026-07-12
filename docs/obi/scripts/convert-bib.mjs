import path from "node:path";
import {
  PUBLIC_DIR,
  bibliographyPageBody,
  layout,
  readBibEntries,
  writeTextFile,
  extractHeadings,
} from "./docs-lib.mjs";

const entries = await readBibEntries();
const body = bibliographyPageBody(entries);

await writeTextFile(
  path.join(PUBLIC_DIR, "bibliography.html"),
  layout({
    title: "Bibliography",
    description: "BibTeX references for OBI documentation.",
    body,
    toc: extractHeadings(body),
    active: "bibliography",
    publicPath: "bibliography.html",
    pageType: "CollectionPage",
  }),
);

await writeTextFile(path.join(PUBLIC_DIR, "bibliography.json"), `${JSON.stringify(entries, null, 2)}\n`);

console.log(`Generated bibliography from ${entries.length} BibTeX entries.`);
