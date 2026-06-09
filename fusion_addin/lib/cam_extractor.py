"""Read quote inputs from the active doc's CAM (Manufacture) data.

When the document has a Manufacture (CAM) product, this returns everything the
backend needs to quote a *programmed* part with zero manual input:

  - operations  : each op's type + Fusion machiningTime (cycle_time_sec)
  - machine_type: from the setup operation type (mill / lathe / swiss)
  - material    : the setup's stock material name (backend fuzzy-matches it)
  - stock_volume_cm3 : real stock volume from the setup's stock solids

Returns ``None`` when there's no CAM; the caller falls back to the design
geometry + the dialog's material/machine selections.
"""

import adsk.core
import adsk.cam

# getMachiningTime tuning: feed scale %, rapid feed (cm/s ~ 1000 in/min), tool-change sec.
_FEED_SCALE = 100.0
_RAPID_FEED_CM_S = 42.0
_TOOL_CHANGE_SEC = 5.0

# Vendor/model substrings that imply a Swiss-type lathe.
_SWISS_KEYWORDS = ("swiss", "citizen", "star ", "tsugami", "tornos", "hanwha", "nexturn", "escomatic")

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


def _machine_type(setup) -> str | None:
    try:
        op_type = setup.operationType
    except Exception:
        return None
    if op_type == adsk.cam.OperationTypes.MillingOperation:
        return "mill"
    if op_type == adsk.cam.OperationTypes.TurningOperation:
        name = ""
        try:
            machine = setup.machine
            if machine:
                name = f"{machine.vendor or ''} {machine.model or ''} {machine.description or ''}".lower()
        except Exception:
            name = ""
        if any(k in name for k in _SWISS_KEYWORDS):
            return "swiss"
        return "lathe"
    return "mill"


def _stock_volume_cm3(setup):
    try:
        solids = setup.stockSolids
    except Exception:
        return None
    if not solids or solids.count == 0:
        return None
    total = 0.0
    found = False
    for ent in solids:
        try:
            props = ent.physicalProperties
            if props:
                total += props.volume
                found = True
        except Exception:
            continue
    return round(total, 4) if found and total > 0 else None


def _stock_material(setup):
    try:
        mat = setup.stockMaterial
    except Exception:
        return None
    if not mat:
        return None
    return getattr(mat, "name", None) or (mat if isinstance(mat, str) else None)


def get_cam_inputs():
    """Return ``{available, operations, machine_type, material_name,
    stock_volume_cm3, total_machining_sec}`` or ``None`` if there's no CAM."""
    cam = get_active_cam()
    if not cam:
        return None
    if cam.setups.count == 0 or cam.allOperations.count == 0:
        return {"available": False, "reason": "no_cam_operations"}

    operations = []
    generated = adsk.core.ObjectCollection.create()
    for op in cam.allOperations:
        if not op.hasToolpath:
            continue
        generated.add(op)
        seconds = None
        try:
            seconds = round(cam.getMachiningTime(op, _FEED_SCALE, _RAPID_FEED_CM_S, _TOOL_CHANGE_SEC).machiningTime, 2)
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

    # Setup-level inputs come from the first setup that has operations.
    setup = None
    for s in cam.setups:
        if s.allOperations.count > 0:
            setup = s
            break
    if setup is None:
        setup = cam.setups.item(0)

    total = None
    try:
        total = round(cam.getMachiningTime(generated, _FEED_SCALE, _RAPID_FEED_CM_S, _TOOL_CHANGE_SEC).machiningTime, 2)
    except Exception:
        total = None

    return {
        "available": True,
        "operations": operations,
        "machine_type": _machine_type(setup),
        "material_name": _stock_material(setup),
        "stock_volume_cm3": _stock_volume_cm3(setup),
        "total_machining_sec": total,
    }
