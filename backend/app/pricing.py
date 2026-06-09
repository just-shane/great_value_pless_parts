"""The (deliberately naive) cost-estimation engine.

This is *not* a real quoting model. It produces plausible-looking numbers from
crude heuristics so the end-to-end Fusion -> backend -> quote loop has something
to show. See the README disclaimer.
"""

from __future__ import annotations

from .materials import Material, resolve_material
from .models import LineItem, Process, QuoteRequest, QuoteResponse

# ---- Shop "configuration" knobs (USD) --------------------------------------
MACHINE_RATE_PER_HR = 75.0      # spindle time billing rate
SETUP_COST = 60.0               # flat per-setup charge (amortized over qty)
STOCK_WASTE_FACTOR = 0.15       # extra stock bought beyond the bounding box
BASE_MRR_CM3_PER_MIN = 12.0     # material removal rate for a 1.0-machinability material
MARGIN_MULTIPLIER = 1.35        # gross margin markup
MIN_MACHINING_MIN = 5.0         # nobody sets up a job for 30 seconds
BASE_LEAD_DAYS = 5


def _round_money(value: float) -> float:
    return round(value + 1e-9, 2)


def _quantity_discount(quantity: int) -> float:
    """Per-unit machining multiplier that eases off as volume grows.

    1 pc -> 1.0, then a gentle decay bottoming out around 0.7 for big runs.
    """
    if quantity <= 1:
        return 1.0
    # logarithmic-ish decay without importing math: simple, monotonic, bounded
    discount = 0.06 * (quantity - 1) / quantity
    return max(0.70, 1.0 - discount)


def estimate(request: QuoteRequest) -> QuoteResponse:
    geom = request.geometry
    material: Material = resolve_material(request.material)
    qty = request.quantity
    notes: list[str] = []

    # --- Material cost ------------------------------------------------------
    stock_volume_cm3 = geom.bounding_box.volume_cm3 * (1.0 + STOCK_WASTE_FACTOR)
    if stock_volume_cm3 < geom.volume_cm3:
        # part volume should never exceed its bounding box; guard anyway
        stock_volume_cm3 = geom.volume_cm3 * (1.0 + STOCK_WASTE_FACTOR)
    stock_mass_kg = stock_volume_cm3 * material.density / 1000.0
    material_cost = stock_mass_kg * material.cost_per_kg

    # --- Machining cost -----------------------------------------------------
    removed_volume_cm3 = max(stock_volume_cm3 - geom.volume_cm3, 0.0)
    mrr = BASE_MRR_CM3_PER_MIN * material.machinability
    roughing_min = removed_volume_cm3 / mrr if mrr > 0 else 0.0

    # surface-area term stands in for finishing/complexity (cm^2 -> minutes)
    finishing_min = geom.surface_area_cm2 * 0.05 / material.machinability

    if request.process is Process.cnc_turning:
        # turning is generally quicker per unit volume on round stock
        roughing_min *= 0.8
        notes.append("Turning selected: roughing time scaled for round stock.")

    machining_min = max(roughing_min + finishing_min, MIN_MACHINING_MIN)
    machining_min *= _quantity_discount(qty)
    machining_cost = (machining_min / 60.0) * MACHINE_RATE_PER_HR

    # --- Setup (amortized over the order) -----------------------------------
    setup_per_unit = SETUP_COST / qty

    # --- Roll up ------------------------------------------------------------
    raw_unit_cost = material_cost + machining_cost + setup_per_unit
    unit_price = raw_unit_cost * MARGIN_MULTIPLIER
    total_price = unit_price * qty

    # --- Lead time (very rough) ---------------------------------------------
    lead_time_days = BASE_LEAD_DAYS + int(qty / 25) + (3 if material.machinability < 0.4 else 0)

    if material.machinability < 0.4:
        notes.append(f"{material.name} is hard to machine; expect longer lead time.")
    if qty == 1:
        notes.append("Single piece: setup dominates the price. Order more to amortize.")

    line_items = [
        LineItem(
            label="Material",
            amount=_round_money(material_cost),
            detail=(
                f"{stock_mass_kg:.3f} kg {material.name} "
                f"@ ${material.cost_per_kg:.2f}/kg (incl. {int(STOCK_WASTE_FACTOR * 100)}% waste)"
            ),
        ),
        LineItem(
            label="Machining",
            amount=_round_money(machining_cost),
            detail=f"{machining_min:.1f} min @ ${MACHINE_RATE_PER_HR:.0f}/hr",
        ),
        LineItem(
            label="Setup (per unit)",
            amount=_round_money(setup_per_unit),
            detail=f"${SETUP_COST:.0f} setup amortized over {qty} pc",
        ),
        LineItem(
            label="Margin",
            amount=_round_money(unit_price - raw_unit_cost),
            detail=f"{int((MARGIN_MULTIPLIER - 1) * 100)}% markup",
        ),
    ]

    return QuoteResponse(
        part_name=geom.name,
        material=material.name,
        process=request.process,
        quantity=qty,
        unit_price=_round_money(unit_price),
        total_price=_round_money(total_price),
        lead_time_days=lead_time_days,
        line_items=line_items,
        notes=notes,
    )
