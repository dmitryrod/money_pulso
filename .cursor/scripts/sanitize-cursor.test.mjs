import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "fs";
import path from "path";
import os from "os";
import { fileURLToPath } from "url";
import { buildPlan, applyPlan } from "./sanitize-cursor.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

test("buildPlan: dry targets session json and never lists agents or skills", () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "cursor-san-"));
  fs.mkdirSync(path.join(tmp, ".cursor", "reports"), { recursive: true });
  fs.mkdirSync(path.join(tmp, ".cursor", "agents"), { recursive: true });
  fs.mkdirSync(path.join(tmp, ".cursor", "skills", "x"), { recursive: true });
  fs.writeFileSync(
    path.join(tmp, ".cursor", "reports", "session-2026.json"),
    "{}"
  );
  fs.writeFileSync(path.join(tmp, ".cursor", "agents", "worker.md"), "x");
  const plan = buildPlan(tmp, {
    soft: false,
    all: false,
    stripProjectIdentity: false,
    replaceWithExample: false,
  });
  const rels = new Set(plan.map((r) => r.path.replace(/\\/g, "/")));
  assert.ok(
    Array.from(rels).some(
      (p) => p.includes("session-") && p.endsWith(".json")
    )
  );
  assert.ok(![...rels].some((p) => p.includes(".cursor/agents")));
  assert.ok(![...rels].some((p) => p.includes(".cursor/skills")));
});

test("applyPlan dry-run: files remain", () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "cursor-san-"));
  fs.mkdirSync(path.join(tmp, ".cursor", "reports"), { recursive: true });
  const s = path.join(tmp, ".cursor", "reports", "session-1.json");
  fs.writeFileSync(s, "{}");
  const plan = buildPlan(tmp, {
    soft: true,
    all: false,
    stripProjectIdentity: false,
    replaceWithExample: false,
  });
  applyPlan(tmp, plan, { dryRun: true, replaceWithExample: false });
  assert.ok(fs.existsSync(s));
});

test("applyPlan: removes session file when not dry", () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "cursor-san-"));
  fs.mkdirSync(path.join(tmp, ".cursor", "reports"), { recursive: true });
  const s = path.join(tmp, ".cursor", "reports", "session-2.json");
  fs.writeFileSync(s, "{}");
  const plan = buildPlan(tmp, {
    soft: true,
    all: false,
    stripProjectIdentity: false,
    replaceWithExample: false,
  });
  applyPlan(tmp, plan, { dryRun: false, replaceWithExample: false });
  assert.ok(!fs.existsSync(s));
});
