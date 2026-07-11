# GoldRock "Live Prices" page — ready-to-paste content

Build this as a normal page in Bricks. The chart is one HTML/Code element in the
middle; everything else is Heading + Text elements. This page's own text is what
ranks your SITE in Google (the embedded chart doesn't pass SEO on its own).

---

## SEO fields (set in your SEO plugin — Yoast / RankMath / Google Site Kit — or page settings)

- **URL slug:** `live-prices`  → goldrockmetalexchange.com/live-prices
- **Meta title:** Live Gold, Silver & Platinum Spot Prices & Charts | GoldRock Metal Exchange
- **Meta description:** Track live gold, silver, and platinum spot prices with interactive charts going back over a century. Physical metals & Precious-Metals IRAs from GoldRock. Call (888) 859-0978.

---

## Page body (top to bottom in Bricks)

### [Heading — H1]
Live Gold, Silver & Platinum Spot Prices

### [Text — intro, directly under the H1]
Follow gold, silver, and platinum spot prices live, with interactive charts that
reach back more than a century. Whether you're timing a purchase, tracking the
market, or planning a Precious-Metals IRA, you can see exactly where each metal
stands today — and the full history behind it.

### [HTML / Code element — the chart]
<!-- exact iframe provided once your GitHub Pages URL is live -->
<iframe src="https://YOUR-USERNAME.github.io/goldrock-metals-chart/"
        style="width:100%;height:900px;border:0" loading="lazy"
        title="Live gold, silver and platinum spot price chart"></iframe>

### [Heading — H2]
What is the spot price?

### [Text]
The spot price is the current market price to buy or sell one troy ounce of a
metal for immediate settlement — the global benchmark that moves throughout the
trading day. The chart above shows the live spot price for gold, silver, and
platinum, so you can watch it in real time and compare it against days, years,
or decades of history.

### [Heading — H2]
Set a free spot-price alert

### [Text]
Want to know the moment a metal reaches your number? Use the alert on the chart
above — pick gold, silver, or platinum, choose a percentage move or a target
price, and we'll let you know when it hits.

### [Heading — H2]
Own physical metal or open a Precious-Metals IRA

### [Text]
When you're ready to act, work directly with a GoldRock specialist on physical
gold, silver, and platinum, or a Precious-Metals IRA — with clear guidance, fees
disclosed up front, and insured, fully documented delivery. Call
(888) 859-0978 or email contact@goldrockmetalexchange.com.

### [Heading — H2]
Frequently asked questions

**What is the current spot price of gold?**
The live gold spot price is shown at the top of the chart above and updates
continuously throughout the trading day. Silver and platinum are one tap away.

**How often do the prices update?**
The live spot price refreshes about every minute while the page is open, and the
historical chart is refreshed daily.

**Can I hold gold, silver, or platinum in an IRA?**
Yes. A Precious-Metals IRA lets you hold IRS-approved physical gold, silver, and
platinum inside a tax-advantaged retirement account. A GoldRock specialist can
walk you through eligibility and setup.

**How do I get started with GoldRock?**
Call (888) 859-0978 or email contact@goldrockmetalexchange.com, and a specialist
will help you with physical delivery or a Precious-Metals IRA.

---

Optional add-on: I can also give you FAQ **schema markup** (JSON-LD) to paste in,
which can earn the expandable FAQ rich-result in Google. Just ask.

---

## FAQ schema (JSON-LD) — paste into the page for the expandable Google rich result

Add a Code element (or your SEO plugin's "custom schema" box) containing:

```html
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[
 {"@type":"Question","name":"What is the current spot price of gold?",
  "acceptedAnswer":{"@type":"Answer","text":"The live gold spot price is shown at the top of the chart above and refreshes automatically while the page is open. Silver and platinum are one tap away."}},
 {"@type":"Question","name":"How often do the prices update?",
  "acceptedAnswer":{"@type":"Answer","text":"The live spot price refreshes about every minute while the page is open, and the historical chart is refreshed daily."}},
 {"@type":"Question","name":"Can I hold gold, silver, or platinum in an IRA?",
  "acceptedAnswer":{"@type":"Answer","text":"Yes. A Precious-Metals IRA lets you hold IRS-approved physical gold, silver, and platinum inside a tax-advantaged retirement account. A GoldRock specialist can walk you through eligibility and setup."}},
 {"@type":"Question","name":"How do I get started with GoldRock?",
  "acceptedAnswer":{"@type":"Answer","text":"Call (888) 859-0978 or email contact@goldrockmetalexchange.com, and a specialist will help you with physical delivery or a Precious-Metals IRA."}}
]}
</script>
```
