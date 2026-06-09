"""Material master for the pricing engine.

``rate_usd_per_in3`` is the raw bar-stock price per cubic inch (anchored to the
in-house ``tlk-quoting-engine`` rates for 6061, 304, brass, and PEEK; the rest
are reasonable shop ballparks). ``machinability`` is a relative cutting-ease
factor (1.0 == 6061-T6). ``density_lb_in3`` is used for weight display only.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Material:
    key: str
    name: str
    rate_usd_per_in3: float
    machinability: float
    density_lb_in3: float


MATERIALS: dict[str, Material] = {
    m.key: m
    for m in (
        Material("aluminum_6061", "Aluminum 6061-T6", 0.09, 1.00, 0.098),
        Material("aluminum_7075", "Aluminum 7075-T6", 0.14, 0.90, 0.102),
        Material("steel_1018", "Mild Steel 1018", 0.06, 0.78, 0.284),
        Material("stainless_304", "Stainless Steel 304", 0.18, 0.50, 0.289),
        Material("stainless_316", "Stainless Steel 316", 0.24, 0.45, 0.289),
        Material("brass_360", "Brass C360", 0.22, 1.30, 0.307),
        Material("titanium_ti6al4v", "Titanium Ti-6Al-4V", 1.10, 0.22, 0.160),
        Material("peek", "PEEK", 1.40, 1.20, 0.047),
        Material("abs", "ABS Plastic", 0.06, 1.60, 0.038),
        Material("delrin", "Delrin / Acetal", 0.15, 1.45, 0.051),
    )
}

DEFAULT_MATERIAL_KEY = "aluminum_6061"


def resolve_material(name_or_key: str | None) -> Material:
    """Best-effort match a free-text material name/key to a known material."""
    if not name_or_key:
        return MATERIALS[DEFAULT_MATERIAL_KEY]

    needle = name_or_key.strip().lower()
    if needle in MATERIALS:
        return MATERIALS[needle]

    compact = needle.replace("-", " ").replace("_", " ")
    for mat in MATERIALS.values():
        haystacks = (mat.key.replace("_", " "), mat.name.lower())
        if any(compact in h or h in compact for h in haystacks):
            return mat

    for mat in MATERIALS.values():
        family = mat.name.split()[0].lower()
        if family in compact:
            return mat

    return MATERIALS[DEFAULT_MATERIAL_KEY]
