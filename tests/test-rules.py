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

if __name__ == "__main__":
    print("Testing SQL RLS and Supabase service_role rules...")
    test_rls_permissive_policy()
    test_rls_disabled()
    test_sql_double_dash_ignored()
    test_supabase_service_role_key_exposed()
    test_supabase_anon_key_allowed()
    print("========================================================")
    print("All rule tests passed cleanly!")
