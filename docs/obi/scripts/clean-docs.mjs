import { cleanPublicDocs, ensureDocumentationLayout } from "./docs-lib.mjs";

await ensureDocumentationLayout();
await cleanPublicDocs();

console.log("Cleaned docs/public.");
