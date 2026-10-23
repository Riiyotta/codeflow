#!/usr/bin/env python3
"""Adversarial suite: every mutation must be REJECTED with the expected rule id; every control must pass with 0 errors.

Usage: python3 schema/tests/adversarial_test.py   (exit 1 on any failure)
"""
import sys
sys.dont_write_bytecode = True

import copy
import importlib.util
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))

spec_ = importlib.util.spec_from_file_location("semantic_validate", os.path.join(REPO, "schema", "semantic_validate.py"))
sv = importlib.util.module_from_spec(spec_)
spec_.loader.exec_module(sv)

with open(os.path.join(REPO, "schema", "example.pagespec.json"), encoding="utf-8") as f:
    EXAMPLE = json.load(f)
BASE_REPO = sv.load_repo(REPO)


def node(s, section, variant=None):
    for n in s["nodes"]:
        if n["section"] == section and (variant is None or n["variant"] == variant):
            return n
    raise KeyError(section)


def idx(s, section, variant=None):
    return s["nodes"].index(node(s, section, variant))


def generated_control(s):
    """Neutral copy, provenance 'generated': must pass (proves BRAND_PASSOFF does not over-reject)."""
    s["contentProvenance"] = "generated"
    s["meta"]["title"] = "Join Waitlist"
    f = node(s, "shell.footer-wordmark")["content"]
    f["wordmark"] = [{"text": "THE", "layer": "front"}, {"text": "NEW", "layer": "behind-canvas-deep"},
                     {"text": "WAVE", "layer": "behind-canvas"}, {"text": "CO", "layer": "front"}]
    f["credit"]["linkLabel"] = "YOUR SITE"
    return s


# (name, category, expected rule, mutate(spec) -> spec, mutate_repo(repo) or None)
def M(name, cat, rule, fn, repo_fn=None):
    return (name, cat, rule, fn, repo_fn)


def _set(path_fn):
    def f(s):
        path_fn(s)
        return s
    return f


MUTATIONS = [
    # ---- schema layer
    M("wrong template enum", "schema", "SCHEMA", _set(lambda s: s.__setitem__("template", "template.home"))),
    M("missing motion on a node", "schema", "SCHEMA", _set(lambda s: node(s, "hero.course-intro").pop("motion"))),
    M("missing reducedMotionFallback", "schema", "SCHEMA", _set(lambda s: node(s, "list.numbered-topics")["motion"].pop("reducedMotionFallback"))),
    M("wrong reducedMotionFallback value", "schema", "SCHEMA", _set(lambda s: node(s, "hero.course-intro")["motion"].__setitem__("reducedMotionFallback", "static-single-frame"))),
    M("invented motion field", "schema", "SCHEMA", _set(lambda s: node(s, "hero.course-intro")["motion"].__setitem__("inventedAnimation", "parallax"))),
    M("webgl pattern on hero", "schema", "SCHEMA", _set(lambda s: node(s, "hero.course-intro")["motion"]["patterns"].append("webgl-solve"))),
    M("invented marquee section", "schema", "NO_MARQUEE_SECTION", _set(lambda s: s["nodes"].insert(6, {"section": "marquee.ticker", "variant": "default", "content": {"text": "x"}, "motion": {"patterns": ["alpha-fade"], "reducedMotionFallback": "final-state-instant"}}))),
    M("invented variant", "schema", "SCHEMA", _set(lambda s: node(s, "content.block-pairs", "feature-pairs").__setitem__("variant", "testimonials"))),
    M("extra content field", "schema", "SCHEMA", _set(lambda s: node(s, "hero.course-intro")["content"].__setitem__("backgroundVideo", "x"))),
    M("missing required content field", "schema", "SCHEMA", _set(lambda s: node(s, "form.waitlist")["content"].pop("action"))),
    M("cta href retargeted", "schema", "SCHEMA", _set(lambda s: node(s, "hero.course-intro")["content"]["cta"].__setitem__("href", "https://example.test"))),
    M("anchorId changed", "schema", "SCHEMA", _set(lambda s: node(s, "form.waitlist").__setitem__("anchorId", "join"))),
    M("invented assetRole", "schema", "SCHEMA", _set(lambda s: node(s, "shell.nav")["content"]["logo"].__setitem__("assetRole", "brand.mascot"))),
    M("assetRole swapped to another valid role", "schema", "SCHEMA", _set(lambda s: node(s, "shell.nav")["content"]["logo"].__setitem__("assetRole", "icon.arrow"))),
    M("discord link made visible", "schema", "SCHEMA", _set(lambda s: node(s, "shell.nav")["content"]["communityLink"].__setitem__("hidden", False))),
    M("timeline column count changed", "schema", "SCHEMA", _set(lambda s: node(s, "content.block-pairs", "pitch-timeline")["content"]["timeline"]["columns"].pop())),
    # ---- structural
    M("duplicate (section,variant) node", "structural", "ONE_PER_PAGE_BY_SECTION_VARIANT", _set(lambda s: s["nodes"].insert(4, copy.deepcopy(node(s, "content.block-pairs", "feature-pairs"))))),
    M("removed mandatory form", "structural", "TEMPLATE_SEQUENCE_MATCH", _set(lambda s: s["nodes"].pop(idx(s, "form.waitlist")))),
    M("removed form -> CTA target gone", "structural", "CTA_TARGETS_FORM", _set(lambda s: s["nodes"].pop(idx(s, "form.waitlist")))),
    M("footer moved before form", "structural", "FORM_PRECEDES_FOOTER", _set(lambda s: s["nodes"].insert(idx(s, "form.waitlist"), s["nodes"].pop(idx(s, "shell.footer-wordmark"))))),
    M("nav not first", "structural", "NAV_FIRST", _set(lambda s: s["nodes"].insert(1, s["nodes"].pop(0)))),
    M("hero not after nav", "structural", "HERO_FOLLOWS_NAV", _set(lambda s: s["nodes"].insert(1, s["nodes"].pop(idx(s, "list.numbered-topics"))))),
    M("webgl layer not last", "structural", "WEBGL_LAYER_LAST", _set(lambda s: s["nodes"].insert(1, s["nodes"].pop()))),
    M("footer not before layer", "structural", "FOOTER_PRECEDES_LAYER", _set(lambda s: s["nodes"].insert(idx(s, "form.waitlist"), s["nodes"].pop(idx(s, "shell.footer-wordmark"))))),
    M("variants swapped (template mismatch)", "structural", "TEMPLATE_SEQUENCE_MATCH", _set(lambda s: s["nodes"].insert(idx(s, "content.block-pairs", "feature-pairs"), s["nodes"].pop(idx(s, "content.block-pairs", "pitch-timeline"))))),
    M("evidence-reference on a non-real route", "structural", "TEMPLATE_SEQUENCE_MATCH", _set(lambda s: s.__setitem__("route", "/pricing"))),
    M("footer link to missing anchor", "structural", "FOOTER_NAV_ANCHORS_RESOLVE", _set(lambda s: node(s, "shell.footer-wordmark")["content"]["siteNav"]["links"].__setitem__(2, {"label": "PRICING", "href": "#pricing"}))),
    M("behind-canvas words without layer", "structural", "BEHIND_CANVAS_REQUIRES_LAYER", _set(lambda s: s["nodes"].pop(idx(s, "layer.webgl-object")))),
    # ---- runtime word budgets
    M("maxWords overflow: hero eyebrow", "runtime", "MAX_WORDS", _set(lambda s: node(s, "hero.course-intro")["content"].__setitem__("eyebrow", "A VERY LONG EYEBROW THAT KEEPS GOING ON AND ON"))),
    M("maxWords overflow: list item", "runtime", "MAX_WORDS", _set(lambda s: node(s, "list.numbered-topics")["content"]["items"][0].__setitem__("text", "API AND DATA AND MORE STUFF"))),
    M("maxWords overflow: text-block body", "runtime", "MAX_WORDS", _set(lambda s: node(s, "content.block-pairs", "feature-pairs")["content"]["rows"][1]["right"].__setitem__("body", " ".join(["word"] * 60)))),
    M("maxWords overflow: meta description", "runtime", "MAX_WORDS", _set(lambda s: s["meta"].__setitem__("description", " ".join(["word"] * 60)))),
    # ---- asset / compliance
    M("live MailChimp endpoint in form action", "compliance", "ASSET_REF_DENYLIST", _set(lambda s: node(s, "form.waitlist")["content"]["action"].__setitem__("ref", "placeholder:https://ooo.us21.list-manage.com/subscribe/post"))),
    M("form action source generated", "compliance", "ASSET_SOURCE_POLICY", _set(lambda s: node(s, "form.waitlist")["content"]["action"].update({"source": "generated", "ref": "generated:endpoint"}))),
    M("logo generated (must-not-reproduce)", "compliance", "ASSET_SOURCE_POLICY", _set(lambda s: node(s, "shell.nav")["content"]["logo"].update({"source": "generated", "ref": "generated:logo"}))),
    M("real cube model filename", "compliance", "ASSET_REF_DENYLIST", _set(lambda s: node(s, "layer.webgl-object")["content"]["model"].__setitem__("ref", "placeholder:cube8.glb"))),
    M("real umami website id", "compliance", "ASSET_REF_DENYLIST", _set(lambda s: s["meta"]["analytics"].__setitem__("ref", "placeholder:13ed4638-a8ba-4623-9987-1f6112450739"))),
    M("commercial font shipped as placeholder", "compliance", "ASSET_SOURCE_POLICY", _set(lambda s: s["fonts"]["sans"].__setitem__("source", "placeholder"))),
    M("ref prefix does not match source", "compliance", "ASSET_SOURCE_POLICY", _set(lambda s: node(s, "shell.nav")["content"]["logo"].__setitem__("ref", "https://example.test/logo.png"))),
    M("generated page keeps real wordmark", "compliance", "BRAND_PASSOFF", lambda s: (lambda g: (node(g, "shell.footer-wordmark")["content"].__setitem__("wordmark", [{"text": "THE", "layer": "front"}, {"text": "CODE", "layer": "behind-canvas-deep"}, {"text": "FLOW", "layer": "behind-canvas"}, {"text": "CO", "layer": "front"}]), g)[1])(generated_control(s))),
    M("generated page keeps author domain", "compliance", "BRAND_PASSOFF", lambda s: (lambda g: (node(g, "shell.footer-wordmark")["content"]["credit"].__setitem__("linkLabel", "HTTPS://FEDERIC.OOO"), g)[1])(generated_control(s))),
    M("generated page keeps real title", "compliance", "BRAND_PASSOFF", lambda s: (lambda g: (g["meta"].__setitem__("title", "Join Waitlist — thecodeflow.co"), g)[1])(generated_control(s))),
    # pinned-value mutations: a DIFFERENT BUT VALID policy (enum membership alone cannot catch these)
    M("pinned: form endpoint policy -> may-generate-new", "pinned", "PINNED_POLICY", lambda s: s,
      lambda r: r["roles"]["roles"]["endpoint.form-action"].__setitem__("generationPolicy", "may-generate-new")),
    M("pinned: logo policy -> may-generate-new", "pinned", "PINNED_POLICY", lambda s: s,
      lambda r: r["roles"]["roles"]["brand.logo-mark"].__setitem__("generationPolicy", "may-generate-new")),
    M("pinned: analytics policy -> must-not-reproduce", "pinned", "PINNED_POLICY", lambda s: s,
      lambda r: r["roles"]["roles"]["endpoint.analytics"].__setitem__("generationPolicy", "must-not-reproduce")),
    M("pinned: commercial font -> may-generate-new", "pinned", "PINNED_POLICY", lambda s: s,
      lambda r: r["roles"]["roles"]["font.commercial-sans"].__setitem__("generationPolicy", "may-generate-new")),
    M("pinned: cube model unpinned", "pinned", "PINNED_POLICY", lambda s: s,
      lambda r: r["roles"]["roles"]["webgl.cube-model"].__setitem__("pinned", False)),
    # ---- motion contract (validator layer, contract file mutated to prove the validator reads it)
    M("section contract narrows allowed motion", "motion", "MOTION_PATTERNS_ALLOWED", lambda s: s,
      lambda r: r["contracts"][("hero.course-intro", "default")]["motion"].__setitem__("allowedPatterns", ["alpha-fade"])),
    # the 'cta' duplicate is only tolerated because it is documented; withdraw the documentation and it must become an error
    M("undocumented duplicate anchor", "structural", "DUPLICATE_ANCHOR_ONLY_DOCUMENTED", lambda s: s,
      lambda r: sv.DOCUMENTED_DUPLICATE_ANCHORS.pop("cta")),
]


def run():
    fails = 0
    # ---- controls
    controls = [("unmodified example (evidence-reference)", copy.deepcopy(EXAMPLE))]
    # one synthesized control per template: the example's nodes re-ordered to that template's own node list
    for tid, t in BASE_REPO["templates"]["templates"].items():
        s = copy.deepcopy(EXAMPLE)
        s["template"] = tid
        pool = {(n["section"], n["variant"]): n for n in s["nodes"]}
        s["nodes"] = [copy.deepcopy(pool[(tn["section"], tn["variant"])]) for tn in t["nodes"]]
        controls.append(("template control: %s" % tid, s))
    controls.append(("generated-provenance neutral copy", generated_control(copy.deepcopy(EXAMPLE))))
    for name, s in controls:
        errs, warns = sv.validate(s, BASE_REPO)
        ok = not errs
        fails += not ok
        print("%s CONTROL  %-52s errors=%d warnings=%d" % ("PASS" if ok else "FAIL", name, len(errs), len(warns)))
        for e in errs:
            print("      ", e)
    # ---- mutations
    for name, cat, rule, fn, repo_fn in MUTATIONS:
        s = fn(copy.deepcopy(EXAMPLE))
        repo = copy.deepcopy(BASE_REPO)
        saved = copy.deepcopy(sv.DOCUMENTED_DUPLICATE_ANCHORS)
        if repo_fn:
            repo_fn(repo)
        try:
            errs, warns = sv.validate(s, repo)
        finally:
            sv.DOCUMENTED_DUPLICATE_ANCHORS.clear()
            sv.DOCUMENTED_DUPLICATE_ANCHORS.update(saved)
        hit = [e for e in errs if e[0] == rule]
        ok = bool(hit)
        fails += not ok
        print("%s REJECT   [%-10s] %-48s -> %s%s" % ("PASS" if ok else "FAIL", cat, name, rule,
              "" if ok else "  (got: %s)" % sorted({e[0] for e in errs})))
    print("\n%d mutations, %d controls, %d failure(s)" % (len(MUTATIONS), len(controls), fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(run())
