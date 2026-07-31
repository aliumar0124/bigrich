# Big Rich Hauling — Instant Quote Calculator

A self-contained pricing calculator for **bigrichhauling.com**, built to drop straight into an
Elementor **HTML** widget. A customer picks their items, answers two quick questions and gets a
real dollar estimate without calling anyone.

Pricing comes from `Big_Rich_Hauling_Master_Household_Item_Price_List.xlsx`:
**640 items across 20 categories at $40 per cubic yard.**

---

## Install (Elementor)

1. Edit the page in Elementor.
2. Drag in the **HTML** widget (Elementor → General → HTML).
3. Open **`dist/big-rich-quote-calculator.html`**, copy the whole file, paste it into the widget's
   *HTML Code* box.
4. Update the page. Done — nothing else to install, no plugin, no external requests.

To preview it outside WordPress, open `dist/preview.html` in any browser.

---

## What the customer sees

| Step | What happens |
|------|--------------|
| **1. Your items** | Search all 640 items or browse 20 room tabs (plus a *Popular items* tab). Quantity steppers, live running total, and a truck-load meter. |
| **2. Access & extras** | Optional toggles for stairs, long carry, disassembly, unusually heavy items, and same-day service. |
| **3. Your details** | Name, phone, email, ZIP, address, preferred date and time window, notes. Validated before continuing. |
| **4. Your estimate** | Big headline price, a ±10% range, a full itemized breakdown, and the calls to action (call, text, copy, print/PDF, and optionally email or webhook). |

## How the price is calculated

```
item price      = estimated cubic yards × $40            (straight from the master price list)
items subtotal  = sum of every line
base            = max(items subtotal, $125 minimum)
add-ons         = base × (sum of the checked percentages)
estimated total = base + add-ons
range shown     = total ±10%
```

Every price in the widget is derived from the item's cubic yards, so the spreadsheet stays the single
source of truth. `build.py` refuses to build if any row's stated price disagrees with
`cubic yards × rate`.

The disclaimers from the sheet's *Instructions & Rates* tab are surfaced in the UI: volumes are
practical loading allowances rather than manufacturer dimensions, and special disposal charges
(mattresses, appliances, refrigerant units, tires, electronics, concrete, dirt, paint) plus extra
labor for heavy or hard-to-reach items are excluded and confirmed on site.

---

## Settings you can change

All of them live in the `BRH_CONFIG` block near the top of the `<script>` in the built file
(and in `src/calculator.template.html`):

| Setting | Default | Notes |
|---------|---------|-------|
| `ratePerCubicYard` | `40` | Master price list basis. |
| `minimumCharge` | `125` | Lowest price ever quoted. Set `0` to disable — a $2 toaster then quotes as $2. |
| `truckCapacityCY` | `16` | Cubic yards per truck, used only by the load meter. |
| `rangePercent` | `10` | Width of the "most jobs land between" range. |
| `phone` / `phoneDial` | `916-252-9500` | Display text and the `tel:` number. |
| `smsEnabled` | `true` | Shows a **Text us photos** button that pre-fills the item list. |
| `quoteEmail` | `""` | Set an address to add an **Email my quote** button (opens the customer's mail app pre-filled). |
| `webhookUrl` | `""` | Set a Zapier/Make/form endpoint to add a **Request this pickup** button that POSTs the quote as JSON. |
| `addons` | 5 entries | Label, description and `pct` for each access/labor allowance. Add, remove or reprice freely. |
| `popularIds` | 20 IDs | Item IDs (e.g. `LR-049`) shown on the *Popular items* tab. |

### Webhook payload

If `webhookUrl` is set, the button POSTs JSON: `customer` (all form fields), `pricing`
(rate, minimum, cubic yards, subtotal, each add-on, total, range), `items` (id, name, category,
cubic yards, qty, line total) and a ready-to-read `summaryText`.

---

## Elementor / theme style collisions

This was the main design constraint, so it is handled defensively:

- Everything is scoped under `#brh-quote` — the widget cannot leak styles onto the page.
- **Every CSS declaration carries `!important`**, and a universal in-scope reset
  (`#brh-quote *`) neutralises inherited fonts, colors, borders, padding, text-transform,
  line-height and `-webkit-text-fill-color` that Elementor globals or the theme push down.
  Component rules are class-based, so they outrank that reset and still win.
- Verified in Chromium against a deliberately hostile host page that forces Comic Sans,
  `line-height:3`, lime headings, magenta full-width buttons with dashed borders, and
  `box-sizing:content-box` on `*`. The widget renders identically.
- No external CSS, JS, fonts or images are loaded, so nothing can be blocked or slow the page.
- Icons are inline SVG using `path` only — never `rect`/`width` attributes, which the in-scope
  width reset would otherwise collapse.

---

## Updating prices

1. Replace `data/Big_Rich_Hauling_Master_Household_Item_Price_List.xlsx` with the new sheet
   (same column layout: Item ID, Category, Household Item, Estimated Cubic Yards, Estimated Price).
2. Run `python3 build.py` — standard library only, no dependencies.
3. Re-paste `dist/big-rich-quote-calculator.html` into the Elementor HTML widget.

```
$ python3 build.py
rate            $40.00 per cubic yard
categories      20
items           640
wrote           dist/big-rich-quote-calculator.html  (92.0 KB)
```

Do not hand-edit the generated item data in `dist/` — edit the spreadsheet or
`src/calculator.template.html` and rebuild.

---

## Layout

```
build.py                          spreadsheet -> widget build script (stdlib only)
data/…price list.xlsx             master price list, the source of truth
src/calculator.template.html      the widget (markup + CSS + JS), with a data placeholder
dist/big-rich-quote-calculator.html   ← paste THIS into Elementor
dist/preview.html                 same widget wrapped in a standalone page for previewing
```

## Colors

Taken from the live site: red `#D5291B`, gold `#C4A052`, near-black `#23282D` on white.
They are CSS variables at the top of the stylesheet (`--brh-red`, `--brh-gold`, `--brh-ink`, …),
so the whole widget re-skins from those few lines.
