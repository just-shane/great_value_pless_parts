"""Read CAM operations (and Fusion's own machining times) from the active doc.

When the active document has a Manufacture (CAM) product with generated
toolpaths, this returns a list of operations in the backend's contract, each
carrying Fusion's computed ``cycle_time_sec``. The backend then prices from
those real times (confidence ``high``, source ``fusion_cam``) — no speeds/feeds
lookup needed.

When there's no CAM (or no generated toolpaths), it returns ``None`` and the
caller falls back to geometry mode.
"""

import adsk.core
import adsk.cam

# getMachiningTime tuning: feed scale %, rapid feed (cm/s ~ 1000 in/min), tool-change sec.
_FEED_SCALE = 100.0
_RAPID_FEED_CM_S = 42.0
_TOOL_CHANGE_SEC = 5.0

# Fusion CAM strategyType -> backend operation type.
_STRATEGY_MAP = {
    "turningProfile": "turn",
    "turningProfileGroove": "turn",
    "turningChamfer": "turn",
    "turningBore": "turn",
    "turningStock": "turn",
    "turningFace": "face",
    "turningGroove": "groove",
    "turningSingleGroove": "groove",
    "turningPart": "cutoff",
    "turningThread": "thread",
    "drilling": "drill",
    "tapping": "drill",
}


def get_active_cam():
    app = adsk.core.Application.get()
    doc = app.activeDocument
    if not doc:
        return None
    for product in doc.products:
        if product.productType == "CAMProductType":
            return adsk.cam.CAM.cast(product)
    return None


def _map_type(strategy: str) -> str:
    if not strategy:
        return "mill"
    if strategy in _STRATEGY_MAP:
        return _STRATEGY_MAP[strategy]
    s = strategy.lower()
    if "drill" in s or "bore" in s or "tap" in s:
        return "drill"
    if "thread" in s:
        return "thread"
    if "face" in s:
        return "face"
    if "groove" in s:
        return "groove"
    if "part" in s or "cutoff" in s:
        return "cutoff"
    if "turn" in s:
        return "turn"
    return "mill"  # any milling strategy; time comes from CAM, not a formula


def _tool_dia_in(op):
    try:
        tool = op.tool
        if not tool:
            return None
        param = tool.parameters.itemByName("tool_diameter")
        if param and param.value:
            return round(param.value.value / 2.54, 4)  # internal cm -> in
    except Exception:
        return None
    return None


def get_cam_operations():
    """Return ``{available, operations, total_machining_sec}`` or ``None``."""
    cam = get_active_cam()
    if not cam:
        return None
    if cam.allOperations.count == 0:
        return {"available": False, "reason": "no_cam_operations"}

    operations = []
    generated = adsk.core.ObjectCollection.create()
    for op in cam.allOperations:
        if not op.hasToolpath:
            continue
        generated.add(op)
        seconds = None
        try:
            mt = cam.getMachiningTime(op, _FEED_SCALE, _RAPID_FEED_CM_S, _TOOL_CHANGE_SEC)
            seconds = round(mt.machiningTime, 2)
        except Exception:
            seconds = None
        operations.append(
            {
                "type": _map_type(op.strategyType),
                "label": op.name,
                "dia_in": _tool_dia_in(op),
                "cycle_time_sec": seconds,
            }
        )

    if not operations:
        return {"available": False, "reason": "toolpaths_not_generated"}

    total = None
    try:
        total = round(
            cam.getMachiningTime(generated, _FEED_SCALE, _RAPID_FEED_CM_S, _TOOL_CHANGE_SEC).machiningTime,
            2,
        )
    except Exception:
        total = None

    return {"available": True, "operations": operations, "total_machining_sec": total}
