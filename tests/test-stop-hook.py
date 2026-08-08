#!/usr/bin/env python3
"""
Test suite for vibe-check-stop-hook.py.

Exists because of ECC issue #2697: their blocking hook shipped inert because
nobody proved it blocked. The single most important assertion here is
test_blocks_dirty_file, which fails if the hook stops enforcing.

Uses VIBE_CHECK_STRICT_ROOTS env override so no real project is ever touched.
VIBE_CHECK_PROD_ROOTS left empty so --prod never applies during tests.

Run: python3 ~/.claude/hooks/test-vibe-check-stop-hook.py
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

def _resolve_hook():
    """Locate the stop hook.

    The hook is installed under the Claude Code config dir, not next to this
    file. Pointing at a nonexistent path made the suite pass its headline
    assertion for the wrong reason: python exits 2 on "no such file", which is
    the same exit code a real block uses. Fail loudly instead.
    """
    override = os.environ.get("VIBE_CHECK_STOP_HOOK")
    candidates = [Path(override)] if override else []
    candidates += [
        Path(__file__).resolve().parent / "vibe-check-stop-hook.py",
        Path.home() / ".claude" / "hooks" / "vibe-check-stop-hook.py",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise SystemExit(
        "stop hook not found. Looked in:\n  " + "\n  ".join(str(c) for c in candidates)
        + "\nSet VIBE_CHECK_STOP_HOOK to its path."
    )


HOOK = _resolve_hook()
EM_DASH = "—"

results = []


def build_transcript(path, edited_paths, tool="Write"):
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(json.dumps({"type": "user", "message": {"role": "user", "content": "hi"}}) + "\n")
        for target in edited_paths:
            entry = {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [
                        {"type": "text", "text": "editing"},
                        {
                            "type": "tool_use",
                            "id": "tu_1",
                            "name": tool,
                            "input": {"file_path": str(target), "content": "x"},
                        },
                    ],
                },
            }
            handle.write(json.dumps(entry) + "\n")
        handle.write("this line is not valid json\n")


def run_hook(payload, env_extra=None):
    env = dict(os.environ)
    env.pop("VIBE_CHECK_SKIP", None)
    if env_extra:
        env.update(env_extra)
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload) if isinstance(payload, (dict, list)) else payload,
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )
    return proc


def check(name, condition, detail=""):
    results.append((name, bool(condition), detail))
    mark = "PASS" if condition else "FAIL"
    print(f"  [{mark}] {name}" + (f"  {detail}" if detail and not condition else ""))


def main():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp).resolve()
        in_scope = tmp / "in-scope"
        outside = tmp / "outside"
        for d in (in_scope, outside):
            d.mkdir()

        dirty_in = in_scope / "dirty.md"
        dirty_in.write_text(f"# Title\n\nThis has an em dash {EM_DASH} right here.\n", encoding="utf-8")
        clean_in = in_scope / "clean.md"
        clean_in.write_text("# Title\n\nThis is clean, no banned characters.\n", encoding="utf-8")
        dirty_outside = outside / "dirty.md"
        dirty_outside.write_text(f"# Title\n\nEm dash {EM_DASH} outside all roots.\n", encoding="utf-8")
        not_checked = in_scope / "notes.txt"
        not_checked.write_text(f"em dash {EM_DASH} in an unchecked extension\n", encoding="utf-8")

        env = {
            "VIBE_CHECK_STRICT_ROOTS": str(in_scope),
            "VIBE_CHECK_PROD_ROOTS": "",
        }

        tr = tmp / "transcript.jsonl"

        print("\nSanity: vibe-check itself flags the fixture")
        vc = subprocess.run(
            ["vibe-check", str(dirty_in)], capture_output=True, text=True
        )
        check("vibe-check exits 1 on an em-dash file", vc.returncode == 1,
              f"got {vc.returncode}; fixture or tool changed")

        print("\nCore: does it actually block?")
        build_transcript(tr, [dirty_in])
        p = run_hook({"transcript_path": str(tr), "stop_hook_active": False}, env)
        check("BLOCKS dirty file (exit 2)", p.returncode == 2,
              f"got exit {p.returncode}")
        check("blocking reason reaches Claude on stderr",
              "vibe-check FAILED" in p.stderr and "dirty.md" in p.stderr,
              f"stderr={p.stderr[:200]!r}")

        print("\nLoop guard")
        p = run_hook({"transcript_path": str(tr), "stop_hook_active": True}, env)
        check("stop_hook_active releases the session (exit 0)", p.returncode == 0,
              f"got exit {p.returncode}")

        print("\nNo false positives")
        build_transcript(tr, [clean_in])
        p = run_hook({"transcript_path": str(tr), "stop_hook_active": False}, env)
        check("clean file passes", p.returncode == 0, f"got {p.returncode}")

        build_transcript(tr, [dirty_outside])
        p = run_hook({"transcript_path": str(tr), "stop_hook_active": False}, env)
        check("dirty file outside all roots ignored", p.returncode == 0, f"got {p.returncode}")

        build_transcript(tr, [not_checked])
        p = run_hook({"transcript_path": str(tr), "stop_hook_active": False}, env)
        check("unchecked extension ignored", p.returncode == 0, f"got {p.returncode}")

        print("\nMultiple failures")
        dirty2 = in_scope / "also-dirty.tsx"
        dirty2.write_text(f"const x = \"also has {EM_DASH} here\";\n", encoding="utf-8")
        build_transcript(tr, [dirty_in, dirty2, clean_in])
        p = run_hook({"transcript_path": str(tr), "stop_hook_active": False}, env)
        check("blocks with multiple dirty files", p.returncode == 2, f"got {p.returncode}")
        check("both files mentioned in output",
              "dirty.md" in p.stderr and "also-dirty.tsx" in p.stderr,
              f"stderr={p.stderr[:300]!r}")

        print("\nEscape hatches")
        build_transcript(tr, [dirty_in])
        p = run_hook({"transcript_path": str(tr)}, dict(env, VIBE_CHECK_SKIP="1"))
        check("VIBE_CHECK_SKIP=1 releases", p.returncode == 0, f"got {p.returncode}")

        skip_file = Path.home() / ".cache" / "vibe-check-skip"
        skip_file.parent.mkdir(parents=True, exist_ok=True)
        skip_file.touch()
        p = run_hook({"transcript_path": str(tr), "stop_hook_active": False}, env)
        check("skip file releases", p.returncode == 0, f"got {p.returncode}")
        check("skip file is one-shot (consumed)", not skip_file.exists())
        if skip_file.exists():
            skip_file.unlink()

        print("\nFail-open paths")
        p = run_hook("this is not json", env)
        check("malformed stdin fails open", p.returncode == 0, f"got {p.returncode}")
        p = run_hook("", env)
        check("empty stdin fails open", p.returncode == 0, f"got {p.returncode}")
        p = run_hook({"transcript_path": str(tmp / "nope.jsonl")}, env)
        check("missing transcript fails open", p.returncode == 0, f"got {p.returncode}")
        p = run_hook({}, env)
        check("empty payload fails open", p.returncode == 0, f"got {p.returncode}")

        build_transcript(tr, [dirty_in])
        p = run_hook({"transcript_path": str(tr)},
                     dict(env, VIBE_CHECK_BIN=str(tmp / "no-such-vibe-check")))
        check("missing vibe-check binary fails open", p.returncode == 0, f"got {p.returncode}")

    failed = [n for n, ok, _ in results if not ok]
    print("\n" + "=" * 56)
    print(f"{len(results) - len(failed)}/{len(results)} passed")
    if failed:
        print("FAILED: " + ", ".join(failed))
        return 1
    print("All green. The hook provably blocks and provably fails open.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
