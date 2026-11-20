const test = require("node:test");
const assert = require("node:assert");
const { RULES, scanText } = require("../out/rules");
const { looksLikeBlockInsertion, insertedLineRange } = require("../out/insertions");

const ids = (code) => scanText(code).map((f) => f.ruleId);

// One risky and one safe snippet per rule.
const CASES = {
  "sql-string-built-query": [
    'conn.execute(f"SELECT * FROM users WHERE name = \'{name}\'")',
    'conn.execute("SELECT * FROM users WHERE name = ?", (name,))',
  ],
  "html-built-from-fstring": [
    'return f"<p>Hello, {name}!</p>"',
    'return f"<p>Hello, {html.escape(name)}!</p>"',
  ],
  "unescaped-template": ['return render_template_string(f"<b>{x}</b>")', "return render_template('a.html')"],
  "path-joined-with-input": ["open(os.path.join(base, name))", "path = os.path.realpath(name)"],
  "shell-command": ["os.system('ping ' + host)", 'subprocess.run(["ping", host])'],
  "secret-with-literal-default": [
    'os.environ.get("APP_SECRET_KEY", "dev-secret")',
    'os.environ.get("APP_SECRET_KEY") or secrets.token_hex(32)',
  ],
  "secret-literal-assigned": ['app.secret_key = "hunter2hunter2"', "app.secret_key = os.environ['K']"],
  "weak-hash": ["hashlib.md5(pw.encode()).hexdigest()", "hashlib.pbkdf2_hmac('sha256', pw, salt, 1)"],
  "ecb-mode": ["Cipher(algorithms.AES(key), modes.ECB())", "Cipher(algorithms.AES(key), modes.GCM(n))"],
  "predictable-random": ["token = random.choices(chars, k=32)", "token = secrets.token_urlsafe(32)"],
  "unsafe-deserialization": ["data = pickle.loads(blob)", "data = json.loads(blob)"],
  "request-to-variable-url": ["requests.get(url, timeout=5)", 'requests.get("https://api.example.test")'],
  "redirect-to-request-value": ["return redirect(request.args.get('next'))", "return redirect('/home')"],
  "upload-saved-under-client-name": [
    "f.save(os.path.join(upload_dir, f.filename))",
    "f.save(os.path.join(upload_dir, secure_filename(f.filename)))",
  ],
};

test("every rule has a case, and every case behaves", () => {
  assert.deepStrictEqual(Object.keys(CASES).sort(), RULES.map((r) => r.id).sort());
  for (const [id, [risky, safe]] of Object.entries(CASES)) {
    assert.ok(ids(risky).includes(id), `${id} should flag: ${risky}`);
    assert.ok(!ids(safe).includes(id), `${id} should not flag: ${safe}`);
  }
});

test("yaml.load is flagged unless a safe loader is named", () => {
  assert.ok(ids("cfg = yaml.load(text, Loader=yaml.Loader)").includes("unsafe-deserialization"));
  assert.ok(!ids("cfg = yaml.load(text, Loader=yaml.SafeLoader)").includes("unsafe-deserialization"));
  assert.ok(!ids("cfg = yaml.safe_load(text)").includes("unsafe-deserialization"));
});

test("findings carry position, cwe and message", () => {
  const [f] = scanText("x = 1\nh = hashlib.md5(b'a')\n");
  assert.strictEqual(f.line, 1);
  assert.strictEqual(f.cwe, 327);
  assert.strictEqual(f.start, 4);
  assert.match(f.message, /CWE-327/);
});

test("commented-out code and clean code are not flagged", () => {
  assert.deepStrictEqual(scanText("# h = hashlib.md5(b'a')\n"), []);
  assert.deepStrictEqual(scanText("def add(a, b):\n    return a + b\n"), []);
  assert.deepStrictEqual(scanText(""), []);
});

test("windows line endings give the same line numbers", () => {
  const [f] = scanText("x = 1\r\npickle.loads(b)\r\n");
  assert.strictEqual(f.line, 1);
});

test("block insertions are told apart from typing", () => {
  assert.ok(!looksLikeBlockInsertion({ text: "a", rangeLength: 0 }));
  assert.ok(!looksLikeBlockInsertion({ text: "def f():\n  pass", rangeLength: 0 }));
  assert.ok(looksLikeBlockInsertion({ text: "def compute_total(price, quantity):\n    subtotal = price * quantity\n    return subtotal * 1.2\n", rangeLength: 0 }));
  assert.ok(looksLikeBlockInsertion({ text: "x".repeat(250), rangeLength: 0 }));
  assert.deepStrictEqual(insertedLineRange(4, "a\nb\nc"), [4, 6]);
});
