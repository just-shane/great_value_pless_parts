"""Cost-estimation engine — a faithful port of the tlk-quoting-engine model.

Pricing formula (see tlk-quoting-engine/docs/COST_MODEL.md):

    price_per_piece = (machine + material + tooling + setup_amortized)
                      x overhead / (1 - margin)

      machine_cost    = cycle_time_sec / 3600 x machine_hourly_rate
      material_cost   = stock_volume_in3 x material_rate_per_in3
      setup_amortized = (setup_min / 60 x hourly_rate) / order_qty

The one thing TLK gets from its operation graph that GVPP does not have is
**cycle time**. Here it is estimated from CAD geometry (removed volume + surface
area) and explicitly flagged, so the number is honest rather than fake-precise.
"""

from __future__ import annotations

import math

from .materials import Material, resolve_material
from .models import (
    Confidence,
    LineItem,
    MachineType,
    PartGeometry,
    PriceBreak,
    QuoteRequest,
    QuoteResponse,
)
from .shop import PARAMS

# Unit conversions (Fusion/wire units are metric; the cost model is imperial).
CM3_PER_IN3 = 16.387064
CM2_PER_IN2 = 6.4516
MM_PER_IN = 25.4

_ROUND_BREAK_QTYS = (1, 10, 100, 1000)


def _round2(value: float) -> float:
    return round(value + 1e-9, 2)


def _stock_volume_in3(geom: PartGeometry, machine_type: MachineType, waste: float) -> float:
    """Raw stock volume (in^3): a bounding box for milling, a bounding cylinder
    for turning/Swiss, plus a waste allowance."""
    x_in = geom.bounding_box.x_mm / MM_PER_IN
    y_in = geom.bounding_box.y_mm / MM_PER_IN
    z_in = geom.bounding_box.z_mm / MM_PER_IN

    if machine_type in (MachineType.lathe, MachineType.swiss):
        a, b, length = sorted((x_in, y_in, z_in))  # longest dim = bar length
        diameter = b  # next-largest dim sets the bar diameter
        volume = math.pi * (diameter / 2.0) ** 2 * length
    else:
        volume = x_in * y_in * z_in

    return volume * (1.0 + waste)


def _cycle_time_sec(
    removed_in3: float,
    area_in2: float,
    machinability: float,
    machine_type: MachineType,
    cfg: dict,
) -> float:
    """Estimate spindle cycle time from geometry (roughing + finishing + handling)."""
    mrr_mult = (
        cfg.get("lathe_mrr_multiplier", 1.0)
        if machine_type in (MachineType.lathe, MachineType.swiss)
        else 1.0
    )
    effective_mrr = max(cfg["base_mrr_in3_per_min"] * machinability * mrr_mult, 0.05)

    roughing_sec = (removed_in3 / effective_mrr) * 60.0
    finishing_sec = area_in2 * cfg["finish_seconds_per_in2"] / max(machinability, 0.2)
    handling_sec = cfg["handling_seconds"]
    return roughing_sec + finishing_sec + handling_sec


def _unit_price(
    machine_cost: float,
    material_cost: float,
    tooling: float,
    setup_min: float,
    hourly_rate: float,
    qty: int,
    overhead: float,
    margin_fraction: float,
) -> float:
    setup_amortized = (setup_min / 60.0) * hourly_rate / qty
    subtotal = (machine_cost + material_cost + tooling + setup_amortized) * overhead
    return subtotal / (1.0 - margin_fraction)


def _confidence_and_flags(
    material: Material,
    removed_ratio: float,
    area_to_volume: float,
) -> tuple[Confidence, list[str]]:
    """Geometry-mode confidence. Caps at MEDIUM — HIGH requires an operation graph."""
    flags = ["cycle_time_estimated_from_geometry", "tolerances_unknown_assumed_standard"]
    confidence = Confidence.medium

    if material.machinability < 0.40:
        flags.append("hard_material_verify_tooling")
        confidence = Confidence.low
    if removed_ratio > 0.85:
        flags.append("high_stock_removal_verify_roughing")
        confidence = Confidence.low
    if area_to_volume > 12.0:
        flags.append("complex_or_thin_walls_human_review")
        confidence = Confidence.low

    return confidence, flags


def estimate(request: QuoteRequest) -> QuoteResponse:
    p = PARAMS
    geom = request.geometry
    material = resolve_material(request.material)
    machine_type = request.machine_type
    qty = request.quantity

    hourly_rate = p["machine_hourly_rate_usd"]
    setup_min = p["setup_time_minutes"][machine_type.value]
    tooling = p["tooling_amortization_per_cycle_usd"]
    overhead = p["overhead_multiplier"]
    margin_fraction = p["margin_percent"] / 100.0
    waste = p["stock_waste_factor"]
    cycle_cfg = p["cycle_time_estimation"]

    # --- Geometry in imperial -------------------------------------------------
    part_in3 = geom.volume_cm3 / CM3_PER_IN3
    area_in2 = geom.surface_area_cm2 / CM2_PER_IN2
    stock_in3 = _stock_volume_in3(geom, machine_type, waste)
    if stock_in3 < part_in3:  # guard against odd geometry
        stock_in3 = part_in3 * (1.0 + waste)
    removed_in3 = max(stock_in3 - part_in3, 0.0)

    # --- Cost components ------------------------------------------------------
    material_cost = stock_in3 * material.rate_usd_per_in3
    cycle_sec = _cycle_time_sec(removed_in3, area_in2, material.machinability, machine_type, cycle_cfg)
    machine_cost = (cycle_sec / 3600.0) * hourly_rate

    # --- Price + breaks -------------------------------------------------------
    def price_at(q: int) -> float:
        return _unit_price(machine_cost, material_cost, tooling, setup_min, hourly_rate, q, overhead, margin_fraction)

    unit_price = _round2(price_at(qty))
    total_price = _round2(unit_price * qty)
    break_qtys = sorted({1, qty, *_ROUND_BREAK_QTYS})
    price_breaks = [PriceBreak(qty=q, unit_price=_round2(price_at(q))) for q in break_qtys]

    # --- Line items at the requested quantity ---------------------------------
    setup_amortized = (setup_min / 60.0) * hourly_rate / qty
    subtotal = machine_cost + material_cost + tooling + setup_amortized
    margin_amount = (subtotal * overhead) / (1.0 - margin_fraction) - (subtotal * overhead)
    overhead_amount = subtotal * overhead - subtotal

    line_items = [
        LineItem(
            label="Machine time",
            amount=_round2(machine_cost),
            detail=f"{cycle_sec / 60.0:.1f} min cycle @ ${hourly_rate:.0f}/hr (cycle est. from geometry)",
        ),
        LineItem(
            label="Material",
            amount=_round2(material_cost),
            detail=f"{stock_in3:.2f} in^3 {material.name} stock @ ${material.rate_usd_per_in3:.2f}/in^3",
        ),
        LineItem(
            label="Tooling",
            amount=_round2(tooling),
            detail="per-piece tooling amortization",
        ),
        LineItem(
            label="Setup (per unit)",
            amount=_round2(setup_amortized),
            detail=f"{setup_min:.0f} min {machine_type.value} setup amortized over {qty} pc",
        ),
        LineItem(
            label="Overhead",
            amount=_round2(overhead_amount),
            detail=f"{int((overhead - 1) * 100)}% overhead multiplier",
        ),
        LineItem(
            label="Margin",
            amount=_round2(margin_amount),
            detail=f"{p['margin_percent']}% gross margin",
        ),
    ]

    # --- Confidence, flags, lead time, notes ----------------------------------
    removed_ratio = removed_in3 / stock_in3 if stock_in3 else 0.0
    area_to_volume = area_in2 / part_in3 if part_in3 else 0.0
    confidence, flags = _confidence_and_flags(material, removed_ratio, area_to_volume)

    lead = p["lead_time"]
    lead_time_days = (
        lead["base_days"]
        + int(qty / 25) * lead["days_per_25_units"]
        + (lead["hard_material_penalty_days"] if material.machinability < 0.40 else 0)
        + (lead["low_confidence_penalty_days"] if confidence is Confidence.low else 0)
    )

    notes: list[str] = [
        "Cycle time is estimated from CAD geometry - confirm against CAM for a firm quote.",
    ]
    if qty == 1:
        notes.append("Single piece: setup dominates. Per-unit price drops sharply with quantity.")
    if confidence is Confidence.low:
        notes.append("Low confidence: flagged for estimator review before sending.")

    return QuoteResponse(
        part_name=geom.name,
        material=material.name,
        machine_type=machine_type,
        quantity=qty,
        unit_price=unit_price,
        total_price=total_price,
        estimated_cycle_time_sec=round(cycle_sec, 1),
        setup_time_min=float(setup_min),
        lead_time_days=lead_time_days,
        confidence=confidence,
        price_breaks=price_breaks,
        line_items=line_items,
        flags=flags,
        notes=notes,
    )
