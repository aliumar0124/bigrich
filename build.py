#!/usr/bin/env python3
"""Build the Big Rich Hauling quote calculator widget.

Reads the master household price list spreadsheet, and injects its items into
src/calculator.template.html to produce the paste-ready Elementor HTML widget
at dist/big-rich-quote-calculator.html.

Usage:  python3 build.py
Only the standard library is used (zipfile + xml), so no pip install is needed.
"""

import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).parent
XLSX = ROOT / "data" / "Big_Rich_Hauling_Master_Household_Item_Price_List.xlsx"
TEMPLATE = ROOT / "src" / "calculator.template.html"
OUT = ROOT / "dist" / "big-rich-quote-calculator.html"

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

# Emoji shown on each category tab. Categories missing here fall back to a box.
CATEGORY_EMOJI = {
    "Living Room": "\U0001F6CB️",
    "Bedroom": "\U0001F6CF️",
    "Dining Room": "\U0001F37D️",
    "Kitchen": "\U0001F373",
    "Bathroom": "\U0001F6BF",
    "Laundry Room": "\U0001F9FA",
    "Home Office": "\U0001F4BC",
    "Electronics": "\U0001F5A5️",
    "Garage & Storage": "\U0001F4E6",
    "Tools": "\U0001F527",
    "Patio & Outdoor": "\U0001F333",
    "Exercise & Recreation": "\U0001F3CB️",
    "Baby & Kids": "\U0001F9F8",
    "Clothing, Linens & Personal": "\U0001F455",
    "Books, Media & Decor": "\U0001F4DA",
    "Pet Supplies": "\U0001F43E",
    "Holiday & Seasonal": "\U0001F384",
    "Musical Instruments": "\U0001F3B8",
    "Construction & Remodeling": "\U0001F9F1",
    "Miscellaneous Household": "\U0001F3E0",
}


def read_sheet(zf, shared, index):
    """Return the sheet's rows as a list of {column_letter: value} dicts."""
    sheet = ET.fromstring(zf.read(f"xl/worksheets/sheet{index}.xml"))
    rows = []
    for row in sheet.iter(NS + "row"):
        cells = {}
        for cell in row.iter(NS + "c"):
            ref = cell.get("r")
            col = "".join(ch for ch in ref if ch.isalpha())
            kind = cell.get("t")
            value = cell.find(NS + "v")
            if kind == "s":
                cells[col] = shared[int(value.text)]
            elif kind == "inlineStr":
                cells[col] = "".join(t.text or "" for t in cell.iter(NS + "t"))
            else:
                cells[col] = value.text if value is not None else ""
        rows.append(cells)
    return rows


def load_items():
    """Parse the spreadsheet into (rate_per_cubic_yard, ordered category list)."""
    with zipfile.ZipFile(XLSX) as zf:
        shared = []
        sst = ET.fromstring(zf.read("xl/sharedStrings.xml"))
        for si in sst.iter(NS + "si"):
            shared.append("".join(t.text or "" for t in si.iter(NS + "t")))
        price_rows = read_sheet(zf, shared, 1)
        rate_rows = read_sheet(zf, shared, 2)

    rate = None
    for row in rate_rows:
        if str(row.get("A", "")).strip().lower() == "rate per cubic yard":
            rate = float(row.get("B"))
    if rate is None:
        raise SystemExit("Could not find 'Rate per cubic yard' on the rates sheet")

    categories, order = {}, []
    for row in price_rows:
        item_id, category, name = row.get("A", ""), row.get("B", ""), row.get("C", "")
        cubic_yards, price = row.get("D", ""), row.get("E", "")
        if not (item_id and category and name and cubic_yards):
            continue  # title rows, header row, blank spacers
        if item_id == "Item ID":
            continue
        cubic_yards = float(cubic_yards)
        # The widget derives price from volume, so make sure the sheet agrees.
        if price not in ("", None) and abs(float(price) - cubic_yards * rate) > 0.005:
            raise SystemExit(
                f"{item_id} '{name}': sheet price {price} != {cubic_yards} cu yd x {rate}. "
                "The widget computes price from volume — reconcile the sheet first."
            )
        if category not in categories:
            categories[category] = []
            order.append(category)
        categories[category].append([item_id, name, cubic_yards])

    return rate, [
        {"n": c, "e": CATEGORY_EMOJI.get(c, "\U0001F4E6"), "i": categories[c]}
        for c in order
    ]


def as_js(categories):
    """Compact, readable JS literal — one line per category."""
    out = ["["]
    for idx, cat in enumerate(categories):
        items = ",".join(
            "[" + json.dumps(i[0]) + "," + json.dumps(i[1], ensure_ascii=False) + "," + trim(i[2]) + "]"
            for i in cat["i"]
        )
        comma = "," if idx < len(categories) - 1 else ""
        out.append(
            "    {n:"
            + json.dumps(cat["n"], ensure_ascii=False)
            + ',e:"'
            + cat["e"]
            + '",i:['
            + items
            + "]}"
            + comma
        )
    out.append("  ]")
    return "\n".join(out)


def trim(number):
    """0.75 -> '.75', 1.0 -> '1' (keeps the generated data block small)."""
    text = ("%f" % number).rstrip("0").rstrip(".")
    return text[1:] if text.startswith("0.") else text


def main():
    rate, categories = load_items()
    template = TEMPLATE.read_text(encoding="utf-8")

    start, end = "/*__BRH_DATA__*/", "/*__END__*/"
    head, _, rest = template.partition(start)
    _, _, tail = rest.partition(end)
    if not tail:
        raise SystemExit("Data placeholder missing from the template")

    html = head + as_js(categories) + tail
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")

    # Standalone page for previewing in a browser without WordPress.
    preview = OUT.parent / "preview.html"
    preview.write_text(
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        "<title>Big Rich Hauling — quote calculator preview</title>\n"
        "<style>body{margin:0;padding:28px 16px;background:#EEF0F2;}</style>\n"
        "</head>\n<body>\n" + html + "\n</body>\n</html>\n",
        encoding="utf-8",
    )

    total = sum(len(c["i"]) for c in categories)
    print(f"rate            ${rate:.2f} per cubic yard")
    print(f"categories      {len(categories)}")
    print(f"items           {total}")
    print(f"wrote           {OUT.relative_to(ROOT)}  ({len(html) / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
