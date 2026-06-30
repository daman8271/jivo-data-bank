#!/usr/bin/env python3
"""Helper for coverage_sync.sh.
  dedup <src.csv> <out.csv>  -> write latest-per-(pincode,platform) ledger; print: MAXDATE NPLAT NCELLS SIG
  sig   <file.csv>           -> print a content signature (sha256 of sorted cell identities), or 'none'
Signature ignores cosmetic formatting; it captures the actual coverage data (pincode,platform,status,date,run)."""
import csv, sys, hashlib

COLS = ["platform","pincode","city","date_ist","run_id","status","sku_count","price_seen"]

def signature(rows):
    s = "".join(sorted("%s,%s,%s,%s,%s\n" % (r["pincode"], r["platform"], r["status"],
                                              r["date_ist"], r["run_id"]) for r in rows))
    return hashlib.sha256(s.encode()).hexdigest()[:16]

def main():
    mode = sys.argv[1]
    if mode == "sig":
        try:
            rows = list(csv.DictReader(open(sys.argv[2])))
            print(signature(rows) if rows else "none")
        except Exception:
            print("none")
        return
    if mode == "dedup":
        src, out = sys.argv[2], sys.argv[3]
        rows = list(csv.DictReader(open(src)))
        latest = {}
        for r in rows:                              # keep newest run per pincode x platform
            k = (r["pincode"], r["platform"])
            if k not in latest or r["run_id"] > latest[k]["run_id"]:
                latest[k] = r
        recs = sorted(latest.values(), key=lambda r: (r["platform"], r["pincode"]))
        w = csv.DictWriter(open(out, "w", newline=""), fieldnames=COLS)
        w.writeheader()
        for r in recs:
            w.writerow({c: r.get(c, "") for c in COLS})
        maxdate = max(r["date_ist"] for r in recs)
        nplat = len(set(r["platform"] for r in recs))
        print(maxdate, nplat, len(recs), signature(recs))
        return
    sys.exit("usage: dedup <src> <out> | sig <file>")

if __name__ == "__main__":
    main()
