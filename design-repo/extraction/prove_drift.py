#!/usr/bin/env python3
"""Proves verify_all.py's drift checks actually fail on bad input (MASTER-GUIDE 3.2 / 3.4 / 3.16 / 3.23).

For each case: copy design-repo/ to a fresh OS temp dir, inject one drift, run verify_all.py there
(pointing --source-root at the real evidence tree so citations can be checked), and require that the
named check FAILs. A clean copy must pass, and a copy with NO sibling evidence must downgrade the
citation check to WARN (not FAIL).

Usage: python3 extraction/prove_drift.py [--source-root PATH] [--scratch DIR]   (exit 1 if any case misbehaves)
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


def set_height(d, key, px):
    sh = d["sectionHeights"]
    if sh["sections"][key]["inFlow"]:
        sh["pageHeight"] += px - sh["sections"][key]["heightPx"]
    sh["sections"][key]["heightPx"] = px


def add_whitelist(d, key, cap, just="Reviewed: this section legitimately spans the whole page on this page type.", reviewer="agent-attestation:drift-test"):
    s, v = key.split("/")
    d["entries"].append({"section": s, "variant": v, "rules": ["HERO_HEIGHT_FAIL"], "maxHeightPx": cap, "justification": just, "reviewer": reviewer, "reviewedOn": "2026-10-23"})


def unpin_layer_everywhere(root):
    """Edit the contract, the allowlist AND semantic_validate.py's own pin so only verify_all's independent table can object."""
    def contract(d):
        d["retrievalEligible"] = True
        d.pop("retrievalReason", None)
    edit_json(root, "sections/layer-webgl-object.json", contract)
    edit_json(root, "tokens/llm/component-allowlist.json", lambda d: d["sections"]["layer.webgl-object"].__setitem__("retrievalEligible", True))
    edit_text(root, "schema/semantic_validate.py", lambda t: t.replace('RETRIEVAL_PINNED = {"layer.webgl-object": False}', "RETRIEVAL_PINNED = {}")
              .replace('if (UTILITY_ID_RE.search(sid) or cat == "layer") and got is not False:', "if False:"))


def retag_form_everywhere(root):
    """Re-class the waitlist form as generic content in the contract AND in semantic_validate.py's own pin."""
    edit_json(root, "sections/cta-waitlist-form.json", lambda d: d["semantic"].__setitem__("category", "content"))
    edit_text(root, "schema/semantic_validate.py", lambda t: t.replace('"cta.waitlist-form": "cta",', '"cta.waitlist-form": "content",'))


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
     lambda r: edit_json(r, "tokens/llm/component-allowlist.json", lambda d: d.__setitem__("allowlistVersion", "9.9.9"))),
    ("manifest count drift", "manifest + README counts",
     lambda r: edit_json(r, "registry.manifest.json", lambda d: d["counts"].__setitem__("sections", 12))),
    ("README count drift", "manifest + README counts",
     lambda r: edit_text(r, "README.md", lambda t: t.replace("| sections | 8 |", "| sections | 9 |"))),
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
    ("WebGL overlay made retrievable", "retrieval eligibility pinned",
     lambda r: edit_json(r, "sections/layer-webgl-object.json", lambda d: d.__setitem__("retrievalEligible", True))),
    ("overlay retrievalReason shortened below 30 chars", "retrieval eligibility pinned",
     lambda r: edit_json(r, "sections/layer-webgl-object.json", lambda d: d.__setitem__("retrievalReason", "decorative canvas"))),
    ("hero marked ineligible", "retrieval eligibility pinned",
     lambda r: edit_json(r, "sections/hero-course-intro.json", lambda d: d.update({"retrievalEligible": False, "retrievalReason": "Pretend this hero is utility chrome so it never reaches retrieval."}))),
    ("allowlist retrievalEligible diverges from contract", "allowlist parity",
     lambda r: edit_json(r, "tokens/llm/component-allowlist.json", lambda d: d["sections"]["layer.webgl-object"].__setitem__("retrievalEligible", True))),
    ("retrieval pin removed from semantic_validate too (verify_all's own table still objects)", "retrieval eligibility pinned", unpin_layer_everywhere),
    ("retrievalIneligibleSections count drift", "manifest + README counts",
     lambda r: edit_json(r, "registry.manifest.json", lambda d: d["counts"].__setitem__("retrievalIneligibleSections", 0))),
    ("waitlist form re-classed as content", "section taxonomy pinned",
     lambda r: edit_json(r, "sections/cta-waitlist-form.json", lambda d: d["semantic"].__setitem__("category", "content"))),
    ("form re-classed in contract AND semantic_validate (verify_all's own table still objects)", "section taxonomy pinned", retag_form_everywhere),
    ("CTA field hidden in the generic content section", "section taxonomy pinned",
     lambda r: edit_json(r, "sections/content-block-pairs.json", lambda d: d["variants"]["feature-pairs"]["contentFields"].append("cta"))),
    ("unknown field added to source", "section contracts: closed schema",
     lambda r: edit_json(r, "sections/hero-course-intro.json", lambda d: d["source"].__setitem__("selector", "header#intro"))),
    ("taxonomy field leaked into source", "section contracts: closed schema",
     lambda r: edit_json(r, "sections/hero-course-intro.json", lambda d: d["source"].__setitem__("category", "hero"))),
    ("legacy top-level category re-added", "section contracts: closed schema",
     lambda r: edit_json(r, "sections/hero-course-intro.json", lambda d: d.__setitem__("category", "hero"))),
    ("source range ends one line early", "section source provenance",
     lambda r: edit_json(r, "sections/hero-course-intro.json", lambda d: d["source"].__setitem__("lines", "15-37"))),
    ("source range shifted (in range, wrong lines)", "section source provenance",
     lambda r: edit_json(r, "sections/shell-nav.json", lambda d: d["source"].__setitem__("lines", "6-22"))),
    ("source id differs from the element's id", "section source provenance",
     lambda r: edit_json(r, "sections/list-numbered-topics.json", lambda d: (d["source"].__setitem__("id", "course"), d["variants"]["default"].__setitem__("anchorId", "course")))),
    ("source citation points at an unrelated ledger entry", "section source provenance",
     lambda r: edit_json(r, "sections/shell-nav.json", lambda d: d["source"].__setitem__("citation", "mv.section.canvas"))),
    ("source file does not exist", "section source provenance",
     lambda r: edit_json(r, "sections/shell-nav.json", lambda d: d["source"].__setitem__("file", "src/components/Nav.jsx"))),
    ("hero measured at 3500px (page wrapper)", "whole-page-wrapper gate",
     lambda r: edit_json(r, "extraction/measured-values.json", lambda d: set_height(d, "hero.course-intro/default", 3500))),
    ("one section holds 65% of the page", "whole-page-wrapper gate",
     lambda r: edit_json(r, "extraction/measured-values.json", lambda d: set_height(d, "list.numbered-topics/default", 9000))),
    ("section measurement deleted", "whole-page-wrapper gate",
     lambda r: edit_json(r, "extraction/measured-values.json", lambda d: d["sectionHeights"]["sections"].pop("cta.waitlist-form/default"))),
    ("sectionHeights block deleted", "whole-page-wrapper gate",
     lambda r: edit_json(r, "extraction/measured-values.json", lambda d: d.pop("sectionHeights"))),
    ("hero measured 3100px, whitelist justification too short", "whole-page-wrapper gate",
     lambda r: (edit_json(r, "extraction/measured-values.json", lambda d: set_height(d, "hero.course-intro/default", 3100)),
                edit_json(r, "extraction/wrapper-whitelist.json", lambda d: add_whitelist(d, "hero.course-intro/default", 3200, just="ok")))),
    ("typo'd maxWords path", "maxWords budget paths",
     lambda r: edit_json(r, "sections/hero-course-intro.json", lambda d: d["variants"]["default"]["maxWords"].__setitem__("eybrow", 3) or d["variants"]["default"]["realWordCounts"].__setitem__("eybrow", 1))),
]


# (name, inject, regex that must appear in the output): the run must still PASS (rc 0), only warn
WARN_CASES = [
    ("hero 1900px -> warn only", lambda r: edit_json(r, "extraction/measured-values.json", lambda d: set_height(d, "hero.course-intro/default", 1900)),
     r"^\[WARN\] whole-page-wrapper gate warning HERO_HEIGHT_WARN"),
    ("one section 51% of the page -> warn only", lambda r: edit_json(r, "extraction/measured-values.json", lambda d: set_height(d, "list.numbered-topics/default", 5000)),
     r"^\[WARN\] whole-page-wrapper gate warning SECTION_SHARE_WARN"),
    ("hero 3100px with a reviewed whitelist entry -> warn only",
     lambda r: (edit_json(r, "extraction/measured-values.json", lambda d: set_height(d, "hero.course-intro/default", 3100)),
                edit_json(r, "extraction/wrapper-whitelist.json", lambda d: add_whitelist(d, "hero.course-intro/default", 3200))),
     r"^\[WARN\] whole-page-wrapper gate warning HERO_HEIGHT_FAIL_WHITELISTED"),
    ("stale whitelist entry -> warn only", lambda r: edit_json(r, "extraction/wrapper-whitelist.json", lambda d: add_whitelist(d, "hero.course-intro/default", 3200)),
     r"^\[WARN\] whole-page-wrapper gate warning WHITELIST_UNUSED"),
]


# checks that can only fail when the cited source files exist next to design-repo/
SOURCE_DEPENDENT = {"citation validity", "section source provenance"}


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
    scratch = os.path.abspath(argv[argv.index("--scratch") + 1]) if "--scratch" in argv else None
    tmp_parent = tempfile.mkdtemp(prefix="drift-", dir=scratch)
    bad = 0
    skipped = 0
    try:
        rc, out = run_verify(fresh_copy(tmp_parent), source_root)
        ok = rc == 0
        bad += not ok
        print("%s control: clean copy passes (rc=%d)" % ("PASS" if ok else "FAIL", rc))
        if not ok:
            print(out)

        empty = tempfile.mkdtemp(dir=tmp_parent)
        rc, out = run_verify(fresh_copy(tmp_parent), empty)
        ok = rc == 0 and re.search(r"^\[WARN\] citation validity", out, re.M) is not None and re.search(r"^\[WARN\] section source provenance", out, re.M) is not None
        bad += not ok
        print("%s control: no sibling evidence -> citation + source-provenance checks WARN, run still passes (rc=%d)" % ("PASS" if ok else "FAIL", rc))

        have_source = os.path.exists(os.path.join(source_root, "src", "App.jsx"))
        for name, check, inject in CASES:
            if check in SOURCE_DEPENDENT and not have_source:
                skipped += 1
                print("SKIP drift case (needs the source tree, none under --source-root): %s" % name)
                continue
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
        for name, inject, pattern in WARN_CASES:
            root = fresh_copy(tmp_parent)
            inject(root)
            rc, out = run_verify(root, source_root)
            ok = rc == 0 and re.search(pattern, out, re.M) is not None
            bad += not ok
            print("%s warn-only case: %-47s (rc=%d)" % ("PASS" if ok else "MISS", name, rc))
            if not ok:
                print(out)
    finally:
        shutil.rmtree(tmp_parent, ignore_errors=True)
    print("\nprove_drift: %d drift cases (%d skipped: no source tree) + %d warn-only cases + 2 controls, %d problem(s)" % (len(CASES), skipped, len(WARN_CASES), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
