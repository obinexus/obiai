import { writeSearchIndex } from "./docs-lib.mjs";

const records = await writeSearchIndex();

console.log(`Indexed ${records.length} public HTML pages into docs/public/search.json.`);
