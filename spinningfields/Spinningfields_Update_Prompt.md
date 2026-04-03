# Spinningfields Competitive Map — Update Prompt

Use this prompt to refresh the Spinningfields Competitive Map data. Copy and paste the relevant section into a new session with access to the Mapletree folder containing the three project files.

## Project Files

All files must be in the same folder:

| File | Purpose | Volatility |
|------|---------|------------|
| `Spinningfields_Competitive_Map.html` | Main map — rarely needs changes | Stable |
| `spinningfields_data.js` | Building specs, transactions, charts, market insights | Semi-annual |
| `spinningfields_availability.js` | Marketed spaces, status, agent URLs | Monthly–quarterly |

---

## 1. Availability Refresh (Monthly)

This is the most frequent update. The file `spinningfields_availability.js` contains `window.AVAILABILITY_DATA` with marketed spaces for ~47 buildings.

### Prompt

> Read `spinningfields_availability.js`. For each building with `status: "Leasing"`, verify whether the marketed spaces are still current by checking the listing URLs. For buildings without URLs, search for current availability on Savills, CBRE, Colliers, JLL, Cushman & Wakefield, and OBI Property websites for that building name in Manchester.
>
> For each building, update:
> - `status` — one of: Fully Let, Leasing, Refurb, Pipeline, Non-office
> - `marketedSpaces` array — each entry has: floor, sqft, condition (Cat A / Cat B / Fitted / Shell), rent (£ psf or —), agent, url, urlSource, notes
> - `availabilityPageUrl` — the building's own availability page if one exists
> - Remove any spaces that are no longer marketed (let/withdrawn)
> - Add any new spaces that have appeared
>
> Update `lastVerified` to the current month/year.
>
> Priority buildings to check first (most likely to change):
> - 3 Hardman Street (JMW vacating 4th & 7th floors)
> - 1 Hardman Boulevard / The Metropolitan (major refurb — status may change to Leasing)
> - Tower 12 (Allied London, active leasing)
> - The Quoin (new build, leasing up)
> - No. 1 Spinningfields (premium space)
>
> Do not change `spinningfields_data.js` or the HTML file.

---

## 2. Market Data Refresh (Semi-annual)

Updates the chart, rent table, market insights, and leasing activity in `spinningfields_data.js`.

### Prompt

> Read `spinningfields_data.js`. Update the following sections using current public sources (Savills, CBRE, JLL, Deloitte Crane Survey, Knight Frank, Colliers research reports for Manchester offices). Always cite the source and date in the text fields.
>
> **a) `chartData` — Prime Rents vs Yields (line ~551)**
> - Add the next year's data point (or update forecast years ending in "F")
> - Current series ends at 2027F. When actuals become available for a forecast year, replace the forecast with the actual and add a new forecast year
> - Update `rentRange` and `yieldRange` if new data falls outside current bounds
>
> **b) `submarketRentTable` (line ~600)**
> - Update Grade A and Grade B rent ranges for each submarket
> - Update the `source` string with the latest report references and key data points (record rent, prime vacancy, forecast)
>
> **c) `marketInsights` (line ~640)**
> - Four subsections: occupational, investment, supplyPipeline, micromarket
> - Refresh each bullet with the latest data. Key things to check:
>   - Take-up figures (annual and H1/H2 split)
>   - Prime headline rent (has the record been broken?)
>   - Rental forecasts (new broker reports)
>   - Vacancy rates (prime and Grade A)
>   - Prime yield (any movement?)
>   - Investment volumes and notable transactions
>   - Supply pipeline (completions, new starts, Deloitte Crane Survey)
>   - Micro-market changes (new developments, tenancy moves)
>
> **d) `leasingActivity` (line ~763)**
> - Add any significant new lettings (>5,000 sq ft) in the mapped area
> - Each entry: { building, tenant, size, date, notes }
> - Keep historical entries — append new ones at the end
>
> **e) `ownerInsights` (line ~749)**
> - Update if any buildings have changed ownership
> - Check against keyBuildings owner fields for consistency
>
> Do not change `spinningfields_availability.js` or the HTML file.

---

## 3. Building Data Refresh (Annual / Event-driven)

Updates building-level facts in `spinningfields_data.js` when ownership changes, buildings complete, or new buildings enter the mapped area.

### Prompt

> Read `spinningfields_data.js`. Review the `keyBuildings` array (46 entries). Check for:
>
> **a) Ownership changes**
> - Search for recent Manchester office transactions (Savills, CBRE, CoStar, Property Week, React News, EG)
> - Update the `owner` field for any buildings that have traded
> - Also update the corresponding `ownerInsights` entry and `marketInsights.investment` key transactions
>
> **b) Building completions**
> - Any Pipeline buildings that have completed? Change year and verify NLA
> - Any new buildings completed within 1km of 3 Hardman Street (53.4799, -2.2508)?
>   - Add to `keyBuildings` with: name, lat, lon, nla, floors, year, owner, txn (if known)
>   - Also add to `spinningfields_availability.js` with current marketed status
>
> **c) Refurbishment completions**
> - 1 Hardman Boulevard / The Metropolitan — has it relaunched?
> - Any other refurbs completing?
>
> **d) Transaction data (`txn` field)**
> - Update with any new sale price/date/yield/buyer information
>
> Do not change the HTML file.

---

## 4. Full Refresh (Annual)

Run all three updates above in sequence: Buildings → Market Data → Availability.

### Prompt

> Perform a full refresh of the Spinningfields Competitive Map. Read all three files:
> - `spinningfields_data.js`
> - `spinningfields_availability.js`
> - `Spinningfields_Competitive_Map.html` (read-only — for context on what fields the HTML consumes)
>
> Then run the following updates in order:
> 1. Building data refresh (ownership, completions, new buildings, transactions)
> 2. Market data refresh (chart, rent table, insights, leasing activity)
> 3. Availability refresh (all buildings, listing URLs, status)
>
> Cross-check for consistency:
> - Every building in keyBuildings should have a matching entry in AVAILABILITY_DATA.buildings
> - Owner fields in keyBuildings should match ownerInsights
> - Market insights should reference the latest chartData figures
> - Any building mentioned in leasingActivity should exist in keyBuildings
>
> Update `lastVerified` in spinningfields_availability.js.

---

## Data Sources Checklist

When searching for updates, check these sources in order:

| Source | What it covers | URL pattern |
|--------|---------------|-------------|
| Savills Manchester | Rents, yields, availability, research | savills.co.uk/research, search.savills.com |
| CBRE Manchester | Market outlook, investment, lettings | cbre.co.uk/research |
| JLL Manchester | Take-up, vacancy, quarterly reports | jll.co.uk/research |
| Deloitte Crane Survey | Supply pipeline, completions | deloitte.co.uk (annual, usually Jan/Feb) |
| Knight Frank | Yields, investment volumes | knightfrank.co.uk/research |
| Colliers Manchester | Lettings, availability | colliers.com |
| OBI Property | Local lettings and availability | obiproperty.co.uk |
| CoStar / Property Week / EG | Transactions, news | (paywalled — use what's publicly available) |
| Building-specific websites | Availability pages | e.g. 3hardmanstreet.com, tower12manchester.com |

## Notes

- The HTML file (`Spinningfields_Competitive_Map.html`) should almost never need updating — it derives Status and Available sq ft dynamically from `AVAILABILITY_DATA` at render time
- If adding a new building, remember to add it to both `keyBuildings` (in data.js) and `buildings` (in availability.js)
- Latitude/longitude for new buildings: use Google Maps, right-click → "What's here?"
- The `sqft` field in marketedSpaces accepts approximate values with `~` prefix (e.g. `"~10,000"`) — the HTML parses out the number for the totals column
