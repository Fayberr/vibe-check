#!/usr/bin/env python3
"""
Test suite for the findings cache.

Exists because of a real bug: cache v1 stored only {path: sha256} and did a bare
`continue` on a hash hit, so an unchanged file contributed zero findings to the
run. The same code scanned twice reported 25 errors and then 15. The verdict was
a function of run history rather than of the code, and a gate that passes on the
second try is worse than no gate.

The single most important assertion here is test_cached_run_matches_uncached: it
fails the moment a cache hit stops replaying its findings.

Every test runs against a temp project and an isolated VIBE_CHECK_CACHE_DIR, so
no real project or real cache is ever touched.

Run: python3 tests/test-cache.py
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

VIBE_CHECK = Path(__file__).resolve().parent.parent / "vibe-check"

results = []


def check(name, passed, detail=""):
    results.append((name, passed, detail))
    print(f"  {'PASS' if passed else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not passed else ""))


def scan(project, cache_dir, *extra):
    """Run a scan, return the parsed --json report."""
    env = dict(os.environ, VIBE_CHECK_CACHE_DIR=str(cache_dir), NO_COLOR="1")
    proc = subprocess.run(
        [sys.executable, str(VIBE_CHECK), str(project), "--json", "--quiet", *extra],
        capture_output=True, text=True, env=env, timeout=120,
    )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise AssertionError(f"non-JSON output (rc={proc.returncode}): {proc.stdout[:400]}{proc.stderr[:400]}")


def fingerprint(report):
    """Findings as an order-independent comparable set."""
    return sorted(json.dumps(f, sort_keys=True) for f in report["findings"])


# A file that trips several rules at once: console.log, a TODO marker, an `as any`
# cast, and an em-dash in a string. Enough that a suppressed file is obvious.
DIRTY = """\
export function handler(input: unknown) {
  // TODO: fix this later
  console.log("debug", input);
  const value = input as any;
  return "loading\\u2014please wait" + String(value);
}
"""

CLEAN = """\
export function add(a: number, b: number): number {
  return a + b;
}
"""


def main():
    if not VIBE_CHECK.is_file():
        print(f"vibe-check not found at {VIBE_CHECK}")
        return 1

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        project = tmp / "project"
        (project / "src").mkdir(parents=True)
        cache_dir = tmp / "cache"

        dirty = project / "src" / "dirty.ts"
        clean = project / "src" / "clean.ts"
        dirty.write_text(DIRTY, encoding="utf-8")
        clean.write_text(CLEAN, encoding="utf-8")

        print("Cache correctness (the v1 bug)")
        cold = scan(project, cache_dir)
        check("cold run finds the planted problems", cold["errors"] + cold["warnings"] > 0,
              f"got {cold['errors']}e/{cold['warnings']}w")
        check("cold run reports nothing as cached", cold["cached"] == 0, f"got {cold['cached']}")

        warm = scan(project, cache_dir)
        check("warm run actually used the cache", warm["cached"] > 0, f"got {warm['cached']}")
        check("warm run has identical error count", warm["errors"] == cold["errors"],
              f"cold {cold['errors']} vs warm {warm['errors']}")
        check("warm run has identical warning count", warm["warnings"] == cold["warnings"],
              f"cold {cold['warnings']} vs warm {warm['warnings']}")
        # The assertion that would have caught the original bug.
        check("test_cached_run_matches_uncached", fingerprint(warm) == fingerprint(cold),
              "cached run reported different findings than the cold run")

        nocache = scan(project, cache_dir, "--no-cache")
        check("--no-cache matches the cached run", fingerprint(nocache) == fingerprint(warm),
              "the cache changes the verdict")
        check("scanned count covers cached files too", warm["scanned"] == cold["scanned"],
              f"cold {cold['scanned']} vs warm {warm['scanned']}")

        print("\nInvalidation")
        clean.write_text(DIRTY, encoding="utf-8")
        after_edit = scan(project, cache_dir)
        check("editing a file re-scans it", len(after_edit["findings"]) > len(warm["findings"]),
              f"warm {len(warm['findings'])} findings vs after edit {len(after_edit['findings'])}")
        clean.write_text(CLEAN, encoding="utf-8")
        scan(project, cache_dir)

        # A changed rule set must invalidate every entry, or new rules never fire
        # on untouched code. Simulated by a config change, which is part of the key.
        (project / ".vibecheckrc").write_text(json.dumps({"rules": {"console-log": "off"}}), encoding="utf-8")
        after_config = scan(project, cache_dir)
        check("config change invalidates the cache", after_config["cached"] == 0,
              f"got {after_config['cached']} cached entries after config change")
        check("config change is actually honoured",
              not any(f["rule"] == "console-log" for f in after_config["findings"]),
              "console-log still reported after being turned off")
        (project / ".vibecheckrc").unlink()

        print("\nHygiene")
        scan(project, cache_dir)
        check("no cache file written into the project",
              not (project / ".vibe-check-cache.json").exists(),
              "v1 wrote an untracked cache file into the scanned repo")
        check("cache lives in the per-user cache dir",
              any(cache_dir.rglob("*.json")), f"nothing under {cache_dir}")

        legacy = project / ".vibe-check-cache.json"
        legacy.write_text('{"stale": "v1"}', encoding="utf-8")
        scan(project, cache_dir)
        check("legacy v1 cache file is cleaned up", not legacy.exists())

        print("\nFail-safe")
        unwritable = tmp / "unwritable"
        unwritable.mkdir()
        os.chmod(unwritable, 0o500)
        try:
            report = scan(project, unwritable / "sub")
            check("unwritable cache dir does not break the scan",
                  report["errors"] + report["warnings"] > 0, "scan produced no findings")
        finally:
            os.chmod(unwritable, 0o700)

        corrupt_dir = tmp / "corrupt"
        corrupt_dir.mkdir()
        scan(project, corrupt_dir)
        for entry in corrupt_dir.rglob("*.json"):
            entry.write_text("{not json at all", encoding="utf-8")
        report = scan(project, corrupt_dir)
        check("corrupt cache falls back to a full scan",
              fingerprint(report) == fingerprint(nocache), "corrupt cache changed the verdict")

    failed = [n for n, ok, _ in results if not ok]
    print("\n" + "=" * 56)
    print(f"{len(results) - len(failed)}/{len(results)} passed")
    if failed:
        print("FAILED: " + ", ".join(failed))
        return 1
    print("All green. The cache speeds up scans without changing the verdict.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
