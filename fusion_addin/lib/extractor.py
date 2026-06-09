"""Pull a geometry summary out of the active Fusion design.

Fusion's internal API units are centimeters, square centimeters, cubic
centimeters, and kilograms, so we convert lengths to millimeters to match the
backend's JSON contract (see ``backend/app/models.py``).
"""

import adsk.core
import adsk.fusion


def get_active_part_geometry():
    """Return ``(geometry_dict, detected_material_name)`` for the active design.

    Raises ``RuntimeError`` with a user-friendly message if there's nothing to
    quote (no design open, or no solid bodies).
    """
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        raise RuntimeError(
            "No active Fusion design.\nOpen a part in the Design workspace and try again."
        )

    root = design.rootComponent
    if root.bRepBodies.count == 0 and root.occurrences.count == 0:
        raise RuntimeError("This design has no solid bodies to quote.")

    props = root.physicalProperties  # area (cm^2), volume (cm^3), mass (kg)

    bbox = root.boundingBox  # min/max points in cm
    x_mm = (bbox.maxPoint.x - bbox.minPoint.x) * 10.0
    y_mm = (bbox.maxPoint.y - bbox.minPoint.y) * 10.0
    z_mm = (bbox.maxPoint.z - bbox.minPoint.z) * 10.0

    detected_material = root.material.name if root.material else ""
    part_name = app.activeDocument.name if app.activeDocument else root.name

    geometry = {
        "name": part_name or "Untitled Part",
        "volume_cm3": round(props.volume, 4),
        "surface_area_cm2": round(props.area, 4),
        "bounding_box": {
            "x_mm": round(x_mm, 3),
            "y_mm": round(y_mm, 3),
            "z_mm": round(z_mm, 3),
        },
        "mass_kg": round(props.mass, 5),
    }
    return geometry, detected_material
