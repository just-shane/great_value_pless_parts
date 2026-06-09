"""Request/response schemas — the JSON contract between add-in and backend."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Process(str, Enum):
    cnc_milling = "cnc_milling"
    cnc_turning = "cnc_turning"


class BoundingBox(BaseModel):
    """Axis-aligned bounding box of the part, in millimeters."""

    x_mm: float = Field(gt=0, description="Length along X (mm)")
    y_mm: float = Field(gt=0, description="Length along Y (mm)")
    z_mm: float = Field(gt=0, description="Length along Z (mm)")

    @property
    def volume_cm3(self) -> float:
        return (self.x_mm * self.y_mm * self.z_mm) / 1000.0


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
    process: Process = Field(default=Process.cnc_milling)


class LineItem(BaseModel):
    label: str
    amount: float
    detail: str | None = None


class QuoteResponse(BaseModel):
    part_name: str
    material: str
    process: Process
    quantity: int

    unit_price: float
    total_price: float
    lead_time_days: int
    currency: str = "USD"

    line_items: list[LineItem]
    notes: list[str] = []
    disclaimer: str = (
        "Great Value grade estimate. Not affiliated with Paperless Parts. "
        "Do not use to bid real work."
    )
