import { validateDocumentation } from "./docs-lib.mjs";

const result = await validateDocumentation();

if (!result.ok) {
  if (result.missing.length) {
    console.error("Missing required files:");
    for (const file of result.missing) console.error(`- ${file}`);
  }
  if (result.invalidJson.length) {
    console.error("Invalid JSON:");
    for (const file of result.invalidJson) console.error(`- ${file}`);
  }
  if (result.missingSemantics.length) {
    console.error("HTML semantic checks failed:");
    for (const message of result.missingSemantics) console.error(`- ${message}`);
  }
  process.exit(1);
}

console.log("OBI documentation validation passed.");
