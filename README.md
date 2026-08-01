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
| **3. Your Estimate** | "Your quote is ready" → the headline total, an itemized breakdown with the minimum-charge adjustment, a booking-details card, the accessibility/disposal note. Also call, copy and print/PDF. |
| **4. Book Your Time** | The Workiz online-booking calendar, embedded inline. The lead is sent **before** this screen opens, so a customer who abandons the calendar is still captured. |

With `booking.mode: "none"` the flow instead becomes Select Items → Your Info → **Schedule**
(the widget's own date + six two-hour windows) → Your Estimate, ending in **Confirm booking**.

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

## The booking calendar

`BRH_CONFIG.booking` embeds the Workiz online-booking calendar as the final step, so the customer
picks their slot without leaving the page.

```js
booking: {
  mode          : "workiz",                     // "workiz" | "none"
  url           : "https://online-booking.workiz.com/?ac=…",
  height        : 780,
  prefillParams : { name:"name", phone:"phone", email:"email", address:"address" }
}
```

Three things worth understanding about it:

- **It replaces the widget's own scheduling step.** Otherwise the customer picks a time twice — once
  in our form and once in the calendar — and only the second one is real. With `mode: "workiz"` the
  Schedule step is dropped from the flow automatically.
- **The lead is sent before the calendar loads.** The quote screen's button reads *Continue to
  scheduling*; pressing it submits the booking to your provider and only then reveals the calendar.
  Abandoning the calendar (common with embedded booking widgets) therefore still leaves you a lead
  with the full item list. If the send fails, the customer is still taken to the calendar and
  prompted to paste their details in — the booking is never blocked by our own plumbing.
- **The iframe is loaded lazily**, only when that step is reached, so it costs nothing on page load.

### About prefilling

The calendar is a third-party page, so we cannot read it, fill it programmatically, or detect
whether the customer completed it — the browser forbids all three across origins.

`prefillParams` appends the customer's details to the iframe URL as query parameters. **Workiz does
not document prefill parameters**, so this is best-effort: if it ignores them nothing breaks, the
customer just retypes their name and phone. Test it once and see. If Workiz uses different parameter
names, put them in the map (e.g. `{ name:"customer_name", phone:"customer_phone" }`); set it to `{}`
to send a clean URL.

Because a retype is possible, the booking screen shows the customer's details with a **Copy my
details** button — one tap puts their name, phone, address, estimate and item list on the clipboard
to paste into the booking form's notes.

## Where the lead goes

`BRH_CONFIG.submit.provider` picks the destination. Four options:

| provider | What happens | Setup |
|----------|--------------|-------|
| **`"ghl"`** *(shipped default)* | Posts to a GoHighLevel **Inbound Webhook**. The lead becomes a GHL contact (and optionally an opportunity), and the GHL workflow emails bigrichhauling@att.net. | Paste one URL — no code |
| `"wordpress"` | Posts to the `brh_booking` handler in `functions.php`; `wp_mail()` sends it, so WP Mail SMTP delivers. Same-origin, so CORS can never bite, and the destination stays server-side. Can also relay to GHL. | Add the PHP snippet |
| `"formsubmit"` | Posts to FormSubmit, which emails the address. | One-time activation click |
| `"mailto"` | No POST — opens the customer's mail app with the quote pre-filled. | None |

**Whatever you choose, a failed send falls back to the pre-filled mailto** to
bigrichhauling@att.net and shows the phone number, so a lead is never silently lost.

---

## GoHighLevel setup (the shipped default)

This is the least work and gives you the most: the lead lands in your CRM *and* GHL sends the email
to bigrichhauling@att.net, so you don't need FormSubmit or the `functions.php` snippet at all.

### 1. Create the workflow trigger

In GHL: **Automation → Workflows → + Create Workflow → Start from scratch**, then add the trigger
**Inbound Webhook**. Copy the webhook URL it shows you (it looks like
`https://services.leadconnectorhq.com/hooks/<locationId>/webhook-trigger/<uuid>`).

### 2. Paste it into the widget

In `BRH_CONFIG.submit`:

```js
provider      : "ghl",
ghlWebhookUrl : "https://services.leadconnectorhq.com/hooks/…/webhook-trigger/…",
```

Re-paste the file into the Elementor HTML widget. **Until that URL is filled in, every booking
quietly falls back to the email** — `python3 verify.py` prints an "ACTION REQUIRED" line while it's
empty, and the browser console warns too.

### 3. Send one test booking

GHL only learns the field names after it has actually received a payload, so submit one real test
booking through the widget now. Then reopen the trigger and you'll see every field available for
mapping.

### 4. Build the workflow

Add these actions:

1. **Create/Update Contact** — map the incoming fields:

   | GHL contact field | Webhook field |
   |---|---|
   | First Name | `first_name` |
   | Last Name | `last_name` |
   | Email | `email` |
   | Phone | `phone` |
   | Address | `address1` |
   | City | `city` |
   | Postal Code | `postal_code` |
   | State | `state` |
   | Source | `source` |

2. **Send Internal Notification** (Email) to `bigrichhauling@att.net` — this is the part that
   replaces the old email path. Reference any field with the
   `{{inboundWebhookRequest.<field>}}` token, e.g.:

   ```
   Subject: New estimate — {{inboundWebhookRequest.estimated_total}} — {{inboundWebhookRequest.full_name}} ({{inboundWebhookRequest.city}})

   {{inboundWebhookRequest.quote_summary}}
   ```

   `quote_summary` is the whole formatted quote — name, phone, address, pickup date and window,
   every item with its price, the subtotal, the minimum adjustment, the total and the disclaimer —
   so that single token is enough for a complete notification email.

3. *(Optional)* **Create Opportunity** in a pipeline, using `estimated_value` as the monetary value.
   It's sent as a bare number (e.g. `95`) precisely so GHL accepts it, alongside the formatted
   `estimated_total` (`"$95.00"`) for use in emails and SMS.

4. *(Optional)* **Send SMS / Email to the customer** confirming the request, and add a tag like
   `website-estimator` so you can segment these leads.

### Fields sent to GHL

All flat and snake_case, because Inbound Webhook mapping struggles with nested objects:

| Field | Example |
|---|---|
| `source` | `Website Estimator` |
| `full_name` / `first_name` / `last_name` | `Maria De La Cruz` / `Maria` / `De La Cruz` |
| `email`, `phone` | `maria@example.com`, `(916) 555-0177` |
| `address1`, `city`, `postal_code`, `state` | `44 Oak Ave`, `Roseville`, `95661`, `CA` |
| `preferred_date`, `preferred_date_iso`, `preferred_window` | `Sat, Sep 5, 2026`, `2026-09-05`, `7:00 AM – 9:00 AM` |
| `item_count`, `cubic_yards` | `1`, `3` |
| `items_subtotal`, `minimum_adjustment`, `estimated_total` | `$120.00`, `` (empty when none), `$120.00` |
| `estimated_value` | `120` — bare number, for opportunity value |
| `extra_labor` | `Items are upstairs or downstairs; Long carry or tight access` |
| `itemized_list` | `1 x Sofa - 3 cushion — $120.00` (one per line) |
| `customer_notes` | whatever the customer typed |
| `quote_summary` | the entire formatted quote as plain text |

The surname split takes the **first** word as the given name and everything after it as the surname,
so multi-word surnames survive.

### If leads don't reach GHL

The widget posts straight from the visitor's browser, so a cross-origin POST is involved. If GHL
refuses it at the CORS layer, the widget automatically retries as a CORS-simple request (no preflight,
response hidden) so the lead still lands, and only falls back to email if that fails too.

If bookings still don't appear in GHL, route them through WordPress instead — no CORS involved at all,
and it keeps the webhook URL out of your page source. Set `provider: "wordpress"`, add the snippet
below, and have the PHP forward to GHL server-side by inserting this before the `wp_mail()` call:

```php
    // relay the booking into GoHighLevel, server-side
    wp_remote_post( 'https://services.leadconnectorhq.com/hooks/…/webhook-trigger/…', array(
        'headers'  => array( 'Content-Type' => 'application/json' ),
        'body'     => wp_json_encode( $data ),
        'timeout'  => 15,
        'blocking' => false,
    ) );
```

> **One caveat about the webhook URL:** because the widget is client-side, the URL is visible in the
> page source. It is write-only — it can only start your workflow, not read anything out of GHL — so
> the worst case is junk contacts, which the honeypot and a GHL filter step handle. Never put a GHL
> **API key or private-integration token** in the widget; that would be readable by anyone. If you
> want the URL hidden entirely, use the WordPress relay above.

---

## FormSubmit (no code, no CRM)

With `provider: "formsubmit"` the booking posts to [FormSubmit](https://formsubmit.co), which
forwards it to `submit.email`:

> ⚠️ **One-time activation.** The very first booking triggers an activation email from FormSubmit to
> bigrichhauling@att.net. Click the link in it once, and every later booking arrives automatically.
> Send a test booking yourself first so the activation is out of the way before real customers use it.

The email arrives as a table with name, phone, email, address, preferred date and window, item count,
cubic yards, items subtotal, minimum adjustment, extra-labor flags, estimated total, the full
itemized list and the customer's notes. With `autoReply: true` the customer also gets a confirmation
copy. Replies go straight to the customer's address.

## WordPress / WP Mail SMTP (alternative, or as a GHL relay)

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

**Step 2.** In the widget's `BRH_CONFIG.submit`, set `provider: "wordpress"`. Leave
`wordpressUrl` as the **relative path** it ships with — that way it always resolves against whatever
host the page is on, so a www / non-www mismatch can never trip CORS.

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

**`provider: "mailto"`** always opens the customer's own mail app with the quote pre-filled and
addressed to `submit.email`. Zero dependencies, but it relies on the customer pressing send.

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
| `submit.provider` | `"ghl"` | `"ghl"` / `"wordpress"` / `"formsubmit"` / `"mailto"` — see the table above. |
| `submit.ghlWebhookUrl` | `""` | **Paste your GHL Inbound Webhook URL here.** Empty = falls back to email. |
| `submit.wordpressUrl` | `/wp-admin/admin-ajax.php?action=brh_booking` | Relative on purpose, so www / non-www cannot trip CORS. |
| `submit.formsubmitUrl` | FormSubmit URL | Only used by the `formsubmit` provider. |
| `submit.email` | `bigrichhauling@att.net` | The mailto-fallback destination, and FormSubmit's target. |
| `submit.leadSource` | `"Website Estimator"` | Stamped on the GHL contact as its source. |
| `submit.autoReply` | `true` | Customer confirmation copy (formsubmit / wordpress only — with GHL, do it in the workflow). |
| `cities` | 21 entries | The City / area dropdown. |
| `windows` | 6 entries | The pickup windows on the Schedule step. |
| `accessFlags` | 4 entries | Extra-labor checkboxes. Give one a `pct` (e.g. `pct:10`) to price it automatically — it then appears as its own breakdown line. |

---

## If raw code appears on the page and the buttons are dead

Symptom: the widget renders, but partway down the page a block of JavaScript shows up as visible
text, nothing is clickable, and "Prefer to call?" shows a dash instead of the phone number —
**often only for logged-out visitors, not for admins.**

That means the inline `<script>` was cut short, so no JavaScript ran at all. The usual cause is a
plugin that injects its code with a plain `str_replace` on the **first closing `</body>` tag it
finds in the page**. If a string inside our script contains that literal, the injection lands in the
middle of our code, ends the script element early, and the browser renders the remainder as text.
It shows up only for visitors because analytics, chat-widget and cache plugins typically skip
logged-in admins.

The widget is now built so there is nothing for such a plugin to match:

- The print view is constructed with DOM calls into a hidden iframe, never by concatenating an HTML
  document as a string. That also removed the popup, which mobile browsers frequently block.
- `build.py` **fails the build** if any of `</body`, `</html`, `</head`, `</script`, `</style`,
  `</title` or `<!doctype` reappears inside the script.
- Config comments use `/* */` rather than `//`, so a minifier that strips newlines can't comment out
  the rest of the file — a second, independent route to the same symptom.

If you ever see it again after editing the widget, run `python3 build.py` and read the error; that
check exists precisely to catch it before it reaches the site.

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
  charge and the on-screen copy that quotes it, the pickup windows, and the submit provider (that it
  is a known one, that its URL is filled in, and that a mailto fallback address exists).

Config gaps are reported separately as **ACTION REQUIRED** rather than failing the check, since they
mean "correct build, not wired up yet" rather than "data mismatch". An empty `ghlWebhookUrl` shows up
there until you paste it in.

Current state: all 20 categories reconcile, 640/640 items, rate $40.00, $95 minimum,
provider `ghl` (webhook URL still to be pasted), mailto fallback to bigrichhauling@att.net.

---

## Layout

```
build.py                          spreadsheet -> widget build script (stdlib only)
verify.py                         reconciles the build against all three sheets
docs/Big-Rich-Hauling-GHL-Setup-Guide.pdf   hand this to whoever builds the GHL workflow
docs/ghl-guide.html               its source; re-render with `node docs/render-guide.js`
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
