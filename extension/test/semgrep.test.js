const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const {
  parseSemgrep,
  relocate,
  runSemgrep,
  scanWithSemgrep,
  semgrepArgs,
  withinLines,
} = require("../out/semgrep");

const CODE = "import os\n\ndef f(host):\n    os.system('ping ' + host)\n";
const RULES = path.join(__dirname, "..", "rules", "codetrust.yml");

// The parts of Semgrep's JSON report that the extension reads (lines and columns start at 1).
const result = (over = {}) => ({
  check_id: "rules.codetrust.shell-command-from-variable",
  start: { line: 4, col: 5 },
  end: { line: 4, col: 30 },
  extra: { severity: "ERROR", message: "Shell command.", metadata: { cwe: ["CWE-78"] } },
  ...over,
});
const report = (results = [], errors = []) => JSON.stringify({ results, errors });

test("a Semgrep result becomes a finding with 0-based position", () => {
  const [f] = parseSemgrep(report([result()]), CODE);
  assert.deepStrictEqual(f, {
    ruleId: "shell-command-from-variable",
    cwe: 78,
    severity: "error",
    message: "Shell command. (CWE-78)",
    line: 3,
    start: 4,
    end: 29,
  });
});

test("a multi-line result is highlighted to the end of its first line", () => {
  const [f] = parseSemgrep(report([result({ end: { line: 5, col: 2 } })]), CODE);
  assert.strictEqual(f.end, "    os.system('ping ' + host)".length);
});

test("output that cannot be trusted is an error, not a clean result", () => {
  assert.throws(() => parseSemgrep("not json", CODE));
  assert.throws(() => parseSemgrep("{}", CODE), /unexpected/);
  assert.throws(() => parseSemgrep(report([], [{ message: "could not parse" }]), CODE), /parse/);
  assert.deepStrictEqual(parseSemgrep(report(), CODE), []);
});

test("Semgrep runs offline on a temporary copy that is removed afterwards", async () => {
  let seen;
  const exec = async (command, args) => {
    const target = args[args.length - 1];
    seen = { command, args, target, code: fs.readFileSync(target, "utf8") };
    return report([result()]);
  };
  const findings = await runSemgrep(CODE, { command: "my-semgrep", rulesFile: RULES, exec });
  assert.strictEqual(findings.length, 1);
  assert.strictEqual(seen.command, "my-semgrep");
  assert.strictEqual(seen.code, CODE);
  assert.deepStrictEqual(seen.args, semgrepArgs(RULES, seen.target));
  assert.strictEqual(seen.args[seen.args.indexOf("--metrics") + 1], "off");
  assert.ok(seen.args.includes("--disable-version-check"));
  assert.strictEqual(seen.args[seen.args.indexOf("--config") + 1], RULES);
  assert.ok(!fs.existsSync(path.dirname(seen.target)));
});

test("the temporary copy is removed when Semgrep fails", async () => {
  let target;
  const exec = async (_command, args) => {
    target = args[args.length - 1];
    throw new Error("timed out");
  };
  await assert.rejects(runSemgrep(CODE, { command: "semgrep", rulesFile: RULES, exec }), /timed/);
  assert.ok(!fs.existsSync(path.dirname(target)));
});

test("a missing Semgrep falls back to the built-in rules and says why", async () => {
  const outcome = await scanWithSemgrep(CODE, {
    command: "codetrust-no-such-program",
    rulesFile: RULES,
  });
  assert.strictEqual(outcome.engine, "builtin");
  assert.match(outcome.fallbackReason, /was not found/);
  assert.deepStrictEqual(outcome.findings.map((f) => f.ruleId), ["shell-command"]);
});

test("a working Semgrep replaces the built-in rules", async () => {
  const outcome = await scanWithSemgrep(CODE, {
    command: "semgrep",
    rulesFile: RULES,
    exec: async () => report(),
  });
  assert.deepStrictEqual(outcome, { findings: [], engine: "semgrep" });
});

test("findings are limited to the requested lines", () => {
  const findings = [{ line: 1 }, { line: 3 }, { line: 6 }];
  assert.deepStrictEqual(withinLines(findings, 2, 5), [{ line: 3 }]);
});

test("findings follow their line when the file is edited during a scan", () => {
  const before = "a\nbad()\nc\nbad()";
  const after = "new\nnew\na\nbad()\nc\nchanged()";
  assert.deepStrictEqual(relocate([{ line: 1 }], before, after), [{ line: 3 }]);
  assert.deepStrictEqual(relocate([{ line: 2 }], before, "a\nb"), []);
  assert.deepStrictEqual(relocate([{ line: 3 }], before, before), [{ line: 3 }]);
});

test("the bundled Semgrep rules match the benchmark's rules", () => {
  const read = (p) => fs.readFileSync(p, "utf8").replace(/\r\n/g, "\n");
  const original = path.join(__dirname, "..", "..", "data", "rules", "codetrust.yml");
  assert.strictEqual(read(RULES), read(original));
});

test("a project's settings cannot choose which program runs", () => {
  const manifest = require("../package.json");
  const properties = manifest.contributes.configuration.properties;
  assert.strictEqual(properties["codetrust.semgrepPath"].scope, "machine");
  assert.strictEqual(properties["codetrust.useLocalSemgrep"].scope, "machine");
  assert.strictEqual(properties["codetrust.useLocalSemgrep"].default, false);
  assert.ok(!fs.readFileSync(path.join(__dirname, "..", ".vscodeignore"), "utf8").includes("rules"));
});
