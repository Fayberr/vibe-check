# vibe-check

**Catch AI-vibecoded slop before it ships.** A single-file, zero-dependency Python linter that detects 50 patterns of AI-generated code smell in web projects , from missing favicons to hardcoded API keys.

```bash
vibe-check ./my-project
# 43 file(s) scanned. 7 error(s), 4 warning(s) found.
```

## Why?

AI code assistants are incredible accelerators, but they reproduce common patterns from their training data at scale: placeholder copy, insecure defaults, skipped accessibility, and cargo-culted anti-patterns. vibe-check catches these automatically so you don't have to.

## Quick Start

```bash
# pip install (recommended)
pip install vibe-linter

# Or download the single file (no pip needed)
curl -O https://raw.githubusercontent.com/Fayberr/vibe-check/main/vibe-check
chmod +x vibe-check

# Or clone
git clone https://github.com/Fayberr/vibe-check.git
cd vibe-check

# Run on a project
./vibe-check /path/to/project

# Production mode (stricter checks)
./vibe-check /path/to/project --prod

# Auto-fix what's fixable
./vibe-check /path/to/project --fix

# Audit prevention layers (AI co-author blocking, git hooks)
./vibe-check --setup

# Machine-readable for AI agents and CI
./vibe-check /path/to/project --json --quiet

# Only scan files changed since last git commit
./vibe-check /path/to/project --changed
```

**Requirements:** Python 3.9+. Nothing else.

## What It Checks (50 Rules)

Each bullet below is a distinct `rule` id you'll see in `--json` output (shown in backticks). Rules
marked **(prod)** only fire with `--prod`. Run `vibe-check --setup --json` to see rule severities,
or list them all with `grep -oE "Finding\('[a-z-]+'" vibe-check`.

### Domain & Branding
- `vercel-urls` , hardcoded `vercel.app` URL in source
- `ai-watermarks` , leftover AI builder watermarks ("Made with Lovable", "Created with v0", "built with bolt.new")
- `missing-favicon` , no `<link rel="icon">` tag
- `default-favicon` , default Vite/React placeholder favicon left in place

### Copywriting & Placeholder Content
- `em-dashes` , em-dash (U+2014) characters in copy (auto-fixable)
- `double-dash` , `--` used as a prose dash, e.g. "great , this works" (auto-fixable)
- `placeholder-copy` , unedited placeholder text ("John Doe", "Jane Smith", "Trusted by 10,000+ creators", "Lorem ipsum")

### Design & UI Hygiene
- `script-fonts` , cursive/script Google Font imports (Dancing Script, Pacifico, Great Vibes, Satisfy, Caveat)
- `emoji-in-ui` , emoji characters in rendered page content, use SVG icons instead
- `unstyled-selects` , `<select>` elements in JSX/TSX with no `className`
- `inline-styles` , inline `style={{...}}` objects (use Tailwind/CSS modules)
- `missing-input-autocomplete` , `<input type="password">` missing an `autocomplete` attribute

### SEO & Accessibility
- `missing-meta-desc` , missing `<meta name="description">` tag
- `default-title` , default framework tab title ("Vite + React")
- `long-title` , page title over 24 characters (browser tabs truncate)
- `missing-og-image` , missing `og:image` social preview tag
- `missing-h1` , no `<h1>` element on the page
- `multiple-h1` , more than one `<h1>` element on the page
- `img-no-alt-html` , `<img>` in `.html` missing alt text
- `img-no-alt` , `<img>` in JSX/TSX missing alt text
- `missing-lang` , missing `lang` attribute on `<html>`
- `missing-canonical` **(prod)** , missing `<link rel="canonical">`
- `missing-sitemap` **(prod)** , no `sitemap.xml` found
- `missing-llms-txt` **(prod)** , no `llms.txt` found
- `missing-privacy-policy` **(prod)** , no Privacy Policy file/route found
- `missing-terms` **(prod)** , no Terms & Conditions file/route found
- `broken-buttons` , interactive elements with a dead `href="#"` target

### Technical & Code Quality
- `console-log` , `console.log()` calls left in `.tsx` files
- `exposed-source-maps` , `.map` files shipped in `dist`/`public`
- `dangerously-set-html` , `dangerouslySetInnerHTML` in JSX/TSX
- `target-blank-noopener` , `target="_blank"` without `rel="noopener noreferrer"`
- `as-type-casts` , `as` type casts in TypeScript (prefer type narrowing)
- `tech-debt-markers` , TODO/FIXME/HACK comments

### Security
- `xss-sinks` , `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write`, `eval()`, `v-html`, `javascript:` URLs
- `file-upload-gaps` , `<input type="file">` without `accept`, multer without `fileFilter`, `express.static` over upload dirs
- `unsigned-webhooks` , a file handles a webhook route but has no HMAC signature verification
- `unsigned-webhooks-project` , same check, project-wide (webhook handler and verification live in different files)
- `hardcoded-secrets` , API keys, DB credentials, private keys, access tokens, DB connection strings with embedded credentials
- `broken-jwt` , `verify=False`, `algorithms=["none"]`, `ignoreExpiration:true`, `jwt.decode()` without algorithm pinning
- `debug-mode` , `DEBUG=True`, `NODE_ENV=development`, Flask/Django/FastAPI debug flags left on
- `unsafe-deserialization` , `pickle.loads()`, `yaml.load()` without `SafeLoader`, `torch.load()` without `weights_only`, `vm.runInNewContext()`
- `math-random-security` , `Math.random()` used near token/auth/reset/session/csrf/nonce/otp context
- `missing-security-headers` , Express without helmet, Flask without Talisman, FastAPI without Secure
- `ssrf-user-urls` , unfiltered user input flowing into `fetch()`/`axios`/`requests`/`httpx`/`urllib`
- `no-rate-limiting` , no rate-limiting middleware on an Express/Flask/FastAPI server
- `rls-permissive-policy` , Supabase/Postgres `USING (true)` or `WITH CHECK (true)` unconditional RLS policy
- `rls-disabled` , `DISABLE ROW LEVEL SECURITY` in a SQL migration
- `supabase-service-role-key-exposed` , a decoded JWT with `role: "service_role"` hardcoded in source

### Git & AI-Attribution Hygiene
- `ai-co-author-trailers` , `Co-Authored-By: Claude/GPT/Gemini/Copilot/Codex` trailers in git commit history
- `claude-attribution` , `~/.claude/settings.json` leaves AI co-author trailers enabled (`--fix` corrects this at the source)

## Output

```
🔍 Running Vibe-Check on: /home/user/my-project

📄 src/components/Hero.jsx
  ✖ [ERROR] Found 1 target="_blank" link(s) without rel="noopener noreferrer" (lines 18).
  ⚠ [WARN]  Found 1 inline style={{...}} object(s) (lines 52).

📄 src/utils/api.ts
  ✖ [ERROR] Found 1 hardcoded secret(s): L12:API key assignment.
  ⚠ [WARN]  Found 2 tech-debt marker(s): L5:TODO, L33:FIXME.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Scanned 43 file(s).
FAILED: 3 error(s), 3 warning(s) found.
```

- **ERROR** , blocks CI, must fix
- **WARN** , advisory, should fix

## Exit Codes

| Exit | Meaning |
|------|---------|
| 0 | Clean (or warnings only) |
| 1 | Errors found |

## Flags

| Flag | Description |
|------|-------------|
| `--prod` | Stricter checks: legal pages, sitemaps, canonical tags |
| `--fix` | Auto-fix fixable errors (em-dashes) |
| `--changed` | Only scan files changed since last git commit |
| `--no-cache` | Disable file-hash caching (always re-scan) |
| `--setup` | Audit prevention layers (Claude attribution, git hooks). Add `--json` for AI agent consumption |
| `--install-hooks` | Install git commit-msg hook to block AI co-author trailers |
| `--install-hooks --global` | Install the commit-msg hook globally (all repos) |
| `--install-hooks --server` | Install pre-receive hook on all bare repos under `<path>` (server-side, cannot be bypassed) |
| `--json` | Output findings as machine-readable JSON (for AI agent consumption) |
| `--quiet` | Suppress human-readable output (use with `--json` for clean machine output) |

### Defense Layers Against AI Co-Author Trailers

vibe-check provides layered defense. Each layer catches what the previous one might miss:

| Layer | Scope | Bypassable? | Install |
|-------|-------|-------------|---------|
| 1. Settings fix | Per-machine (root cause) | No | `vibe-check --fix` |
| 2. Commit-msg hook | Client-side | `--no-verify` | `vibe-check --install-hooks` |
| 3. Pre-receive hook | Server-side (all pushes) | No | `vibe-check --install-hooks --server ~/` |
| 4. Stop-hook scan | Session-end (Claude Code) | Machine scope | Automatic |
| 5. `ai-co-author-trailers` detection | Retroactive scan | Detection only | Built-in |

Recommended setup for self-hosted git servers:
```bash
vibe-check --setup              # audit: see what needs fixing
vibe-check --fix                # root cause: fix Claude Code settings
vibe-check --install-hooks --global  # client-side: block commits
vibe-check --install-hooks --server ~/    # server-side: block pushes
```

### For AI Agents

If you are an AI agent, start with [`llms.txt`](llms.txt) for a structured guide to installing, configuring, and running vibe-check. It covers the recommended workflow, JSON output schema, decision logic, and all flags in a dense, AI-actionable format.

### Machine-Readable Output (`--json`)

When `--json` is passed, vibe-check outputs a structured JSON object instead of human-readable text. This is designed for AI agent consumption and CI pipelines:

```bash
vibe-check . --json --quiet
```

```json
{
  "status": "failed",
  "scanned": 43,
  "errors": 3,
  "warnings": 5,
  "findings": [
    {
      "rule": "target-blank-noopener",
      "severity": "error",
      "message": "Found 1 target=\"_blank\" link(s) without rel=\"noopener noreferrer\" (lines 18).",
      "line": 18,
      "file": "src/components/Hero.jsx"
    }
  ]
}
```

- `status`: `"ok"`, `"warn"` (warnings only), or `"failed"` (errors present)
- `findings`: array of finding objects, each with `rule`, `severity`, `message`, optional `line`, `file`, and `fixable`
- Exit code: 0 for ok/warn, 1 for failed

### Git Hook: Blocking AI Co-Author Trailers

**Start with `vibe-check --setup`** ,  it audits your machine and tells you exactly which prevention layers are missing and how to install them.

**Root cause fix:** Run `vibe-check --fix` once. It sets `attribution.commit` and `attribution.pr` to `""` in `~/.claude/settings.json`, which tells Claude Code to never append `Co-Authored-By` trailers. This fixes the problem at the source.

The git hook below is the safety net, it blocks trailers that slip past the settings fix (e.g., from other AI tools or misconfigured machines).

The `ai-co-author-trailers` rule detects AI co-author trailers in past commits, but detection after the fact is not enough: GitHub caches contributors aggressively, making retroactive cleanup painful. The `--install-hooks` flag installs a git `commit-msg` hook that **blocks commits before they happen**:

```bash
# Per-repo (recommended)
vibe-check --install-hooks

# Or globally (all repos on the machine)
vibe-check --install-hooks --global
```

Once installed, any `git commit` with a `Co-Authored-By:` trailer referencing an AI tool (Claude, GPT, Gemini, Copilot, Codex) will be rejected. Emergency bypass: `git commit --no-verify`.

## CI Integration

### GitHub Actions

```yaml
- name: Run vibe-check
  run: |
    pip install vibe-linter
    vibe-check . --prod
```

### pre-commit

```yaml
repos:
  - repo: https://github.com/Fayberr/vibe-check
    rev: main
    hooks:
      - id: vibe-check
```

## Design

vibe-check is intentionally a **single file with zero dependencies**. This means:

- Single `pip install` (or zero-dependency single file), no venv setup
- Works on any machine with Python 3.9+
- Runs in environments where package installs are blocked (CI, corporate)
- Can be vendored directly into any project

The tool uses only Python's standard library: `re`, `json`, `hashlib`, `argparse`, `pathlib`, `html.parser`, `subprocess`.

### False-Positive Suppression

Security checks are designed to minimize noise:
- Comment lines are skipped (`//`, `#`, `<!--`)
- Test/mock/fixture files are excluded
- Environment variable references (`process.env`, `os.environ`) prevent secret-flagging
- Placeholder values (`changeme`, `your-api-key`, `TODO`) are recognized
- Per-project deduplication prevents repeat-warnings from multi-file frameworks

### Configuration (`.vibecheckrc`)

Drop a `.vibecheckrc` (or `.vibe-check.json`) in your project root to override rule severities.
Both a flat form and a nested `rules` form are accepted:

```json
{
  "em-dashes": "off",
  "console-log": "warn"
}
```

```json
{
  "rules": {
    "em-dashes": "off",
    "console-log": "warn"
  }
}
```

Each value is one of `"error"`, `"warn"`, or `"off"`. Use the exact rule `id` from the
[What It Checks](#what-it-checks-50-rules) list above (e.g. `em-dashes`, not `em-dash`).

### Caching

Findings are cached per file, keyed on the file's hash. An unchanged file has its findings replayed from cache instead of being re-read, so repeat scans are fast **without changing the verdict**: a cached run and a `--no-cache` run always report the same errors and warnings. Use `--no-cache` to force a full re-read.

The cache lives outside your project, at `$XDG_CACHE_HOME/vibe-check/` (or `~/.cache/vibe-check/`), so there is nothing to add to `.gitignore`. Override with `VIBE_CHECK_CACHE_DIR`.

The cache key includes a hash of vibe-check itself and of your resolved config, so upgrading the tool or editing `.vibecheckrc` invalidates every entry. New rules always fire on untouched code.

> Upgrading from an older version: it wrote `.vibe-check-cache.json` into the project root and **skipped** unchanged files rather than replaying them, which meant a second scan of the same code reported fewer problems than the first. That file is now deleted automatically on the next scan.

## Contributing

vibe-check is built for universality , every rule must make sense on any web project, not just one person's setup.

Before contributing a new check, verify:
1. It catches a real, common AI-generated anti-pattern
2. It has false-positive suppression (comment lines, test files, env var references)
3. The error message is understandable to a stranger
4. It works on the file types where the pattern commonly appears

Run the test suite:
```bash
python3 tests/test-rules.py
python3 tests/test-cache.py
python3 tests/test-stop-hook.py
```

## FAQ

**Q: Why not ESLint/Stylelint/some-other-linter?**
A: vibe-check catches patterns those tools don't , copywriting tropes, branding mistakes, security misconfigurations that span frameworks. It complements, not replaces, existing linters.

**Q: What about false positives?**
A: Every check has suppression logic. If you hit a false positive, open an issue , we'll add a suppression pattern.

**Q: Can I use this in my own projects?**
A: Yes. MIT licensed. Designed to be universal from day one.

**Q: How is this different from other "vibe coding" critiques?**
A: This is an automated tool, not a blog post. It runs in CI, blocks deployments, and enforces rules mechanically , not by memory.

## License

MIT , see [LICENSE](LICENSE).
