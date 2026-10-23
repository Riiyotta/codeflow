#!/usr/bin/env python3
"""Whole-page-wrapper quality gate (a HERO that is really the page wrapper, or one section swallowing the page).

Reads measured heights from extraction/measured-values.json -> sectionHeights (written by the optional
extraction/measure_sections.mjs) and the reviewed exceptions in extraction/wrapper-whitelist.json.

Rules (code -> severity):
  HERO_HEIGHT_WARN      warn              a section whose semantic.category is 'hero' is taller than 1800px
  HERO_HEIGHT_FAIL      error             a hero section is taller than 3000px (unless whitelisted)
  SECTION_SHARE_WARN    warn              one in-flow section holds > 50% of the page's in-flow height
  SECTION_SHARE_FAIL    error             ... > 60% (unless whitelisted)
  MEASUREMENT_MISSING   error             a template node has no usable measurement, or a stale/extra one exists
  MEASUREMENT_INCONSISTENT error          wrong viewport, or in-flow heights do not add up to pageHeight (+-1%)
  WHITELIST_INVALID     error             malformed whitelist entry (missing/short justification, bad reviewer, no cap)
  WHITELIST_UNUSED      warn              whitelist entry that exempts nothing (stale)

The share rule needs at least 3 in-flow sections; a page with fewer has no meaningful share (it would
always be 100%), so the rule is skipped there and reported as skipped, never silently.
Fixed/absolute sections (nav bar, WebGL layer) take no page height and are excluded from the share.

Usage: python3 extraction/wrapper_gate.py      exit 1 if any error
"""
import sys
sys.dont_write_bytecode = True

import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

HERO_WARN_PX = 1800
HERO_FAIL_PX = 3000
SHARE_WARN = 0.50
SHARE_FAIL = 0.60
MIN_INFLOW_SECTIONS = 3
VIEWPORT_WIDTH = 1440
SUM_TOLERANCE = 0.01
MIN_JUSTIFICATION = 30
WHITELISTABLE = {"HERO_HEIGHT_FAIL", "SECTION_SHARE_FAIL"}
REVIEWER_PREFIXES = ("human:", "agent-attestation:")


def _load(rel, root):
    with open(os.path.join(root, rel), encoding="utf-8") as f:
        return json.load(f)


def evaluate(template_nodes, categories, heights, whitelist):
    """template_nodes: [{'section','variant',...}]; categories: {section id: semantic category};
    heights: the sectionHeights block; whitelist: list of entries. Returns (errors, warnings, info)
    where each item is (code, message)."""
    errors, warnings, info = [], [], []
    keys = ["%s/%s" % (n["section"], n["variant"]) for n in template_nodes]

    # --- whitelist validity -----------------------------------------------------
    allowed = {}
    for i, w in enumerate(whitelist or []):
        where = "whitelist[%d]" % i
        bad = []
        if not isinstance(w, dict) or not {"section", "variant", "rules", "maxHeightPx", "justification", "reviewer", "reviewedOn"} <= set(w):
            errors.append(("WHITELIST_INVALID", "%s needs section, variant, rules, maxHeightPx, justification, reviewer, reviewedOn" % where))
            continue
        k = "%s/%s" % (w["section"], w["variant"])
        if k not in keys:
            bad.append("%s is not a template node" % k)
        if not w["rules"] or not set(w["rules"]) <= WHITELISTABLE:
            bad.append("rules must be a non-empty subset of %s" % sorted(WHITELISTABLE))
        if not isinstance(w["maxHeightPx"], (int, float)) or isinstance(w["maxHeightPx"], bool) or w["maxHeightPx"] <= 0:
            bad.append("maxHeightPx must be a positive cap")
        if not isinstance(w["justification"], str) or len(w["justification"]) < MIN_JUSTIFICATION:
            bad.append("justification must be %d+ characters" % MIN_JUSTIFICATION)
        if not isinstance(w["reviewer"], str) or not w["reviewer"].startswith(REVIEWER_PREFIXES):
            bad.append("reviewer must start with one of %s" % (REVIEWER_PREFIXES,))
        if bad:
            errors.append(("WHITELIST_INVALID", "%s (%s): %s" % (where, k, "; ".join(bad))))
            continue
        allowed[k] = w
    used = set()

    # --- measurements present and sane ------------------------------------------
    secs = (heights or {}).get("sections", {}) if isinstance(heights, dict) else {}
    if not secs:
        errors.append(("MEASUREMENT_MISSING", "no sectionHeights.sections in measured-values.json (run extraction/measure_sections.mjs --write)"))
        return errors, warnings, info
    usable = {}
    for k in keys:
        m = secs.get(k)
        h = m.get("heightPx") if isinstance(m, dict) else None
        if not isinstance(h, (int, float)) or isinstance(h, bool) or h <= 0 or not isinstance(m.get("inFlow"), bool):
            errors.append(("MEASUREMENT_MISSING", "%s has no usable measurement (heightPx > 0 and boolean inFlow required)" % k))
        else:
            usable[k] = m
    for k in sorted(set(secs) - set(keys)):
        errors.append(("MEASUREMENT_MISSING", "measurement %s matches no template node (stale)" % k))
    vp = heights.get("viewport", {})
    if vp.get("width") != VIEWPORT_WIDTH:
        errors.append(("MEASUREMENT_INCONSISTENT", "measured at viewport width %r, gate requires %d" % (vp.get("width"), VIEWPORT_WIDTH)))
    inflow = {k: m["heightPx"] for k, m in usable.items() if m["inFlow"]}
    total = sum(inflow.values())
    ph = heights.get("pageHeight")
    if len(usable) == len(keys):
        if not isinstance(ph, (int, float)) or ph <= 0 or abs(total - ph) > SUM_TOLERANCE * ph:
            errors.append(("MEASUREMENT_INCONSISTENT", "in-flow heights add up to %.1f but pageHeight is %r (tolerance %d%%)" % (total, ph, SUM_TOLERANCE * 100)))

    def judge(k, code, msg, hpx):
        # only the two *_FAIL rules go through here; a valid whitelist entry downgrades them to a warning
        w = allowed.get(k)
        if w and code in w["rules"] and hpx <= w["maxHeightPx"]:
            used.add(k)
            warnings.append((code + "_WHITELISTED", "%s (exempted by %s, cap %spx)" % (msg, w["reviewer"], w["maxHeightPx"])))
        else:
            errors.append((code, msg))

    # --- HERO rule --------------------------------------------------------------
    for k, m in usable.items():
        if categories.get(k.split("/")[0]) != "hero":
            continue
        h = m["heightPx"]
        if h > HERO_FAIL_PX:
            judge(k, "HERO_HEIGHT_FAIL", "%s is classed hero but is %.0fpx tall (> %d): that is a page wrapper, not a hero" % (k, h, HERO_FAIL_PX), h)
        elif h > HERO_WARN_PX:
            warnings.append(("HERO_HEIGHT_WARN", "%s is classed hero and %.0fpx tall (> %d)" % (k, h, HERO_WARN_PX)))

    # --- share rule -------------------------------------------------------------
    if len(inflow) < MIN_INFLOW_SECTIONS:
        info.append("share rule skipped: only %d in-flow section(s), need %d" % (len(inflow), MIN_INFLOW_SECTIONS))
    elif total > 0:
        for k, h in sorted(inflow.items()):
            share = h / total
            if share > SHARE_FAIL:
                judge(k, "SECTION_SHARE_FAIL", "%s holds %.0f%% of the in-flow page height (> %d%%)" % (k, share * 100, SHARE_FAIL * 100), h)
            elif share > SHARE_WARN:
                warnings.append(("SECTION_SHARE_WARN", "%s holds %.0f%% of the in-flow page height (> %d%%)" % (k, share * 100, SHARE_WARN * 100)))

    for k in sorted(set(allowed) - used):
        warnings.append(("WHITELIST_UNUSED", "whitelist entry for %s exempts nothing at its measured height (stale?)" % k))
    return errors, warnings, info


def load_inputs(root=None):
    root = root or REPO
    ledger = _load("extraction/measured-values.json", root)
    templates = _load("templates/templates.json", root)
    wl = _load("extraction/wrapper-whitelist.json", root)
    cats = {}
    sdir = os.path.join(root, "sections")
    for fn in sorted(os.listdir(sdir)):
        if fn.endswith(".json"):
            c = _load(os.path.join("sections", fn), root)
            cats[c["id"]] = (c.get("semantic") or {}).get("category")
    nodes = [n for t in templates["templates"].values() for n in t["nodes"]]
    return nodes, cats, ledger.get("sectionHeights"), wl.get("entries", [])


def main():
    errs, warns, info = evaluate(*load_inputs())
    for c, m in errs:
        print("ERROR %s: %s" % (c, m))
    for c, m in warns:
        print("WARN  %s: %s" % (c, m))
    for m in info:
        print("INFO  %s" % m)
    print("wrapper_gate: %d error(s), %d warning(s)" % (len(errs), len(warns)))
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
