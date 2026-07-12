import { buildDocumentation } from "./docs-lib.mjs";

const result = await buildDocumentation();

console.log(
  `Built OBI documentation: ${result.generatedDocuments.length} source pages, ${result.bibliographyEntries.length} bibliography entries, ${result.archives.length} archived bundles.`,
);
