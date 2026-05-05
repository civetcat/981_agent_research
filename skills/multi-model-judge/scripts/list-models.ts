import { Cursor } from "@cursor/sdk";

const apiKey = process.env.CURSOR_API_KEY;
if (!apiKey) {
  console.error("CURSOR_API_KEY 未設定");
  process.exit(1);
}

const models = await Cursor.models.list({ apiKey });
for (const m of models) {
  const id = (m as { id?: string }).id ?? "(unknown)";
  const name = (m as { displayName?: string; name?: string }).displayName
    ?? (m as { name?: string }).name
    ?? "";
  console.log(`${id}\t${name}`);
}
