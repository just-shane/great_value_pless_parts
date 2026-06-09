"""FastAPI app for the Great Value Pless Parts quoting service."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .materials import MATERIALS
from .models import QuoteRequest, QuoteResponse
from .pricing import estimate
from .shop import PARAMS

app = FastAPI(
    title="Great Value Pless Parts — Quoting API",
    description=(
        "Off-brand instant quoting backend. Receives part geometry and returns a "
        "machining cost estimate using a cost model ported from tlk-quoting-engine. "
        "Not affiliated with Paperless Parts."
    ),
    version=__version__,
)

# The Fusion palette (and local tooling) call this from a different origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": __version__}


@app.get("/api/v1/params")
def shop_params() -> dict:
    """Return the shop-level rate configuration driving the quotes."""
    return {k: v for k, v in PARAMS.items() if not k.startswith("_")}


@app.get("/api/v1/materials")
def list_materials() -> dict:
    """Return the material master and its reference properties."""
    return {
        "materials": [
            {
                "key": m.key,
                "name": m.name,
                "rate_usd_per_in3": m.rate_usd_per_in3,
                "machinability": m.machinability,
                "density_lb_in3": m.density_lb_in3,
            }
            for m in MATERIALS.values()
        ]
    }


@app.post("/api/v1/quote", response_model=QuoteResponse)
def create_quote(request: QuoteRequest) -> QuoteResponse:
    """Estimate a price for the submitted part geometry."""
    return estimate(request)
