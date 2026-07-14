#!/usr/bin/env python3
"""
verify_databank.py — FAIL-CLOSED accuracy gate for the JIVO Data Bank.

Run after a rebuild, before any commit. Exit 0 only if EVERY gate passes;
exit 1 on any loss/regression. Accuracy at all costs: stale-but-correct beats
fresh-but-wrong.

Gates
-----
1. ZERO-LOSS (from .manifest.json, written by combined_backbone.py):
     * summary.zero_loss_ok is true
     * for each vault: original_prefix_preserved_all, n_altered==0,
       n_truncated==0, no missing_in_dest, no extra_in_dest
     * combined_dest_notes == jivo_source_notes + ecom_source_notes
2. STRUCTURE / REGRESSION (vs bin/.baseline.json, if present):
     * Home.md exists and is non-trivial
     * exactly 10 Platform hubs and 3 Tier hubs (the fixed backbone)
     * >= 1 Category hub
     * product count and source-note count do NOT drop below baseline
       (growth is fine; shrinkage is treated as loss)
3. LINK INTEGRITY ("link verification"):
     * every wikilink emitted in the GENERATED layer (Home.md, products/, hubs/)
       resolves to a real note in the vault (Obsidian basename or vault-relative
       path resolution). Any unresolved target = FAIL.

Usage:
  verify_databank.py [--vault DIR] [--update-baseline]
"""
import argparse
import json
import os
import re
import sys

WIKILINK_RE = re.compile(r"!?\[\[([^\[\]]+?)\]\]")


def norm_target(raw):
    """Wikilink inner -> comparable lowercase target (path or basename, no .md)."""
    t = raw.replace("\\|", "|").split("|", 1)[0]   # drop alias (handles table \|)
    t = t.split("#", 1)[0].split("^", 1)[0]        # drop heading / block ref
    t = t.strip().rstrip("\\").strip()
    if t.startswith("./"):
        t = t[2:]
    if t.lower().endswith(".md"):
        t = t[:-3]
    return t.lower()


def build_index(vault):
    """Index every note: by vault-relative path (no .md) and by basename."""
    by_path = set()
    by_base = set()
    for dp, dns, fns in os.walk(vault):
        dns[:] = [d for d in dns if not d.startswith(".")]  # skip .links, .git, .obsidian
        for fn in fns:
            if not fn.endswith(".md"):
                continue
            rel = os.path.relpath(os.path.join(dp, fn), vault).replace(os.sep, "/")
            by_path.add(rel[:-3].lower())
            by_base.add(fn[:-3].lower())
    return by_path, by_base


def resolve(target, by_path, by_base):
    if target in by_path:
        return True
    if "/" in target:
        return os.path.basename(target) in by_base
    return target in by_base


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--baseline", default=None,
                    help="path to .baseline.json (default: <vault>/bin/.baseline.json)")
    ap.add_argument("--update-baseline", action="store_true")
    args = ap.parse_args()

    vault = os.path.abspath(args.vault)
    manifest_p = os.path.join(vault, ".manifest.json")
    baseline_p = os.path.abspath(args.baseline) if args.baseline \
        else os.path.join(vault, "bin", ".baseline.json")
    failures = []
    info = {}

    # ---------------- GATE 1: zero-loss ----------------
    if not os.path.isfile(manifest_p):
        failures.append("manifest missing: .manifest.json")
        manifest = {}
    else:
        manifest = json.load(open(manifest_p))
    summary = manifest.get("summary", {})
    if not summary.get("zero_loss_ok"):
        failures.append("zero_loss_ok is not true (lossless proof failed)")
    for vname, v in manifest.get("vaults", {}).items():
        loss = v.get("lossless", {})
        if not loss.get("original_prefix_preserved_all"):
            failures.append(f"[{vname}] original_prefix_preserved_all is false")
        if loss.get("n_altered"):
            failures.append(f"[{vname}] {loss['n_altered']} altered file(s)")
        if loss.get("n_truncated"):
            failures.append(f"[{vname}] {loss['n_truncated']} truncated file(s)")
        if loss.get("missing_in_dest"):
            failures.append(f"[{vname}] {len(loss['missing_in_dest'])} missing-in-dest")
        if loss.get("extra_in_dest"):
            failures.append(f"[{vname}] {len(loss['extra_in_dest'])} extra-in-dest")
    # Sum across ALL pillars (jivo + ecom + factory + any future) so the
    # combined dest count is checked against the true source total.
    src_total = sum(v.get("source", {}).get("count", 0)
                    for v in manifest.get("vaults", {}).values())
    dn = summary.get("combined_dest_notes", 0)
    if src_total and dn != src_total:
        failures.append(f"combined_dest_notes {dn} != sum of vault source counts {src_total}")
    info["source_notes"] = src_total
    info["pillars"] = summary.get("pillars", sorted(manifest.get("vaults", {}).keys()))

    # ---------------- GATE 2: structure / regression ----------------
    home_p = os.path.join(vault, "Home.md")
    if not (os.path.isfile(home_p) and os.path.getsize(home_p) > 500):
        failures.append("Home.md missing or trivially small")

    hub_dir = os.path.join(vault, "hubs")
    prod_dir = os.path.join(vault, "products")
    hubs = [f for f in os.listdir(hub_dir) if f.endswith(".md")] if os.path.isdir(hub_dir) else []
    prods = [f for f in os.listdir(prod_dir) if f.endswith(".md")] if os.path.isdir(prod_dir) else []
    n_platform = sum(1 for h in hubs if h.startswith("Platform - "))
    n_tier = sum(1 for h in hubs if h.startswith("Tier - "))
    n_category = sum(1 for h in hubs if h.startswith("Category - "))
    info.update({"products": len(prods), "hubs": len(hubs),
                 "platform_hubs": n_platform, "tier_hubs": n_tier,
                 "category_hubs": n_category})
    if n_platform != 10:
        failures.append(f"expected 10 Platform hubs, found {n_platform}")
    if n_tier != 3:
        failures.append(f"expected 3 Tier hubs, found {n_tier}")
    if n_category < 1:
        failures.append("no Category hubs found")

    try:
        baseline = json.load(open(baseline_p)) if os.path.isfile(baseline_p) else {}
    except (json.JSONDecodeError, ValueError):
        baseline = {}   # empty/corrupt baseline -> treat as no baseline (don't crash)
    if baseline:
        if len(prods) < baseline.get("products", 0):
            failures.append(f"product REGRESSION: {len(prods)} < baseline {baseline['products']}")
        if src_total < baseline.get("source_notes", 0):
            failures.append(f"source-note REGRESSION: {src_total} < baseline {baseline['source_notes']}")
        if len(hubs) < baseline.get("hubs", 0):
            failures.append(f"hub REGRESSION: {len(hubs)} < baseline {baseline['hubs']}")

    # ---------------- GATE 3: link integrity (generated layer) ----------------
    by_path, by_base = build_index(vault)
    broken = []
    checked = 0
    gen_files = [home_p] + [os.path.join(prod_dir, f) for f in prods] + \
                [os.path.join(hub_dir, f) for f in hubs]
    for fp in gen_files:
        try:
            txt = open(fp, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for m in WIKILINK_RE.finditer(txt):
            t = norm_target(m.group(1))
            if not t:
                continue
            checked += 1
            if not resolve(t, by_path, by_base):
                broken.append((os.path.relpath(fp, vault), m.group(1)))
    info["generated_links_checked"] = checked
    info["broken_links"] = len(broken)
    if broken:
        for f, tgt in broken[:20]:
            failures.append(f"broken link in {f}: [[{tgt}]]")
        if len(broken) > 20:
            failures.append(f"... and {len(broken) - 20} more broken links")

    ok = not failures
    verdict = {"PASS": ok, "info": info, "failures": failures}
    print(json.dumps(verdict, indent=2))

    if ok and args.update_baseline:
        os.makedirs(os.path.dirname(baseline_p), exist_ok=True)
        with open(baseline_p, "w") as f:
            json.dump({"products": len(prods), "hubs": len(hubs),
                       "source_notes": src_total}, f, indent=2)
            f.write("\n")
        print(f"[baseline] updated -> {baseline_p}", file=sys.stderr)

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
