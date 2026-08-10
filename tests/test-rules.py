#!/usr/bin/env python3
"""
Unit/integration tests for vibe-check rules, including SQL RLS and Supabase service_role key detection.
"""

import sys
import os
import tempfile
import shutil
import subprocess
import json
from pathlib import Path

# Locate vibe-check binary
VIBE_CHECK_BIN = Path(__file__).parent.parent / "vibe-check"

def run_vibe_check(target_dir, extra_args=None):
    cmd = [sys.executable, str(VIBE_CHECK_BIN), str(target_dir), "--json", "--quiet"]
    if extra_args:
        cmd.extend(extra_args)
    res = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return res.returncode, json.loads(res.stdout)
    except json.JSONDecodeError:
        print("STDERR:", res.stderr)
        print("STDOUT:", res.stdout)
        raise

def test_rls_permissive_policy():
    tmp_dir = Path(tempfile.mkdtemp(prefix="vibe_test_rls_"))
    try:
        sql_file = tmp_dir / "migration.sql"
        sql_file.write_text("""
-- Enable RLS
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

-- Permissive policy
CREATE POLICY "Public profiles are viewable by everyone" ON profiles
    FOR SELECT USING (true);

CREATE POLICY "Anyone can insert" ON profiles
    FOR INSERT WITH CHECK ( true );
""")
        code, out = run_vibe_check(tmp_dir)
        findings = [f for f in out.get("findings", []) if f["rule"] == "rls-permissive-policy"]
        assert len(findings) == 1, f"Expected 1 rls-permissive-policy finding, got {len(findings)}: {out}"
        assert findings[0]["severity"] == "error"
        assert "USING(true)" in findings[0]["message"]
        assert "WITH CHECK(true)" in findings[0]["message"]
        print("  PASS  rls-permissive-policy detected in SQL")
    finally:
        shutil.rmtree(tmp_dir)

def test_rls_disabled():
    tmp_dir = Path(tempfile.mkdtemp(prefix="vibe_test_rls_dis_"))
    try:
        sql_file = tmp_dir / "disable_rls.sql"
        sql_file.write_text("""
-- Disable RLS for debug
ALTER TABLE secret_vault DISABLE ROW LEVEL SECURITY;
""")
        code, out = run_vibe_check(tmp_dir)
        findings = [f for f in out.get("findings", []) if f["rule"] == "rls-disabled"]
        assert len(findings) == 1, f"Expected 1 rls-disabled finding, got {len(findings)}: {out}"
        assert findings[0]["severity"] == "error"
        assert "DISABLE ROW LEVEL SECURITY" in findings[0]["message"]
        print("  PASS  rls-disabled detected in SQL")
    finally:
        shutil.rmtree(tmp_dir)

def test_sql_double_dash_ignored():
    tmp_dir = Path(tempfile.mkdtemp(prefix="vibe_test_sql_dd_"))
    try:
        sql_file = tmp_dir / "comments.sql"
        sql_file.write_text("""
-- This is a standard SQL comment -- it should not trigger double-dash
SELECT * FROM users; -- another comment -- here
""")
        code, out = run_vibe_check(tmp_dir)
        dd_findings = [f for f in out.get("findings", []) if f["rule"] == "double-dash"]
        assert len(dd_findings) == 0, f"Expected 0 double-dash findings for SQL comments, got {len(dd_findings)}"
        print("  PASS  SQL -- comments do not trigger double-dash false positives")
    finally:
        shutil.rmtree(tmp_dir)


def test_test_files_exempt_from_prose_rules():
    """Test/fixture files must be exempt regardless of how the path is written.

    Regression: _is_test_path() used to substring-match '/tests/', so the same
    file was exempt when scanned by absolute path but flagged when scanned via
    a relative path. Prose rules also have to stay off test files, because a
    test asserting this rule's behaviour must contain the offending pattern.
    """
    tmp_dir = Path(tempfile.mkdtemp(prefix="vibe_test_exempt_"))
    try:
        tests_dir = tmp_dir / "tests"
        tests_dir.mkdir()
        fixture = tests_dir / "fixture_check.py"
        fixture.write_text(
            'BAD = "this is prose -- with a double dash"\n'
            'WORSE = "this one has an em dash — right here"\n')

        for extra in ([], ["--no-cache"]):
            code, out = run_vibe_check(tmp_dir, extra)
            for rule in ("double-dash", "em-dashes"):
                assert len(_findings_for(out, rule)) == 0, \
                    f"{rule} fired inside tests/ (args={extra}): {out}"

        # The same content outside a test dir must still be caught, so this is
        # an exemption and not a hole.
        real = tmp_dir / "copy.py"
        real.write_text('BAD = "this is prose -- with a double dash"\n')
        code, out = run_vibe_check(tmp_dir, ["--no-cache"])
        assert len(_findings_for(out, "double-dash")) == 1, \
            f"double-dash should still fire outside tests/: {out}"
        print("  PASS  test dirs exempt from prose rules, non-test files still checked")
    finally:
        shutil.rmtree(tmp_dir)


def test_supabase_service_role_key_exposed():
    tmp_dir = Path(tempfile.mkdtemp(prefix="vibe_test_service_role_"))
    try:
        # Construct JWT with payload: {"role": "service_role", "iss": "supabase"}
        # eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoic2VydmljZV9yb2xlIiwiaXNzIjoic3VwYWJhc2UifQ.dHVtbXlzaWduYXR1cmVmb3J0ZXN0aW5ncHVycG9zZXM
        service_role_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoic2VydmljZV9yb2xlIiwiaXNzIjoic3VwYWJhc2UifQ.dHVtbXlzaWduYXR1cmVmb3J0ZXN0aW5ncHVycG9zZXM"
        
        js_file = tmp_dir / "client.js"
        js_file.write_text(f"""
const SUPABASE_URL = "https://xyz.supabase.co";
const SUPABASE_KEY = "{service_role_jwt}";
""")
        code, out = run_vibe_check(tmp_dir)
        findings = [f for f in out.get("findings", []) if f["rule"] == "supabase-service-role-key-exposed"]
        assert len(findings) == 1, f"Expected 1 service_role finding, got {len(findings)}: {out}"
        assert findings[0]["severity"] == "error"
        assert "service_role" in findings[0]["message"]
        print("  PASS  Supabase service_role key exposed in JS detected")
    finally:
        shutil.rmtree(tmp_dir)

def test_supabase_anon_key_allowed():
    tmp_dir = Path(tempfile.mkdtemp(prefix="vibe_test_anon_role_"))
    try:
        # Construct JWT with payload: {"role": "anon", "iss": "supabase"}
        # eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoiYW5vbiIsImlzcyI6InN1cGFiYXNlIn0.dHVtbXlzaWduYXR1cmVmb3J0ZXN0aW5ncHVycG9zZXM
        anon_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoiYW5vbiIsImlzcyI6InN1cGFiYXNlIn0.dHVtbXlzaWduYXR1cmVmb3J0ZXN0aW5ncHVycG9zZXM"
        
        js_file = tmp_dir / "client.js"
        js_file.write_text(f"""
const SUPABASE_URL = "https://xyz.supabase.co";
const SUPABASE_KEY = "{anon_jwt}";
""")
        code, out = run_vibe_check(tmp_dir)
        findings = [f for f in out.get("findings", []) if f["rule"] == "supabase-service-role-key-exposed"]
        assert len(findings) == 0, f"Expected 0 service_role findings for anon key, got {len(findings)}"
        print("  PASS  Supabase anon key does not trigger service_role rule")
    finally:
        shutil.rmtree(tmp_dir)

def _findings_for(out, rule):
    return [f for f in out.get("findings", []) if f["rule"] == rule]


SEO_PAGE = ('<html lang="en"><head><title>Shop</title>'
            '<meta name="description" content="A shop that sells things.">'
            '{extra}</head><body><h1>Shop</h1></body></html>')


def test_json_ld_missing():
    """Rule 33: prod-mode SEO pages without JSON-LD structured data."""
    tmp_dir = Path(tempfile.mkdtemp(prefix="vibe_test_jsonld_"))
    try:
        (tmp_dir / "index.html").write_text(SEO_PAGE.format(extra=""))
        code, out = run_vibe_check(tmp_dir, ["--prod"])
        assert len(_findings_for(out, "json-ld-missing")) == 1, \
            f"Expected 1 json-ld-missing finding, got {out}"

        # With JSON-LD present it must not fire.
        (tmp_dir / "index.html").write_text(SEO_PAGE.format(
            extra='<script type="application/ld+json">'
                  '{"@context":"https://schema.org"}</script>'))
        code, out = run_vibe_check(tmp_dir, ["--prod", "--no-cache"])
        assert len(_findings_for(out, "json-ld-missing")) == 0, \
            f"json-ld-missing fired despite ld+json present: {out}"

        # Must be production-only, silent in normal mode.
        (tmp_dir / "index.html").write_text(SEO_PAGE.format(extra=""))
        code, out = run_vibe_check(tmp_dir, ["--no-cache"])
        assert len(_findings_for(out, "json-ld-missing")) == 0, \
            "json-ld-missing should only fire with --prod"

        # An app shell with no SEO metadata at all (extension popup, Electron
        # window) is not an indexable page, so structured data is meaningless.
        (tmp_dir / "index.html").write_text(
            '<html lang="en"><head><title>Popup</title></head>'
            '<body><h1>Popup</h1><div id="root"></div></body></html>')
        code, out = run_vibe_check(tmp_dir, ["--prod", "--no-cache"])
        assert len(_findings_for(out, "json-ld-missing")) == 0, \
            f"json-ld-missing fired on a non-SEO app shell: {out}"
        print("  PASS  json-ld-missing fires on SEO pages only, in prod only")
    finally:
        shutil.rmtree(tmp_dir)


def test_oversized_bundle():
    """Rule 27: shipped JS chunks over 500KB."""
    tmp_dir = Path(tempfile.mkdtemp(prefix="vibe_test_bundle_"))
    try:
        dist = tmp_dir / "dist"
        dist.mkdir()
        (dist / "small.js").write_text("console.info('ok');\n")
        code, out = run_vibe_check(tmp_dir)
        assert len(_findings_for(out, "oversized-bundle")) == 0, \
            f"oversized-bundle fired on a small chunk: {out}"

        (dist / "vendor.js").write_text("var a=1;" * 70000)
        assert (dist / "vendor.js").stat().st_size > 500 * 1024
        code, out = run_vibe_check(tmp_dir, ["--no-cache"])
        found = _findings_for(out, "oversized-bundle")
        assert len(found) == 1, f"Expected 1 oversized-bundle finding, got {out}"
        assert "vendor.js" in found[0]["message"]
        assert found[0]["severity"] == "warn"
        print("  PASS  oversized-bundle detects >500KB chunk, ignores small ones")
    finally:
        shutil.rmtree(tmp_dir)


def test_robots_blocks_crawlers():
    """Rule 28: robots.txt de-indexing the whole site."""
    tmp_dir = Path(tempfile.mkdtemp(prefix="vibe_test_robots_"))
    try:
        (tmp_dir / "robots.txt").write_text("User-agent: *\nDisallow: /\n")
        code, out = run_vibe_check(tmp_dir)
        found = _findings_for(out, "robots-blocks-crawlers")
        assert len(found) == 1, f"Expected 1 robots finding, got {out}"
        assert "every crawler" in found[0]["message"]

        # A normal robots.txt must stay silent.
        (tmp_dir / "robots.txt").write_text(
            "User-agent: *\nDisallow: /admin/\nSitemap: https://x.dev/sitemap.xml\n")
        code, out = run_vibe_check(tmp_dir, ["--no-cache"])
        assert len(_findings_for(out, "robots-blocks-crawlers")) == 0, \
            f"robots rule fired on a healthy robots.txt: {out}"

        # Blocking only AI crawlers is a deliberate choice, not a finding.
        (tmp_dir / "robots.txt").write_text(
            "User-agent: GPTBot\nDisallow: /\n\nUser-agent: *\nDisallow:\n")
        code, out = run_vibe_check(tmp_dir, ["--no-cache"])
        assert len(_findings_for(out, "robots-blocks-crawlers")) == 0, \
            f"robots rule should not fire on AI-only blocks: {out}"
        print("  PASS  robots-blocks-crawlers flags full block, allows AI-only block")
    finally:
        shutil.rmtree(tmp_dir)


def test_generic_gradient_palette():
    """Rule 5: default purple/indigo gradient palette."""
    tmp_dir = Path(tempfile.mkdtemp(prefix="vibe_test_palette_"))
    try:
        (tmp_dir / "hero.css").write_text(
            ".hero { background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%); }\n")
        code, out = run_vibe_check(tmp_dir)
        found = _findings_for(out, "generic-gradient-palette")
        assert len(found) == 1, f"Expected 1 palette finding, got {out}"
        assert found[0]["severity"] == "warn"

        # Tailwind form.
        (tmp_dir / "hero.css").unlink()
        (tmp_dir / "Hero.tsx").write_text(
            'export const Hero = () => <div className="bg-gradient-to-r '
            'from-indigo-500 to-purple-500">hi</div>;\n')
        code, out = run_vibe_check(tmp_dir, ["--no-cache"])
        assert len(_findings_for(out, "generic-gradient-palette")) == 1, \
            f"Expected Tailwind palette finding, got {out}"

        # The same hex outside a gradient is a legitimate brand colour.
        (tmp_dir / "Hero.tsx").unlink()
        (tmp_dir / "brand.css").write_text(".btn { color: #6366f1; }\n")
        code, out = run_vibe_check(tmp_dir, ["--no-cache"])
        assert len(_findings_for(out, "generic-gradient-palette")) == 0, \
            f"palette rule fired on a non-gradient colour: {out}"
        print("  PASS  generic-gradient-palette flags gradients only, not brand colours")
    finally:
        shutil.rmtree(tmp_dir)


def test_gradient_hero_text():
    """Rule 7: gradient-filled hero typography."""
    tmp_dir = Path(tempfile.mkdtemp(prefix="vibe_test_gradtext_"))
    try:
        (tmp_dir / "Hero.tsx").write_text(
            'export const H = () => <h1 className="bg-gradient-to-r from-blue-400 '
            'to-teal-400 bg-clip-text text-transparent">Ship</h1>;\n')
        code, out = run_vibe_check(tmp_dir)
        found = _findings_for(out, "gradient-hero-text")
        assert len(found) == 1, f"Expected 1 gradient-hero-text finding, got {out}"

        # bg-clip-text without a gradient is not the trope.
        (tmp_dir / "Hero.tsx").write_text(
            'export const H = () => <h1 className="bg-clip-text">Ship</h1>;\n')
        code, out = run_vibe_check(tmp_dir, ["--no-cache"])
        assert len(_findings_for(out, "gradient-hero-text")) == 0, \
            f"gradient-hero-text fired without a gradient: {out}"
        print("  PASS  gradient-hero-text needs clip+transparent+gradient together")
    finally:
        shutil.rmtree(tmp_dir)


def test_new_rules_are_suppressible():
    """Every new rule must be turn-off-able from .vibecheckrc."""
    tmp_dir = Path(tempfile.mkdtemp(prefix="vibe_test_suppress_"))
    try:
        (tmp_dir / "hero.css").write_text(
            ".hero { background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%); }\n")
        (tmp_dir / "robots.txt").write_text("User-agent: *\nDisallow: /\n")
        (tmp_dir / ".vibecheckrc").write_text(
            '{"rules": {"generic-gradient-palette": "off", '
            '"robots-blocks-crawlers": "off"}}')
        code, out = run_vibe_check(tmp_dir)
        assert len(_findings_for(out, "generic-gradient-palette")) == 0
        assert len(_findings_for(out, "robots-blocks-crawlers")) == 0
        print("  PASS  new rules respect .vibecheckrc severity overrides")
    finally:
        shutil.rmtree(tmp_dir)


if __name__ == "__main__":
    print("Testing SQL RLS and Supabase service_role rules...")
    test_rls_permissive_policy()
    test_rls_disabled()
    test_sql_double_dash_ignored()
    test_test_files_exempt_from_prose_rules()
    test_supabase_service_role_key_exposed()
    test_supabase_anon_key_allowed()
    print("\nTesting Tier 1 automated standard rules...")
    test_json_ld_missing()
    test_oversized_bundle()
    test_robots_blocks_crawlers()
    test_generic_gradient_palette()
    test_gradient_hero_text()
    test_new_rules_are_suppressible()
    print("========================================================")
    print("All rule tests passed cleanly!")
