"""Request/response schemas — the JSON contract between add-in and backend."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class MachineType(str, Enum):
    mill = "mill"
    lathe = "lathe"
    swiss = "swiss"


class Confidence(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class BoundingBox(BaseModel):
    """Axis-aligned bounding box of the part, in millimeters."""

    x_mm: float = Field(gt=0, description="Length along X (mm)")
    y_mm: float = Field(gt=0, description="Length along Y (mm)")
    z_mm: float = Field(gt=0, description="Length along Z (mm)")


class PartGeometry(BaseModel):
    """Geometry summary extracted from the Fusion design."""

    name: str = Field(default="Untitled Part")
    volume_cm3: float = Field(gt=0, description="Solid volume (cm^3)")
    surface_area_cm2: float = Field(gt=0, description="Surface area (cm^2)")
    bounding_box: BoundingBox
    mass_kg: float | None = Field(default=None, ge=0)


class QuoteRequest(BaseModel):
    geometry: PartGeometry
    material: str = Field(default="aluminum_6061", description="Material key or name")
    quantity: int = Field(default=1, ge=1, le=100_000)
    machine_type: MachineType = Field(default=MachineType.mill)


class LineItem(BaseModel):
    label: str
    amount: float
    detail: str | None = None


class PriceBreak(BaseModel):
    qty: int
    unit_price: float


class QuoteResponse(BaseModel):
    part_name: str
    material: str
    machine_type: MachineType
    quantity: int
    currency: str = "USD"

    unit_price: float
    total_price: float

    estimated_cycle_time_sec: float
    setup_time_min: float
    lead_time_days: int
    confidence: Confidence

    price_breaks: list[PriceBreak]
    line_items: list[LineItem]
    flags: list[str] = []
    notes: list[str] = []

    disclaimer: str = (
        "Off-brand estimate. Cost model ported from tlk-quoting-engine; cycle "
        "time is estimated from CAD geometry, not a verified toolpath. Confirm "
        "against CAM before issuing a firm quote."
    )
