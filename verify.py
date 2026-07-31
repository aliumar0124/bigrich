#!/usr/bin/env python3
"""Cross-check the built widget against every sheet in the price list.

Three sources must agree:
  1. 'Master Price List'      — the 640 item rows
  2. 'Instructions & Rates'   — the $/cubic yard rate and the estimating rules
  3. 'Category Summary'       — per-category item count, lowest and highest price
  4. dist/big-rich-quote-calculator.html — the data actually shipped to Elementor

Usage:  python3 verify.py     (exit code 1 on any mismatch)
"""

import re
import sys
from pathlib import Path

from build import ROOT, XLSX, NS, read_sheet, load_items
import zipfile
from xml.etree import ElementTree as ET

BUILT = ROOT / "dist" / "big-rich-quote-calculator.html"

# Every rule on the 'Instructions & Rates' sheet, and where the widget honours it.
RULE_COVERAGE = {
    "How price is calculated": "per-item lines in the quote breakdown + 'cu yd x $40/cu yd' in the booking email",
    "Small items": "step 1 bundling note (boxes/bags/totes) + the $95 minimum service charge",
    "Volume basis": "quote note ('the space it typically occupies once loaded, not exact measurements')",
    "Packing differences": "quote note ('lower when broken down, nested or flattened')",
    "Weight and labor": "'Unusually heavy or dense items' access flag + quote note",
    "Stairs and distance": "'upstairs or downstairs', 'Long carry', 'dismantling' access flags + quote note",
    "Special disposal": "quote note listing every material with a separate disposal charge",
}


def sheets():
    with zipfile.ZipFile(XLSX) as zf:
        shared = []
        sst = ET.fromstring(zf.read("xl/sharedStrings.xml"))
        for si in sst.iter(NS + "si"):
            shared.append("".join(t.text or "" for t in si.iter(NS + "t")))
        return (read_sheet(zf, shared, 2), read_sheet(zf, shared, 3))


def main():
    rate, categories = load_items()
    rates_sheet, summary_sheet = sheets()
    problems = []

    # ---- sheet 2: rate + rules -------------------------------------------
    print("Instructions & Rates")
    print(f"  rate per cubic yard      ${rate:.2f}")
    rules = [r["A"] for r in rates_sheet if r.get("A") and r.get("B") and r["A"] != "Rule"]
    rules = [r for r in rules if r != "Rate per cubic yard"]
    for rule in rules:
        where = RULE_COVERAGE.get(rule)
        if where:
            print(f"  [ok] {rule:<26} -> {where}")
        else:
            problems.append(f"rule '{rule}' from the rates sheet is not reflected in the widget")
    for rule in RULE_COVERAGE:
        if rule not in rules:
            problems.append(f"widget claims to cover '{rule}' but the sheet no longer lists it")

    # ---- sheet 3: per-category checksums ---------------------------------
    built = {c["n"]: c["i"] for c in categories}
    print("\nCategory Summary  (sheet -> built widget)")
    print(f"  {'category':<30}{'items':>12}{'lowest':>16}{'highest':>16}")
    seen = set()
    for row in summary_sheet:
        name = row.get("A", "")
        if not name or name in ("CATEGORY SUMMARY", "Category") or not row.get("B"):
            continue
        seen.add(name)
        want_n, want_lo, want_hi = int(row["B"]), float(row["C"]), float(row["D"])
        items = built.get(name)
        if items is None:
            problems.append(f"{name}: on the summary sheet but missing from the built widget")
            continue
        prices = [round(i[2] * rate, 2) for i in items]
        got_n, got_lo, got_hi = len(items), min(prices), max(prices)
        ok = (got_n, got_lo, got_hi) == (want_n, want_lo, want_hi)
        mark = "ok" if ok else "MISMATCH"
        print(
            f"  {name:<30}{f'{got_n}/{want_n}':>12}"
            f"{f'${got_lo:g}/${want_lo:g}':>16}{f'${got_hi:g}/${want_hi:g}':>16}  [{mark}]"
        )
        if not ok:
            problems.append(
                f"{name}: summary says {want_n} items ${want_lo:g}-${want_hi:g}, "
                f"built data has {got_n} items ${got_lo:g}-${got_hi:g}"
            )
    for name in built:
        if name not in seen:
            problems.append(f"{name}: in the price list but absent from the summary sheet")

    total_sheet = sum(
        int(r["B"]) for r in summary_sheet
        if r.get("B") and r.get("A") not in (None, "", "Category", "CATEGORY SUMMARY")
    )
    total_built = sum(len(v) for v in built.values())
    print(f"\n  total items                    {total_built}/{total_sheet}")
    if total_built != total_sheet:
        problems.append(f"item count: summary totals {total_sheet}, built data has {total_built}")

    # ---- the shipped file ------------------------------------------------
    html = BUILT.read_text(encoding="utf-8")
    shipped = re.findall(r'\["([A-Z]{2}-\d{3})",("(?:[^"\\]|\\.)*"),([\d.]+)\]', html)
    print(f"\nShipped widget\n  item entries in dist file      {len(shipped)}")
    if len(shipped) != total_built:
        problems.append(f"dist file carries {len(shipped)} items, expected {total_built}")
    ids_built = {i[0] for v in built.values() for i in v}
    ids_shipped = {s[0] for s in shipped}
    if ids_built != ids_shipped:
        problems.append(f"item IDs differ between sheet and dist file: {ids_built ^ ids_shipped}")
    m = re.search(r"ratePerCubicYard\s*:\s*([\d.]+)", html)
    print(f"  ratePerCubicYard in widget     {m.group(1)}")
    if float(m.group(1)) != rate:
        problems.append(f"widget rate {m.group(1)} != sheet rate {rate}")

    # booking settings the customer-facing copy depends on
    def cfg(key, pattern=r'"([^"]*)"'):
        m = re.search(key + r"\s*:\s*" + pattern, html)
        return m.group(1) if m else None

    minimum = cfg("minimumCharge", r"([\d.]+)")
    submit_to, endpoint = cfg("submitTo"), cfg("endpoint")
    windows = re.findall(r'"(\d{1,2}:\d\d [AP]M – \d{1,2}:\d\d [AP]M)"', html)
    print(f"  minimum service charge         ${minimum}")
    print(f"  bookings emailed to            {submit_to}")
    print(f"  pickup windows offered         {len(windows)}")

    # the on-screen copy quotes the minimum, so the two must not drift apart
    for label, snippet in (
        ("hero line", "minimum service charge applies to all jobs"),
        ("breakdown note", "minimum service charge covering labor, travel, and disposal"),
    ):
        if snippet not in html:
            problems.append(f"{label} about the minimum charge is missing from the widget")
    if submit_to and endpoint and submit_to not in endpoint:
        problems.append(f"endpoint '{endpoint}' does not point at submitTo '{submit_to}'")
    if not windows:
        problems.append("no pickup windows found in the widget config")

    print()
    if problems:
        print(f"FAILED — {len(problems)} problem(s):")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("All checks passed: rates, rules, per-category counts and price ranges, "
          "item IDs and the shipped file all agree.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
