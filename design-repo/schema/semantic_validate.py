#!/usr/bin/env python3
"""Semantic validator for codeflow-waitlist PageSpecs.

Runs the Draft-07 schema first, then every rule JSON Schema cannot express.
Each rule id in RULES must also exist (same severity) in compatibility/graph.json;
extraction/verify_all.py checks that the two stay in agreement.

Token rules (TOKEN_*): every token a PageSpec names (the closed `tokens` slots and the WebGL clear colour) must be
an approved catalog path (tokens/llm/token-catalog.json) that the slot accepts (tokens/llm/token-policy.json), and
must be valid for the declared theme. Raw colours, arbitrary spacing and unsupported fonts are rejected by name.

Mode rules: PageSpec.mode is `reference` (a page for the source brand) or `generated` (a page for any other
brand). In `generated` mode only generation-safe asset roles are allowed (GENERATED_MODE_REFERENCE_ASSET), no source
copy (GENERATED_MODE_SOURCE_COPY), no source host (GENERATED_MODE_SOURCE_URL), every URL-like string on a reserved
.example/.invalid domain (GENERATED_MODE_URL_NOT_RESERVED), and BRAND_PASSOFF applies to all text and the route.

Usage:  python3 schema/semantic_validate.py [pagespec.json ...]
        (defaults to schema/example.pagespec.json). Exit 1 if any error.
Requires: jsonschema (pip install jsonschema).
"""
import sys
sys.dont_write_bytecode = True

import copy
import json
import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

RULES = {
    "SCHEMA": "error",
    "TEMPLATE_SEQUENCE_MATCH": "error",
    "ONE_PER_PAGE_BY_SECTION_VARIANT": "error",
    "NAV_FIRST": "error",
    "HERO_FOLLOWS_NAV": "error",
    "FORM_PRECEDES_FOOTER": "error",
    "FOOTER_PRECEDES_LAYER": "error",
    "WEBGL_LAYER_LAST": "error",
    "CTA_TARGETS_FORM": "error",
    "FOOTER_NAV_ANCHORS_RESOLVE": "error",
    "DUPLICATE_ANCHOR_ONLY_DOCUMENTED": "warn",
    "BEHIND_CANVAS_REQUIRES_LAYER": "error",
    "BEHIND_CANVAS_BUDGET": "warn",
    "MOTION_PATTERNS_ALLOWED": "error",
    "REDUCED_MOTION_REQUIRED": "error",
    "MAX_WORDS": "error",
    "ASSET_ROLE_KNOWN": "error",
    "ASSET_SOURCE_POLICY": "error",
    "ASSET_REF_DENYLIST": "error",
    "PINNED_POLICY": "error",
    "BRAND_PASSOFF": "error",
    "NO_MARQUEE_SECTION": "error",
    "SECTION_CONTRACT_SCHEMA": "error",
    "SECTION_TAXONOMY_PINNED": "error",
    "CONVERSION_BLOCK_CLASSED_CTA": "error",
    "RETRIEVAL_ELIGIBILITY_PINNED": "error",
    "SECTION_SOURCE_STRUCTURE": "error",
    "TOKEN_UNKNOWN": "error",
    "TOKEN_RAW_COLOR": "error",
    "TOKEN_ARBITRARY_SPACING": "error",
    "TOKEN_UNSUPPORTED_FONT": "error",
    "TOKEN_SLOT_MISMATCH": "error",
    "TOKEN_THEME_COMBINATION": "error",
    "TOKEN_NOT_APPROVED": "error",
    "MODE_PROVENANCE_MISMATCH": "error",
    "PINNED_AVAILABILITY": "error",
    "GENERATED_MODE_REFERENCE_ASSET": "error",
    "GENERATED_MODE_SOURCE_COPY": "error",
    "GENERATED_MODE_SOURCE_URL": "error",
    "GENERATED_MODE_URL_NOT_RESERVED": "error",
}
# SCHEMA is the Draft-07 layer itself, not a graph rule.
NON_GRAPH_RULES = {"SCHEMA"}

# Second, independent source of truth for compliance-critical roles (MASTER-GUIDE 3.23):
# membership in the policy enum is not enough; these roles must carry exactly this policy.
PINNED_POLICIES = {
    "brand.logo-mark": "must-not-reproduce",
    "icon.discord": "must-not-reproduce",
    "webgl.cube-model": "must-not-reproduce",
    "webgl.matcap": "must-not-reproduce",
    "webgl.sticker-colormap": "must-not-reproduce",
    "meta.og-image": "must-not-reproduce",
    "meta.favicon": "must-not-reproduce",
    "identity.author-link": "must-not-reproduce",
    "endpoint.form-action": "must-not-reuse-live-endpoint",
    "endpoint.analytics": "must-not-reuse-live-endpoint",
    "font.commercial-sans": "license-required",
}
# Asset availability by mode, pinned (second source of truth next to assets/asset-roles.json `availability`;
# extraction/verify_all.py keeps its own independent copy). Moving a role to a different-but-valid availability
# (the source's mark -> generation-safe) must be caught, not just a value outside the closed vocabulary.
PINNED_AVAILABILITY = {
    "brand.logo-mark": "reference-only",
    "identity.author-link": "reference-only",
    "meta.og-image": "reference-only",
    "meta.favicon": "reference-only",
    "webgl.cube-model": "reference-only",
    "webgl.matcap": "reference-only",
    "webgl.sticker-colormap": "reference-only",
    "icon.discord": "blocked-for-generation",
    "icon.arrow": "generation-safe",
    "endpoint.form-action": "generation-safe",
    "endpoint.analytics": "generation-safe",
    "font.commercial-sans": "generation-safe",
    "font.mono": "generation-safe",
    "brand.logo-placeholder": "generation-safe",
    "identity.link-placeholder": "generation-safe",
    "meta.og-placeholder": "generation-safe",
    "meta.favicon-placeholder": "generation-safe",
    "webgl.model-placeholder": "generation-safe",
    "webgl.matcap-placeholder": "generation-safe",
    "webgl.colormap-placeholder": "generation-safe",
}
MODE_PROVENANCE = {"reference": "evidence-reference", "generated": "generated"}

# --- token classification -------------------------------------------------------------------------------
PATH_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]*(?:\.[A-Za-z0-9]+)+$")
HEX_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")
COLOR_FN_RE = re.compile(r"\b(?:rgb|rgba|hsl|hsla|hwb|lab|lch|oklab|oklch|color|color-mix)\s*\(", re.I)
RAW_LENGTH_RE = re.compile(r"^\s*(?:-?\d*\.?\d+(?:px|rem|em|vh|vw|vmin|vmax|%|ch|pt|cm|mm|in)?\s*)+$|\b(?:calc|clamp|min|max|var)\s*\(", re.I)
NAMED_COLORS = set("""aliceblue antiquewhite aqua aquamarine azure beige bisque black blanchedalmond blue blueviolet brown burlywood
cadetblue chartreuse chocolate coral cornflowerblue cornsilk crimson cyan darkblue darkcyan darkgoldenrod darkgray darkgreen
darkgrey darkkhaki darkmagenta darkolivegreen darkorange darkorchid darkred darksalmon darkseagreen darkslateblue darkslategray
darkslategrey darkturquoise darkviolet deeppink deepskyblue dimgray dimgrey dodgerblue firebrick floralwhite forestgreen fuchsia
gainsboro ghostwhite gold goldenrod gray green greenyellow grey honeydew hotpink indianred indigo ivory khaki lavender
lavenderblush lawngreen lemonchiffon lightblue lightcoral lightcyan lightgoldenrodyellow lightgray lightgreen lightgrey lightpink
lightsalmon lightseagreen lightskyblue lightslategray lightslategrey lightsteelblue lightyellow lime limegreen linen magenta
maroon mediumaquamarine mediumblue mediumorchid mediumpurple mediumseagreen mediumslateblue mediumspringgreen mediumturquoise
mediumvioletred midnightblue mintcream mistyrose moccasin navajowhite navy oldlace olive olivedrab orange orangered orchid
palegoldenrod palegreen paleturquoise palevioletred papayawhip peachpuff peru pink plum powderblue purple rebeccapurple red
rosybrown royalblue saddlebrown salmon sandybrown seagreen seashell sienna silver skyblue slateblue slategray slategrey snow
springgreen steelblue tan teal thistle tomato turquoise violet wheat white whitesmoke yellow yellowgreen transparent
currentcolor""".split())
KIND_CATEGORIES = {"semanticColor": "semanticColor", "color": "color", "fontFamily": "fontFamily", "spacing": "spacing", "radius": "radius"}


def is_raw_color(v):
    t = v.strip()
    return bool(HEX_RE.search(t) or COLOR_FN_RE.search(t) or t.lower() in NAMED_COLORS)


def _lum(hexstr):
    h = hexstr.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        return None
    ch = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255.0
        ch.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]


def contrast_ratio(a, b):
    la, lb = _lum(a), _lum(b)
    if la is None or lb is None:
        return None
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


# --- generated-mode text/URL scanning ---------------------------------------------------------------------
SCHEME_HOST_RE = re.compile(r"\b[a-z][a-z0-9+.-]*://(?:[^\s/@?#\"']*@)?([^\s/:?#\"']+)", re.I)
WWW_RE = re.compile(r"\b(www\.[a-z0-9-]+(?:\.[a-z0-9-]+)*)", re.I)


def _words(s):
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).split()


def _shingles(words, n):
    return {tuple(words[i:i + n]) for i in range(len(words) - n + 1)}


# Section taxonomy, pinned (second source of truth next to each contract's `semantic.category`;
# extraction/verify_all.py keeps its own independent copy). `semantic` = what the section IS;
# `source` = where it came from in the real files. They are separate closed objects.
SECTION_TAXONOMY_PINNED = {
    "shell.nav": "shell",
    "hero.course-intro": "hero",
    "list.numbered-topics": "list",
    "content.block-pairs": "content",
    "cta.pitch-timeline": "cta",
    "cta.waitlist-form": "cta",
    "shell.footer-wordmark": "shell",
    "layer.webgl-object": "layer",
}
# Utility / runtime UI (cookie/consent, modal, dialog, overlay, toast, decorative fixed layer) is not a
# retrievable page section. Closed boolean on each contract; false needs a 30+ char retrievalReason.
# Everything not listed here must be true (the default).
RETRIEVAL_PINNED = {"layer.webgl-object": False}
UTILITY_ID_RE = re.compile(r"(cookie|consent|modal|dialog|overlay|toast|popup|lightbox|drawer|snackbar)")
# Fields that mark a block as a conversion block. Submit/action/timeline-style fields force category 'cta';
# a CTA or price note may never sit in a generic content/list section.
CONVERSION_FORCE_CTA_FIELDS = {"submit", "action", "timeline"}
CONVERSION_NOT_IN_GENERIC_FIELDS = {"cta", "priceNote"}
GENERIC_CATEGORIES = {"content", "list"}
MIN_RETRIEVAL_REASON = 30

SOURCE_REF_PREFIX = {"placeholder": "placeholder:", "generated": "generated:", "licensed-by-deployer": "licensed:"}

# The one documented source duplicate (mv.structure.duplicate-cta-id).
DOCUMENTED_DUPLICATE_ANCHORS = {
    "cta": {("content.block-pairs", "feature-pairs"), ("cta.pitch-timeline", "default")},
}
BEHIND = ("behind-canvas", "behind-canvas-deep")
NON_TEXT_KEYS = {"assetRole", "source", "ref", "section", "variant", "template", "route", "theme", "mode", "tokens",
                 "contentProvenance", "pageSpecVersion", "reducedMotionFallback", "patterns", "layer",
                 "href", "clearColorToken", "anchorId"}


def _load(rel, root):
    with open(os.path.join(root, rel), encoding="utf-8") as f:
        return json.load(f)


def load_repo(root=None):
    root = root or REPO
    repo = {
        "root": root,
        "schema": _load("schema/pagespec.schema.json", root),
        "templates": _load("templates/templates.json", root),
        "roles": _load("assets/asset-roles.json", root),
        "graph": _load("compatibility/graph.json", root),
        "motion": _load("tokens/llm/motion-patterns.json", root),
        "catalog": _load("tokens/llm/token-catalog.json", root),
        "policy": _load("tokens/llm/token-policy.json", root),
        "sections": {},
        "contracts": {},
        "contractSchema": _load("schema/section-contract.schema.json", root),
    }
    sdir = os.path.join(root, "sections")
    for fn in sorted(os.listdir(sdir)):
        if fn.endswith(".json"):
            c = _load(os.path.join("sections", fn), root)
            repo["sections"][c["id"]] = c
            for vname, v in c["variants"].items():
                repo["contracts"][(c["id"], vname)] = v
    repo["reference"] = _reference_corpus(repo, root)
    return repo


def _reference_corpus(repo, root):
    """Normalised copy of the reference example (the source's real text): whole strings of 2+ words and word
    shingles. A generated page must share neither (GENERATED_MODE_SOURCE_COPY)."""
    cfg = repo["roles"].get("sourceBrand", {}).get("copyOverlap", {})
    n = cfg.get("shingleWords", 4)
    minw = cfg.get("minWholeStringWords", 2)
    path = os.path.join(root, cfg.get("referenceExample", "schema/example.pagespec.json"))
    whole, shingles = set(), set()
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            ref = json.load(f)
        for t in iter_text(ref):
            w = _words(t)
            if len(w) >= minw:
                whole.add(" ".join(w))
            shingles |= _shingles(w, n)
    return {"whole": whole, "shingles": shingles, "n": n, "minw": minw}


def word_count(s):
    return len(s.replace("**", "").replace("__", "").split())


def walk_path(obj, path):
    """Dotted path; a '[]' suffix iterates an array (repeatable)."""
    vals = [obj]
    for part in path.split("."):
        key, depth = part, 0
        while key.endswith("[]"):
            key, depth = key[:-2], depth + 1
        nxt = []
        for v in vals:
            if key:
                if not isinstance(v, dict) or key not in v:
                    continue
                v = v[key]
            cur = [v]
            for _ in range(depth):
                cur = [x for c in cur if isinstance(c, list) for x in c]
            nxt.extend(cur)
        vals = nxt
    return vals


def iter_dicts(obj, path="$"):
    if isinstance(obj, dict):
        yield path, obj
        for k, v in obj.items():
            for x in iter_dicts(v, "%s.%s" % (path, k)):
                yield x
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            for x in iter_dicts(v, "%s[%d]" % (path, i)):
                yield x


def iter_text(obj, key=None):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in NON_TEXT_KEYS:
                continue
            for x in iter_text(v, k):
                yield x
    elif isinstance(obj, list):
        for v in obj:
            for x in iter_text(v, key):
                yield x
    elif isinstance(obj, str):
        yield obj


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def match_template(nodes, tnodes):
    """Greedy match of (section, variant) keys against structured template nodes. Returns list of problems."""
    keys = [(n.get("section"), n.get("variant")) for n in nodes]
    i, problems = 0, []
    for t in tnodes:
        tk = (t["section"], t["variant"])
        count = 0
        while i < len(keys) and keys[i] == tk and (count == 0 or t["repeatable"]):
            i += 1
            count += 1
        if count == 0 and t["required"]:
            got = "%s/%s" % keys[i] if i < len(keys) else "end of nodes"
            problems.append("required node %s/%s missing at position %d (found %s)" % (tk[0], tk[1], i, got))
    if i < len(keys):
        problems.append("unexpected node(s) not in template order starting at position %d: %s" %
                        (i, ", ".join("%s/%s" % k for k in keys[i:])))
    return problems


def check_section_contracts(repo, report):
    """Repo-level rules on the section contracts themselves (taxonomy, provenance, retrieval eligibility)."""
    from jsonschema import Draft7Validator
    sections = repo["sections"]
    validator = Draft7Validator(repo["contractSchema"])
    for sid, c in sorted(sections.items()):
        for e in sorted(validator.iter_errors(c), key=lambda e: list(e.path)):
            report("SECTION_CONTRACT_SCHEMA", "%s: %s: %s" % (sid, "/".join(str(p) for p in e.path) or "$", e.message[:200]))
    sources = {}
    for sid, c in sorted(sections.items()):
        sem, src = c.get("semantic") or {}, c.get("source") or {}
        cat = sem.get("category")
        # taxonomy
        if sem.get("id") != c.get("id"):
            report("SECTION_TAXONOMY_PINNED", "%s: semantic.id %r must equal the contract id" % (sid, sem.get("id")))
        if cat != sid.split(".")[0]:
            report("SECTION_TAXONOMY_PINNED", "%s: semantic.category %r must equal the id prefix %r" % (sid, cat, sid.split(".")[0]))
        if sid not in SECTION_TAXONOMY_PINNED:
            report("SECTION_TAXONOMY_PINNED", "%s has no pinned taxonomy entry; add it to SECTION_TAXONOMY_PINNED (and verify_all) after review" % sid)
        elif cat != SECTION_TAXONOMY_PINNED[sid]:
            report("SECTION_TAXONOMY_PINNED", "%s: semantic.category %r but pinned %r" % (sid, cat, SECTION_TAXONOMY_PINNED[sid]))
        fields = {f for v in c.get("variants", {}).values() for f in v.get("contentFields", [])}
        if fields & CONVERSION_FORCE_CTA_FIELDS and cat != "cta":
            report("CONVERSION_BLOCK_CLASSED_CTA", "%s has conversion field(s) %s but category %r (must be 'cta')" % (sid, sorted(fields & CONVERSION_FORCE_CTA_FIELDS), cat))
        if fields & CONVERSION_NOT_IN_GENERIC_FIELDS and cat in GENERIC_CATEGORIES:
            report("CONVERSION_BLOCK_CLASSED_CTA", "%s hides conversion field(s) %s inside generic category %r" % (sid, sorted(fields & CONVERSION_NOT_IN_GENERIC_FIELDS), cat))
        # retrieval eligibility
        want = RETRIEVAL_PINNED.get(sid, True)
        got = c.get("retrievalEligible", True)
        if got is not want:
            report("RETRIEVAL_ELIGIBILITY_PINNED", "%s: retrievalEligible is %r but pinned %r" % (sid, got, want))
        if (UTILITY_ID_RE.search(sid) or cat == "layer") and got is not False:
            report("RETRIEVAL_ELIGIBILITY_PINNED", "%s looks like utility/runtime UI (cookie/consent/modal/dialog/overlay/toast/layer) and must set retrievalEligible false" % sid)
        if got is False and len(c.get("retrievalReason") or "") < MIN_RETRIEVAL_REASON:
            report("RETRIEVAL_ELIGIBILITY_PINNED", "%s: retrievalEligible false needs a retrievalReason of %d+ characters" % (sid, MIN_RETRIEVAL_REASON))
        # provenance structure (real-file range checks live in verify_all)
        m = re.match(r"^(\d+)-(\d+)$", src.get("lines") or "")
        if not m or int(m.group(1)) < 1 or int(m.group(2)) < int(m.group(1)):
            report("SECTION_SOURCE_STRUCTURE", "%s: source.lines %r must be 'a-b' with 1 <= a <= b" % (sid, src.get("lines")))
        anchors = {v.get("anchorId") for v in c.get("variants", {}).values()}
        if anchors != {src.get("id")}:
            report("SECTION_SOURCE_STRUCTURE", "%s: source.id %r must equal every variant anchorId %s" % (sid, src.get("id"), sorted(anchors, key=str)))
        key = (src.get("file"), src.get("lines"))
        if key in sources:
            report("SECTION_SOURCE_STRUCTURE", "%s and %s claim the same source range %s:%s" % (sources[key], sid, key[0], key[1]))
        sources[key] = sid


def iter_strings(obj, path="$"):
    """Every string in a PageSpec with its path (no key exclusions): text, refs, hrefs, route, meta."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            for x in iter_strings(v, "%s.%s" % (path, k)):
                yield x
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            for x in iter_strings(v, "%s[%d]" % (path, i)):
                yield x
    elif isinstance(obj, str):
        yield path, obj


def classify_token(slot_name, slot, value, repo):
    """Return (rule, message) if `value` is not an approved token for this slot, else None."""
    cat, pol = repo["catalog"], repo["policy"]
    kind = slot["kind"]
    if is_raw_color(value):
        return "TOKEN_RAW_COLOR", "%s: raw colour %r; name a token (%s)" % (slot_name, value, ", ".join(slot["allow"][:3]))
    if kind == "spacing" and RAW_LENGTH_RE.search(value):
        return "TOKEN_ARBITRARY_SPACING", "%s: arbitrary spacing %r; name a spacing token (%s)" % (slot_name, value, ", ".join(slot["allow"][:3]))
    if not PATH_RE.match(value):
        if kind == "fontFamily":
            return "TOKEN_UNSUPPORTED_FONT", "%s: unsupported font %r; fonts are tokens (%s)" % (slot_name, value, ", ".join(slot["allow"]))
        return "TOKEN_UNKNOWN", "%s: %r is not a token path" % (slot_name, value)
    if value not in cat["tokens"]:
        return "TOKEN_UNKNOWN", "%s: unknown token %r (not in tokens/llm/token-catalog.json)" % (slot_name, value)
    if value in pol["notGenerationApproved"]:
        return "TOKEN_NOT_APPROVED", "%s: token %r is in notGenerationApproved (%s)" % (slot_name, value, pol["notGenerationApprovedReason"][:90])
    if value not in slot["allow"]:
        return "TOKEN_SLOT_MISMATCH", "%s: token %r (%s) is not accepted by this slot (allowed: %s)" % (slot_name, value, cat["tokens"][value]["category"], ", ".join(slot["allow"]))
    return None


def check_tokens(spec, repo, report):
    cat, pol = repo["catalog"], repo["policy"]
    slots = {n: x for n, x in pol["pageSpecTokenSlots"].items() if not n.startswith("$")}
    given = {}
    for n, x in slots.items():
        loc = x["location"]
        if loc.startswith("tokens."):
            v = (spec.get("tokens") or {}).get(n)
        else:
            vs = [d.get("clearColorToken") for nd in spec["nodes"] if nd["section"] == "layer.webgl-object" for d in [nd["content"]] if "clearColorToken" in d]
            v = vs[0] if vs else None
        if isinstance(v, str):
            given[n] = v
    ok = {}
    for n, v in given.items():
        res = classify_token(n, slots[n], v, repo)
        if res:
            report(res[0], res[1])
        else:
            ok[n] = v
    theme = spec["theme"]
    th = cat["themes"].get(theme)
    if th is None:
        report("TOKEN_THEME_COMBINATION", "theme %r is not a theme of the token catalog %s" % (theme, sorted(cat["themes"])))
    else:
        for n, v in ok.items():
            if slots[n].get("themeResolved") and v not in th["semanticTokens"]:
                report("TOKEN_THEME_COMBINATION", "%s: token %r is not resolved by theme %r" % (n, v, theme))
        against = slots.get("text", {}).get("contrastAgainst")
        if against and "text" in ok and against in ok:
            a = th["resolves"].get(ok["text"], cat["tokens"][ok["text"]]["value"])
            b = th["resolves"].get(ok[against], cat["tokens"][ok[against]]["value"])
            if isinstance(a, str) and isinstance(b, str):
                r = contrast_ratio(a, b)
                need = pol["themeRules"]["minTextContrast"]
                if r is not None and r < need:
                    report("TOKEN_THEME_COMBINATION", "text %r (%s) on %s %r (%s) has contrast %.2f, below the minimum %s in theme %r" % (ok["text"], a, against, ok[against], b, r, need, theme))
    for n, v in ok.items():
        af = slots[n].get("assetField")
        if af:
            want = (spec.get("fonts", {}).get(af.split(".")[1]) or {}).get("assetRole")
            have = cat["tokens"][v].get("assetRole")
            if want != have:
                report("TOKEN_SLOT_MISMATCH", "%s: font token %r carries assetRole %r but %s is %r" % (n, v, have, af, want))


def check_mode(spec, repo, report):
    mode, prov = spec["mode"], spec["contentProvenance"]
    if MODE_PROVENANCE.get(mode) != prov:
        report("MODE_PROVENANCE_MISMATCH", "mode %r requires contentProvenance %r, found %r" % (mode, MODE_PROVENANCE.get(mode), prov))
    if mode != "generated":
        return
    roles = repo["roles"]["roles"]
    sb = repo["roles"].get("sourceBrand", {})
    for path, d in iter_dicts(spec):
        role = d.get("assetRole") if isinstance(d, dict) else None
        if role in roles and roles[role].get("availability") != "generation-safe":
            subs = ", ".join(roles[role].get("generationSafeSubstitutes", [])) or "none: omit it"
            report("GENERATED_MODE_REFERENCE_ASSET", "%s: role %s is %s and cannot appear in a generated page (use: %s)" % (path, role, roles[role].get("availability"), subs))
    hosts = [h.lower() for h in sb.get("hosts", [])]
    reserved = tuple(sb.get("reservedPlaceholderDomains", [".example", ".invalid"]))
    tlds = "|".join(re.escape(t) for t in sorted(sb.get("urlLikeTlds", []), key=len, reverse=True))
    bare = re.compile(r"(?<![\w.-])((?:[a-z0-9-]+\.)+(?:%s))(?![\w-])" % tlds, re.I) if tlds else None
    for path, v in iter_strings(spec):
        if ".tokens." in path or path.endswith(".source"):
            continue
        low = v.lower()
        for h in hosts:
            if h in low:
                report("GENERATED_MODE_SOURCE_URL", "%s names the source host %r" % (path, h))
        found = [m.group(1) for m in SCHEME_HOST_RE.finditer(v)] + [m.group(1) for m in WWW_RE.finditer(v)]
        if bare is not None:
            found += [m.group(1) for m in bare.finditer(v)]
        for host in sorted(set(x.lower().rstrip(".") for x in found)):
            if not host.endswith(reserved):
                report("GENERATED_MODE_URL_NOT_RESERVED", "%s: URL-like host %r is not on a reserved %s domain" % (path, host, "/".join(reserved)))
    ref = repo["reference"]
    sigs = [(t, " ".join(_words(t))) for t in sb.get("signatureCopy", [])]
    for t in iter_text(spec):
        w = _words(t)
        joined = " ".join(w)
        if len(w) >= ref["minw"] and joined in ref["whole"]:
            report("GENERATED_MODE_SOURCE_COPY", "generated text %r repeats a whole string of the source copy" % t[:60])
        elif _shingles(w, ref["n"]) & ref["shingles"]:
            report("GENERATED_MODE_SOURCE_COPY", "generated text %r shares a %d-word run with the source copy" % (t[:60], ref["n"]))
        else:
            for raw, ns in sigs:
                if ns and (" " + ns + " ") in (" " + joined + " "):
                    report("GENERATED_MODE_SOURCE_COPY", "generated text %r contains source signature copy %r" % (t[:60], raw))
                    break


def validate(spec, repo=None):
    repo = repo or load_repo()
    errors, warnings = [], []

    def report(rule, msg):
        (errors if RULES[rule] == "error" else warnings).append((rule, msg))

    # --- repo-level compliance pinning (runs for every spec) ---------------------
    policies = repo["roles"]["generationPolicies"]
    roles = repo["roles"]["roles"]
    for role, expected in PINNED_POLICIES.items():
        actual = roles.get(role, {}).get("generationPolicy")
        if actual != expected:
            report("PINNED_POLICY", "asset role %s must be pinned to %r but asset-roles.json says %r" % (role, expected, actual))
        if not roles.get(role, {}).get("pinned"):
            report("PINNED_POLICY", "asset role %s must be marked pinned:true" % role)

    for role, expected in PINNED_AVAILABILITY.items():
        actual = roles.get(role, {}).get("availability")
        if actual != expected:
            report("PINNED_AVAILABILITY", "asset role %s must be availability %r but asset-roles.json says %r" % (role, expected, actual))
    for role in roles:
        if role not in PINNED_AVAILABILITY:
            report("PINNED_AVAILABILITY", "asset role %s has no pinned availability; add it to PINNED_AVAILABILITY (and verify_all) after review" % role)

    # --- section-contract layer (taxonomy / provenance / retrieval eligibility) ----
    check_section_contracts(repo, report)

    # --- schema layer ------------------------------------------------------------
    from jsonschema import Draft7Validator
    sch_errors = sorted(Draft7Validator(repo["schema"]).iter_errors(spec), key=lambda e: list(e.path))
    for e in sch_errors:
        report("SCHEMA", "%s: %s" % ("/".join(str(p) for p in e.path) or "$", e.message[:300]))
    if sch_errors:
        # still flag an unknown/marquee section explicitly for clarity
        for n in spec.get("nodes", []) if isinstance(spec, dict) else []:
            if isinstance(n, dict) and n.get("section") not in repo["sections"]:
                report("NO_MARQUEE_SECTION", "section %r is not a contract in sections/ (no marquee or invented sections)" % n.get("section"))
        return errors, warnings

    nodes = spec["nodes"]
    keys = [(n["section"], n["variant"]) for n in nodes]
    sections = repo["sections"]

    for n in nodes:
        if n["section"] not in sections:
            report("NO_MARQUEE_SECTION", "section %r has no contract" % n["section"])

    # --- template cross-reference (declared template vs its real node list) ------
    tpl = repo["templates"]["templates"].get(spec["template"])
    if tpl is None:
        report("TEMPLATE_SEQUENCE_MATCH", "template %r not in templates.json" % spec["template"])
    else:
        for p in match_template(nodes, tpl["nodes"]):
            report("TEMPLATE_SEQUENCE_MATCH", "%s: %s" % (spec["template"], p))
        routes = [r["path"] for r in repo["templates"]["routes"] if r["template"] == spec["template"]]
        # generated pages may live on new routes; evidence-reference pages must sit on a real route
        if (spec["mode"] == "reference" or spec["contentProvenance"] == "evidence-reference") and spec["route"] not in routes:
            report("TEMPLATE_SEQUENCE_MATCH", "evidence-reference spec route %r is not a real route of %s %s" % (spec["route"], spec["template"], routes))

    # --- one per page, keyed on (section, variant) -------------------------------
    seen = {}
    for k in keys:
        seen[k] = seen.get(k, 0) + 1
    for (sid, var), c in seen.items():
        cons = sections.get(sid, {}).get("constraints", {})
        limit = 1 if cons.get("onePerPage") else None
        if limit and c > limit:
            report("ONE_PER_PAGE_BY_SECTION_VARIANT", "%s/%s appears %d times" % (sid, var, c))

    # --- position rules from section constraints ---------------------------------
    ids = [k[0] for k in keys]
    def idx(sid):
        return ids.index(sid) if sid in ids else None
    for sid, s in sections.items():
        cons = s.get("constraints", {})
        i = idx(sid)
        if i is None:
            continue
        if cons.get("mustBeFirst") and i != 0:
            report("NAV_FIRST", "%s must be first (is at %d)" % (sid, i))
        if cons.get("mustBeLast") and i != len(ids) - 1:
            report("WEBGL_LAYER_LAST", "%s must be last (is at %d of %d)" % (sid, i, len(ids)))
        if cons.get("mustFollowNav") and (i == 0 or ids[i - 1] != "shell.nav"):
            report("HERO_FOLLOWS_NAV", "%s must immediately follow shell.nav" % sid)
        if cons.get("mustPrecedeFooter") and (i + 1 >= len(ids) or ids[i + 1] != "shell.footer-wordmark"):
            report("FORM_PRECEDES_FOOTER", "%s must immediately precede shell.footer-wordmark" % sid)
        if cons.get("mustPrecedeLayer") and (i + 1 >= len(ids) or ids[i + 1] != "layer.webgl-object"):
            report("FOOTER_PRECEDES_LAYER", "%s must immediately precede layer.webgl-object" % sid)

    # --- anchors -----------------------------------------------------------------
    anchors = {}
    for n in nodes:
        if "anchorId" in n:
            anchors.setdefault(n["anchorId"], set()).add((n["section"], n["variant"]))
    anchor_counts = {}
    for n in nodes:
        if "anchorId" in n:
            anchor_counts[n["anchorId"]] = anchor_counts.get(n["anchorId"], 0) + 1
    for a, cnt in anchor_counts.items():
        if cnt > 1:
            if a in DOCUMENTED_DUPLICATE_ANCHORS and anchors[a] <= DOCUMENTED_DUPLICATE_ANCHORS[a] and cnt == len(anchors[a]):
                warnings.append(("DUPLICATE_ANCHOR_ONLY_DOCUMENTED", "anchor #%s used %d times (documented source duplicate, mv.structure.duplicate-cta-id)" % (a, cnt)))
            else:
                errors.append(("DUPLICATE_ANCHOR_ONLY_DOCUMENTED", "anchor #%s duplicated %d times and is not the documented duplicate" % (a, cnt)))

    cta_paths = [p for p, d in iter_dicts(nodes) if p.endswith(".cta") and "href" in d]
    if cta_paths and anchors.get("signup") != {("cta.waitlist-form", "default")}:
        report("CTA_TARGETS_FORM", "CTAs target #signup but no cta.waitlist-form node with anchorId 'signup' exists")

    for n in nodes:
        if n["section"] == "shell.footer-wordmark":
            for link in n["content"]["siteNav"]["links"]:
                if link["href"][1:] not in anchors:
                    report("FOOTER_NAV_ANCHORS_RESOLVE", "footer link %r -> %s does not resolve to any anchorId %s" % (link["label"], link["href"], sorted(anchors)))

    # --- behind-canvas layering --------------------------------------------------
    has_layer = "layer.webgl-object" in ids
    for i, n in enumerate(nodes):
        behind = [d for _, d in iter_dicts(n["content"]) if d.get("layer") in BEHIND]
        if behind and not has_layer:
            report("BEHIND_CANVAS_REQUIRES_LAYER", "node %d %s/%s has %d behind-canvas segment(s) but no layer.webgl-object node" % (i, n["section"], n["variant"], len(behind)))
        heading = n["content"].get("heading")
        if isinstance(heading, dict) and "lines" in heading:
            c = sum(1 for line in heading["lines"] for s in line if s["layer"] in BEHIND)
            if c > 1:
                report("BEHIND_CANVAS_BUDGET", "node %d heading has %d behind-canvas segments (observed max 1)" % (i, c))
        if n["section"] == "list.numbered-topics":
            c = sum(1 for s in n["content"]["items"] if s["layer"] in BEHIND)
            if c > 3:
                report("BEHIND_CANVAS_BUDGET", "list has %d behind-canvas items (observed max 3)" % c)
        if n["section"] == "shell.footer-wordmark":
            c = sum(1 for s in n["content"]["wordmark"] if s["layer"] in BEHIND)
            if c > 2:
                report("BEHIND_CANVAS_BUDGET", "wordmark has %d behind-canvas words (observed max 2)" % c)

    # --- motion ------------------------------------------------------------------
    for i, n in enumerate(nodes):
        contract = repo["contracts"].get((n["section"], n["variant"]))
        if contract is None:
            continue
        allowed = set(contract["motion"]["allowedPatterns"])
        bad = [p for p in n["motion"]["patterns"] if p not in allowed]
        if bad:
            report("MOTION_PATTERNS_ALLOWED", "node %d %s/%s uses %s; allowed %s" % (i, n["section"], n["variant"], bad, sorted(allowed)))
        if n["motion"].get("reducedMotionFallback") != contract["motion"]["reducedMotionFallback"]:
            report("REDUCED_MOTION_REQUIRED", "node %d %s/%s reducedMotionFallback must be %r" % (i, n["section"], n["variant"], contract["motion"]["reducedMotionFallback"]))
    page_allowed = {k for k, v in repo["motion"]["patterns"].items() if v["scope"] == "page"}
    bad = [p for p in spec["pageMotion"]["patterns"] if p not in page_allowed]
    if bad:
        report("MOTION_PATTERNS_ALLOWED", "pageMotion uses non-page patterns %s" % bad)
    if spec["pageMotion"].get("reducedMotionFallback") != "no-fade-native-scroll":
        report("REDUCED_MOTION_REQUIRED", "pageMotion reducedMotionFallback must be 'no-fade-native-scroll'")

    # --- maxWords (per instance) ---------------------------------------------------
    for i, n in enumerate(nodes):
        contract = repo["contracts"].get((n["section"], n["variant"]))
        if contract is None:
            continue
        for path, budget in contract["maxWords"].items():
            for v in walk_path(n["content"], path):
                if isinstance(v, str) and word_count(v) > budget:
                    report("MAX_WORDS", "node %d %s/%s %s has %d words (max %d): %r" % (i, n["section"], n["variant"], path, word_count(v), budget, v[:60]))
    if tpl is not None:
        for path, budget in tpl.get("pageMaxWords", {}).items():
            for v in walk_path(spec, path):
                if isinstance(v, str) and word_count(v) > budget:
                    report("MAX_WORDS", "%s has %d words (max %d)" % (path, word_count(v), budget))

    # --- assets --------------------------------------------------------------------
    deny = [t.lower() for t in repo["roles"]["refDenylist"]["terms"]]
    for path, d in iter_dicts(spec):
        if "assetRole" not in d:
            continue
        role = d["assetRole"]
        if role not in roles:
            report("ASSET_ROLE_KNOWN", "%s: unknown assetRole %r" % (path, role))
            continue
        pol = roles[role]["generationPolicy"]
        allowed = policies.get(pol, {}).get("allowedSources", [])
        if d["source"] not in allowed:
            report("ASSET_SOURCE_POLICY", "%s: role %s (%s) allows sources %s, got %r" % (path, role, pol, allowed, d["source"]))
        ref = d.get("ref")
        if ref is not None:
            prefix = SOURCE_REF_PREFIX.get(d["source"])
            if prefix is None or not ref.startswith(prefix):
                report("ASSET_SOURCE_POLICY", "%s: ref %r must start with %r for source %r" % (path, ref, prefix, d["source"]))
            hits = [t for t in deny if t in ref.lower()]
            if hits:
                report("ASSET_REF_DENYLIST", "%s: ref %r contains real-asset/endpoint term(s) %s" % (path, ref, hits))

    # --- tokens (closed slots, catalog + policy) and mode (reference / generated) ----------------
    check_tokens(spec, repo, report)
    check_mode(spec, repo, report)

    # --- brand pass-off --------------------------------------------------------------
    if spec["contentProvenance"] == "generated" or spec["mode"] == "generated":
        terms = [(t, _norm(t)) for t in repo["roles"]["brandTextDenylist"]["terms"]]
        for s in iter_text(spec):
            ns = _norm(s)
            for t, nt in terms:
                if nt and nt in ns:
                    report("BRAND_PASSOFF", "generated text %r contains real brand/author term %r" % (s[:60], t))
        for t, nt in terms:
            if nt and nt in _norm(spec["route"]):
                report("BRAND_PASSOFF", "generated route %r contains real brand/author term %r" % (spec["route"], t))
        wm = [n for n in nodes if n["section"] == "shell.footer-wordmark"]
        for n in wm:
            joined = _norm("".join(s["text"] for s in n["content"]["wordmark"]))
            for t, nt in terms:
                if nt and nt in joined:
                    report("BRAND_PASSOFF", "generated wordmark spells real brand term %r" % t)
    return errors, warnings


def main(argv):
    paths = argv or [os.path.join(REPO, "schema", "example.pagespec.json")]
    repo = load_repo()
    total = 0
    for p in paths:
        with open(p, encoding="utf-8") as f:
            spec = json.load(f)
        errs, warns = validate(spec, repo)
        total += len(errs)
        print("%s: %d error(s), %d warning(s)" % (os.path.basename(p), len(errs), len(warns)))
        for r, m in errs:
            print("  ERROR %s: %s" % (r, m))
        for r, m in warns:
            print("  WARN  %s: %s" % (r, m))
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
