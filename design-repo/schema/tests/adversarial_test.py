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
GEN_PATH = os.path.join(REPO, "schema", "examples", "generated.template.waitlist-landing.pagespec.json")
with open(GEN_PATH, encoding="utf-8") as f:
    GENERATED = json.load(f)
BASE_REPO = sv.load_repo(REPO)


def node(s, section, variant=None):
    for n in s["nodes"]:
        if n["section"] == section and (variant is None or n["variant"] == variant):
            return n
    raise KeyError(section)


def idx(s, section, variant=None):
    return s["nodes"].index(node(s, section, variant))


# (name, category, expected rule, mutate(spec) -> spec, mutate_repo(repo) or None, base)
# base is "reference" (schema/example.pagespec.json) or "generated" (schema/examples/generated.*.pagespec.json)
def M(name, cat, rule, fn, repo_fn=None, base="reference"):
    return (name, cat, rule, fn, repo_fn, base)


def GM(name, cat, rule, fn, repo_fn=None):
    return M(name, cat, rule, fn, repo_fn, "generated")


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


# ======================================================================================================
# Token policy (tokens/llm/token-catalog.json + token-policy.json) and reference/generated mode
# ======================================================================================================
def tok(slot, value):
    return lambda s: s["tokens"].__setitem__(slot, value)


def tokd(slot):
    return lambda s: s["tokens"].pop(slot)


def toks(**kw):
    return lambda s: s["tokens"].update(kw)


def repo_cat(fn):
    return lambda r: fn(r["catalog"])


def repo_pol(fn):
    return lambda r: fn(r["policy"])


def _nav(s):
    return node(s, "shell.nav")["content"]


def _foot(s):
    return node(s, "shell.footer-wordmark")["content"]


def _hero(s):
    return node(s, "hero.course-intro")["content"]


def _role(path_fn, role):
    return lambda s: path_fn(s).__setitem__("assetRole", role)


def _set_label(fn, key, value):
    return lambda s: fn(s).__setitem__(key, value)


def _flip_to_generated(s):
    s["mode"] = "generated"
    s["contentProvenance"] = "generated"


def _community(s):
    _nav(s)["communityLink"] = {"icon": {"assetRole": "icon.discord", "source": "placeholder", "ref": "placeholder:community-icon"}, "hidden": True}


def _drop_role(role):
    return lambda r: r["roles"]["roles"].pop(role)


def _avail(role, value):
    return lambda r: r["roles"]["roles"][role].__setitem__("availability", value)


def _new_role(r):
    r["roles"]["roles"]["brand.logo-extra"] = dict(r["roles"]["roles"]["brand.logo-placeholder"])


def _theme_rename(c):
    c["themes"]["light"] = c["themes"].pop("dark")


def _theme_drop(token):
    return lambda c: c["themes"]["dark"]["semanticTokens"].remove(token)


def _theme_resolve(token, value):
    return lambda c: c["themes"]["dark"]["resolves"].__setitem__(token, value)


TOKEN_MUTATIONS = [
    # ---- unknown tokens
    M("unknown semantic surface token", "tokens", "TOKEN_UNKNOWN", _set(tok("surface", "semantic.surface.nope"))),
    M("unknown text token", "tokens", "TOKEN_UNKNOWN", _set(tok("text", "semantic.text.shiny"))),
    M("unknown border token", "tokens", "TOKEN_UNKNOWN", _set(tok("border", "semantic.border.glow"))),
    M("unknown spacing token", "tokens", "TOKEN_UNKNOWN", _set(tok("sectionPadding", "spacing.section.huge"))),
    M("unknown font token (serif)", "tokens", "TOKEN_UNKNOWN", _set(tok("fontSans", "typography.fontFamily.serif"))),
    M("unknown radius token", "tokens", "TOKEN_UNKNOWN", _set(tok("buttonRadius", "radius.square"))),
    M("token slot holds prose, not a path", "tokens", "TOKEN_UNKNOWN", _set(tok("surface", "the page background"))),
    M("token slot holds a bare word", "tokens", "TOKEN_UNKNOWN", _set(tok("surface", "page"))),
    M("token slot holds a group, not a leaf token", "tokens", "TOKEN_UNKNOWN", _set(tok("surface", "semantic.surface"))),
    M("token path with the wrong case", "tokens", "TOKEN_UNKNOWN", _set(tok("surface", "semantic.surface.Page"))),
    M("token path with a trailing dot", "tokens", "TOKEN_UNKNOWN", _set(tok("text", "semantic.text.primary."))),
    GM("generated page: unknown token", "tokens", "TOKEN_UNKNOWN", _set(tok("surface", "semantic.surface.nope"))),
    M("catalog loses the token the example uses", "tokens", "TOKEN_UNKNOWN", lambda s: s, repo_cat(lambda c: c["tokens"].pop("semantic.text.primary"))),
    M("catalog loses the WebGL clear colour", "tokens", "TOKEN_UNKNOWN", lambda s: s, repo_cat(lambda c: c["tokens"].pop("color.webgl.clear"))),
    # ---- raw colours
    M("raw hex colour (6 digits) in surface", "tokens", "TOKEN_RAW_COLOR", _set(tok("surface", "#0c0c0c"))),
    M("raw hex colour (3 digits) in text", "tokens", "TOKEN_RAW_COLOR", _set(tok("text", "#fff"))),
    M("raw hex colour (upper-case) in border", "tokens", "TOKEN_RAW_COLOR", _set(tok("border", "#F5D0E6"))),
    M("raw hex colour with alpha (8 digits)", "tokens", "TOKEN_RAW_COLOR", _set(tok("surface", "#0c0c0c80"))),
    M("raw rgb() colour", "tokens", "TOKEN_RAW_COLOR", _set(tok("surface", "rgb(12, 12, 12)"))),
    M("raw rgba() colour", "tokens", "TOKEN_RAW_COLOR", _set(tok("text", "rgba(245,208,230,0.9)"))),
    M("raw hsl() colour", "tokens", "TOKEN_RAW_COLOR", _set(tok("surface", "hsl(0 0% 5%)"))),
    M("raw oklch() colour", "tokens", "TOKEN_RAW_COLOR", _set(tok("text", "oklch(0.9 0.05 340)"))),
    M("raw color-mix() colour", "tokens", "TOKEN_RAW_COLOR", _set(tok("border", "color-mix(in srgb, red, blue)"))),
    M("CSS colour name (black)", "tokens", "TOKEN_RAW_COLOR", _set(tok("surface", "black"))),
    M("CSS colour name (HotPink, mixed case)", "tokens", "TOKEN_RAW_COLOR", _set(tok("text", "HotPink"))),
    M("CSS keyword transparent", "tokens", "TOKEN_RAW_COLOR", _set(tok("surface", "transparent"))),
    M("CSS keyword currentColor", "tokens", "TOKEN_RAW_COLOR", _set(tok("border", "currentColor"))),
    M("raw hex colour in a spacing slot", "tokens", "TOKEN_RAW_COLOR", _set(tok("sectionPadding", "#123456"))),
    M("raw hex colour in a font slot", "tokens", "TOKEN_RAW_COLOR", _set(tok("fontMono", "#123456"))),
    M("raw hex colour with surrounding space", "tokens", "TOKEN_RAW_COLOR", _set(tok("surface", "  #0c0c0c  "))),
    GM("generated page: raw hex colour", "tokens", "TOKEN_RAW_COLOR", _set(tok("surface", "#0c0c0c"))),
    # ---- arbitrary spacing
    M("arbitrary spacing in px", "tokens", "TOKEN_ARBITRARY_SPACING", _set(tok("sectionPadding", "24px"))),
    M("arbitrary spacing in rem", "tokens", "TOKEN_ARBITRARY_SPACING", _set(tok("sectionPadding", "2rem"))),
    M("the raw value of spacing.section.padding copied out of the token file", "tokens", "TOKEN_ARBITRARY_SPACING", _set(tok("sectionPadding", "10vh 3vw 5vh"))),
    M("arbitrary spacing calc()", "tokens", "TOKEN_ARBITRARY_SPACING", _set(tok("sectionPadding", "calc(1rem + 2vw)"))),
    M("arbitrary spacing clamp()", "tokens", "TOKEN_ARBITRARY_SPACING", _set(tok("sectionPadding", "clamp(1rem, 2vw, 3rem)"))),
    M("arbitrary spacing zero", "tokens", "TOKEN_ARBITRARY_SPACING", _set(tok("sectionPadding", "0"))),
    M("arbitrary spacing bare number", "tokens", "TOKEN_ARBITRARY_SPACING", _set(tok("sectionPadding", "8"))),
    M("arbitrary spacing percentage", "tokens", "TOKEN_ARBITRARY_SPACING", _set(tok("sectionPadding", "5%"))),
    M("arbitrary spacing with em", "tokens", "TOKEN_ARBITRARY_SPACING", _set(tok("sectionPadding", ".6em 1.2em"))),
    GM("generated page: arbitrary spacing", "tokens", "TOKEN_ARBITRARY_SPACING", _set(tok("sectionPadding", "16px"))),
    # ---- unsupported fonts
    M("unsupported font name (Comic Sans MS)", "tokens", "TOKEN_UNSUPPORTED_FONT", _set(tok("fontSans", "Comic Sans MS"))),
    M("commercial source font named directly (Helvetica Neue)", "tokens", "TOKEN_UNSUPPORTED_FONT", _set(tok("fontSans", "Helvetica Neue"))),
    M("commercial display font named directly", "tokens", "TOKEN_UNSUPPORTED_FONT", _set(tok("fontDisplay", "Helvetica Neue Condensed"))),
    M("font stack in the font slot", "tokens", "TOKEN_UNSUPPORTED_FONT", _set(tok("fontSans", "Inter, sans-serif"))),
    M("quoted font stack in the mono slot", "tokens", "TOKEN_UNSUPPORTED_FONT", _set(tok("fontMono", "\"Firacode\", monospace"))),
    M("system font name", "tokens", "TOKEN_UNSUPPORTED_FONT", _set(tok("fontSans", "Arial"))),
    M("generic family keyword", "tokens", "TOKEN_UNSUPPORTED_FONT", _set(tok("fontDisplay", "sans-serif"))),
    M("a length in a font slot", "tokens", "TOKEN_UNSUPPORTED_FONT", _set(tok("fontSans", "14px"))),
    M("mono slot with a different mono font", "tokens", "TOKEN_UNSUPPORTED_FONT", _set(tok("fontMono", "Courier New"))),
    GM("generated page: unsupported font", "tokens", "TOKEN_UNSUPPORTED_FONT", _set(tok("fontSans", "Comic Sans MS"))),
    # ---- slot / category mismatches
    M("font token in the surface slot", "tokens", "TOKEN_SLOT_MISMATCH", _set(tok("surface", "typography.fontFamily.sans"))),
    M("text token in the surface slot", "tokens", "TOKEN_SLOT_MISMATCH", _set(tok("surface", "semantic.text.primary"))),
    M("surface token in the text slot", "tokens", "TOKEN_SLOT_MISMATCH", _set(tok("text", "semantic.surface.page"))),
    M("list-valued flash colour as page surface", "tokens", "TOKEN_SLOT_MISMATCH", _set(tok("surface", "semantic.surface.solveFlash"))),
    M("foundation colour in a semantic slot", "tokens", "TOKEN_SLOT_MISMATCH", _set(tok("surface", "color.base.black"))),
    M("real semantic token the border slot does not accept", "tokens", "TOKEN_SLOT_MISMATCH", _set(tok("border", "semantic.line.rule"))),
    M("type role in the text slot", "tokens", "TOKEN_SLOT_MISMATCH", _set(tok("text", "typography.role.body"))),
    M("mono family in the sans slot", "tokens", "TOKEN_SLOT_MISMATCH", _set(tok("fontSans", "typography.fontFamily.mono"))),
    M("sans family in the mono slot", "tokens", "TOKEN_SLOT_MISMATCH", _set(tok("fontMono", "typography.fontFamily.sans"))),
    M("sans family in the display slot", "tokens", "TOKEN_SLOT_MISMATCH", _set(tok("fontDisplay", "typography.fontFamily.sans"))),
    M("spacing token in the radius slot", "tokens", "TOKEN_SLOT_MISMATCH", _set(tok("buttonRadius", "spacing.button.padding"))),
    M("real radius token the slot does not accept", "tokens", "TOKEN_SLOT_MISMATCH", _set(tok("buttonRadius", "radius.circle"))),
    M("radius token in the spacing slot", "tokens", "TOKEN_SLOT_MISMATCH", _set(tok("sectionPadding", "radius.pill"))),
    M("min-height spacing token in the padding slot", "tokens", "TOKEN_SLOT_MISMATCH", _set(tok("sectionPadding", "spacing.section.minHeight"))),
    M("font token whose assetRole disagrees with the fonts field", "tokens", "TOKEN_SLOT_MISMATCH", lambda s: s,
      repo_cat(lambda c: c["tokens"]["typography.fontFamily.sans"].__setitem__("assetRole", "font.mono"))),
    M("policy widened: surface slot loses its allow list", "tokens", "TOKEN_SLOT_MISMATCH", lambda s: s,
      repo_pol(lambda p: p["pageSpecTokenSlots"]["surface"].__setitem__("allow", ["semantic.surface.webglClear"]))),
    # ---- theme / combination
    M("text identical to surface (onButtonHover on page)", "tokens", "TOKEN_THEME_COMBINATION", _set(tok("text", "semantic.text.onButtonHover"))),
    M("text identical to surface (primary on buttonHover)", "tokens", "TOKEN_THEME_COMBINATION", _set(tok("surface", "semantic.surface.buttonHover"))),
    M("placeholder text on the pink surface (contrast about 2)", "tokens", "TOKEN_THEME_COMBINATION", _set(toks(surface="semantic.surface.buttonHover", text="semantic.text.placeholder"))),
    M("white submit text on the pink surface", "tokens", "TOKEN_THEME_COMBINATION", _set(toks(surface="semantic.surface.buttonHover", text="semantic.text.submit"))),
    M("near-identical surface and text (webglClear + onButtonHover)", "tokens", "TOKEN_THEME_COMBINATION", _set(toks(surface="semantic.surface.webglClear", text="semantic.text.onButtonHover"))),
    GM("generated page: text identical to surface", "tokens", "TOKEN_THEME_COMBINATION", _set(tok("text", "semantic.text.onButtonHover"))),
    M("theme missing from the catalog", "tokens", "TOKEN_THEME_COMBINATION", lambda s: s, repo_cat(_theme_rename)),
    M("theme no longer resolves the text token", "tokens", "TOKEN_THEME_COMBINATION", lambda s: s, repo_cat(_theme_drop("semantic.text.primary"))),
    M("theme no longer resolves the surface token", "tokens", "TOKEN_THEME_COMBINATION", lambda s: s, repo_cat(_theme_drop("semantic.surface.page"))),
    M("theme resolves text.primary to the surface colour", "tokens", "TOKEN_THEME_COMBINATION", lambda s: s, repo_cat(_theme_resolve("semantic.text.primary", "#0c0c0c"))),
    M("policy raises the contrast bar above the real pair", "tokens", "TOKEN_THEME_COMBINATION", lambda s: s, repo_pol(lambda p: p["themeRules"].__setitem__("minTextContrast", 20))),
    # ---- not approved
    M("effectively-invisible border token", "tokens", "TOKEN_NOT_APPROVED", _set(tok("border", "semantic.border.inputFocus"))),
    M("unused foundation colour as surface", "tokens", "TOKEN_NOT_APPROVED", _set(tok("surface", "color.base.dark"))),
    M("effectively-invisible grey as text", "tokens", "TOKEN_NOT_APPROVED", _set(tok("text", "color.base.grey"))),
    M("unused spacing variable", "tokens", "TOKEN_NOT_APPROVED", _set(tok("sectionPadding", "spacing.unusedVars.py"))),
    M("policy marks the token the example uses as not approved", "tokens", "TOKEN_NOT_APPROVED", lambda s: s,
      repo_pol(lambda p: p["notGenerationApproved"].append("semantic.text.primary"))),
    M("policy marks the WebGL clear colour as not approved", "tokens", "TOKEN_NOT_APPROVED", lambda s: s,
      repo_pol(lambda p: p["notGenerationApproved"].append("color.webgl.clear"))),
    GM("generated page: not-approved token", "tokens", "TOKEN_NOT_APPROVED", _set(tok("border", "semantic.border.inputFocus"))),
    # ---- schema layer (closed tokens object)
    M("tokens object missing", "tokens", "SCHEMA", lambda s: s.pop("tokens")),
    M("required token slot missing", "tokens", "SCHEMA", _set(tokd("sectionPadding"))),
    M("invented token slot", "tokens", "SCHEMA", _set(tok("accent", "semantic.text.primary"))),
    M("token slot is a number", "tokens", "SCHEMA", _set(tok("sectionPadding", 24))),
    M("token slot is null", "tokens", "SCHEMA", _set(tok("surface", None))),
    M("token slot is empty", "tokens", "SCHEMA", _set(tok("surface", ""))),
    M("token slot is an object", "tokens", "SCHEMA", _set(tok("surface", {"value": "#0c0c0c"}))),
    M("token slot is a very long string", "tokens", "SCHEMA", _set(tok("surface", "semantic." + "x" * 90))),
    M("per-node style override smuggled in", "tokens", "SCHEMA", _set(lambda s: node(s, "hero.course-intro").__setitem__("style", {"color": "#fff"}))),
    M("WebGL clear colour as a raw value", "tokens", "SCHEMA", _set(lambda s: node(s, "layer.webgl-object")["content"].__setitem__("clearColorToken", "#0f0f0f"))),
    M("WebGL clear colour as another token", "tokens", "SCHEMA", _set(lambda s: node(s, "layer.webgl-object")["content"].__setitem__("clearColorToken", "color.base.black"))),
]

# ---- mode: reference | generated
MODE_MUTATIONS = [
    M("mode missing", "mode", "SCHEMA", lambda s: s.pop("mode")),
    M("mode outside the closed enum", "mode", "SCHEMA", _set(lambda s: s.__setitem__("mode", "production"))),
    M("mode wrong case", "mode", "SCHEMA", _set(lambda s: s.__setitem__("mode", "Generated"))),
    M("mode null", "mode", "SCHEMA", _set(lambda s: s.__setitem__("mode", None))),
    M("mode a list", "mode", "SCHEMA", _set(lambda s: s.__setitem__("mode", ["generated"]))),
    GM("generated example: mode removed", "mode", "SCHEMA", lambda s: s.pop("mode")),
    M("generated mode with evidence-reference provenance", "mode", "MODE_PROVENANCE_MISMATCH", _set(lambda s: s.__setitem__("mode", "generated"))),
    M("reference mode with generated provenance", "mode", "MODE_PROVENANCE_MISMATCH", _set(lambda s: s.__setitem__("contentProvenance", "generated"))),
    GM("generated example flipped to reference mode", "mode", "MODE_PROVENANCE_MISMATCH", _set(lambda s: s.__setitem__("mode", "reference"))),
    GM("generated example given evidence-reference provenance", "mode", "MODE_PROVENANCE_MISMATCH", _set(lambda s: s.__setitem__("contentProvenance", "evidence-reference"))),
    M("the reference example flipped to generated is rejected (real mark, model, links, copy, hosts)", "mode", "GENERATED_MODE_REFERENCE_ASSET", _set(_flip_to_generated)),
    M("the reference example flipped to generated: source copy", "mode", "GENERATED_MODE_SOURCE_COPY", _set(_flip_to_generated)),
    M("the reference example flipped to generated: source host", "mode", "GENERATED_MODE_SOURCE_URL", _set(_flip_to_generated)),
    M("the reference example flipped to generated: brand", "mode", "BRAND_PASSOFF", _set(_flip_to_generated)),
    M("the reference example flipped to generated: real url in a label", "mode", "GENERATED_MODE_URL_NOT_RESERVED", _set(_flip_to_generated)),
    # reference-only roles smuggled into a generated page (each must be rejected)
    GM("source logo role in the navbar", "mode", "GENERATED_MODE_REFERENCE_ASSET", _set(_role(lambda s: _nav(s)["logo"], "brand.logo-mark"))),
    GM("source logo role in the footer", "mode", "GENERATED_MODE_REFERENCE_ASSET", _set(_role(lambda s: _foot(s)["logo"], "brand.logo-mark"))),
    GM("author link role in the footer social link", "mode", "GENERATED_MODE_REFERENCE_ASSET", _set(_role(lambda s: _foot(s)["social"]["link"], "identity.author-link"))),
    GM("author link role in the privacy link", "mode", "GENERATED_MODE_REFERENCE_ASSET", _set(_role(lambda s: _foot(s)["privacy"]["link"], "identity.author-link"))),
    GM("author link role in the credit link", "mode", "GENERATED_MODE_REFERENCE_ASSET", _set(_role(lambda s: _foot(s)["credit"]["link"], "identity.author-link"))),
    GM("source og image role", "mode", "GENERATED_MODE_REFERENCE_ASSET", _set(_role(lambda s: s["meta"]["ogImage"], "meta.og-image"))),
    GM("source favicon role", "mode", "GENERATED_MODE_REFERENCE_ASSET", _set(_role(lambda s: s["meta"]["favicon"], "meta.favicon"))),
    GM("source cube model role", "mode", "GENERATED_MODE_REFERENCE_ASSET", _set(_role(lambda s: node(s, "layer.webgl-object")["content"]["model"], "webgl.cube-model"))),
    GM("source matcap role", "mode", "GENERATED_MODE_REFERENCE_ASSET", _set(_role(lambda s: node(s, "layer.webgl-object")["content"]["matcaps"][0], "webgl.matcap"))),
    GM("source sticker colour map role", "mode", "GENERATED_MODE_REFERENCE_ASSET", _set(_role(lambda s: node(s, "layer.webgl-object")["content"]["colorMap"], "webgl.sticker-colormap"))),
    GM("blocked Discord community icon in a generated page", "mode", "GENERATED_MODE_REFERENCE_ASSET", _set(_community)),
    # source brand in generated text
    GM("source wordmark in the footer", "mode", "BRAND_PASSOFF", _set(lambda s: _foot(s).__setitem__("wordmark", [{"text": "THE", "layer": "front"}, {"text": "CODE", "layer": "behind-canvas-deep"}, {"text": "FLOW", "layer": "behind-canvas"}, {"text": "CO", "layer": "front"}]))),
    GM("source author domain as the credit label", "mode", "BRAND_PASSOFF", _set(_set_label(lambda s: _foot(s)["credit"], "linkLabel", "HTTPS://FEDERIC.OOO"))),
    GM("source title", "mode", "BRAND_PASSOFF", _set(lambda s: s["meta"].__setitem__("title", "Join Waitlist — thecodeflow.co"))),
    GM("source brand in a heading line", "mode", "BRAND_PASSOFF", _set(lambda s: _hero(s)["heading"]["lines"][0][0].__setitem__("text", "CODEFLOW"))),
    GM("source brand in the route", "mode", "BRAND_PASSOFF", _set(lambda s: s.__setitem__("route", "/thecodeflow"))),
    GM("source brand split by punctuation", "mode", "BRAND_PASSOFF", _set(_set_label(_hero, "eyebrow", "THE-CODE-FLOW"))),
    GM("source author name in body copy", "mode", "BRAND_PASSOFF", _set(lambda s: node(s, "cta.waitlist-form")["content"].__setitem__("body", "Built by Federico Valla."))),
    # source copy in generated text
    GM("source CTA label reused", "mode", "GENERATED_MODE_SOURCE_COPY", _set(_set_label(lambda s: _hero(s)["cta"], "label", "Reserve your Spot"))),
    GM("source CTA label reused, upper-case", "mode", "GENERATED_MODE_SOURCE_COPY", _set(_set_label(lambda s: _hero(s)["cta"], "label", "RESERVE YOUR SPOT"))),
    GM("source CTA label reused, punctuation and markdown changed", "mode", "GENERATED_MODE_SOURCE_COPY", _set(_set_label(lambda s: _hero(s)["cta"], "label", "**Reserve** your __Spot__!"))),
    GM("source nav CTA reused", "mode", "GENERATED_MODE_SOURCE_COPY", _set(_set_label(lambda s: _nav(s)["cta"], "label", "Join Waitlist"))),
    GM("source list heading reused", "mode", "GENERATED_MODE_SOURCE_COPY", _set(lambda s: node(s, "list.numbered-topics")["content"].__setitem__("heading", "COURSE CONTENT"))),
    GM("source subheading reused (signature phrase)", "mode", "GENERATED_MODE_SOURCE_COPY", _set(lambda s: _hero(s)["subheading"].__setitem__("regular", "JAVASCRIPT COURSE FOR"))),
    GM("source price pitch inside new words (signature phrase)", "mode", "GENERATED_MODE_SOURCE_COPY", _set(lambda s: _hero(s)["priceNote"].__setitem__("line1", "*LOCK PRICE AT **$48,**"))),
    GM("source guarantee line reused", "mode", "GENERATED_MODE_SOURCE_COPY", _set(lambda s: _hero(s)["priceNote"].__setitem__("line2", "**GUARANTEES** ENTRY"))),
    GM("source meta description reused", "mode", "GENERATED_MODE_SOURCE_COPY", _set(lambda s: s["meta"].__setitem__("description", "Level up your Webflow game by learning Javascript."))),
    GM("source perk reused inside a longer sentence (4-word run)", "mode", "GENERATED_MODE_SOURCE_COPY", _set(lambda s: node(s, "cta.waitlist-form")["content"]["perks"].__setitem__(0, "Includes early access to Discord inner circle for all"))),
    GM("source footer label reused", "mode", "GENERATED_MODE_SOURCE_COPY", _set(lambda s: _foot(s)["privacy"].__setitem__("label", "PRIVACY POLICY"))),
    GM("source form error reused", "mode", "GENERATED_MODE_SOURCE_COPY", _set(lambda s: node(s, "cta.waitlist-form")["content"].__setitem__("error", "Something went wrong. Try again?"))),
    # source hosts / non-reserved URLs
    GM("source host as a label", "mode", "GENERATED_MODE_SOURCE_URL", _set(_set_label(lambda s: _foot(s)["credit"], "linkLabel", "thecodeflow.co"))),
    GM("source URL with scheme in the description", "mode", "GENERATED_MODE_SOURCE_URL", _set(lambda s: s["meta"].__setitem__("description", "Read more at https://www.thecodeflow.co/join today."))),
    GM("source author site in a label", "mode", "GENERATED_MODE_SOURCE_URL", _set(_set_label(lambda s: _foot(s)["social"], "label", "FEDERIC.OOO"))),
    GM("source mail host in the form error", "mode", "GENERATED_MODE_SOURCE_URL", _set(lambda s: node(s, "cta.waitlist-form")["content"].__setitem__("error", "Try ooo.us21.list-manage.com"))),
    GM("source analytics host in a ref", "mode", "GENERATED_MODE_SOURCE_URL", _set(lambda s: node(s, "cta.waitlist-form")["content"]["action"].__setitem__("ref", "placeholder:cloud.umami.is/x"))),
    GM("source privacy-policy document host in a label", "mode", "GENERATED_MODE_SOURCE_URL", _set(_set_label(lambda s: _foot(s)["privacy"], "label", "docs.google.com/doc"))),
    GM("source CMS host in a label", "mode", "GENERATED_MODE_SOURCE_URL", _set(_set_label(lambda s: _foot(s)["social"], "label", "webflow.com"))),
    GM("real domain in a label (.com)", "mode", "GENERATED_MODE_URL_NOT_RESERVED", _set(_set_label(lambda s: _foot(s)["credit"], "linkLabel", "studio.com"))),
    GM("real domain with scheme in the description", "mode", "GENERATED_MODE_URL_NOT_RESERVED", _set(lambda s: s["meta"].__setitem__("description", "Book at https://shop.io/join now."))),
    GM("www host on a real TLD", "mode", "GENERATED_MODE_URL_NOT_RESERVED", _set(_set_label(lambda s: _foot(s)["social"], "label", "www.mystudio.net"))),
    GM("email on a real domain", "mode", "GENERATED_MODE_URL_NOT_RESERVED", _set(lambda s: node(s, "cta.waitlist-form")["content"]["fields"]["email"].__setitem__("placeholder", "you@mail.org"))),
    GM("real .ai domain", "mode", "GENERATED_MODE_URL_NOT_RESERVED", _set(_set_label(lambda s: _foot(s)["credit"], "linkLabel", "studio.ai"))),
    GM("localhost URL", "mode", "GENERATED_MODE_URL_NOT_RESERVED", _set(lambda s: s["meta"].__setitem__("description", "Try http://localhost:3000 first."))),
    GM("example.org is reserved by RFC but not an allowed placeholder here", "mode", "GENERATED_MODE_URL_NOT_RESERVED", _set(lambda s: s["meta"].__setitem__("description", "See ftp://files.example.org/list for details."))),
    GM("example.com bare host", "mode", "GENERATED_MODE_URL_NOT_RESERVED", _set(_set_label(lambda s: _foot(s)["credit"], "linkLabel", "example.com"))),
    GM("real URL in a ref (placeholder: prefix kept)", "mode", "GENERATED_MODE_URL_NOT_RESERVED", _set(lambda s: node(s, "cta.waitlist-form")["content"]["action"].__setitem__("ref", "placeholder:https://hooks.shop.io/x"))),
    # availability pinned (registry mutated: a DIFFERENT BUT VALID availability, or an invalid one)
    M("pinned availability: source logo -> generation-safe", "mode", "PINNED_AVAILABILITY", lambda s: s, _avail("brand.logo-mark", "generation-safe")),
    M("pinned availability: author link -> generation-safe", "mode", "PINNED_AVAILABILITY", lambda s: s, _avail("identity.author-link", "generation-safe")),
    M("pinned availability: cube model -> blocked", "mode", "PINNED_AVAILABILITY", lambda s: s, _avail("webgl.cube-model", "blocked")),
    M("pinned availability: Discord glyph -> generation-safe", "mode", "PINNED_AVAILABILITY", lambda s: s, _avail("icon.discord", "generation-safe")),
    M("pinned availability: Discord glyph -> reference-only", "mode", "PINNED_AVAILABILITY", lambda s: s, _avail("icon.discord", "reference-only")),
    M("pinned availability: placeholder logo -> reference-only", "mode", "PINNED_AVAILABILITY", lambda s: s, _avail("brand.logo-placeholder", "reference-only")),
    M("pinned availability: arrow icon -> blocked", "mode", "PINNED_AVAILABILITY", lambda s: s, _avail("icon.arrow", "blocked")),
    M("pinned availability: value outside the closed vocabulary", "mode", "PINNED_AVAILABILITY", lambda s: s, _avail("icon.arrow", "sometimes")),
    M("pinned availability: availability removed", "mode", "PINNED_AVAILABILITY", lambda s: s, lambda r: r["roles"]["roles"]["icon.arrow"].pop("availability")),
    M("pinned availability: a new role nobody pinned", "mode", "PINNED_AVAILABILITY", lambda s: s, _new_role),
    M("pinned availability: a pinned role deleted from the registry", "mode", "PINNED_AVAILABILITY", lambda s: s, _drop_role("meta.og-placeholder")),
    GM("registry lets the source logo through (validator still pinned)", "mode", "PINNED_AVAILABILITY", _set(_role(lambda s: _nav(s)["logo"], "brand.logo-mark")), _avail("brand.logo-mark", "generation-safe")),
]

MUTATIONS += TOKEN_MUTATIONS + MODE_MUTATIONS


def _tok_control(name, **kw):
    s = copy.deepcopy(EXAMPLE)
    s["tokens"].update(kw)
    return (name, s, None)


def _gen_ctl(name, fn):
    s = copy.deepcopy(GENERATED)
    fn(s)
    return (name, s, None)


def _foot_label(s, key, value):
    _foot(s)["credit"][key] = value


def _meta_desc(s, value):
    s["meta"]["description"] = value


EXTRA_CONTROLS = [
    # every allowed value of every non-contrast slot
    *[(("slot %s accepts %s" % (slot, t)), (lambda sl, tt: (lambda s: (s["tokens"].__setitem__(sl, tt), s)[1])(copy.deepcopy(EXAMPLE)))(slot, t), None)
      for slot, x in sorted(json.load(open(os.path.join(REPO, "tokens", "llm", "token-policy.json")))["pageSpecTokenSlots"].items())
      if not slot.startswith("$") and x["location"].startswith("tokens.") and slot not in ("surface", "text")
      for t in x["allow"]],
    _tok_control("valid pair: placeholder text on the page surface (contrast above 4.5)", text="semantic.text.placeholder"),
    _tok_control("valid pair: white submit text on the page surface", text="semantic.text.submit"),
    _tok_control("valid pair: hover text on the hover surface (the real hover state)", surface="semantic.surface.buttonHover", text="semantic.text.onButtonHover"),
    _tok_control("valid pair: primary text on the WebGL clear surface", surface="semantic.surface.webglClear"),
    ("border slot omitted (optional)", (lambda s: (s["tokens"].pop("border"), s)[1])(copy.deepcopy(EXAMPLE)), None),
    _gen_ctl("generated example: valid token combination", lambda s: s["tokens"].update(surface="semantic.surface.buttonHover", text="semantic.text.onButtonHover")),
    # generated mode: reserved placeholder domains are accepted
    _gen_ctl("generated: .example host as a label", lambda s: _foot_label(s, "linkLabel", "studio.example")),
    _gen_ctl("generated: .invalid host as a label", lambda s: _foot_label(s, "linkLabel", "studio.invalid")),
    _gen_ctl("generated: upper-case .EXAMPLE host", lambda s: _foot_label(s, "linkLabel", "STUDIO.EXAMPLE")),
    _gen_ctl("generated: https URL on a reserved domain", lambda s: _meta_desc(s, "Book your seat at https://shop.studio.example/join today.")),
    _gen_ctl("generated: www host on a reserved domain", lambda s: _meta_desc(s, "Visit www.studio.invalid for the latest dates.")),
    _gen_ctl("generated: email on a reserved domain", lambda s: node(s, "cta.waitlist-form")["content"]["fields"]["email"].__setitem__("placeholder", "jo@mail.example")),
    _gen_ctl("generated: analytics placeholder (generation-safe role)", lambda s: s["meta"].__setitem__("analytics", {"assetRole": "endpoint.analytics", "source": "placeholder", "ref": "placeholder:analytics"})),
    _gen_ctl("generated: generated-source logo placeholder", lambda s: _nav(s).__setitem__("logo", {"assetRole": "brand.logo-placeholder", "source": "generated", "ref": "generated:logo"})),
    _gen_ctl("generated: font licensed by the deployer", lambda s: s["fonts"].__setitem__("sans", {"assetRole": "font.commercial-sans", "source": "licensed-by-deployer", "ref": "licensed:studio-sans"})),
    _gen_ctl("generated: generic CTA words that are single words are not source copy", lambda s: _nav(s)["cta"].__setitem__("label", "Reserve")),
    ("reference example unchanged: reference-only and blocked roles are allowed in reference mode", copy.deepcopy(EXAMPLE), None),
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
    controls.append(("generated example (mode generated, fictional copy, placeholder assets)", copy.deepcopy(GENERATED)))
    controls += [(n, sp) for n, sp, _ in EXTRA_CONTROLS]
    for name, s in controls:
        errs, warns = sv.validate(s, BASE_REPO)
        ok = not errs
        fails += not ok
        print("%s CONTROL  %-52s errors=%d warnings=%d" % ("PASS" if ok else "FAIL", name, len(errs), len(warns)))
        for e in errs:
            print("      ", e)
    # ---- mutations
    for name, cat, rule, fn, repo_fn, base in MUTATIONS:
        s = fn(copy.deepcopy(GENERATED if base == "generated" else EXAMPLE))
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
