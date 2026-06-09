# TODO — Great Value Pless Parts

Roadmap for the off-brand Paperless Parts clone. Loosely ordered; check things
off as they land.

## ✅ Done (initial scaffold)

- [x] Research Paperless Parts' Fusion integration + the Fusion add-in API
- [x] Repo layout, README, license, `.gitignore`
- [x] FastAPI quoting backend: `/health`, `/api/v1/materials`, `/api/v1/quote`
- [x] Naive pricing engine (material + machining + setup + markup + price breaks)
- [x] Materials table (Al 6061, SS 304, 1018 steel, brass, Ti, ABS, Delrin)
- [x] Fusion add-in skeleton: manifest, `run`/`stop`, command + button
- [x] Geometry/property extractor from the active design
- [x] HTTP client + palette to display the returned quote
- [x] `sample_payload.json` so the API is testable without Fusion

## 🔜 Next up (MVP polish)

- [ ] Add 16×16 / 32×32 button icons under `commands/quote/resources/`
- [ ] Quantity input in the palette + re-quote without re-clicking the button
- [ ] Handle assemblies (sum/iterate occurrences, per-component quotes)
- [ ] Graceful UX when the backend is unreachable (retry + clear error in palette)
- [ ] Unit handling: respect the design's unit system (mm/in) end-to-end
- [ ] Pull real material name → map to backend material keys (fuzzy match)

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
