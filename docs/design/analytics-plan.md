# Analytics plan — ugmi.ca (week-1 UX validation)

Owner asked (Aug 6, 2026): "set up analytics to see, in the first week, if any
of these UX things are working." This is the instrumentation spec. The v2
mockup (`theme-explorations/tactile-calm-v2.html`) already stubs every event
as `track(name, props)`.

## Tool decision

Requirements: static site, custom events, cookieless (this audience checks for
trackers; a consent banner is friction and a grift-smell), cheap, readable by
one person in ten minutes a week.

- **Recommended: Umami Cloud** (free tier, cookieless, custom events with
  properties, no consent banner needed). One `<script>` tag; events via
  `umami.track(name, props)` — drop-in for the existing stub.
- **Alternative: Plausible** (~$9/mo) if funnels and saved goals earn their
  keep after month 1.
- Rejected: GA4 (consent burden, overkill), PostHog (session recordings are
  the wrong instinct for a trust-first product), Cloudflare WA (no custom
  events).

## Event schema (keep it this small)

| Event | Props | The question it answers |
|---|---|---|
| pageview (auto) | referrer, `?from=` reel param | Which reel/DM cohort arrived |
| `filter_answered` | q, v | Is the 3-tap collapse used at all, and which taps |
| `apply_click` | company | Is the free list doing its job |
| `contact_open` | company | **Is the referral wedge interesting** (the key new bet) |
| `sheet_cta_click` | — | Does the sheet sell once opened |
| `stripe_click` | placement (checkout / sheet) | Paid intent, by entry point |
| `email_submit` | — | Monday-email demand |
| `template_copy` | — | Is the template earning trust |

Zero-results state: fire `filter_answered` normally; a `zero_results` event is
worth adding only if the sample counts suggest it happens at all.

## The week-1 read (directional, not significant)

Traffic at current scale (reel-driven spikes, low base) means **week 1 is a
qualitative read, not an A/B test**. Do not make keep/kill calls on
sub-percent differences; look for order-of-magnitude signals:

1. **filter engagement**: what share of visitors answer ≥1 tap? (If near
   zero, the collapse is invisible or unwanted; move it or shrink it.)
2. **contact_open / visit**: the single most important number. It validates
   (or kills) the per-card contact wedge before any more is built on it.
3. **contact_open → sheet_cta_click → stripe_click**: does the sheet convert
   better than the bottom pitch (`stripe_click` placement prop tells you)?
4. **apply_click / visit**: the free product's pulse. If this is low, nothing
   downstream matters.
5. **email_submit / visit**: whether the Monday email earns its operational
   cost (it is a weekly SLA once anyone subscribes).

Review lives in the Friday `/retro` alongside the reel analytics; the reel →
site → event chain is the whole funnel in one view (join on `?from=`).

## Constitution (applies to analytics too)

- No tracking pixels in emails (`ugmi-10-weekly.md` rule). Site analytics is
  cookieless or it doesn't ship.
- Never display analytics-derived numbers on the page ("2,341 students used
  this") — every on-page number stays build-time computed from the dataset.
- The `?from=` param is set by us in DM links, not read from ad networks.
