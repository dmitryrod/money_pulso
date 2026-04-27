#!/usr/bin/env node
/**
 * Удаляет локальные/сессионные артефакты под `.cursor/`, не трогая версионируемую сборку.
 * Запуск из корня workspace: `node .cursor/scripts/sanitize-cursor.mjs [опции]`
 *
 * Env: `SANITIZE_CURSOR_ROOT` — альтернативный корень (для тестов).
 */
import fs from "fs";
import path from "path";
import { fileURLToPath, pathToFileURL } from "url";
import readline from "readline";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/** @typedef {{ path: string, action: 'delete' | 'keep' | 'strip_marketing', reason: string }} Row */

const PROTECTED_PREFIXES = [
  ".cursor/agents",
  ".cursor/skills",
  ".cursor/rules",
  ".cursor/commands",
  ".cursor/docs",
  ".cursor/templates",
  ".cursor/memory/tests",
  ".cursor/plans",
];

const PROTECTED_FILES = [".cursor/config.json"];

const PROTECTED_REGEX = [/^\.cursor\/hooks(\.|\/|$)/, /^\.cursor\/memory\/[^/]+\.py$/, /^\.cursor\/scripts\/.*\.test\.mjs$/];

function normPosix(p) {
  return p.split(path.sep).join("/");
}

function resolveUnder(root, rel) {
  const full = path.resolve(root, rel);
  const r = normPosix(path.relative(root, full));
  if (r.startsWith("..")) return null;
  return full;
}

/**
 * @param {string} relPosix
 */
function isProtectedRel(relPosix) {
  const p = relPosix.replace(/\\/g, "/");
  if (PROTECTED_FILES.includes(p)) return true;
  for (const pre of PROTECTED_PREFIXES) {
    if (p === pre || p.startsWith(pre + "/")) return true;
  }
  for (const re of PROTECTED_REGEX) {
    if (re.test(p)) return true;
  }
  if (p.endsWith(".example.md")) return true;
  return false;
}

/**
 * @param {string} root
 * @param {string} rel
 * @param {'delete'|'keep'|'strip_marketing'} action
 * @param {string} reason
 * @param {Row[]} out
 */
function pushRow(root, rel, action, reason, out) {
  const relP = normPosix(rel);
  if (isProtectedRel(relP)) {
    if (action !== "keep") {
      out.push({ path: relP, action: "keep", reason: "protected path" });
    }
    return;
  }
  const full = resolveUnder(root, relP);
  if (action === "delete" && full && !fs.existsSync(full)) {
    return;
  }
  if (action === "strip_marketing" && relP === ".cursor/marketing-context.md") {
    if (full && fs.existsSync(full)) {
      out.push({ path: relP, action: "strip_marketing", reason });
    }
    return;
  }
  if (action === "delete") {
    out.push({ path: relP, action: "delete", reason });
  }
}

/**
 * @param {string} root
 * @param {{ soft: boolean, all: boolean, stripProjectIdentity: boolean, replaceWithExample: boolean }} opts
 * @returns {Row[]}
 */
export function buildPlan(root, opts) {
  const soft = opts.soft === true;
  const all = opts.all === true;
  const out = [];

  const reports = path.join(root, ".cursor", "reports");
  if (fs.existsSync(reports)) {
    for (const f of fs.readdirSync(reports)) {
      if (f.startsWith("session-") && f.endsWith(".json")) {
        pushRow(
          root,
          path.join(".cursor", "reports", f),
          "delete",
          "session report",
          out
        );
      }
      if (f === "METRICS_SUMMARY.md") {
        pushRow(
          root,
          path.join(".cursor", "reports", f),
          "delete",
          "metrics summary",
          out
        );
      }
      if (all && !soft && f !== "METRICS_SUMMARY.md" && !(f.startsWith("session-") && f.endsWith(".json"))) {
        const rel = path.join(".cursor", "reports", f);
        if (!isProtectedRel(normPosix(rel))) {
          pushRow(root, rel, "delete", "extra file in reports (--all)", out);
        }
      }
    }
  }

  pushRow(root, ".cursor/active_memory.md", "delete", "RAG active_memory", out);

  pushRow(root, ".cursor/memory/chroma_db", "delete", "Chroma index (dir)", out);
  pushRow(root, ".cursor/memory/rag_fts.sqlite", "delete", "SQLite FTS index", out);
  pushRow(root, ".cursor/memory/.ingest_state.json", "delete", "ingest state", out);

  const mem = path.join(root, ".cursor", "memory");
  if (fs.existsSync(mem)) {
    for (const f of fs.readdirSync(mem)) {
      if (f.endsWith(".tmp")) {
        pushRow(root, path.join(".cursor", "memory", f), "delete", "temp", out);
      }
    }
  }

  const cur = path.join(root, ".cursor");
  if (fs.existsSync(cur)) {
    for (const f of fs.readdirSync(cur)) {
      if (/^mcp.*\.local\.json$/i.test(f)) {
        pushRow(root, path.join(".cursor", f), "delete", "local MCP config", out);
      }
    }
  }

  const gh = [
    "gh-issue-title.txt",
    "gh-issue-body.txt",
    "gh-pr-title.txt",
    "gh-pr-body.txt",
  ];
  for (const name of gh) {
    pushRow(root, path.join(".cursor", name), "delete", "temp gh (under .cursor)", out);
    pushRow(root, name, "delete", "temp gh (repo root)", out);
  }

  const dist = path.join(root, ".cursor", "presentations", "dist");
  if (fs.existsSync(dist)) {
    for (const f of fs.readdirSync(dist)) {
      if (f === ".gitkeep") continue;
      pushRow(
        root,
        path.join(".cursor", "presentations", "dist", f),
        "delete",
        "generated Marp output (keeps .gitkeep)",
        out
      );
    }
  }

  pushRow(root, ".cursor/.cache", "delete", "editor cache (dir)", out);

  const pyc = path.join(root, ".cursor", "scripts", "__pycache__");
  if (fs.existsSync(pyc)) {
    pushRow(
      root,
      path.join(".cursor", "scripts", "__pycache__"),
      "delete",
      "python cache under scripts",
      out
    );
  }

  if (all && !soft) {
    const walk = (absDir, relPos) => {
      if (!fs.existsSync(absDir)) return;
      for (const name of fs.readdirSync(absDir)) {
        const abs = path.join(absDir, name);
        const rel = path.join(relPos, name);
        const n = normPosix(rel);
        if (isProtectedRel(n)) continue;
        const st = fs.lstatSync(abs);
        if (st.isDirectory() && name === "__pycache__") {
          pushRow(root, rel, "delete", "python cache (--all)", out);
        } else if (st.isDirectory()) {
          walk(abs, rel);
        }
      }
    };
    walk(path.join(root, ".cursor"), ".cursor");
  }

  if (opts.stripProjectIdentity) {
    const m = ".cursor/marketing-context.md";
    const mfull = path.join(root, m);
    if (fs.existsSync(mfull)) {
      if (opts.replaceWithExample) {
        const ex = path.join(root, ".cursor", "marketing-context.example.md");
        if (fs.existsSync(ex)) {
          out.push({
            path: m,
            action: "strip_marketing",
            reason:
              "backup then replace with marketing-context.example.md (--replace-with-example)",
          });
        } else {
          out.push({
            path: m,
            action: "keep",
            reason: "no .cursor/marketing-context.example.md to copy from",
          });
        }
      } else {
        out.push({
          path: m,
          action: "strip_marketing",
          reason: "backup then remove (--strip-project-identity)",
        });
      }
    }
  }

  if (!soft) return dedupeRows(out);

  const allowSub = (p) => {
    const s = p.replace(/\\/g, "/");
    if (s.match(/^\.cursor\/reports\/session-.*\.json$/)) return true;
    if (s === ".cursor/reports/METRICS_SUMMARY.md") return true;
    if (s === ".cursor/active_memory.md") return true;
    if (s === ".cursor/memory/chroma_db" || s.startsWith(".cursor/memory/chroma_db/"))
      return true;
    if (s === ".cursor/memory/rag_fts.sqlite") return true;
    if (s === ".cursor/memory/.ingest_state.json") return true;
    if (s.match(/\.tmp$/)) return true;
    if (s.match(/^\.cursor\/mcp.*\.local\.json$/)) return true;
    if (gh.some((g) => s === g || s === ".cursor/" + g)) return true;
    if (s.startsWith(".cursor/presentations/dist/") && !s.endsWith("/.gitkeep")) return true;
    if (s === ".cursor/.cache" || s.startsWith(".cursor/.cache/")) return true;
    if (s.includes("__pycache__")) return true;
    if (s === ".cursor/marketing-context.md" && opts.stripProjectIdentity) return true;
    return false;
  };

  return dedupeRows(out.filter((r) => r.action === "keep" || allowSub(r.path)));
}

function dedupeRows(rows) {
  const seen = new Set();
  const out = [];
  for (const r of rows) {
    const k = r.path + "\0" + r.action;
    if (seen.has(k)) continue;
    seen.add(k);
    out.push(r);
  }
  return out;
}

function printTable(rows) {
  const w = (s, n) => String(s) + " ".repeat(Math.max(0, n - String(s).length));
  console.log(`${w("path", 58)} | ${w("action", 18)} | reason`);
  console.log("-".repeat(120));
  for (const r of rows) {
    console.log(`${w(r.path, 58)} | ${w(r.action, 18)} | ${r.reason}`);
  }
}

export function rmRecursive(p) {
  if (!fs.existsSync(p)) return;
  const st = fs.lstatSync(p);
  if (st.isDirectory()) {
    for (const name of fs.readdirSync(p)) {
      rmRecursive(path.join(p, name));
    }
    fs.rmdirSync(p);
  } else {
    fs.unlinkSync(p);
  }
}

/**
 * @param {string} root
 * @param {Row[]} plan
 * @param {{ dryRun: boolean, replaceWithExample: boolean }} opts
 */
export function applyPlan(root, plan, opts) {
  if (opts.dryRun) return;
  for (const row of plan) {
    if (row.action === "keep") continue;
    const full = resolveUnder(root, row.path);
    if (!full) continue;
    if (isProtectedRel(normPosix(row.path))) continue;

    if (row.action === "delete") {
      if (!fs.existsSync(full)) continue;
      const st = fs.lstatSync(full);
      if (st.isDirectory()) {
        rmRecursive(full);
      } else {
        fs.unlinkSync(full);
      }
    } else if (row.action === "strip_marketing") {
      if (row.path !== ".cursor/marketing-context.md") continue;
      if (!fs.existsSync(full)) continue;
      const backup =
        full + ".sanitize.bak." + new Date().toISOString().replace(/[:.]/g, "-");
      fs.copyFileSync(full, backup);
      if (opts.replaceWithExample) {
        const ex = path.join(root, ".cursor", "marketing-context.example.md");
        if (fs.existsSync(ex)) {
          fs.copyFileSync(ex, full);
        }
      } else {
        fs.unlinkSync(full);
      }
    }
  }
}

function parseArgs(argv) {
  const o = {
    dryRun: false,
    force: false,
    soft: false,
    all: false,
    stripProjectIdentity: false,
    replaceWithExample: false,
  };
  for (const a of argv) {
    if (a === "--dry-run") o.dryRun = true;
    else if (a === "--force") o.force = true;
    else if (a === "--soft") o.soft = true;
    else if (a === "--all") o.all = true;
    else if (a === "--strip-project-identity") o.stripProjectIdentity = true;
    else if (a === "--replace-with-example") o.replaceWithExample = true;
  }
  if (o.replaceWithExample && !o.stripProjectIdentity) {
    throw new Error("--replace-with-example requires --strip-project-identity");
  }
  if (o.soft && o.all) {
    throw new Error("Use only one of --soft or --all");
  }
  return o;
}

function confirmLine(question) {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });
  return new Promise((resolve) => {
    rl.question(question, (ans) => {
      rl.close();
      resolve(String(ans).trim().toLowerCase() === "yes");
    });
  });
}

export async function runCli(argv, env, stdinIsTTY) {
  const options = parseArgs(argv);
  const root = env.SANITIZE_CURSOR_ROOT
    ? path.resolve(env.SANITIZE_CURSOR_ROOT)
    : process.cwd();

  if (!fs.existsSync(path.join(root, ".cursor"))) {
    throw new Error("Root must contain .cursor/ (set SANITIZE_CURSOR_ROOT for tests).");
  }

  if (options.stripProjectIdentity && !options.dryRun) {
    if (!options.force && !stdinIsTTY) {
      throw new Error(
        "Refusing: --strip-project-identity in non-interactive mode requires --force (or use --dry-run)."
      );
    }
    if (!options.force && stdinIsTTY) {
      const ok = await confirmLine(
        "This may remove or replace .cursor/marketing-context.md. Type exactly yes: "
      );
      if (!ok) {
        return { exitCode: 0, message: "Aborted." };
      }
    }
  }

  const plan = buildPlan(root, {
    soft: options.soft,
    all: options.all,
    stripProjectIdentity: options.stripProjectIdentity,
    replaceWithExample: options.replaceWithExample,
  });

  if (options.dryRun) {
    printTable(plan);
    return { exitCode: 0, plan };
  }

  const willTouch = plan.some(
    (r) => r.action === "delete" || r.action === "strip_marketing"
  );
  if (willTouch && !options.force && !stdinIsTTY) {
    throw new Error("Destructive run in CI requires --force (or use --dry-run).");
  }

  if (willTouch && !options.force && stdinIsTTY) {
    const ok = await confirmLine("Apply changes? Type exactly yes: ");
    if (!ok) {
      return { exitCode: 0, message: "Aborted." };
    }
  }

  applyPlan(root, plan, {
    dryRun: false,
    replaceWithExample: options.replaceWithExample,
  });
  return { exitCode: 0, plan, message: "Done." };
}

const isMain =
  process.argv[1] &&
  import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href;

if (isMain) {
  runCli(process.argv.slice(2), process.env, process.stdin.isTTY)
    .then((r) => {
      if (r.message) console.log(r.message);
      process.exit(r.exitCode ?? 0);
    })
    .catch((e) => {
      console.error(e.message || e);
      process.exit(1);
    });
}
