// Precision and recall of the extension's rules against the benchmark's labels.
//
//   cd extension && npm run compile && node scripts/evaluate.js
//
// Labels: each task's vulnerable.py is a positive, its reference.py a negative. If
// results/scores.csv exists, scored generations are evaluated too (label = scored as vulnerable,
// only for functionally correct code, so the label is trustworthy). Numbers are reported
// separately for the 20 dev tasks (used to write the rules) and the 30 test tasks (held out).
const fs = require("fs");
const path = require("path");
const { scanText } = require("../out/rules");

const root = path.resolve(__dirname, "..", "..");
const splits = JSON.parse(fs.readFileSync(path.join(root, "data", "splits.json"), "utf8"));

function counts() {
  return { tp: 0, fp: 0, fn: 0, tn: 0 };
}

function add(c, label, flagged) {
  if (label && flagged) c.tp++;
  else if (label) c.fn++;
  else if (flagged) c.fp++;
  else c.tn++;
}

function rates(c) {
  const precision = c.tp + c.fp ? c.tp / (c.tp + c.fp) : null;
  const recall = c.tp + c.fn ? c.tp / (c.tp + c.fn) : null;
  return { ...c, precision, recall };
}

const solutions = { dev: counts(), test: counts() };
// Simple baseline: flag any file that merely mentions a risky module or function. A rule set is
// only worth shipping if it clearly beats this.
const KEYWORDS =
  /\b(os|subprocess|pickle|marshal|yaml|requests|urllib|hashlib|random|redirect|execute|open|zipfile)\b/;
const keyword = { dev: counts(), test: counts() };
const misses = [];
const falseAlarms = [];
const ruleHits = {};
for (const id of Object.keys(splits).sort()) {
  const dir = path.join(root, "data", "tasks", id);
  for (const kind of ["vulnerable", "reference"]) {
    const found = scanText(fs.readFileSync(path.join(dir, `${kind}.py`), "utf8"));
    found.forEach((f) => (ruleHits[f.ruleId] = (ruleHits[f.ruleId] || 0) + 1));
    add(solutions[splits[id]], kind === "vulnerable", found.length > 0);
    const source = fs.readFileSync(path.join(dir, `${kind}.py`), "utf8");
    add(keyword[splits[id]], kind === "vulnerable", KEYWORDS.test(source));
    if (splits[id] === "test" && kind === "vulnerable" && !found.length) misses.push(id);
    if (splits[id] === "test" && kind === "reference" && found.length)
      falseAlarms.push(`${id}: ${[...new Set(found.map((f) => f.ruleId))].join(", ")}`);
  }
}

function parseCsv(file) {
  const [head, ...rows] = fs.readFileSync(file, "utf8").trim().split(/\r?\n/);
  const cols = head.split(",");
  return rows.map((r) => Object.fromEntries(r.split(",").map((v, i) => [cols[i], v])));
}

const generations = {};
const scoresFile = path.join(root, "results", "scores.csv");
if (fs.existsSync(scoresFile)) {
  for (const row of parseCsv(scoresFile)) {
    if (row.functional_pass !== "True") continue;
    if (row.repeat !== "0" || row.model_tag.endsWith("+reminder")) continue; // main grid only
    const [, task, index, repeat] = row.id.split(/:/);
    const file = path.join(root, "data", "generated", row.model_tag, `${task}__${index}__${repeat}.json`);
    if (!fs.existsSync(file)) continue;
    const code = JSON.parse(fs.readFileSync(file, "utf8")).code || "";
    const bucket = (generations[row.model_tag] ||= { dev: counts(), test: counts() });
    add(bucket[splits[task]], row.vulnerable === "True", scanText(code).length > 0);
  }
}

const report = {
  solutions: { dev: rates(solutions.dev), test: rates(solutions.test) },
  generations: Object.fromEntries(
    Object.entries(generations).map(([m, b]) => [m, { dev: rates(b.dev), test: rates(b.test) }])
  ),
  keyword_baseline: { dev: rates(keyword.dev), test: rates(keyword.test) },
  test_misses: misses,
  test_false_alarms: falseAlarms,
  rule_hits: ruleHits,
};

const pct = (x) => (x === null ? "n/a" : `${(100 * x).toFixed(0)}%`);
const row = (name, r) =>
  `| ${name} | ${r.tp} | ${r.fp} | ${r.fn} | ${r.tn} | ${pct(r.precision)} | ${pct(r.recall)} |`;
const lines = [
  "# Extension evaluation",
  "",
  "Rules were written from the 20 dev tasks; the 30 test tasks are held out. A file counts as",
  "flagged when at least one rule fires. Positives are vulnerable solutions.",
  "",
  "| Set | TP | FP | FN | TN | Precision | Recall |",
  "|---|---|---|---|---|---|---|",
  row("Task solutions, dev", report.solutions.dev),
  row("Task solutions, test", report.solutions.test),
  row("Keyword baseline, dev", report.keyword_baseline.dev),
  row("Keyword baseline, test", report.keyword_baseline.test),
  ...Object.entries(report.generations).flatMap(([m, b]) => [
    row(`${m} generations, dev`, b.dev),
    row(`${m} generations, test`, b.test),
  ]),
  "",
  "## Missed on the test tasks",
  "",
  ...(misses.length ? misses.map((m) => `- \`${m}\``) : ["None."]),
  "",
  "## False alarms on the test tasks",
  "",
  ...(falseAlarms.length ? falseAlarms.map((m) => `- ${m}`) : ["None."]),
  "",
  "Caveats: one person wrote both the tasks and the rules, so the dev/test split limits but does",
  "not remove tuning to the benchmark. Joining multi-line statements and broadening the HTML rule",
  "were done after seeing misses on the test tasks, so the test numbers are optimistic. Pattern",
  "matching sees one statement at a time and cannot follow data flow or detect missing checks",
  "(access control), so those families are expected misses.",
  "Generations from `scripted*` models are copies of the task solutions, not real model output.",
  "",
];
fs.mkdirSync(path.join(root, "results"), { recursive: true });
fs.writeFileSync(path.join(root, "results", "extension_eval.json"), JSON.stringify(report, null, 1) + "\n");
fs.writeFileSync(path.join(root, "results", "extension_eval.md"), lines.join("\n"));
console.log(lines.join("\n"));
