"""Shared token loader/resolver used by tokens/build_catalog.py, extraction/verify_all.py and
schema/semantic_validate.py.

A token is a JSON object that has both "value" and "evidence" (the repo-wide leaf rule; the same rule
extraction/verify_all.py uses to recompute the manifest token count). Token files under
tokens/{00-foundation,10-semantic,20-component,30-layout}/ merge into one tree by their root keys.
A path is the root key followed by the nested keys joined with ".", except in the files named in
PREFIX_FILES (typography.json, motion.json, breakpoint.json), whose root keys are nested under the file's
own name ("typography.fontFamily.sans", "motion.ease.expoOut", "breakpoint.deviceDetection"); this is the
convention the primitive/component contracts already use. Keys may themselves contain dots ("surface.page",
"button.pill"), so a path is resolved by trying the longest matching key at each level. A reference is
written {path}.
"""
import glob
import json
import os
import re

TOKENS = os.path.dirname(os.path.abspath(__file__))
LAYER_DIRS = ["00-foundation", "10-semantic", "20-component", "30-layout"]
PREFIX_FILES = ("typography", "motion", "breakpoint")
REF = re.compile(r"\{([^{}]+)\}")


def is_token(node):
    return isinstance(node, dict) and "value" in node and "evidence" in node


def load_tree(tokens_dir=None):
    """Merge every token file into one tree. Returns (tree, roots) where roots maps root key -> source files."""
    base = tokens_dir or TOKENS
    tree, roots = {}, {}
    for layer in LAYER_DIRS:
        for f in sorted(glob.glob(os.path.join(base, layer, "*.json"))):
            with open(f, encoding="utf-8") as fh:
                d = json.load(fh)
            stem = os.path.splitext(os.path.basename(f))[0]
            rel = os.path.relpath(f, base).replace(os.sep, "/")
            for k, v in d.items():
                if k.startswith("$"):
                    continue
                if stem in PREFIX_FILES:
                    target = tree.setdefault(stem, {})
                    items = v.items() if k == stem else [(k, v)]
                    for kk, vv in items:
                        if kk in target:
                            raise ValueError("duplicate token key %r under %r (%s)" % (kk, stem, rel))
                        target[kk] = vv
                    roots.setdefault(stem, []).append(rel)
                else:
                    roots.setdefault(k, []).append(rel)
                    if k in tree:
                        raise ValueError("duplicate token root %r (%s)" % (k, ", ".join(roots[k])))
                    tree[k] = v
    return tree, roots


def lookup(tree, path):
    """Return the node at dotted `path` or raise KeyError."""
    parts = path.split(".")

    def go(node, i):
        if i == len(parts):
            return node
        if not isinstance(node, dict):
            raise KeyError(path)
        for j in range(len(parts), i, -1):
            key = ".".join(parts[i:j])
            if key in node:
                try:
                    return go(node[key], j)
                except KeyError:
                    continue
        raise KeyError(path)

    return go(tree, 0)


def walk_tokens(tree, prefix=""):
    """Yield (path, node) for every token leaf, in file order."""
    for k, v in tree.items():
        if k.startswith("$"):
            continue
        p = prefix + "." + k if prefix else k
        if is_token(v):
            yield p, v
        elif isinstance(v, dict):
            for x in walk_tokens(v, p):
                yield x


def refs_in(value):
    if isinstance(value, str):
        for r in REF.findall(value):
            yield r
    elif isinstance(value, dict):
        for v in value.values():
            for r in refs_in(v):
                yield r
    elif isinstance(value, list):
        for v in value:
            for r in refs_in(v):
                yield r


def resolve_value(tree, node, trail=()):
    """Resolve a token's value, following whole-value references; embedded references stay as written."""
    v = node["value"] if is_token(node) else node
    if isinstance(v, str):
        m = REF.fullmatch(v)
        if m:
            p = m.group(1)
            if p in trail:
                raise ValueError("reference cycle: " + " -> ".join(trail + (p,)))
            return resolve_value(tree, lookup(tree, p), trail + (p,))
        return v
    if isinstance(v, list):
        return [resolve_value(tree, x, trail) if isinstance(x, (str, dict, list)) else x for x in v]
    if isinstance(v, dict):
        return {k: resolve_value(tree, x, trail) if isinstance(x, (str, dict, list)) else x for k, x in v.items()}
    return v
