"""Material reference table for the (toy) pricing engine.

Densities are in g/cm^3. ``cost_per_kg`` is a rough USD raw-stock price.
``machinability`` is a relative ease-of-cutting factor (1.0 == aluminum 6061);
higher means faster material removal, lower means slower/harder.

These numbers are ballpark figures for a demo, not a sourcing database.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Material:
    key: str
    name: str
    density: float        # g/cm^3
    cost_per_kg: float    # USD per kg of raw stock
    machinability: float  # relative cutting ease, 6061-T6 == 1.0


MATERIALS: dict[str, Material] = {
    m.key: m
    for m in (
        Material("aluminum_6061", "Aluminum 6061-T6", 2.70, 6.50, 1.00),
        Material("aluminum_7075", "Aluminum 7075-T6", 2.81, 11.00, 0.90),
        Material("steel_1018", "Mild Steel 1018", 7.87, 1.50, 0.78),
        Material("stainless_304", "Stainless Steel 304", 8.00, 9.00, 0.50),
        Material("stainless_316", "Stainless Steel 316", 8.00, 11.50, 0.45),
        Material("brass_360", "Brass 360", 8.50, 11.00, 1.30),
        Material("titanium_ti6al4v", "Titanium Ti-6Al-4V", 4.43, 35.00, 0.22),
        Material("abs", "ABS Plastic", 1.05, 3.00, 1.60),
        Material("delrin", "Delrin / Acetal", 1.41, 8.00, 1.45),
    )
}

DEFAULT_MATERIAL_KEY = "aluminum_6061"


def resolve_material(name_or_key: str | None) -> Material:
    """Best-effort match a free-text material name to a known material.

    Tries an exact key match first, then a loose substring match against keys
    and display names, then falls back to the default material.
    """
    if not name_or_key:
        return MATERIALS[DEFAULT_MATERIAL_KEY]

    needle = name_or_key.strip().lower()
    if needle in MATERIALS:
        return MATERIALS[needle]

    # token-ish substring match against keys and names
    compact = needle.replace("-", " ").replace("_", " ")
    for mat in MATERIALS.values():
        haystacks = (
            mat.key.replace("_", " "),
            mat.name.lower(),
        )
        if any(compact in h or h in compact for h in haystacks):
            return mat

    # match on leading family word, e.g. "aluminum 6061 t6 sheet"
    for mat in MATERIALS.values():
        family = mat.name.split()[0].lower()
        if family in compact:
            return mat

    return MATERIALS[DEFAULT_MATERIAL_KEY]
