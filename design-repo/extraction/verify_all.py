#!/usr/bin/env python3
"""One-shot verification for this design-repo. Exit 1 if any check FAILs.

Usage:
  python3 extraction/verify_all.py [--source-root PATH]

--source-root defaults to the folder containing design-repo/ (where the cited evidence lives).
If none of the cited evidence files exist there (design-repo shipped alone), the citation
check is downgraded to a WARN instead of failing.

Every drift-sensitive check here (allowlist parity, citation range + quote, section source ranges,
taxonomy and retrieval-eligibility pins, wrapper gate, allowlistVersion parity, manifest counts,
pinned asset policies, graph/validator agreement, token catalog + policy, asset availability + modes,
validator canaries) is proven to fail on injected drift by extraction/prove_drift.py.
"""
import sys
sys.dont_write_bytecode = True

import glob
import importlib.util
import json
import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = []

# Independent pins (a second copy, deliberately NOT imported from schema/semantic_validate.py): editing one
# side without the other fails a check. See MASTER-GUIDE 3.23 on pinned values.
EXPECT_TAXONOMY = {
    "shell.nav": "shell",
    "hero.course-intro": "hero",
    "list.numbered-topics": "list",
    "content.block-pairs": "content",
    "cta.pitch-timeline": "cta",
    "cta.waitlist-form": "cta",
    "shell.footer-wordmark": "shell",
    "layer.webgl-object": "layer",
}
EXPECT_RETRIEVAL = {sid: sid != "layer.webgl-object" for sid in EXPECT_TAXONOMY}   # utility/runtime UI is the only false

# Pinned ASSET AVAILABILITY by mode (assets/asset-roles.json `availability`). A second copy, independent of
# schema/semantic_validate.py PINNED_AVAILABILITY: flipping a role to a different-but-valid availability
# (the source's mark -> generation-safe, the blocked Discord glyph -> generation-safe) must be caught.
AVAIL_VALUES = ["reference-only", "generation-safe", "blocked"]
PINNED_AVAILABILITY = {
    "brand.logo-mark": "reference-only", "identity.author-link": "reference-only", "meta.og-image": "reference-only",
    "meta.favicon": "reference-only", "webgl.cube-model": "reference-only", "webgl.matcap": "reference-only",
    "webgl.sticker-colormap": "reference-only", "icon.discord": "blocked",
    "icon.arrow": "generation-safe", "endpoint.form-action": "generation-safe", "endpoint.analytics": "generation-safe",
    "font.commercial-sans": "generation-safe", "font.mono": "generation-safe",
    "brand.logo-placeholder": "generation-safe", "identity.link-placeholder": "generation-safe",
    "meta.og-placeholder": "generation-safe", "meta.favicon-placeholder": "generation-safe",
    "webgl.model-placeholder": "generation-safe", "webgl.matcap-placeholder": "generation-safe",
    "webgl.colormap-placeholder": "generation-safe",
}
# Pinned PageSpec token slots (token-policy.json pageSpecTokenSlots): name -> (kind, required, allowed catalog paths).
# Independent of the policy file: widening a slot's allow list (letting `surface` take a flash colour, letting
# `sectionPadding` take a min-height) is a different-but-valid value that only this table catches.
PINNED_TOKEN_SLOTS = {
    "surface": ("semanticColor", True, ["semantic.surface.page", "semantic.surface.buttonHover", "semantic.surface.webglClear"]),
    "text": ("semanticColor", True, ["semantic.text.primary", "semantic.text.onButtonHover", "semantic.text.placeholder", "semantic.text.submit"]),
    "border": ("semanticColor", False, ["semantic.border.default"]),
    "fontSans": ("fontFamily", True, ["typography.fontFamily.sans"]),
    "fontDisplay": ("fontFamily", True, ["typography.fontFamily.sansCondensed"]),
    "fontMono": ("fontFamily", True, ["typography.fontFamily.mono"]),
    "sectionPadding": ("spacing", True, ["spacing.section.padding", "spacing.hero.paddingTop", "spacing.hero.paddingBottom", "spacing.signup.paddingTop", "spacing.footer.paddingTop", "spacing.footer.paddingBottom"]),
    "buttonRadius": ("radius", True, ["radius.pill"]),
    "webglClear": ("color", True, ["color.webgl.clear"]),
}
PINNED_MIN_TEXT_CONTRAST = 4.5
UTILITY_WORDS = ("cookie", "consent", "modal", "dialog", "overlay", "toast", "popup", "lightbox", "drawer", "snackbar")


def rec(status, name, detail=""):
    RESULTS.append((status, name, detail))


def check(name, problems, warn_only=False):
    if problems:
        rec("WARN" if warn_only else "FAIL", name, "; ".join(problems[:12]) + (" ... (+%d more)" % (len(problems) - 12) if len(problems) > 12 else ""))
    else:
        rec("PASS", name)


def J(rel):
    with open(os.path.join(REPO, rel), encoding="utf-8") as f:
        return json.load(f)


def load_module(name, rel):
    spec = importlib.util.spec_from_file_location(name, os.path.join(REPO, rel))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_sv():
    return load_module("semantic_validate", os.path.join("schema", "semantic_validate.py"))


def token_leaves(o):
    if isinstance(o, dict):
        if "value" in o and "evidence" in o:
            return 1
        return sum(token_leaves(v) for k, v in o.items() if not k.startswith("$"))
    return 0


def main(argv):
    source_root = os.path.dirname(REPO)
    if "--source-root" in argv:
        source_root = os.path.abspath(argv[argv.index("--source-root") + 1])

    # 0. the token + mode layer files this verifier depends on exist (a missing one fails here, not with a traceback)
    required = ["tokens/llm/token-catalog.json", "tokens/llm/token-policy.json", "tokens/tokens_lib.py", "tokens/build_catalog.py",
                "schema/examples/generated.template.waitlist-landing.pagespec.json"]
    probs = ["missing: %s" % r_ for r_ in required if not os.path.isfile(os.path.join(REPO, r_))]
    check("required token/mode files exist (%d)" % len(required), probs)
    if probs:
        return finish()

    # 1. every JSON file parses
    probs, data = [], {}
    for p in sorted(glob.glob(os.path.join(REPO, "**", "*.json"), recursive=True)):
        rel = os.path.relpath(p, REPO)
        try:
            with open(p, encoding="utf-8") as f:
                data[rel] = json.load(f)
        except Exception as e:  # noqa
            probs.append("%s: %s" % (rel, e))
    check("json-parse (%d files)" % len(data), probs)
    if probs:
        return finish()

    manifest = J("registry.manifest.json")
    schema = J("schema/pagespec.schema.json")
    example = J("schema/example.pagespec.json")
    allow = J("tokens/llm/component-allowlist.json")
    roles = J("assets/asset-roles.json")
    motion = J("tokens/llm/motion-patterns.json")
    templates = J("templates/templates.json")
    graph = J("compatibility/graph.json")
    ledger = J("extraction/measured-values.json")
    contract_schema = J("schema/section-contract.schema.json")
    whitelist = J("extraction/wrapper-whitelist.json")
    sections = {d["id"]: d for d in (J(os.path.relpath(p, REPO)) for p in sorted(glob.glob(os.path.join(REPO, "sections", "*.json"))))}
    prims = sorted(J(os.path.relpath(p, REPO))["id"] for p in glob.glob(os.path.join(REPO, "primitives", "*.json")))
    comps = sorted(J(os.path.relpath(p, REPO))["id"] for p in glob.glob(os.path.join(REPO, "components", "*.json")))
    sv = load_sv()

    # 2. schema layer
    from jsonschema import Draft7Validator
    probs = []
    try:
        Draft7Validator.check_schema(schema)
    except Exception as e:  # noqa
        probs.append("schema invalid: %s" % e)
    gen_examples = sorted(glob.glob(os.path.join(REPO, "schema", "examples", "generated.*.pagespec.json")))
    errs = list(Draft7Validator(schema).iter_errors(example))
    probs += ["example: %s" % e.message[:200] for e in errs]
    for gp in gen_examples:
        gerrs = list(Draft7Validator(schema).iter_errors(J(os.path.relpath(gp, REPO))))
        probs += ["%s: %s" % (os.path.basename(gp), e.message[:200]) for e in gerrs]
        errs += gerrs
    check("schema Draft-07 (%d examples: %d errors)" % (1 + len(gen_examples), len(errs)), probs)

    # 3. semantic layer on the examples (the reference example and every generated-mode example)
    srepo = sv.load_repo(REPO)
    e, w = sv.validate(example, srepo)
    probs = ["reference example: %s: %s" % x for x in e]
    n_err, n_warn = len(e), len(w)
    for gp in gen_examples:
        gs = J(os.path.relpath(gp, REPO))
        ge, gw = sv.validate(gs, srepo)
        probs += ["%s: %s: %s" % ((os.path.basename(gp),) + x) for x in ge]
        n_err += len(ge)
        n_warn += len(gw)
    check("semantic validator on examples (reference + %d generated: %d errors, %d warnings)" % (len(gen_examples), n_err, n_warn), probs)

    # 4. allowlist parity
    probs = []
    if allow["primitives"] != prims:
        probs.append("primitives allowlist %s != files %s" % (sorted(set(allow["primitives"]) ^ set(prims)), "diff"))
    if allow["components"] != comps:
        probs.append("components allowlist/file mismatch: %s" % sorted(set(allow["components"]) ^ set(comps)))
    if set(allow["sections"]) != set(sections):
        probs.append("sections allowlist/file mismatch: %s" % sorted(set(allow["sections"]) ^ set(sections)))
    node_defs = {(v["properties"]["section"]["const"], v["properties"]["variant"]["const"]): v
                 for k, v in schema["definitions"].items() if k.startswith("node__")}
    for sid, sa in allow["sections"].items():
        c = sections.get(sid)
        if not c:
            continue
        if sa.get("retrievalEligible") is not c.get("retrievalEligible", True):
            probs.append("%s retrievalEligible differs between allowlist (%r) and contract (%r)" % (sid, sa.get("retrievalEligible"), c.get("retrievalEligible", True)))
        if set(sa["variants"]) != set(c["variants"]):
            probs.append("%s variants allowlist %s != contract %s" % (sid, sorted(sa["variants"]), sorted(c["variants"])))
        for var, va in sa["variants"].items():
            nd = node_defs.get((sid, var))
            if nd is None:
                probs.append("%s/%s has no schema node definition" % (sid, var))
                continue
            if sorted(nd["properties"]) != sorted(va["settableProperties"]):
                probs.append("%s/%s settableProperties != schema properties" % (sid, var))
            schema_fields = sorted(nd["properties"]["content"]["properties"])
            if schema_fields != sorted(va["contentFields"]) or schema_fields != sorted(c["variants"].get(var, {}).get("contentFields", [])):
                probs.append("%s/%s contentFields differ between allowlist / schema / contract" % (sid, var))
    if set(node_defs) != {(s, v) for s, c in sections.items() for v in c["variants"]}:
        probs.append("schema node definitions != section contract variants")
    if allow["assetRoles"] != schema["definitions"]["assetRole"]["enum"] or set(allow["assetRoles"]) != set(roles["roles"]):
        probs.append("assetRoles differ between allowlist / schema enum / asset-roles.json")
    if allow["motionPatterns"] != schema["definitions"]["motionPattern"]["enum"] or set(allow["motionPatterns"]) != set(motion["patterns"]):
        probs.append("motionPatterns differ between allowlist / schema enum / motion-patterns.json")
    if allow["reducedMotionFallbacks"] != schema["definitions"]["reducedMotionFallback"]["enum"] or set(allow["reducedMotionFallbacks"]) != set(motion["reducedMotionFallbacks"]):
        probs.append("reducedMotionFallbacks differ between allowlist / schema / motion-patterns.json")
    if sorted(allow["templates"]) != sorted(templates["templates"]) or sorted(schema["properties"]["template"]["enum"]) != sorted(templates["templates"]):
        probs.append("templates differ between allowlist / schema enum / templates.json")
    if sorted(allow["pageProperties"]) != sorted(schema["properties"]):
        probs.append("pageProperties != schema top-level properties")
    if sorted(schema["definitions"]["sectionId"]["enum"]) != sorted(sections):
        probs.append("schema sectionId enum != section contracts")
    consts = set(re.findall(r'"const": "([a-z]+\.[a-z0-9.-]+)"', json.dumps(schema)))
    role_consts = {c for c in consts if c.split(".")[0] in {r.split(".")[0] for r in roles["roles"]}}
    unknown = sorted(c for c in role_consts if c not in roles["roles"] and c not in sections and c != "color.webgl.clear")
    if unknown:
        probs.append("schema assetRole consts not in asset-roles.json: %s" % unknown)
    for sid, c in sections.items():
        for var, v in c["variants"].items():
            bad = [p for p in v["motion"]["allowedPatterns"] if p not in motion["patterns"]]
            if bad:
                probs.append("%s/%s allowedPatterns not in vocabulary: %s" % (sid, var, bad))
            nd = node_defs.get((sid, var))
            if nd and sorted(nd["properties"]["motion"]["properties"]["patterns"]["items"]["enum"]) != sorted(v["motion"]["allowedPatterns"]):
                probs.append("%s/%s schema motion enum != contract allowedPatterns" % (sid, var))
            if nd and nd["properties"]["motion"]["properties"]["reducedMotionFallback"]["const"] != v["motion"]["reducedMotionFallback"]:
                probs.append("%s/%s schema fallback const != contract" % (sid, var))
        for kind, ids in (("primitives", prims), ("components", comps)):
            missing = [u for u in c["uses"][kind] if u not in ids]
            if missing:
                probs.append("%s uses unknown %s %s" % (sid, kind, missing))
    for cpath in glob.glob(os.path.join(REPO, "components", "*.json")):
        c = J(os.path.relpath(cpath, REPO))
        missing = [u for u in c["uses"] if u not in prims]
        if missing:
            probs.append("%s uses unknown primitives %s" % (c["id"], missing))
    check("allowlist parity (allowlist <-> contract files <-> schema)", probs)

    # 5. version parity
    probs = []
    if manifest["allowlistVersion"] != allow["allowlistVersion"]:
        probs.append("manifest allowlistVersion %r != allowlist %r" % (manifest["allowlistVersion"], allow["allowlistVersion"]))
    if manifest["pageSpecVersion"] != schema["properties"]["pageSpecVersion"]["const"]:
        probs.append("manifest pageSpecVersion %r != schema const %r" % (manifest["pageSpecVersion"], schema["properties"]["pageSpecVersion"]["const"]))
    cat_v = J("tokens/llm/token-catalog.json")["version"]
    pol_v = J("tokens/llm/token-policy.json")["version"]
    if manifest.get("tokenCatalogVersion") != cat_v:
        probs.append("manifest tokenCatalogVersion %r != token-catalog.json version %r" % (manifest.get("tokenCatalogVersion"), cat_v))
    if manifest.get("tokenPolicyVersion") != pol_v:
        probs.append("manifest tokenPolicyVersion %r != token-policy.json version %r" % (manifest.get("tokenPolicyVersion"), pol_v))
    if manifest.get("assetRolesVersion") != roles.get("rolesVersion"):
        probs.append("manifest assetRolesVersion %r != asset-roles.json rolesVersion %r" % (manifest.get("assetRolesVersion"), roles.get("rolesVersion")))
    if manifest.get("status") != "design-review-pending" or manifest.get("productionApproved") is not False:
        probs.append("manifest must be status design-review-pending and productionApproved false")
    check("version parity (allowlistVersion, pageSpecVersion, token catalog/policy, asset roles) + status flags", probs)

    # 6. manifest counts recomputed from disk
    real = {
        "tokens": sum(token_leaves(J(os.path.relpath(p, REPO))) for d in ("00-foundation", "10-semantic", "20-component", "30-layout")
                      for p in glob.glob(os.path.join(REPO, "tokens", d, "*.json"))),
        "primitives": len(prims), "components": len(comps), "sections": len(sections),
        "sectionVariants": sum(len(c["variants"]) for c in sections.values()),
        "templates": len(templates["templates"]), "routes": len(templates["routes"]),
        "assetRoles": len(roles["roles"]), "pinnedAssetRoles": sum(1 for r in roles["roles"].values() if r.get("pinned")),
        "retrievalIneligibleSections": sum(1 for c in sections.values() if c.get("retrievalEligible", True) is False),
        "motionPatterns": len(motion["patterns"]), "compatibilityRules": len(graph["rules"]),
        "measuredValueEntries": len(ledger["entries"]),
        "tokenCategories": len(J("tokens/llm/token-catalog.json")["counts"]["byCategory"]),
        "themes": len(glob.glob(os.path.join(REPO, "tokens", "themes", "*.json"))),
        "typographyRoles": len(J("tokens/00-foundation/typography.json")["role"]),
        "tokenPolicySlots": len([k for k in J("tokens/llm/token-policy.json")["pageSpecTokenSlots"] if not k.startswith("$")]),
        "pageSpecExamples": 1 + len(gen_examples),
        "referenceOnlyAssetRoles": sum(1 for r in roles["roles"].values() if r.get("availability") == "reference-only"),
        "generationSafeAssetRoles": sum(1 for r in roles["roles"].values() if r.get("availability") == "generation-safe"),
        "blockedAssetRoles": sum(1 for r in roles["roles"].values() if r.get("availability") == "blocked"),
    }
    probs = ["%s: manifest %r != disk %r" % (k, manifest["counts"].get(k), v) for k, v in real.items() if manifest["counts"].get(k) != v]
    probs += ["manifest count %r has no recompute rule" % k for k in manifest["counts"] if k not in real]
    with open(os.path.join(REPO, "README.md"), encoding="utf-8") as f:
        readme = f.read()
    for k, v in real.items():
        m = re.search(r"^\| %s \| (\d+) \|$" % re.escape(k), readme, re.M)
        if not m or int(m.group(1)) != v:
            probs.append("README counts table %s: %s != disk %r" % (k, m.group(1) if m else "missing", v))
    check("manifest + README counts recompute %s" % json.dumps(real, separators=(",", ":")), probs)

    # 7. entry points are inside the package
    probs = []
    for ep in manifest["entryPoints"] + manifest.get("entryPointDirectories", []):
        if os.path.isabs(ep) or ".." in ep.replace("\\", "/").split("/"):
            probs.append("entry point outside package: %s" % ep)
        elif not os.path.exists(os.path.join(REPO, ep)):
            probs.append("entry point missing: %s" % ep)
    check("entryPoints self-contained (%d)" % len(manifest["entryPoints"]), probs)

    # 8. citations: range + quote, graceful when no sibling source tree
    levels = ledger["evidenceLevels"]
    probs, n_cites, files = [], 0, set()
    for eid, ent in ledger["entries"].items():
        if ent.get("evidenceLevel") not in levels:
            probs.append("%s: unknown evidenceLevel %r" % (eid, ent.get("evidenceLevel")))
        if not ent.get("citations") and ent.get("evidenceLevel") not in ("qa-measured", "requester-reported", "inferred"):
            probs.append("%s: no citations" % eid)
        if ent.get("evidenceLevel") in ("qa-measured", "requester-reported", "inferred") and not ent.get("basis"):
            probs.append("%s: %s entry needs a 'basis'" % (eid, ent["evidenceLevel"]))
        for c in ent.get("citations", []):
            files.add(c["cite"].rsplit(":", 1)[0])
    check("measured-values ledger structure (%d entries)" % len(ledger["entries"]), probs)
    present = [f for f in files if os.path.exists(os.path.join(source_root, f))]
    if not present:
        rec("WARN", "citation validity", "no cited source files under %s (design-repo shipped alone?) - %d files not checked" % (os.path.basename(source_root) or source_root, len(files)))
    else:
        probs = []
        norm = lambda s: re.sub(r"\s+", " ", s).strip()
        cache = {}
        for eid, ent in ledger["entries"].items():
            for c in ent.get("citations", []):
                n_cites += 1
                m = re.match(r"^(.*):(\d+)(?:-(\d+))?$", c["cite"])
                if not m:
                    probs.append("%s: bad cite format %r" % (eid, c["cite"]))
                    continue
                path, a, b = m.group(1), int(m.group(2)), int(m.group(3) or m.group(2))
                if os.path.isabs(path) or ".." in path.split("/"):
                    probs.append("%s: cite path must be project-relative: %s" % (eid, path))
                    continue
                full = os.path.join(source_root, path)
                if not os.path.exists(full):
                    probs.append("%s: cited file missing: %s" % (eid, path))
                    continue
                if full not in cache:
                    with open(full, encoding="utf-8") as f:
                        txt = f.read()
                    lines = txt.split("\n")
                    if txt.endswith("\n"):
                        lines = lines[:-1]
                    cache[full] = lines
                lines = cache[full]
                if a < 1 or b < a or b > len(lines):
                    probs.append("%s: %s out of range (file has %d lines)" % (eid, c["cite"], len(lines)))
                    continue
                if norm(c["quote"]) not in norm("\n".join(lines[a - 1:b])):
                    probs.append("%s: quote not found in %s: %r" % (eid, c["cite"], c["quote"][:60]))
        check("citation validity: range + quote (%d citations, %d files)" % (n_cites, len(present)), probs)

    # 9. every evidence id referenced anywhere in the package exists in the ledger
    probs, n_refs = [], 0
    for p in glob.glob(os.path.join(REPO, "**", "*"), recursive=True):
        if os.path.isdir(p) or not p.endswith((".json", ".md", ".py")) or p.endswith("measured-values.json"):
            continue
        with open(p, encoding="utf-8") as f:
            for ref in re.findall(r"\bmv\.[a-z0-9-]+(?:\.[a-z0-9-]+)+", f.read()):
                n_refs += 1
                if ref not in ledger["entries"]:
                    probs.append("%s -> %s" % (os.path.relpath(p, REPO), ref))
    check("evidence ids resolve (%d references)" % n_refs, sorted(set(probs)))

    # 10. graph <-> validator agreement
    probs = []
    graph_rules = {r["id"]: r["severity"] for r in graph["rules"]}
    code_rules = {k: v for k, v in sv.RULES.items() if k not in sv.NON_GRAPH_RULES}
    for k in sorted(set(graph_rules) | set(code_rules)):
        if graph_rules.get(k) != code_rules.get(k):
            probs.append("%s: graph=%s validator=%s" % (k, graph_rules.get(k), code_rules.get(k)))
    tn = templates["templates"]["template.waitlist-landing"]["nodes"]
    edges = [(e["from"], e["to"]) for e in graph["edges"]]
    expect = [("%s/%s" % (a["section"], a["variant"]), "%s/%s" % (b["section"], b["variant"])) for a, b in zip(tn, tn[1:])]
    if edges != expect:
        probs.append("graph edges do not follow templates.json node order")
    check("graph <-> validator rule agreement (%d rules)" % len(graph_rules), probs)

    # 11. templates and routes
    probs = []
    paths = [r["path"] for r in templates["routes"]]
    if len(paths) != len(set(paths)):
        probs.append("route assigned more than once")
    for r in templates["routes"]:
        if r["template"] not in templates["templates"]:
            probs.append("route %s -> unknown template" % r["path"])
    for tid, t in templates["templates"].items():
        if tid not in [r["template"] for r in templates["routes"]]:
            probs.append("template %s has no route" % tid)
        for nd in t["nodes"]:
            if set(nd) != {"section", "variant", "required", "repeatable"}:
                probs.append("%s node not structured: %s" % (tid, nd))
            if nd["variant"] not in sections.get(nd["section"], {}).get("variants", {}):
                probs.append("%s node %s/%s has no contract" % (tid, nd["section"], nd["variant"]))
    check("templates structured + routes 1:1 (%d routes, %d templates)" % (len(paths), len(templates["templates"])), probs)

    # 12. pinned asset policies (code table vs data)
    probs = []
    for role, pol in sv.PINNED_POLICIES.items():
        r = roles["roles"].get(role)
        if r is None:
            probs.append("pinned role %s missing" % role)
        elif r["generationPolicy"] != pol or not r.get("pinned"):
            probs.append("%s: expected pinned policy %s, found %s (pinned=%s)" % (role, pol, r["generationPolicy"], r.get("pinned")))
    for role, r in roles["roles"].items():
        if r.get("pinned") and role not in sv.PINNED_POLICIES:
            probs.append("%s claims pinned:true but has no enforced pin in semantic_validate.PINNED_POLICIES" % role)
        if r["generationPolicy"] not in roles["generationPolicies"]:
            probs.append("%s: unknown policy %s" % (role, r["generationPolicy"]))
    check("pinned asset-role policies (%d pinned)" % len(sv.PINNED_POLICIES), probs)

    # 13. token references resolve; theme agrees with foundation
    probs = []
    trees = {}
    for p in glob.glob(os.path.join(REPO, "tokens", "*", "*.json")):
        if "/llm/" in p.replace("\\", "/"):
            continue
        d = J(os.path.relpath(p, REPO))
        trees[os.path.splitext(os.path.basename(p))[0]] = d
    roots = {}
    for d in trees.values():
        roots.update({k: v for k, v in d.items() if not k.startswith("$")})
    def resolve(path, node=None):
        node = roots if node is None else node
        parts = path.split(".")
        if not parts or parts == [""]:
            return node
        for j in range(len(parts), 0, -1):
            k = ".".join(parts[:j])
            if isinstance(node, dict) and k in node:
                if j == len(parts):
                    return node[k]
                r = resolve(".".join(parts[j:]), node[k])
                if r is not None:
                    return r
        return None
    def resolve_any(path):
        r = resolve(path)
        if r is None:
            head, _, rest = path.partition(".")
            if head in trees:
                r = resolve(rest, {k: v for k, v in trees[head].items() if not k.startswith("$")}) if rest else trees[head]
        return r
    refs = []
    for folder in ("primitives", "components"):
        for p in glob.glob(os.path.join(REPO, folder, "*.json")):
            refs += [(os.path.basename(p), t) for t in J(os.path.relpath(p, REPO))["tokens"]]
    for name in ("10-semantic/semantic.json", "20-component/component.json"):
        refs += [(name, t) for t in re.findall(r"\{([a-zA-Z0-9.]+)\}", json.dumps(J("tokens/" + name)))]
    for src, t in refs:
        if resolve_any(t) is None:
            probs.append("%s -> %s" % (src, t))
    sem = J("tokens/10-semantic/semantic.json")["semantic"]
    theme = J("tokens/themes/dark.json")["resolves"]
    if set(sem) != set(theme):
        probs.append("theme keys != semantic keys: %s" % sorted(set(sem) ^ set(theme)))
    for k, tok in sem.items():
        vals = tok["value"] if isinstance(tok["value"], list) else [tok["value"]]
        got = [resolve_any(v.strip("{}"))["value"] for v in vals]
        want = theme.get(k)
        want = want if isinstance(want, list) else [want]
        if [g.lower() for g in got] != [str(x).lower() for x in want]:
            probs.append("theme %s=%s but semantic resolves to %s" % (k, want, got))
    check("token references resolve + dark theme agrees (%d refs)" % len(refs), probs)

    # 14. maxWords paths resolve against the example (catches typo'd budget paths)
    probs = []
    for n in example["nodes"]:
        c = sections[n["section"]]["variants"][n["variant"]]
        for path in c["maxWords"]:
            if not sv.walk_path(n["content"], path):
                probs.append("%s/%s budget path %s resolves to nothing" % (n["section"], n["variant"], path))
            if c["maxWords"][path] < c["realWordCounts"][path]:
                probs.append("%s/%s %s budget below real count" % (n["section"], n["variant"], path))
    check("maxWords budget paths resolve", probs)

    # 15. every section contract satisfies the closed section-contract schema; semantic and source stay separate
    probs = []
    cv = Draft7Validator(contract_schema)
    try:
        Draft7Validator.check_schema(contract_schema)
    except Exception as e:  # noqa
        probs.append("section-contract schema invalid: %s" % e)
    for sid, c in sorted(sections.items()):
        for e in cv.iter_errors(c):
            probs.append("%s: %s: %s" % (sid, "/".join(str(p) for p in e.path) or "$", e.message[:140]))
        if c.get("semantic", {}).get("id") != sid or c.get("semantic", {}).get("category") != sid.split(".")[0]:
            probs.append("%s: semantic {id, category} must match the contract id and its prefix" % sid)
    check("section contracts: closed schema, semantic {id,category} vs source {id,tag,file,lines,citation} (%d contracts)" % len(sections), probs)

    # 16. taxonomy + conversion classing pinned by this file's own table
    probs = []
    for sid, cat in EXPECT_TAXONOMY.items():
        got = sections.get(sid, {}).get("semantic", {}).get("category")
        if got != cat:
            probs.append("%s: category %r, verify_all pins %r" % (sid, got, cat))
    for sid in sections:
        if sid not in EXPECT_TAXONOMY:
            probs.append("%s has no entry in verify_all EXPECT_TAXONOMY (review it, then pin it)" % sid)
    for sid, c in sections.items():
        fields = {f for v in c["variants"].values() for f in v["contentFields"]}
        if fields & {"submit", "action", "timeline"} and c.get("semantic", {}).get("category") != "cta":
            probs.append("%s carries conversion fields %s but is not category cta" % (sid, sorted(fields & {"submit", "action", "timeline"})))
        if fields & {"cta", "priceNote"} and c.get("semantic", {}).get("category") in ("content", "list"):
            probs.append("%s hides a CTA/price note inside generic category %s" % (sid, c["semantic"]["category"]))
    check("section taxonomy pinned + conversion blocks classed cta (%d sections)" % len(EXPECT_TAXONOMY), probs)

    # 17. retrieval eligibility pinned by this file's own table
    probs = []
    for sid, c in sections.items():
        got = c.get("retrievalEligible", True)
        if got is not EXPECT_RETRIEVAL.get(sid, True):
            probs.append("%s: retrievalEligible %r, verify_all pins %r" % (sid, got, EXPECT_RETRIEVAL.get(sid, True)))
        if got is False and len(c.get("retrievalReason") or "") < 30:
            probs.append("%s: retrievalEligible false without a 30+ char retrievalReason" % sid)
        if got is not False and "retrievalReason" in c:
            probs.append("%s: retrievalReason present on an eligible section" % sid)
        if (any(w in sid for w in UTILITY_WORDS) or c.get("semantic", {}).get("category") == "layer") and got is not False:
            probs.append("%s looks like utility/runtime UI but is retrieval-eligible" % sid)
    check("retrieval eligibility pinned (utility/runtime UI excluded, reason 30+ chars)", probs)

    # 18. source provenance against the real files (graceful when no sibling source tree)
    probs, checked, absent = [], 0, 0
    tree_present = any(os.path.exists(os.path.join(source_root, c["source"]["file"])) for c in sections.values())
    for sid, c in sorted(sections.items()):
        src = c["source"]
        if os.path.isabs(src["file"]) or ".." in src["file"].split("/"):
            probs.append("%s: source.file must be project-relative: %s" % (sid, src["file"]))
            continue
        cit = ledger["entries"].get(src["citation"])
        if cit is None:
            probs.append("%s: source.citation %s is not a ledger entry" % (sid, src["citation"]))
        elif not any(x["cite"].rsplit(":", 1)[0] == src["file"] for x in cit.get("citations", [])):
            probs.append("%s: ledger entry %s does not cite %s" % (sid, src["citation"], src["file"]))
        full = os.path.join(source_root, src["file"])
        if not os.path.exists(full):
            absent += 1
            if tree_present:
                probs.append("%s: source.file %s does not exist in the source tree" % (sid, src["file"]))
            continue
        checked += 1
        with open(full, encoding="utf-8") as f:
            flines = f.read().split("\n")
        a, b = (int(x) for x in src["lines"].split("-"))
        if a < 1 or b < a or b > len(flines):
            probs.append("%s: source.lines %s out of range (%s has %d lines)" % (sid, src["lines"], src["file"], len(flines)))
            continue
        first, last = flines[a - 1], flines[b - 1]
        if "<" + src["tag"] not in first:
            probs.append("%s: line %d of %s does not open <%s>: %r" % (sid, a, src["file"], src["tag"], first.strip()[:60]))
        if src["id"] is not None and 'id="%s"' % src["id"] not in first:
            probs.append("%s: line %d of %s lacks id=\"%s\": %r" % (sid, a, src["file"], src["id"], first.strip()[:60]))
        if src["id"] is None and ' id="' in first:
            probs.append("%s: source.id is null but the element has an id attribute" % sid)
        if "</%s>" % src["tag"] not in last:
            probs.append("%s: line %d of %s does not close </%s>: %r" % (sid, b, src["file"], src["tag"], last.strip()[:60]))
    if checked == 0:
        rec("WARN", "section source provenance", "no source files under %s (design-repo shipped alone?) - %d contracts not range-checked; structure and ledger links were still checked%s" % (os.path.basename(source_root) or source_root, absent, ("; PROBLEMS: " + "; ".join(probs)) if probs else ""))
        if probs:
            RESULTS[-1] = ("FAIL",) + RESULTS[-1][1:]
    else:
        check("section source provenance: file + line range + opening/closing tag verified (%d of %d contracts)" % (checked, len(sections)), probs)

    # 19. whole-page-wrapper quality gate (measured heights)
    wg = load_module("wrapper_gate", os.path.join("extraction", "wrapper_gate.py"))
    nodes = [n for t in templates["templates"].values() for n in t["nodes"]]
    cats = {sid: c.get("semantic", {}).get("category") for sid, c in sections.items()}
    gerr, gwarn, ginfo = wg.evaluate(nodes, cats, ledger.get("sectionHeights"), whitelist.get("entries"))
    sh = ledger.get("sectionHeights") or {}
    summary = "hero %s, page %s" % (
        ", ".join("%s=%spx" % (k.split("/")[0], v.get("heightPx")) for k, v in sh.get("sections", {}).items() if cats.get(k.split("/")[0]) == "hero"), sh.get("pageHeight"))
    check("whole-page-wrapper gate (%s; %d whitelisted)" % (summary, len(whitelist.get("entries", []))), ["%s: %s" % x for x in gerr])
    for code, msg in gwarn:
        rec("WARN", "whole-page-wrapper gate warning " + code, msg)
    for msg in ginfo:
        print("note: " + msg)

    # 20. token catalog + policy: rebuilt from the real token files, policy resolves against it, slots pinned
    probs = []
    sys.path.insert(0, os.path.join(REPO, "tokens"))
    bc = load_module("build_catalog", os.path.join("tokens", "build_catalog.py"))
    built = bc.build(os.path.join(REPO, "tokens"))
    with open(os.path.join(REPO, "tokens", "llm", "token-catalog.json"), encoding="utf-8") as f:
        disk_text = f.read()
    if disk_text != bc.render(built):
        probs.append("tokens/llm/token-catalog.json differs from what tokens/build_catalog.py builds from the token files (a token file or the catalog was edited alone; run tokens/build_catalog.py)")
    cat = built
    if cat["counts"]["tokens"] != real["tokens"]:
        probs.append("catalog token count %d != token leaves on disk %d" % (cat["counts"]["tokens"], real["tokens"]))
    theme_files = sorted(os.path.splitext(os.path.basename(p_))[0] for p_ in glob.glob(os.path.join(REPO, "tokens", "themes", "*.json")))
    if sorted(cat["themes"]) != theme_files:
        probs.append("catalog themes %s != theme files %s" % (sorted(cat["themes"]), theme_files))
    check("token catalog rebuilt from the token files and identical on disk (%d tokens, %d categories, %d theme(s))" % (cat["counts"]["tokens"], len(cat["counts"]["byCategory"]), len(cat["themes"])), probs)

    # 20b. token policy: resolves against the catalog, slots pinned, schema + examples agree
    probs = []
    policy = J("tokens/llm/token-policy.json")
    byc = cat["counts"]["byCategory"]
    rv = policy["rules"]["rawValueRestrictions"]
    if set(rv) != set(byc):
        probs.append("rawValueRestrictions categories %s != catalog categories %s" % (sorted(rv), sorted(byc)))
    derived = sorted(p_ for p_, t in cat["tokens"].items() if t.get("status") in ("unused", "effectively-invisible"))
    if sorted(policy["notGenerationApproved"]) != derived:
        probs.append("notGenerationApproved %s != catalog tokens with status unused/effectively-invisible %s" % (sorted(policy["notGenerationApproved"]), derived))
    slots = {k: v for k, v in policy["pageSpecTokenSlots"].items() if not k.startswith("$")}
    if sorted(slots) != sorted(PINNED_TOKEN_SLOTS):
        probs.append("policy slots %s != verify_all PINNED_TOKEN_SLOTS %s" % (sorted(slots), sorted(PINNED_TOKEN_SLOTS)))
    kind_cat = {"semanticColor": "semanticColor", "color": "color", "fontFamily": "fontFamily", "spacing": "spacing", "radius": "radius"}
    for n, (kind, req, allow) in PINNED_TOKEN_SLOTS.items():
        sl = slots.get(n)
        if sl is None:
            continue
        if sl.get("kind") != kind or sl.get("required") is not req or sl.get("allow") != allow:
            probs.append("slot %s: policy (kind %r, required %r, allow %s) != pinned (%r, %r, %s)" % (n, sl.get("kind"), sl.get("required"), sl.get("allow"), kind, req, allow))
        for t_ in sl.get("allow", []):
            if t_ not in cat["tokens"]:
                probs.append("slot %s allows %s, which is not in the catalog" % (n, t_))
            elif cat["tokens"][t_]["category"] != kind_cat[sl["kind"]]:
                probs.append("slot %s (kind %s) allows %s of category %s" % (n, sl["kind"], t_, cat["tokens"][t_]["category"]))
            if t_ in policy["notGenerationApproved"]:
                probs.append("slot %s allows the not-approved token %s" % (n, t_))
            if sl.get("themeResolved"):
                for th_, tv in cat["themes"].items():
                    if t_ not in tv["semanticTokens"]:
                        probs.append("slot %s is theme-resolved but theme %s does not resolve %s" % (n, th_, t_))
    tprops = schema["properties"]["tokens"]
    page_slots = sorted(k for k, v in slots.items() if v["location"].startswith("tokens."))
    if sorted(tprops["properties"]) != page_slots:
        probs.append("schema tokens properties %s != policy tokens.* slots %s" % (sorted(tprops["properties"]), page_slots))
    if sorted(tprops["required"]) != sorted(k for k in page_slots if slots[k]["required"]):
        probs.append("schema tokens.required != policy required slots")
    if tprops.get("additionalProperties") is not False or "tokens" not in schema["required"]:
        probs.append("schema tokens object must be closed and required")
    if schema["definitions"]["node__layer_webgl_object__default"]["properties"]["content"]["properties"]["clearColorToken"].get("const") != slots["webglClear"]["allow"][0]:
        probs.append("schema clearColorToken const != policy webglClear token")
    tr = policy["themeRules"]
    if tr.get("minTextContrast") != PINNED_MIN_TEXT_CONTRAST:
        probs.append("themeRules.minTextContrast %r != pinned %r" % (tr.get("minTextContrast"), PINNED_MIN_TEXT_CONTRAST))
    if sorted(schema["properties"]["theme"]["enum"]) != theme_files:
        probs.append("schema theme enum %s != theme files %s" % (schema["properties"]["theme"]["enum"], theme_files))
    if manifest["defaultTheme"] not in cat["themes"] or any(t_ not in cat["themes"] for t_ in manifest["schemaValidatedThemes"]):
        probs.append("manifest defaultTheme/schemaValidatedThemes are not catalog themes")
    for folder in ("primitives", "components"):
        for p_ in glob.glob(os.path.join(REPO, folder, "*.json")):
            c_ = J(os.path.relpath(p_, REPO))
            for t_ in c_["tokens"]:
                if t_ not in cat["tokens"] and not any(k.startswith(t_ + ".") for k in cat["tokens"]):
                    probs.append("%s references %s, which is neither a catalog token nor a catalog token group" % (c_["id"], t_))
    raw_hits = []
    for rel_ in ["schema/example.pagespec.json"] + [os.path.relpath(g_, REPO) for g_ in gen_examples]:
        for path_, val in sv.iter_strings(J(rel_)):
            if sv.HEX_RE.search(val) or sv.COLOR_FN_RE.search(val):
                raw_hits.append("%s %s: %r" % (rel_, path_, val[:40]))
    probs += ["raw colour in a PageSpec example: " + h for h in raw_hits]
    check("token policy resolves against the catalog, %d slots pinned, schema + examples agree (%d categories, %d not-approved tokens)" % (len(slots), len(byc), len(policy["notGenerationApproved"])), probs)

    # 21. asset availability + reference/generated modes
    probs = []
    if roles.get("availabilityValues") != AVAIL_VALUES:
        probs.append("asset-roles availabilityValues must be %s, found %s" % (AVAIL_VALUES, roles.get("availabilityValues")))
    for r_, v_ in roles["roles"].items():
        if v_.get("availability") not in AVAIL_VALUES:
            probs.append("asset role %s: availability %r is not one of %s" % (r_, v_.get("availability"), AVAIL_VALUES))
        if not v_.get("generatedModeGuidance"):
            probs.append("asset role %s: missing generatedModeGuidance" % r_)
    for r_, want in PINNED_AVAILABILITY.items():
        if r_ not in roles["roles"]:
            probs.append("pinned availability: role %s is missing from the registry" % r_)
        elif roles["roles"][r_].get("availability") != want:
            probs.append("pinned availability: role %s must be %s, found %r" % (r_, want, roles["roles"][r_].get("availability")))
    for r_ in roles["roles"]:
        if r_ not in PINNED_AVAILABILITY:
            probs.append("asset role %s has no entry in verify_all PINNED_AVAILABILITY (review it, then pin it)" % r_)
    for r_, v_ in roles["roles"].items():
        subs = v_.get("generationSafeSubstitutes", [])
        if v_.get("availability") == "reference-only":
            if not subs:
                probs.append("asset role %s is reference-only but names no generation-safe substitute" % r_)
            for s_ in subs:
                if s_ not in roles["roles"] or roles["roles"][s_].get("availability") != "generation-safe":
                    probs.append("asset role %s: substitute %s is not a generation-safe role" % (r_, s_))
                elif roles["roles"][s_].get("substituteFor") != r_:
                    probs.append("asset role %s: substitute %s does not declare substituteFor %s" % (r_, s_, r_))
        elif subs:
            probs.append("asset role %s is %s but lists substitutes" % (r_, v_.get("availability")))
        if v_.get("substituteFor") and roles["roles"].get(v_["substituteFor"], {}).get("availability") != "reference-only":
            probs.append("asset role %s substitutes for %s, which is not reference-only" % (r_, v_["substituteFor"]))
    enums = []
    def collect_enums(o):
        if isinstance(o, dict):
            if isinstance(o.get("allOf"), list) and len(o["allOf"]) == 2 and o["allOf"][0] == {"$ref": "#/definitions/assetRole"}:
                enums.append(o["allOf"][1])
            for v in o.values():
                collect_enums(v)
        elif isinstance(o, list):
            for v in o:
                collect_enums(v)
    collect_enums(schema)
    for r_, v_ in roles["roles"].items():
        if v_.get("availability") == "reference-only":
            occ = [e_ for e_ in enums if r_ in (e_.get("enum") or [e_.get("const")])]
            if not occ:
                probs.append("reference-only role %s does not occur in any schema field" % r_)
            for e_ in occ:
                missing = [s_ for s_ in v_.get("generationSafeSubstitutes", []) if s_ not in e_.get("enum", [])]
                if "const" in e_ or missing:
                    probs.append("schema field for %s does not accept its substitute(s) %s" % (r_, missing or v_.get("generationSafeSubstitutes")))
    for r_, v_ in roles["roles"].items():
        if v_.get("availability") == "blocked":
            for nid, nd in schema["definitions"].items():
                if not nid.startswith("node__"):
                    continue
                ct = nd["properties"]["content"]
                for k, sub in ct["properties"].items():
                    if r_ in json.dumps(sub) and k in ct["required"]:
                        probs.append("blocked role %s sits in required field %s of %s: a generated page could not omit it" % (r_, k, nid))
    if sorted(schema["properties"]["mode"]["enum"]) != ["generated", "reference"]:
        probs.append("schema mode enum must be exactly ['reference', 'generated'], found %s" % schema["properties"]["mode"]["enum"])
    if "mode" not in schema["required"]:
        probs.append("schema must require 'mode'")
    if sorted(k for k in roles["modes"] if k != "field") != sorted(schema["properties"]["mode"]["enum"]):
        probs.append("asset-roles modes keys differ from the schema mode enum")
    if example.get("mode") != "reference" or example.get("contentProvenance") != "evidence-reference":
        probs.append("schema/example.pagespec.json must declare mode 'reference' with contentProvenance 'evidence-reference'")
    for tid in templates["templates"]:
        gp = os.path.join(REPO, "schema", "examples", "generated.%s.pagespec.json" % tid)
        if not os.path.isfile(gp):
            probs.append("schema/examples/generated.%s.pagespec.json is missing: every template needs a generation-safe example" % tid)
            continue
        gs = J(os.path.relpath(gp, REPO))
        if gs.get("mode") != "generated" or gs.get("contentProvenance") != "generated":
            probs.append("generated example for %s must declare mode 'generated' and contentProvenance 'generated'" % tid)
        if gs.get("template") != tid:
            probs.append("generated example %s declares template %s" % (os.path.basename(gp), gs.get("template")))
        for path_, d_ in sv.iter_dicts(gs):
            if "assetRole" in d_ and roles["roles"].get(d_["assetRole"], {}).get("availability") != "generation-safe":
                probs.append("generated example %s uses non-generation-safe role %s at %s" % (os.path.basename(gp), d_["assetRole"], path_))
    sb = roles.get("sourceBrand", {})
    norm_ = lambda t_: " ".join(sv._words(t_))
    if sorted(norm_(t_) for t_ in sb.get("names", [])) != sorted(norm_(t_) for t_ in roles["brandTextDenylist"]["terms"]):
        probs.append("sourceBrand.names differ from brandTextDenylist.terms")
    ref_texts = [norm_(t_) for t_ in sv.iter_text(example)]
    for ph in sb.get("signatureCopy", []):
        if not any(norm_(ph) in rt for rt in ref_texts):
            probs.append("sourceBrand.signatureCopy %r does not occur in the reference example (not real source copy)" % ph)
    if len(sb.get("signatureCopy", [])) < 6:
        probs.append("sourceBrand.signatureCopy must keep at least 6 phrases")
    deny_blob = " ".join(roles["refDenylist"]["terms"]).lower() + " " + manifest["source"]["url"].lower()
    tlds = set(sb.get("urlLikeTlds", []))
    for h_ in sb.get("hosts", []):
        if h_.lower() not in deny_blob:
            probs.append("sourceBrand host %r is not evidenced by refDenylist or manifest.source.url" % h_)
        if h_.rsplit(".", 1)[-1] not in tlds:
            probs.append("sourceBrand host %r has a TLD missing from urlLikeTlds" % h_)
    if manifest["source"]["url"].split("//")[1].split("/")[0].replace("www.", "") not in sb.get("hosts", []):
        probs.append("manifest source host is not in sourceBrand.hosts")
    if sb.get("reservedPlaceholderDomains") != [".example", ".invalid"]:
        probs.append("sourceBrand.reservedPlaceholderDomains must be ['.example', '.invalid']")
    if not {"com", "co", "org", "net", "io", "example", "invalid"} <= tlds:
        probs.append("sourceBrand.urlLikeTlds lost a common TLD")
    co = sb.get("copyOverlap", {})
    if co.get("shingleWords") != 4 or co.get("minWholeStringWords") != 2 or co.get("referenceExample") != "schema/example.pagespec.json":
        probs.append("sourceBrand.copyOverlap must stay {referenceExample schema/example.pagespec.json, shingleWords 4, minWholeStringWords 2}")
    try:
        sv_repo = sv.load_repo(REPO)
        if len(sv_repo["reference"]["shingles"]) < 100 or len(sv_repo["reference"]["whole"]) < 40:
            probs.append("reference copy corpus is implausibly small (%d shingles, %d strings)" % (len(sv_repo["reference"]["shingles"]), len(sv_repo["reference"]["whole"])))
    except Exception as ex_:  # noqa
        probs.append("reference corpus failed to build: %s" % ex_)
    check("asset availability pinned + reference/generated modes (%d roles: %d reference-only, %d generation-safe, %d blocked; %d generated example(s))" % (
        len(roles["roles"]), real["referenceOnlyAssetRoles"], real["generationSafeAssetRoles"], real["blockedAssetRoles"], len(gen_examples)), probs)

    # 22. validator canaries: the validator must still REJECT each token / mode failure (a no-op validator cannot pass this)
    import copy as _copy
    probs = []
    crepo = sv.load_repo(REPO)
    gen0 = J(os.path.relpath(gen_examples[0], REPO)) if gen_examples else None

    def rules_of(spec_):
        return {r_ for r_, _ in sv.validate(spec_, crepo)[0]}

    def mut(base, fn):
        b = _copy.deepcopy(base)
        fn(b)
        return b
    canaries = [
        ("TOKEN_RAW_COLOR", mut(example, lambda s_: s_["tokens"].__setitem__("surface", "#0c0c0c"))),
        ("TOKEN_UNKNOWN", mut(example, lambda s_: s_["tokens"].__setitem__("surface", "semantic.surface.nope"))),
        ("TOKEN_ARBITRARY_SPACING", mut(example, lambda s_: s_["tokens"].__setitem__("sectionPadding", "24px"))),
        ("TOKEN_UNSUPPORTED_FONT", mut(example, lambda s_: s_["tokens"].__setitem__("fontSans", "Comic Sans MS"))),
        ("TOKEN_SLOT_MISMATCH", mut(example, lambda s_: s_["tokens"].__setitem__("surface", "typography.fontFamily.sans"))),
        ("TOKEN_THEME_COMBINATION", mut(example, lambda s_: s_["tokens"].__setitem__("text", "semantic.text.onButtonHover"))),
        ("TOKEN_NOT_APPROVED", mut(example, lambda s_: s_["tokens"].__setitem__("border", "semantic.border.inputFocus"))),
        ("MODE_PROVENANCE_MISMATCH", mut(example, lambda s_: s_.__setitem__("mode", "generated"))),
    ]
    if gen0 is not None:
        def set_logo(s_):
            for n_ in s_["nodes"]:
                if n_["section"] == "shell.nav":
                    n_["content"]["logo"]["assetRole"] = "brand.logo-mark"
        def set_label(txt):
            def f(s_):
                for n_ in s_["nodes"]:
                    if n_["section"] == "hero.course-intro":
                        n_["content"]["cta"]["label"] = txt
            return f
        canaries += [
            ("GENERATED_MODE_REFERENCE_ASSET", mut(gen0, set_logo)),
            ("GENERATED_MODE_SOURCE_COPY", mut(gen0, set_label("Join Waitlist"))),  # whole-string rule only (2 words, not a signature phrase)
            ("GENERATED_MODE_SOURCE_COPY", mut(gen0, set_label("Includes early access to discord for all"))),  # 4-word-run rule only
            ("GENERATED_MODE_SOURCE_COPY", mut(gen0, set_label("Lock price at $48"))),  # signature-phrase rule only
            ("GENERATED_MODE_SOURCE_URL", mut(gen0, set_label("thecodeflow.co"))),
            ("GENERATED_MODE_URL_NOT_RESERVED", mut(gen0, set_label("shop.io"))),
            ("BRAND_PASSOFF", mut(gen0, lambda s_: s_.__setitem__("route", "/codeflow"))),
        ]
    for rule_, spec_ in canaries:
        if rule_ not in rules_of(spec_):
            probs.append("validator no longer raises %s on a spec built to violate it" % rule_)
    for name_, spec_ in [("reference example", example)] + [(os.path.basename(g_), J(os.path.relpath(g_, REPO))) for g_ in gen_examples]:
        if rules_of(spec_):
            probs.append("%s no longer validates cleanly: %s" % (name_, sorted(rules_of(spec_))))
    check("validator canaries: %d token/mode failures still rejected, examples still clean" % len(canaries), probs)

    # 23. hygiene: no absolute machine paths, no junk files
    probs = []
    pats = ["/" + "Users/", "/" + "home/", "C:" + "\\" + "Users"]
    for p in glob.glob(os.path.join(REPO, "**", "*"), recursive=True) + glob.glob(os.path.join(REPO, "**", ".*"), recursive=True):
        base = os.path.basename(p)
        if base in (".DS_Store", "Thumbs.db", "desktop.ini", "__MACOSX", "__pycache__") or base.endswith(".pyc"):
            probs.append("junk: %s" % os.path.relpath(p, REPO))
            continue
        if os.path.isfile(p):
            with open(p, encoding="utf-8", errors="ignore") as f:
                txt = f.read()
            for pat in pats:
                if pat in txt:
                    probs.append("absolute path %r in %s" % (pat, os.path.relpath(p, REPO)))
    check("no absolute machine paths, no junk files", probs)

    return finish()


def finish():
    for s, n, d in RESULTS:
        print("[%s] %s%s" % (s, n, (" -- " + d) if d else ""))
    fails = sum(1 for r in RESULTS if r[0] == "FAIL")
    warns = sum(1 for r in RESULTS if r[0] == "WARN")
    print("\nverify_all: %d checks, %d FAIL, %d WARN" % (len(RESULTS), fails, warns))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
