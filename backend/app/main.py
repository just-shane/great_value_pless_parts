"""FastAPI app for the Great Value Pless Parts quoting service."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .materials import MATERIALS
from .models import QuoteRequest, QuoteResponse
from .pricing import estimate

app = FastAPI(
    title="Great Value Pless Parts — Quoting API",
    description=(
        "Off-brand instant quoting backend. Receives part geometry and returns a "
        "toy machining cost estimate. Not affiliated with Paperless Parts."
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


@app.get("/api/v1/materials")
def list_materials() -> dict:
    """Return the supported materials and their reference properties."""
    return {
        "materials": [
            {
                "key": m.key,
                "name": m.name,
                "density_g_cm3": m.density,
                "cost_per_kg_usd": m.cost_per_kg,
                "machinability": m.machinability,
            }
            for m in MATERIALS.values()
        ]
    }


@app.post("/api/v1/quote", response_model=QuoteResponse)
def create_quote(request: QuoteRequest) -> QuoteResponse:
    """Estimate a price for the submitted part geometry."""
    return estimate(request)
