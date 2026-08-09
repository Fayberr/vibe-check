# vibe-check

**Catch AI-vibecoded slop before it ships.** A single-file, zero-dependency Python linter that detects 52 patterns of AI-generated code smell in web projects , from missing favicons to hardcoded API keys.

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

## What It Checks (52 Rules)

### Domain & Branding (Rules 1-4)
- Default `vercel.app` URLs in source
- Text-only unbranded logos
- Missing or default framework favicons (Vite/React placeholders)
- Leftover AI builder watermarks ("Made with Lovable", "v0", "bolt.new")

### Design & Aesthetic Tropes (Rules 5-11)
- Generic purple/indigo gradient palettes
- AI-slop stock photos / synthetic avatars
- Generic gradient hero typography
- Scroll animation bloat (excessive Framer Motion / AOS)
- Cursive/script font imports (Dancing Script, Pacifico, etc.)
- **Emojis in UI copy** , zero tolerance, use SVG icons
- Single-page traps for complex apps

### Copywriting & Social Proof Red Flags (Rules 12-19)
- **Em-dashes** (U+2014) in UI copy: replace with commas (auto-fixable)
- **Double hyphens** (`--`) used as prose dash: replace with comma (auto-fixable)
- Vague buzzword hero headlines
- Fake testimonials ("John Doe", "Jane Smith")
- Fake live visitor badges
- Fake customer counts ("Trusted by 10,000+ creators")
- Fake metric counter bars
- Missing Privacy Policy / Terms & Conditions (production mode)

### Security (Rules 40-50)
- **XSS sinks:** `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write`, `eval()`, `v-html`, `javascript:` URLs
- **File upload gaps:** `<input type="file">` without `accept`, multer without `fileFilter`, `express.static` over upload dirs
- **Unsigned webhooks:** missing HMAC signature verification
- **Hardcoded secrets:** API keys, DB credentials, private keys, access tokens
- **Broken JWT validation:** `verify=False`, `algorithms=["none"]`, missing algorithm pinning
- **Debug mode in production:** `DEBUG=True`, `NODE_ENV=development`, Flask/Django debug flags
- **Unsafe deserialization:** `pickle.loads()`, `yaml.load()` without SafeLoader, `torch.load()` without `weights_only`
- **Math.random() for security:** non-cryptographic random in token/auth/reset contexts
- **Missing security headers:** Express without helmet, Flask without Talisman, FastAPI without Secure
- **SSRF via user URLs:** unfiltered user input flowing to `fetch()`/`axios`/`requests.get()`
- **No rate limiting:** missing `express-rate-limit` / `slowapi` / `flask-limiter`
- **AI co-author trailers in git commits:** `Co-Authored-By: Claude/GPT/Gemini/Copilot` in commit history
- **Claude Code attribution settings:** `~/.claude/settings.json` leaves AI co-author trailers enabled (`--fix` corrects this at the source)

### SEO & Accessibility (Rules 30-39)
- Missing `<meta name="description">`
- Default framework tab titles ("Vite + React")
- Page titles over 24 characters (browser tabs truncate)
- Missing `og:image` social preview tags
- Missing JSON-LD structured data
- Strict H1 hierarchy (exactly one `<h1>` per page)
- Missing `<link rel="canonical">` (production mode)
- Missing `sitemap.xml` / `llms.txt` (production mode)
- Missing `lang` attribute on `<html>`
- Missing `alt` text on images

### Technical & Code Quality (Rules 20-30)
- Broken buttons (`href="#"` without handlers)
- Exposed production source maps
- Console error/warning spam (`console.log` in frontend code)
- Unstyled `<select>` elements in JSX/TSX
- `dangerouslySetInnerHTML` without sanitization
- `target="_blank"` without `rel="noopener noreferrer"`
- Inline `style={{...}}` objects (use Tailwind/CSS modules)
- `as` type casts in TypeScript (prefer type narrowing)
- TODO/FIXME/HACK tech-debt markers
- Placeholder copy ("Lorem ipsum", fake names)
- Password inputs missing `autocomplete` (breaks password managers)

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
| `--install-hooks --server <dir>` | Install pre-receive hook on all bare repos (server-side, cannot be bypassed) |
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
| 5. Rule 51 detection | Retroactive scan | Detection only | Built-in |

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

Rule 51 detects AI co-author trailers in past commits, but detection after the fact is not enough: GitHub caches contributors aggressively, making retroactive cleanup painful. The `--install-hooks` flag installs a git `commit-msg` hook that **blocks commits before they happen**:

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
