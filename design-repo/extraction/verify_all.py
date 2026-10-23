#!/usr/bin/env python3
"""One-shot verification for this design-repo. Exit 1 if any check FAILs.

Usage:
  python3 extraction/verify_all.py [--source-root PATH]

--source-root defaults to the folder containing design-repo/ (where the cited evidence lives).
If none of the cited evidence files exist there (design-repo shipped alone), the citation
check is downgraded to a WARN instead of failing.

Every drift-sensitive check here (allowlist parity, citation range + quote, allowlistVersion
parity, manifest counts, pinned asset policies, graph/validator agreement) is proven to fail
on injected drift by extraction/prove_drift.py.
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


def load_sv():
    spec = importlib.util.spec_from_file_location("semantic_validate", os.path.join(REPO, "schema", "semantic_validate.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


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
    errs = list(Draft7Validator(schema).iter_errors(example))
    probs += ["example: %s" % e.message[:200] for e in errs]
    check("schema Draft-07 (example: %d errors)" % len(errs), probs)

    # 3. semantic layer on the example
    e, w = sv.validate(example, sv.load_repo(REPO))
    check("semantic validator on example (%d errors, %d warnings)" % (len(e), len(w)), ["%s: %s" % x for x in e])

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
    if manifest.get("status") != "design-review-pending" or manifest.get("productionApproved") is not False:
        probs.append("manifest must be status design-review-pending and productionApproved false")
    check("version parity (allowlistVersion, pageSpecVersion) + status flags", probs)

    # 6. manifest counts recomputed from disk
    real = {
        "tokens": sum(token_leaves(J(os.path.relpath(p, REPO))) for d in ("00-foundation", "10-semantic", "20-component", "30-layout")
                      for p in glob.glob(os.path.join(REPO, "tokens", d, "*.json"))),
        "primitives": len(prims), "components": len(comps), "sections": len(sections),
        "sectionVariants": sum(len(c["variants"]) for c in sections.values()),
        "templates": len(templates["templates"]), "routes": len(templates["routes"]),
        "assetRoles": len(roles["roles"]), "pinnedAssetRoles": sum(1 for r in roles["roles"].values() if r.get("pinned")),
        "motionPatterns": len(motion["patterns"]), "compatibilityRules": len(graph["rules"]),
        "measuredValueEntries": len(ledger["entries"]),
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

    # 15. hygiene: no absolute machine paths, no junk files
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
