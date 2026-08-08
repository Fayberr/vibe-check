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
# Download (no install needed , single file, stdlib only)
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

# Only scan files changed since last git commit
./vibe-check /path/to/project --changed
```

**Requirements:** Python 3.9+. Nothing else.

## What It Checks (50 Rules)

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

### Technical & Code Quality (Rules 20-29)
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

## CI Integration

### GitHub Actions

```yaml
- name: Run vibe-check
  run: |
    curl -O https://raw.githubusercontent.com/Fayberr/vibe-check/main/vibe-check
    python3 vibe-check . --prod
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

- No `pip install`, no `npm install`, no venv setup
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

File hashes are cached in `.vibe-check-cache.json` (project root). Unchanged files are skipped on subsequent runs. Add this file to `.gitignore`.

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
