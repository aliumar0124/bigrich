# Big Rich Hauling — Item-by-Item Estimator

A self-contained booking calculator for **bigrichhauling.com**, built to drop straight into an
Elementor **HTML** widget. A customer builds their item list, enters their details, picks a pickup
window and gets a real dollar estimate — without calling anyone.

Pricing comes from `Big_Rich_Hauling_Master_Household_Item_Price_List.xlsx`:
**640 items across 20 categories at $40 per cubic yard**, with a **$95 minimum service charge**.

---

## Install (Elementor)

1. Edit the page in Elementor.
2. Drag in the **HTML** widget (Elementor → General → HTML).
3. Open **`dist/big-rich-quote-calculator.html`**, copy the whole file, paste it into the widget's
   *HTML Code* box.
4. Update the page. Done — nothing else to install, no plugin, no external requests.

To preview it outside WordPress, open `dist/preview.html` in any browser.

---

## The flow

Matches the reference estimator screen for screen:

| Screen | What happens |
|--------|--------------|
| **Before You Begin** | Welcome copy, the four accuracy tips, and the "estimate, not a final quote — you'll pay less, not more" note. The **Get started** button stays disabled until the customer ticks *I understand*. |
| **1. Select Items** | "Include everything" warning, search across all 640 items, a 20-room category grid, and item cards with a gold **+** that becomes a −/qty/+ stepper. **No prices are shown here** — the header cart chip just counts items, and the hint below reads *"your price will be revealed on the next steps after you provide your info."* |
| **2. Your Info** | Name, phone, email, service address, city/area, ZIP, notes — all validated. Plus optional *extra labor* flags (upstairs/downstairs, long carry, dismantling, heavy items) that are sent with the booking but do not change the estimate. |
| **3. Schedule** | Preferred date (today onward) and one of six two-hour pickup windows. |
| **4. Review & Price** | "Your quote is ready" → the headline total, an itemized breakdown with the minimum-charge adjustment, a booking-details card, the accessibility/disposal note, and **Confirm booking**. Also call, copy and print/PDF. |

The header cart chip opens a list where items can be adjusted or removed from any screen, and the
step markers at the top let the customer jump back to an earlier screen without losing anything.

## How the price is calculated

```
item price      = estimated cubic yards × $40            (straight from the master price list)
items subtotal  = sum of every line
estimated total = max(items subtotal, $95 minimum)
```

When the subtotal lands under the minimum, the breakdown shows the gap as a *Minimum service charge
adjustment* — e.g. a wine cabinet at $80.00 becomes $80.00 + $15.00 = **$95.00**.

Every price is derived from the item's cubic yards, so the spreadsheet stays the single source of
truth. `build.py` refuses to build if any row's stated price disagrees with `cubic yards × rate`.

---

## Where bookings go

**Confirm booking** sends the whole quote to **bigrichhauling@att.net**.

Because an Elementor HTML widget has no backend of its own, the default path posts the booking to
[FormSubmit](https://formsubmit.co), which forwards it to that address:

> ⚠️ **One-time activation.** The very first booking triggers an activation email from FormSubmit to
> bigrichhauling@att.net. Click the link in it once, and every later booking arrives automatically.
> Send a test booking yourself first so the activation is out of the way before real customers use it.

The email arrives as a table with name, phone, email, address, preferred date and window, item count,
cubic yards, items subtotal, minimum adjustment, extra-labor flags, estimated total, the full
itemized list and the customer's notes. With `autoReply: true` the customer also gets a confirmation
copy. Replies go straight to the customer's address.

**If the POST ever fails**, the widget automatically opens the customer's mail app with the entire
quote pre-filled and addressed to bigrichhauling@att.net, and shows the phone number — the lead is
never silently lost.

### Prefer not to use a third party?

Two alternatives, both a one-line config change:

1. **`submitMode: "mailto"`** — skips FormSubmit entirely and always opens the customer's own mail app
   with the quote pre-filled. Zero dependencies, but it relies on the customer pressing send.
2. **Send through WordPress** — point `endpoint` at your own handler and let `wp_mail` deliver it.
   Add this to your child theme's `functions.php` (or a Code Snippets plugin):

   ```php
   add_action( 'wp_ajax_nopriv_brh_booking', 'brh_booking' );
   add_action( 'wp_ajax_brh_booking',        'brh_booking' );
   function brh_booking() {
       $data = json_decode( file_get_contents( 'php://input' ), true );
       if ( empty( $data['phone'] ) ) { wp_send_json_error( 'missing phone', 400 ); }
       $body = sanitize_textarea_field( $data['message'] ?? '' );
       wp_mail(
           'bigrichhauling@att.net',
           sanitize_text_field( $data['_subject'] ?? 'New booking request' ),
           $body,
           array( 'Reply-To: ' . sanitize_email( $data['email'] ?? '' ) )
       );
       wp_send_json_success();
   }
   ```

   Then set `endpoint: "https://bigrichhauling.com/wp-admin/admin-ajax.php?action=brh_booking"`.
   This keeps every lead inside your own site and needs no activation step.

---

## Settings you can change

All of them live in the `BRH_CONFIG` block near the top of the `<script>` in the built file
(and in `src/calculator.template.html`):

| Setting | Default | Notes |
|---------|---------|-------|
| `ratePerCubicYard` | `40` | Master price list basis. |
| `minimumCharge` | `95` | Applied to every job. Set `0` to disable — a $2 toaster then quotes as $2. |
| `phone` / `phoneDial` | `916-252-9500` | Display text and the `tel:` number. |
| `submitMode` | `"endpoint"` | `"endpoint"` posts the booking; `"mailto"` opens the customer's mail app. |
| `submitTo` | `bigrichhauling@att.net` | Where bookings land (also the mailto fallback address). |
| `endpoint` | FormSubmit URL | Swap for your own webhook or the WordPress handler above. |
| `autoReply` | `true` | Emails the customer a confirmation copy of their quote. |
| `cities` | 21 entries | The City / area dropdown. |
| `windows` | 6 entries | The pickup windows on the Schedule step. |
| `accessFlags` | 4 entries | Extra-labor checkboxes. Give one a `pct` (e.g. `pct:10`) to price it automatically — it then appears as its own breakdown line. |

---

## Elementor / theme style collisions

This was a main design constraint, so it is handled defensively:

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
3. Run `python3 verify.py` to reconcile the build against all three sheets (see below).
4. Re-paste `dist/big-rich-quote-calculator.html` into the Elementor HTML widget.

### Verifying against the spreadsheet

`python3 verify.py` cross-checks four sources and exits non-zero on any mismatch:

- **Master Price List** — every item row, and that each stated price equals `cubic yards × rate`.
- **Instructions & Rates** — the rate, and that all seven estimating rules are reflected somewhere
  in the widget (it fails if a rule is added to the sheet and not handled).
- **Category Summary** — per-category item count, lowest price and highest price.
- **dist/big-rich-quote-calculator.html** — item count, item IDs, the configured rate, the minimum
  charge and the on-screen copy that quotes it, the booking destination, and the pickup windows.

Current state: all 20 categories reconcile, 640/640 items, rate $40.00, $95 minimum,
bookings to bigrichhauling@att.net.

---

## Layout

```
build.py                          spreadsheet -> widget build script (stdlib only)
verify.py                         reconciles the build against all three sheets
data/…price list.xlsx             master price list, the source of truth
src/calculator.template.html      the widget (markup + CSS + JS), with a data placeholder
dist/big-rich-quote-calculator.html   ← paste THIS into Elementor
dist/preview.html                 same widget wrapped in a standalone page for previewing
```

## Colors

Taken from the live site: red `#D5291B` (header, headings, totals), gold `#C4A052` (buttons, active
states), near-black `#23282D` on white. The reference estimator is dark-themed; this one keeps the
website's light red/gold palette as requested. All values are CSS variables at the top of the
stylesheet (`--brh-red`, `--brh-gold`, `--brh-ink`, …), so the whole widget re-skins from a few lines.
