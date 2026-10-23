#!/usr/bin/env python3
"""Proves verify_all.py's drift checks actually fail on bad input (MASTER-GUIDE 3.2 / 3.4 / 3.16 / 3.23).

For each case: copy design-repo/ to a fresh OS temp dir, inject one drift, run verify_all.py there
(pointing --source-root at the real evidence tree so citations can be checked), and require that the
named check FAILs. A clean copy must pass, and a copy with NO sibling evidence must downgrade the
citation check to WARN (not FAIL).

Usage: python3 extraction/prove_drift.py [--source-root PATH]   (exit 1 if any case misbehaves)
"""
import sys
sys.dont_write_bytecode = True

import json
import os
import re
import shutil
import subprocess
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def edit_json(root, rel, fn):
    p = os.path.join(root, rel)
    with open(p, encoding="utf-8") as f:
        d = json.load(f)
    fn(d)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)


def edit_text(root, rel, fn):
    p = os.path.join(root, rel)
    with open(p, encoding="utf-8") as f:
        t = f.read()
    with open(p, "w", encoding="utf-8") as f:
        f.write(fn(t))


def first_cite(d, path_prefix):
    for e in d["entries"].values():
        for c in e["citations"]:
            if c["cite"].startswith(path_prefix):
                return c
    raise KeyError(path_prefix)


def set_sev(d, rule, sev):
    for r in d["rules"]:
        if r["id"] == rule:
            r["severity"] = sev


CASES = [
    ("phantom allowlist entry", "allowlist parity",
     lambda r: edit_json(r, "tokens/llm/component-allowlist.json", lambda d: d["primitives"].append("primitive.divider"))),
    ("orphan contract (allowlist entry removed)", "allowlist parity",
     lambda r: edit_json(r, "tokens/llm/component-allowlist.json", lambda d: d["components"].remove("component.timeline-table"))),
    ("allowlist settable property drift", "allowlist parity",
     lambda r: edit_json(r, "tokens/llm/component-allowlist.json", lambda d: d["sections"]["hero.course-intro"]["variants"]["default"]["settableProperties"].append("backgroundVideo"))),
    ("out-of-range citation", "citation validity",
     lambda r: edit_json(r, "extraction/measured-values.json", lambda d: first_cite(d, "CLONE_SPEC.md").__setitem__("cite", "CLONE_SPEC.md:9999"))),
    ("in-range citation pointing at the wrong lines", "citation validity",
     lambda r: edit_json(r, "extraction/measured-values.json", lambda d: d["entries"]["mv.color.webgl-clear"]["citations"][1].__setitem__("cite", "src/motion/cube.js:1-10"))),
    ("allowlistVersion drift", "version parity",
     lambda r: edit_json(r, "tokens/llm/component-allowlist.json", lambda d: d.__setitem__("allowlistVersion", "1.1.0"))),
    ("manifest count drift", "manifest + README counts",
     lambda r: edit_json(r, "registry.manifest.json", lambda d: d["counts"].__setitem__("sections", 8))),
    ("README count drift", "manifest + README counts",
     lambda r: edit_text(r, "README.md", lambda t: t.replace("| sections | 7 |", "| sections | 9 |"))),
    ("pinned policy -> different VALID policy", "pinned asset-role policies",
     lambda r: edit_json(r, "assets/asset-roles.json", lambda d: d["roles"]["endpoint.form-action"].__setitem__("generationPolicy", "may-generate-new"))),
    ("graph severity diverges from validator", "graph <-> validator",
     lambda r: edit_json(r, "compatibility/graph.json", lambda d: set_sev(d, "FOOTER_NAV_ANCHORS_RESOLVE", "warn"))),
    ("entry point outside the package", "entryPoints self-contained",
     lambda r: edit_json(r, "registry.manifest.json", lambda d: d["entryPoints"].append("../CLONE_SPEC.md"))),
    ("dangling evidence id", "evidence ids resolve",
     lambda r: edit_json(r, "sections/hero-course-intro.json", lambda d: d["evidence"].append("mv." + "section.made-up"))),
    ("absolute machine path", "no absolute machine paths",
     lambda r: edit_text(r, "README.md", lambda t: t + "\nsee /" + "Users/someone/project\n")),
    ("unresolvable token reference", "token references resolve",
     lambda r: edit_json(r, "primitives/button-pill.json", lambda d: d["tokens"].append("typography.role.doesNotExist"))),
    ("typo'd maxWords path", "maxWords budget paths",
     lambda r: edit_json(r, "sections/hero-course-intro.json", lambda d: d["variants"]["default"]["maxWords"].__setitem__("eybrow", 3) or d["variants"]["default"]["realWordCounts"].__setitem__("eybrow", 1))),
]


def run_verify(root, source_root):
    p = subprocess.run([sys.executable, "-B", os.path.join(root, "extraction", "verify_all.py"), "--source-root", source_root],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    return p.returncode, p.stdout


def fresh_copy(tmp_parent):
    dst = os.path.join(tempfile.mkdtemp(dir=tmp_parent), "design-repo")
    shutil.copytree(REPO, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))
    return dst


def main(argv):
    source_root = os.path.dirname(REPO)
    if "--source-root" in argv:
        source_root = os.path.abspath(argv[argv.index("--source-root") + 1])
    tmp_parent = tempfile.mkdtemp(prefix="drift-")
    bad = 0
    try:
        rc, out = run_verify(fresh_copy(tmp_parent), source_root)
        ok = rc == 0
        bad += not ok
        print("%s control: clean copy passes (rc=%d)" % ("PASS" if ok else "FAIL", rc))
        if not ok:
            print(out)

        empty = tempfile.mkdtemp(dir=tmp_parent)
        rc, out = run_verify(fresh_copy(tmp_parent), empty)
        ok = rc == 0 and re.search(r"^\[WARN\] citation validity", out, re.M) is not None
        bad += not ok
        print("%s control: no sibling evidence -> citation check WARNs, run still passes (rc=%d)" % ("PASS" if ok else "FAIL", rc))

        for name, check, inject in CASES:
            root = fresh_copy(tmp_parent)
            inject(root)
            rc, out = run_verify(root, source_root)
            failed = [l for l in out.splitlines() if l.startswith("[FAIL] " + check)]
            ok = rc != 0 and bool(failed)
            bad += not ok
            print("%s drift caught: %-46s -> [FAIL] %s" % ("PASS" if ok else "MISS", name, check))
            if ok:
                print("        " + failed[0][:170])
            else:
                print(out)
    finally:
        shutil.rmtree(tmp_parent, ignore_errors=True)
    print("\nprove_drift: %d cases + 2 controls, %d problem(s)" % (len(CASES), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
