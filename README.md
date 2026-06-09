# Great Value Pless Parts 🏷️

> Instant manufacturing quotes inside Autodesk Fusion — the off-brand way.

**Great Value Pless Parts** (GVPP) is an open-source, knock-off clone of the
[Paperless Parts](https://www.paperlessparts.com/) Fusion add-in. It adds a
**Get Quote** button to Fusion's toolbar that reads the active design's geometry
and physical properties, sends them to a small quoting service, and shows an
instant machining cost estimate right inside Fusion.

It's the "Great Value" brand of instant quoting: 80% of the workflow, 0% of the
enterprise price tag, and ~0% of the accuracy guarantee. 😄

> ⚠️ **Not affiliated with Paperless Parts, Inc. or Autodesk, Inc.** This is an
> independent, educational project. "Paperless Parts", "Fusion", and "Autodesk"
> are trademarks of their respective owners. Do not use these estimates to
> actually bid on real work — see [Disclaimer](#disclaimer).

---

## What it does

| Paperless Parts (the real thing) | Great Value Pless Parts (this) |
| --- | --- |
| Push CAD from Fusion to a cloud quoting platform | Push part metadata to a local FastAPI service |
| AI-driven manufacturability + costing | Real job-shop cost model, cycle time estimated from geometry |
| Enterprise sales, SOC 2, the works | A `README`, an MIT license, and vibes |

The actual feature loop:

1. Open a design in Fusion.
2. Click **Great Value → Get Quote**.
3. The add-in extracts volume, mass, surface area, bounding box, units, and the
   assigned material.
4. It POSTs that to the quoting backend (`POST /api/v1/quote`).
5. The backend estimates material + machining + setup cost, applies quantity
   price breaks and markup, and returns a quote.
6. The add-in shows the quote in a palette (price, line-item breakdown, lead time).

---

## Architecture

```
┌─────────────────────────────┐         ┌──────────────────────────────┐
│  Autodesk Fusion            │         │  Quoting Backend (FastAPI)    │
│                             │         │                              │
│  fusion_addin/              │  HTTPS  │  backend/app/                 │
│   • Get Quote button        │ ──────► │   • POST /api/v1/quote        │
│   • PhysicalProperties read │  JSON   │   • pricing engine            │
│   • palette UI (HTML/JS)    │ ◄────── │   • materials table           │
│                             │  quote  │   • GET /api/v1/materials     │
└─────────────────────────────┘         └──────────────────────────────┘
```

The two halves are decoupled by a small JSON contract (see
[`backend/app/models.py`](backend/app/models.py)). You can test the backend with
plain `curl` — no Fusion required.

---

## Repository layout

```
great_value_pless_parts/
├── fusion_addin/                 # The Fusion add-in (Python)
│   ├── GreatValuePlessParts.manifest
│   ├── GreatValuePlessParts.py   # run()/stop() entry points
│   ├── config.py                 # add-in + backend config
│   ├── commands/
│   │   └── quote/entry.py        # "Get Quote" command + palette
│   ├── lib/
│   │   ├── extractor.py          # reads geometry from the active design
│   │   ├── api_client.py         # talks to the backend
│   │   └── fusionAddInUtils/     # event + logging helpers
│   └── resources/palette/        # palette HTML/CSS/JS
├── backend/                      # The quoting service (FastAPI)
│   ├── app/
│   │   ├── main.py               # FastAPI app + routes
│   │   ├── models.py             # request/response schemas
│   │   ├── materials.py          # density + cost table
│   │   └── pricing.py            # the (naive) estimation engine
│   ├── requirements.txt
│   └── sample_payload.json       # try the API without Fusion
├── README.md
├── TODO.md
└── LICENSE
```

---

## Getting started

### 1. Run the quoting backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API comes up on `http://127.0.0.1:8000`. Interactive docs at
`http://127.0.0.1:8000/docs`.

Smoke-test it without Fusion:

```powershell
curl -X POST http://127.0.0.1:8000/api/v1/quote `
  -H "Content-Type: application/json" `
  -d "@sample_payload.json"
```

### 2. Install the Fusion add-in

1. In Fusion: **Utilities → Add-Ins → Scripts and Add-Ins** (or `Shift+S`).
2. On the **Add-Ins** tab, click the green **+** next to "My Add-Ins" and select
   the `fusion_addin/` folder. (On Windows you can also copy it into
   `%appdata%\Autodesk\Autodesk Fusion 360\API\AddIns\`.)
3. Select **GreatValuePlessParts** and click **Run**. Check "Run on Startup" if
   you want it loaded automatically.
4. Open a design, then look for the **Great Value** panel in the **Solid** tab
   (or wherever the button lands) and click **Get Quote**.

> The add-in defaults to `http://127.0.0.1:8000`. Change `API_BASE_URL` in
> [`fusion_addin/config.py`](fusion_addin/config.py) to point elsewhere.

---

## How the pricing works

The estimator in [`backend/app/pricing.py`](backend/app/pricing.py) uses a real
job-shop cost model (per-piece price falls as setup amortizes over quantity):

```
                  (machine + material + tooling + setup_amortized) × overhead
price_per_piece = ───────────────────────────────────────────────────────────
                                       (1 − margin)

  machine_cost    = cycle_time_sec / 3600 × machine_hourly_rate
  material_cost   = stock_volume_in³ × material_rate_per_in³
  setup_amortized = (setup_min / 60 × hourly_rate) / order_qty
```

- **Shop rates** (hourly rate, setup time per machine type, tooling, overhead,
  margin, stock waste) come from [`backend/quote_params.json`](backend/quote_params.json).
  The committed file holds **illustrative example values** — put your real shop
  rates in `backend/quote_params.local.json` (gitignored) so they never hit a
  public repo.
- **Material rates** ($/in³ + machinability) live in the material master,
  [`backend/app/materials.py`](backend/app/materials.py).
- **Machine type** (`mill` / `lathe` / `swiss`) sets the setup time and the
  stock model (bounding box for milling, bounding cylinder for turning/Swiss).
- **Cycle time is estimated from CAD geometry** (removed volume + surface area),
  *not* a verified toolpath — so the engine returns a `confidence` level
  (capped at `medium` in geometry mode) and `flags` such as
  `cycle_time_estimated_from_geometry`. Confirm against CAM before issuing a
  firm quote.

The quote response also includes a **quantity price-break curve** (qty 1 / 10 /
100 / 1000) so you can see the setup-amortization effect at a glance.

> The cost *model* is sound; the *cycle-time input* is a geometry estimate.
> Treat quotes as a fast first pass for review, not a binding bid.

---

## Roadmap

See [`TODO.md`](TODO.md). Highlights: real STEP export + upload, a proper palette
UI, more processes (turning / sheet metal), persisted quotes, and auth.

---

## Disclaimer

This software produces **toy estimates** from crude heuristics. It is for
learning the Fusion API and quoting-workflow plumbing only. **Do not** use its
output to price, bid, or sell real manufactured parts. No warranty; see
[`LICENSE`](LICENSE). Not affiliated with, endorsed by, or connected to Paperless
Parts, Inc. or Autodesk, Inc.

## License

[MIT](LICENSE) © 2026
