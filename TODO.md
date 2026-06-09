# TODO — Great Value Pless Parts

Roadmap for the off-brand Paperless Parts clone. Loosely ordered; check things
off as they land.

## ✅ Done (initial scaffold)

- [x] Research Paperless Parts' Fusion integration + the Fusion add-in API
- [x] Repo layout, README, license, `.gitignore`
- [x] FastAPI quoting backend: `/health`, `/api/v1/materials`, `/api/v1/quote`
- [x] Fusion add-in skeleton: manifest, `run`/`stop`, command + button
- [x] Geometry/property extractor from the active design
- [x] HTTP client + palette to display the returned quote
- [x] `sample_payload.json` so the API is testable without Fusion

## ✅ Done (cost model v2 — TLK port)

- [x] Replace the naive markup with the tlk-quoting-engine cost formula
      `(machine + material + tooling + setup_amortized) × overhead / (1 − margin)`
- [x] Machine types (mill / lathe / swiss) → setup time + stock model
      (bbox for milling, bounding cylinder for turning)
- [x] Material master with $/in³ rates + machinability + density
- [x] Geometry-based cycle-time estimate (flagged, not a verified toolpath)
- [x] Confidence levels + flags (geometry mode caps at `medium`)
- [x] Quantity price-break curve (1 / 10 / 100 / 1000) in the response + palette
- [x] Shop rates in `quote_params.json` with gitignored `quote_params.local.json`
      override (keep real rates off the public repo)

## ✅ Done (operations mode — live speeds & feeds)

- [x] Validated the extractor live against a real part via the Fusion MCP
      (firing pin: 0.157 dia × 0.512 long, steel)
- [x] **Operations mode**: turning op set (turn/face/drill/groove/thread/cutoff)
      → cycle time from real machining math → `high` confidence
- [x] Live speeds & feeds from the Datum Supabase `cutting_presets` table
      (median SFM + feed/rev per material), creds in gitignored local config
- [x] Per-operation breakdown (rpm + seconds) in the response
- [x] Graceful fallback to geometry estimate when the DB is unreachable (flagged)

## 🔜 Next up (MVP polish)

- [ ] **Load the add-in in Fusion** as an actual add-in (extractor already
      proven live via MCP) and quote a part end-to-end through the palette
- [ ] **Read CAM ops straight from Fusion** — if the doc has CAM setups, pull the
      real operations (and Fusion's own cycle times) instead of a supplied graph
- [ ] Milling operations in ops mode (profile/pocket via path length or MRR)
- [ ] Add 16×16 / 32×32 button icons under `commands/quote/resources/`
- [ ] Quantity input in the palette + re-quote without re-clicking the button
- [ ] Handle assemblies (sum/iterate occurrences, per-component quotes)
- [ ] Graceful UX when the backend is unreachable (retry + clear error in palette)
- [ ] Unit handling: respect the design's unit system (mm/in) end-to-end
- [x] Pull real material name → map to backend material keys (fuzzy match)

## 🛠️ Backend

- [ ] Real STEP/3MF export from Fusion and multipart upload to the backend
- [ ] Persist quotes (SQLite + SQLAlchemy) and a `GET /api/v1/quote/{id}`
- [ ] More processes: turning, sheet-metal (bends/cuts), 3D printing
- [ ] Better complexity metric (feature count, thin walls, deep pockets)
- [ ] Configurable shop rates / margins via env or a `settings.toml`
- [ ] Tests (pytest) for the pricing engine + API contract
- [ ] Dockerfile + `docker compose up` for the backend

## 🎨 Add-in UX

- [ ] Nicer palette: line-item table, lead-time, copy-to-clipboard, branding
- [ ] Two-way palette messaging (HTML → Python events) for live re-quoting
- [ ] Settings command (backend URL, default material, default margin)
- [ ] "Send to cart / export quote PDF" stub

## 🔐 Later / stretch

- [ ] API key auth between add-in and backend
- [ ] Hosted backend + HTTPS, env-based base URL
- [ ] Quote history view inside Fusion
- [ ] CI: lint (ruff) + tests on push
- [ ] Demo GIF in the README

## 🧹 Housekeeping

- [ ] CONTRIBUTING.md + issue templates
- [ ] Keep the "not affiliated with Paperless Parts/Autodesk" disclaimer visible
