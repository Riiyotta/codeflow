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

def _mod(name, rel):
    spec_ = importlib.util.spec_from_file_location(name, os.path.join(REPO, rel))
    m = importlib.util.module_from_spec(spec_)
    spec_.loader.exec_module(m)
    return m


sv = _mod("semantic_validate", os.path.join("schema", "semantic_validate.py"))
wg = _mod("wrapper_gate", os.path.join("extraction", "wrapper_gate.py"))

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


def sec(r, sid):
    return r["sections"][sid]


def _syn_section(r, new_id, **over):
    """Add a synthetic section (a copy of shell.nav) so new-section rules can be exercised."""
    c = copy.deepcopy(sec(r, "shell.nav"))
    c["id"] = new_id
    c["semantic"] = {"id": new_id, "category": over.pop("category", "shell")}
    c["source"]["lines"] = "100-120"
    c.update(over)
    r["sections"][new_id] = c


def _setsec(sid, path, value):
    """repo_fn: set contract[sid][path[0]][path[1]]... = value."""
    def f(r):
        o = sec(r, sid)
        for k in path[:-1]:
            o = o[k]
        o[path[-1]] = value
    return f


def _delsec(sid, path):
    def f(r):
        o = sec(r, sid)
        for k in path[:-1]:
            o = o[k]
        del o[path[-1]]
    return f


def _contract_mut(name, cat, rule, repo_fn):
    return M(name, cat, rule, lambda s: s, repo_fn)


def _dup_source(r):
    r["sections"]["hero.course-intro"]["source"].update({k: r["sections"]["shell.nav"]["source"][k] for k in ("file", "lines")})


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
    M("missing required content field", "schema", "SCHEMA", _set(lambda s: node(s, "cta.waitlist-form")["content"].pop("action"))),
    M("cta href retargeted", "schema", "SCHEMA", _set(lambda s: node(s, "hero.course-intro")["content"]["cta"].__setitem__("href", "https://example.test"))),
    M("anchorId changed", "schema", "SCHEMA", _set(lambda s: node(s, "cta.waitlist-form").__setitem__("anchorId", "join"))),
    M("invented assetRole", "schema", "SCHEMA", _set(lambda s: node(s, "shell.nav")["content"]["logo"].__setitem__("assetRole", "brand.mascot"))),
    M("assetRole swapped to another valid role", "schema", "SCHEMA", _set(lambda s: node(s, "shell.nav")["content"]["logo"].__setitem__("assetRole", "icon.arrow"))),
    M("discord link made visible", "schema", "SCHEMA", _set(lambda s: node(s, "shell.nav")["content"]["communityLink"].__setitem__("hidden", False))),
    M("timeline column count changed", "schema", "SCHEMA", _set(lambda s: node(s, "cta.pitch-timeline")["content"]["timeline"]["columns"].pop())),
    # ---- structural
    M("duplicate (section,variant) node", "structural", "ONE_PER_PAGE_BY_SECTION_VARIANT", _set(lambda s: s["nodes"].insert(4, copy.deepcopy(node(s, "content.block-pairs", "feature-pairs"))))),
    M("removed mandatory form", "structural", "TEMPLATE_SEQUENCE_MATCH", _set(lambda s: s["nodes"].pop(idx(s, "cta.waitlist-form")))),
    M("removed form -> CTA target gone", "structural", "CTA_TARGETS_FORM", _set(lambda s: s["nodes"].pop(idx(s, "cta.waitlist-form")))),
    M("footer moved before form", "structural", "FORM_PRECEDES_FOOTER", _set(lambda s: s["nodes"].insert(idx(s, "cta.waitlist-form"), s["nodes"].pop(idx(s, "shell.footer-wordmark"))))),
    M("nav not first", "structural", "NAV_FIRST", _set(lambda s: s["nodes"].insert(1, s["nodes"].pop(0)))),
    M("hero not after nav", "structural", "HERO_FOLLOWS_NAV", _set(lambda s: s["nodes"].insert(1, s["nodes"].pop(idx(s, "list.numbered-topics"))))),
    M("webgl layer not last", "structural", "WEBGL_LAYER_LAST", _set(lambda s: s["nodes"].insert(1, s["nodes"].pop()))),
    M("footer not before layer", "structural", "FOOTER_PRECEDES_LAYER", _set(lambda s: s["nodes"].insert(idx(s, "cta.waitlist-form"), s["nodes"].pop(idx(s, "shell.footer-wordmark"))))),
    M("adjacent sections swapped (template mismatch)", "structural", "TEMPLATE_SEQUENCE_MATCH", _set(lambda s: s["nodes"].insert(idx(s, "content.block-pairs", "feature-pairs"), s["nodes"].pop(idx(s, "cta.pitch-timeline"))))),
    M("evidence-reference on a non-real route", "structural", "TEMPLATE_SEQUENCE_MATCH", _set(lambda s: s.__setitem__("route", "/pricing"))),
    M("footer link to missing anchor", "structural", "FOOTER_NAV_ANCHORS_RESOLVE", _set(lambda s: node(s, "shell.footer-wordmark")["content"]["siteNav"]["links"].__setitem__(2, {"label": "PRICING", "href": "#pricing"}))),
    M("behind-canvas words without layer", "structural", "BEHIND_CANVAS_REQUIRES_LAYER", _set(lambda s: s["nodes"].pop(idx(s, "layer.webgl-object")))),
    # ---- runtime word budgets
    M("maxWords overflow: hero eyebrow", "runtime", "MAX_WORDS", _set(lambda s: node(s, "hero.course-intro")["content"].__setitem__("eyebrow", "A VERY LONG EYEBROW THAT KEEPS GOING ON AND ON"))),
    M("maxWords overflow: list item", "runtime", "MAX_WORDS", _set(lambda s: node(s, "list.numbered-topics")["content"]["items"][0].__setitem__("text", "API AND DATA AND MORE STUFF"))),
    M("maxWords overflow: text-block body", "runtime", "MAX_WORDS", _set(lambda s: node(s, "content.block-pairs", "feature-pairs")["content"]["rows"][1]["right"].__setitem__("body", " ".join(["word"] * 60)))),
    M("maxWords overflow: meta description", "runtime", "MAX_WORDS", _set(lambda s: s["meta"].__setitem__("description", " ".join(["word"] * 60)))),
    # ---- asset / compliance
    M("live MailChimp endpoint in form action", "compliance", "ASSET_REF_DENYLIST", _set(lambda s: node(s, "cta.waitlist-form")["content"]["action"].__setitem__("ref", "placeholder:https://ooo.us21.list-manage.com/subscribe/post"))),
    M("form action source generated", "compliance", "ASSET_SOURCE_POLICY", _set(lambda s: node(s, "cta.waitlist-form")["content"]["action"].update({"source": "generated", "ref": "generated:endpoint"}))),
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
    # ---- section contracts: retrieval eligibility (utility/runtime UI is excluded, everything else is not)
    _contract_mut("retrieval: WebGL overlay made retrievable", "retrieval", "RETRIEVAL_ELIGIBILITY_PINNED", _setsec("layer.webgl-object", ["retrievalEligible"], True)),
    _contract_mut("retrieval: hero marked ineligible (with a valid reason)", "retrieval", "RETRIEVAL_ELIGIBILITY_PINNED",
                  lambda r: sec(r, "hero.course-intro").update({"retrievalEligible": False, "retrievalReason": "Pretend this hero is utility chrome so it never reaches retrieval."})),
    _contract_mut("retrieval: overlay reason removed", "retrieval", "SECTION_CONTRACT_SCHEMA", _delsec("layer.webgl-object", ["retrievalReason"])),
    _contract_mut("retrieval: overlay reason too short (<30)", "retrieval", "SECTION_CONTRACT_SCHEMA", _setsec("layer.webgl-object", ["retrievalReason"], "decorative canvas")),
    _contract_mut("retrieval: overlay reason too short (pinned rule too)", "retrieval", "RETRIEVAL_ELIGIBILITY_PINNED", _setsec("layer.webgl-object", ["retrievalReason"], "decorative canvas")),
    _contract_mut("retrieval: flag is a string, not a boolean", "retrieval", "SECTION_CONTRACT_SCHEMA", _setsec("layer.webgl-object", ["retrievalEligible"], "false")),
    _contract_mut("retrieval: flag is null", "retrieval", "SECTION_CONTRACT_SCHEMA", _setsec("layer.webgl-object", ["retrievalEligible"], None)),
    _contract_mut("retrieval: reason present on an eligible section", "retrieval", "SECTION_CONTRACT_SCHEMA", _setsec("hero.course-intro", ["retrievalReason"], "A reason that has no business on an eligible section.")),
    _contract_mut("retrieval: cookie-consent section left eligible", "retrieval", "RETRIEVAL_ELIGIBILITY_PINNED", lambda r: _syn_section(r, "overlay.cookie-consent", category="layer")),
    _contract_mut("retrieval: success-toast id left eligible", "retrieval", "RETRIEVAL_ELIGIBILITY_PINNED", lambda r: _syn_section(r, "shell.success-toast")),
    # ---- section contracts: taxonomy (semantic) and conversion classing
    _contract_mut("taxonomy: waitlist form demoted to content", "taxonomy", "SECTION_TAXONOMY_PINNED", _setsec("cta.waitlist-form", ["semantic", "category"], "content")),
    _contract_mut("taxonomy: waitlist form demoted -> conversion rule", "taxonomy", "CONVERSION_BLOCK_CLASSED_CTA", _setsec("cta.waitlist-form", ["semantic", "category"], "content")),
    _contract_mut("taxonomy: pitch block demoted to list -> conversion rule", "taxonomy", "CONVERSION_BLOCK_CLASSED_CTA", _setsec("cta.pitch-timeline", ["semantic", "category"], "list")),
    _contract_mut("taxonomy: CTA field hidden in generic content block", "taxonomy", "CONVERSION_BLOCK_CLASSED_CTA", lambda r: sec(r, "content.block-pairs")["variants"]["feature-pairs"]["contentFields"].append("cta")),
    _contract_mut("taxonomy: category outside the closed enum (features)", "taxonomy", "SECTION_CONTRACT_SCHEMA", _setsec("content.block-pairs", ["semantic", "category"], "features")),
    _contract_mut("taxonomy: semantic.id differs from contract id", "taxonomy", "SECTION_TAXONOMY_PINNED", _setsec("hero.course-intro", ["semantic", "id"], "hero.something-else")),
    _contract_mut("taxonomy: category differs from id prefix", "taxonomy", "SECTION_TAXONOMY_PINNED", _setsec("list.numbered-topics", ["semantic", "category"], "content")),
    _contract_mut("taxonomy: new section missing from the pinned table", "taxonomy", "SECTION_TAXONOMY_PINNED", lambda r: _syn_section(r, "shell.banner-strip")),
    _contract_mut("taxonomy: semantic object removed", "taxonomy", "SECTION_CONTRACT_SCHEMA", _delsec("hero.course-intro", ["semantic"])),
    _contract_mut("taxonomy: legacy top-level category field re-added", "taxonomy", "SECTION_CONTRACT_SCHEMA", _setsec("hero.course-intro", ["category"], "hero")),
    # ---- section contracts: provenance (source) kept separate from taxonomy (semantic)
    _contract_mut("source: unknown field in source", "source", "SECTION_CONTRACT_SCHEMA", _setsec("hero.course-intro", ["source", "selector"], "header#intro")),
    _contract_mut("source: taxonomy field leaked into source", "source", "SECTION_CONTRACT_SCHEMA", _setsec("hero.course-intro", ["source", "category"], "hero")),
    _contract_mut("source: provenance field leaked into semantic", "source", "SECTION_CONTRACT_SCHEMA", _setsec("hero.course-intro", ["semantic", "file"], "src/components/Hero.jsx")),
    _contract_mut("source: tag removed", "source", "SECTION_CONTRACT_SCHEMA", _delsec("hero.course-intro", ["source", "tag"])),
    _contract_mut("source: tag outside the closed enum", "source", "SECTION_CONTRACT_SCHEMA", _setsec("hero.course-intro", ["source", "tag"], "marquee")),
    _contract_mut("source: absolute file path", "source", "SECTION_CONTRACT_SCHEMA", _setsec("hero.course-intro", ["source", "file"], "/srv/app/src/components/Hero.jsx")),
    _contract_mut("source: file escapes the project", "source", "SECTION_CONTRACT_SCHEMA", _setsec("hero.course-intro", ["source", "file"], "src/../../secret.jsx")),
    _contract_mut("source: reversed line range", "source", "SECTION_SOURCE_STRUCTURE", _setsec("hero.course-intro", ["source", "lines"], "38-15")),
    _contract_mut("source: malformed line range", "source", "SECTION_CONTRACT_SCHEMA", _setsec("hero.course-intro", ["source", "lines"], "15")),
    _contract_mut("source: id disagrees with the variant anchorId", "source", "SECTION_SOURCE_STRUCTURE", _setsec("hero.course-intro", ["source", "id"], "hero")),
    _contract_mut("source: two sections claim the same range", "source", "SECTION_SOURCE_STRUCTURE", _dup_source),
]


# ---- whole-page-wrapper gate cases: (name, expected code, expected severity, mutate(heights, whitelist))
WG_NODES, WG_CATS, WG_HEIGHTS, WG_WHITELIST = wg.load_inputs(REPO)
HK, LK, FK = "hero.course-intro/default", "list.numbered-topics/default", "cta.waitlist-form/default"


def _h(key, px):
    """Set one section's height and keep pageHeight consistent so only the intended rule can fire."""
    def f(h, w):
        h["pageHeight"] += px - h["sections"][key]["heightPx"] if h["sections"][key]["inFlow"] else 0
        h["sections"][key]["heightPx"] = px
    return f


def _chain(*fns):
    def f(h, w):
        for fn in fns:
            fn(h, w)
    return f


def _wl(key, rules, cap, just="Reviewed: this section legitimately spans the whole fold on this page type.", reviewer="agent-attestation:test-reviewer"):
    sec_, var = key.split("/")
    return lambda h, w: w.append({"section": sec_, "variant": var, "rules": rules, "maxHeightPx": cap, "justification": just, "reviewer": reviewer, "reviewedOn": "2026-10-23"})


def _only_inflow(h, w):
    for k, m in h["sections"].items():
        m["inFlow"] = k in (HK, LK)
    h["pageHeight"] = sum(m["heightPx"] for m in h["sections"].values() if m["inFlow"])


def _drop(key):
    return lambda h, w: h["sections"].pop(key)


WRAPPER_CASES = [
    ("hero 1900px (> 1800)", "HERO_HEIGHT_WARN", "warn", _h(HK, 1900)),
    ("hero 3100px (> 3000)", "HERO_HEIGHT_FAIL", "error", _h(HK, 3100)),
    ("hero 3100px, reviewed whitelist cap 3200", "HERO_HEIGHT_FAIL_WHITELISTED", "warn", _chain(_h(HK, 3100), _wl(HK, ["HERO_HEIGHT_FAIL"], 3200))),
    ("hero 3300px exceeds whitelist cap 3200", "HERO_HEIGHT_FAIL", "error", _chain(_h(HK, 3300), _wl(HK, ["HERO_HEIGHT_FAIL"], 3200))),
    ("whitelist for the wrong rule does not exempt", "HERO_HEIGHT_FAIL", "error", _chain(_h(HK, 3100), _wl(HK, ["SECTION_SHARE_FAIL"], 3200))),
    ("whitelist justification too short", "WHITELIST_INVALID", "error", _chain(_h(HK, 3100), _wl(HK, ["HERO_HEIGHT_FAIL"], 3200, just="trust me"))),
    ("whitelist reviewer is not human:/agent-attestation:", "WHITELIST_INVALID", "error", _chain(_h(HK, 3100), _wl(HK, ["HERO_HEIGHT_FAIL"], 3200, reviewer="looks fine"))),
    ("whitelist entry for a non-node", "WHITELIST_INVALID", "error", _wl("hero.nope/default", ["HERO_HEIGHT_FAIL"], 3200)),
    ("whitelist entry that exempts nothing", "WHITELIST_UNUSED", "warn", _wl(HK, ["HERO_HEIGHT_FAIL"], 3200)),
    ("one section 51% of in-flow height", "SECTION_SHARE_WARN", "warn", _h(LK, 5000)),
    ("one section 65% of in-flow height", "SECTION_SHARE_FAIL", "error", _h(LK, 9000)),
    ("65% share, reviewed whitelist cap 9500", "SECTION_SHARE_FAIL_WHITELISTED", "warn", _chain(_h(LK, 9000), _wl(LK, ["SECTION_SHARE_FAIL"], 9500))),
    ("missing measurement for a section", "MEASUREMENT_MISSING", "error", _drop(FK)),
    ("measurement without a height", "MEASUREMENT_MISSING", "error", lambda h, w: h["sections"][FK].__setitem__("heightPx", None)),
    ("stale measurement for a removed section", "MEASUREMENT_MISSING", "error", lambda h, w: h["sections"].__setitem__("cta.gone/default", dict(h["sections"][FK]))),
    ("sectionHeights absent altogether", "MEASUREMENT_MISSING", "error", lambda h, w: h.pop("sections")),
    ("measured at the wrong viewport width", "MEASUREMENT_INCONSISTENT", "error", lambda h, w: h["viewport"].__setitem__("width", 1280)),
    ("heights do not add up to pageHeight", "MEASUREMENT_INCONSISTENT", "error", lambda h, w: h.__setitem__("pageHeight", 9999)),
]
# control: with only 2 in-flow sections the share rule must be skipped (a 2-section page is always >50%)
WRAPPER_NEGATIVES = [("2 in-flow sections: share rule skipped, no share finding", ("SECTION_SHARE_WARN", "SECTION_SHARE_FAIL"), _only_inflow)]


def run_wrapper():
    bad = 0
    e, w, _ = wg.evaluate(WG_NODES, WG_CATS, copy.deepcopy(WG_HEIGHTS), copy.deepcopy(WG_WHITELIST))
    ok = not e and not w
    bad += not ok
    print("%s CONTROL  %-52s errors=%d warnings=%d" % ("PASS" if ok else "FAIL", "wrapper gate on the measured page", len(e), len(w)))
    for name, code, sev, fn in WRAPPER_CASES:
        h, wl = copy.deepcopy(WG_HEIGHTS), copy.deepcopy(WG_WHITELIST)
        fn(h, wl)
        e, w, _ = wg.evaluate(WG_NODES, WG_CATS, h, wl)
        got = [x for x in (e if sev == "error" else w) if x[0] == code]
        ok = bool(got)
        # a warning case must not also be an error, except where the case is about a bad whitelist
        if sev == "warn" and e and not code.startswith("WHITELIST"):
            ok = False
        bad += not ok
        print("%s %-7s [wrapper   ] %-48s -> %s%s" % ("PASS" if ok else "FAIL", "REJECT" if sev == "error" else "FLAG", name, code,
              "" if ok else "  (errors=%s warns=%s)" % (sorted({x[0] for x in e}), sorted({x[0] for x in w}))))
    for name, codes, fn in WRAPPER_NEGATIVES:
        h, wl = copy.deepcopy(WG_HEIGHTS), copy.deepcopy(WG_WHITELIST)
        fn(h, wl)
        e, w, info = wg.evaluate(WG_NODES, WG_CATS, h, wl)
        ok = not [x for x in e + w if x[0] in codes] and not e and any("skipped" in i for i in info)
        bad += not ok
        print("%s ACCEPT   [wrapper   ] %-48s" % ("PASS" if ok else "FAIL", name))
    return bad, len(WRAPPER_CASES) + len(WRAPPER_NEGATIVES)


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
    wbad, wn = run_wrapper()
    fails += wbad
    controls.append(None)  # the wrapper-gate control
    print("\n%d mutations (%d contract/page + %d wrapper-gate cases), %d controls, %d failure(s)" % (len(MUTATIONS) + wn, len(MUTATIONS), wn, len(controls), fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(run())
