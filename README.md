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

### Recommended: send through WordPress (works with WP Mail SMTP)

If the site runs **WP Mail SMTP**, this is the better path — that plugin intercepts `wp_mail()`
itself, so the snippet below needs no plugin-specific code and every booking goes out over your own
authenticated SMTP. No third party ever sees a lead, and there's no activation step.

**Step 1.** Add this to your child theme's `functions.php` (or a Code Snippets plugin):

```php
/**
 * Big Rich Hauling — estimator booking handler.
 * Receives the widget's JSON, emails the office and confirms to the customer.
 */
add_action( 'wp_ajax_nopriv_brh_booking', 'brh_handle_booking' );
add_action( 'wp_ajax_brh_booking',        'brh_handle_booking' );
function brh_handle_booking() {

    $office          = 'bigrichhauling@att.net';  // where bookings land
    $notify_customer = true;                      // false = don't email the customer a copy

    $data = json_decode( file_get_contents( 'php://input' ), true );
    if ( ! is_array( $data ) ) {
        wp_send_json_error( 'bad payload', 400 );
    }

    // 1. same-site requests only
    $origin = isset( $_SERVER['HTTP_ORIGIN'] )
        ? wp_parse_url( $_SERVER['HTTP_ORIGIN'], PHP_URL_HOST ) : '';
    if ( $origin && $origin !== wp_parse_url( home_url(), PHP_URL_HOST ) ) {
        wp_send_json_error( 'bad origin', 403 );
    }

    // 2. bot filters: the widget's off-screen honeypot, and how long the form took
    if ( ! empty( $data['_hp'] ) ) {
        wp_send_json_error( 'spam', 400 );
    }
    if ( isset( $data['_elapsed'] ) && (int) $data['_elapsed'] < 5 ) {
        wp_send_json_error( 'too fast', 400 );
    }

    // 3. rate limit: 5 bookings per hour per IP
    $ip  = isset( $_SERVER['REMOTE_ADDR'] ) ? sanitize_text_field( $_SERVER['REMOTE_ADDR'] ) : 'unknown';
    $key = 'brh_rl_' . md5( $ip );
    $hits = (int) get_transient( $key );
    if ( $hits >= 5 ) {
        wp_send_json_error( 'rate limited', 429 );
    }
    set_transient( $key, $hits + 1, HOUR_IN_SECONDS );

    // 4. required fields
    $name  = sanitize_text_field( $data['name'] ?? '' );
    $phone = sanitize_text_field( $data['phone'] ?? '' );
    $email = sanitize_email( $data['email'] ?? '' );
    if ( ! $name || ! $phone || ! is_email( $email ) ) {
        wp_send_json_error( 'missing fields', 400 );
    }

    $subject = sanitize_text_field( $data['_subject'] ?? 'New booking request' );
    $body    = sanitize_textarea_field( $data['message'] ?? '' );

    // 5. the office copy — Reply-To is the customer, so hitting reply reaches them
    $sent = wp_mail( $office, $subject, $body, array(
        'Reply-To: ' . $name . ' <' . $email . '>',
    ) );

    // 6. the customer's confirmation
    if ( $sent && $notify_customer ) {
        wp_mail(
            $email,
            'We received your junk removal request — Big Rich Hauling',
            "Thanks {$name}!\n\nWe received your request and will call you shortly to confirm "
            . "your pickup window.\n\n{$body}\n\nQuestions? Call 916-252-9500.",
            array( 'Reply-To: ' . $office )
        );
    }

    $sent ? wp_send_json_success() : wp_send_json_error( 'wp_mail failed', 500 );
}
```

**Step 2.** In the widget's `BRH_CONFIG`, swap the two `endpoint` lines — uncomment the
admin-ajax one and delete (or comment out) the FormSubmit one:

```js
   endpoint   : "/wp-admin/admin-ajax.php?action=brh_booking",
// endpoint   : "https://formsubmit.co/ajax/bigrichhauling@att.net",
```

Keep it as a **relative path**. That way it always resolves against whatever host the page is on, so
a www / non-www mismatch can never trip CORS.

**Step 3.** In WP Mail SMTP, set *From Email* to an address on your own domain
(e.g. `no-reply@bigrichhauling.com`) and leave *Force From Email* on. The snippet sets Reply-To to
the customer, which survives that setting — so replies still go to the customer, not to no-reply.
This matters because att.net (AT&T/Yahoo) is strict about sender authentication: mail from your
SMTP with SPF/DKIM on bigrichhauling.com lands in the inbox where raw PHP `mail()` often doesn't.
Use *WP Mail SMTP → Tools → Email Test* to confirm delivery to bigrichhauling@att.net before going
live, then submit one real booking through the widget end to end.

### Notes for the current WP Mail SMTP setup (Google / Gmail mailer)

The site is configured with the **Google / Gmail** mailer, OAuth-connected as
`websites@strousehouse.io`, *From Email* `websites@strousehouse.io`, *From Name*
"Big Rich Hauling & Junk Removal", with **Force From Email** and **Force From Name** both ON.

That works with the snippet above as-is. Specifically:

- **Force From Email does not touch Reply-To.** It overrides the From address only, so the office
  email still has Reply-To set to the customer — pressing reply in the att.net inbox reaches the
  customer, not the sending account.
- **Volume is fine.** WP Mail SMTP warns that the Gmail mailer suits low-volume sites because of
  Gmail API rate limits. A booking form is exactly that.

Two things to decide before going live:

1. **The customer's confirmation email will come from `websites@strousehouse.io`** (displayed as
   "Big Rich Hauling & Junk Removal"). A homeowner who just booked Big Rich Hauling receiving mail
   from an unrelated agency domain looks odd and costs a little trust. Three ways to handle it:
   - Add a bigrichhauling.com address as a verified *Send mail as* alias inside the connected Gmail
     account, then set *From Email* to it. **Gmail rejects any From address that isn't the connected
     account or a verified alias** — this is the most likely way to break sending, so verify the
     alias in Gmail first, then change the field.
   - Point WP Mail SMTP at a mailer authenticated for bigrichhauling.com instead (SendLayer,
     SMTP.com and Brevo are the three it recommends).
   - Or don't email customers at all: set `$notify_customer = false;` in the snippet, or
     `autoReply: false` in the widget config. You still get every booking; the customer just relies
     on the on-screen confirmation and your callback.
2. **Check SPF/DKIM for strousehouse.io.** Sending happens through Google's infrastructure, so make
   sure that domain has `include:_spf.google.com` in SPF and DKIM enabled in Google Admin
   (Apps → Google Workspace → Gmail → Authenticate email). Without DKIM, Google signs with a default
   `*.gappssmtp.com` key that doesn't align with the From domain, which weakens DMARC — and att.net
   (AT&T/Yahoo) is strict. Send one booking and check it lands in the inbox, not spam; mail-tester.com
   gives you a score if you want detail.

Two more notes:

- Some hosts and security plugins (Wordfence, certain Cloudflare rules) block anonymous
  `admin-ajax.php` POSTs. If bookings start failing, register a REST route instead and point
  `endpoint` at `/wp-json/brh/v1/booking`:

  ```php
  add_action( 'rest_api_init', function () {
      register_rest_route( 'brh/v1', '/booking', array(
          'methods'             => 'POST',
          'callback'            => 'brh_handle_booking',
          'permission_callback' => '__return_true',
      ) );
  } );
  ```

- WP Mail SMTP's email log (Pro) then keeps a record of every booking, which is a handy backstop if
  a customer says they submitted and never heard back.

### Or skip sending entirely

**`submitMode: "mailto"`** always opens the customer's own mail app with the quote pre-filled and
addressed to `submitTo`. Zero dependencies, but it relies on the customer pressing send.

### Spam protection

The widget ships an off-screen honeypot field and reports how long the form took. Both are sent
**only** to a self-hosted endpoint (FormSubmit would print them as rows in the email), and the PHP
snippet above checks them along with an origin check and a per-IP rate limit.

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
