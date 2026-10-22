import { readFile, mkdir, writeFile } from "node:fs/promises";
import { parse } from "yaml";

const catalog = parse(await readFile(new URL("../../data/checklist/aml_bd_v1.yaml", import.meta.url), "utf8"));
const expected = Array.from({ length: 34 }, (_, index) => `AML-BD-${String(index + 1).padStart(3, "0")}`);
if (JSON.stringify(catalog.requests.map((request) => request.id)) !== JSON.stringify(expected)) {
  throw new Error("Canonical checklist must contain all 34 unique IDs in order");
}
await mkdir(new URL("../.generated/", import.meta.url), { recursive: true });
await writeFile(new URL("../.generated/catalog.json", import.meta.url), JSON.stringify(catalog));
console.log("Generated frontend request data from the canonical 34-request YAML");
