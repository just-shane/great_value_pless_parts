"""The "Get Quote" command: a button + dialog that quotes the active part.

Flow: button -> dialog (material / quantity / process) -> extract geometry ->
POST to backend -> show the quote in a docked palette.
"""

import json
import os

import adsk.core

from ... import config
from ...lib import api_client, cam_extractor, extractor
from ...lib import fusionAddInUtils as futil

app = adsk.core.Application.get()
ui = app.userInterface

# --- UI identifiers ----------------------------------------------------------
CMD_ID = f"{config.COMPANY_NAME}_{config.ADDIN_NAME}_getQuote"
CMD_NAME = "Get Quote"
CMD_DESCRIPTION = "Estimate the machining cost of the active part (off-brand)."

WORKSPACE_ID = "FusionSolidEnvironment"
TAB_ID = "SolidTab"
PANEL_ID = f"{config.COMPANY_NAME}_panel"
PANEL_NAME = "Great Value"

PALETTE_ID = f"{config.COMPANY_NAME}_{config.ADDIN_NAME}_palette"
PALETTE_NAME = "Great Value Quote"

# Resolve the palette HTML relative to the add-in root (this file is at
# <addin>/commands/quote/entry.py, so go up three levels).
_ADDIN_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PALETTE_URL = os.path.join(_ADDIN_ROOT, "resources", "palette", "index.html")

# Empty string => Fusion uses a default button icon. Drop 16x16/32x32 PNGs in a
# resources folder and point here to brand the button.
ICON_FOLDER = ""

# --- Dialog choices (mirror the backend material keys) -----------------------
MATERIAL_CHOICES = [
    ("auto", "Auto-detect from design"),
    ("aluminum_6061", "Aluminum 6061-T6"),
    ("aluminum_7075", "Aluminum 7075-T6"),
    ("steel_1018", "Mild Steel 1018"),
    ("stainless_304", "Stainless Steel 304"),
    ("stainless_316", "Stainless Steel 316"),
    ("brass_360", "Brass 360"),
    ("titanium_ti6al4v", "Titanium Ti-6Al-4V"),
    ("peek", "PEEK"),
    ("abs", "ABS Plastic"),
    ("delrin", "Delrin / Acetal"),
]

MACHINE_CHOICES = [
    ("mill", "CNC Mill"),
    ("lathe", "CNC Lathe (Turning)"),
    ("swiss", "Swiss / Screw Machine"),
]

# Handlers scoped to a single command invocation.
local_handlers = []

# The most recent quote, held so we can hand it to the palette once it loads.
_last_quote = None


def start():
    """Create the command definition and place its button in the toolbar."""
    cmd_def = ui.commandDefinitions.itemById(CMD_ID)
    if not cmd_def:
        cmd_def = ui.commandDefinitions.addButtonDefinition(
            CMD_ID, CMD_NAME, CMD_DESCRIPTION, ICON_FOLDER
        )
    futil.add_handler(cmd_def.commandCreated, command_created)

    panel = _get_or_create_panel()
    if panel and not panel.controls.itemById(CMD_ID):
        control = panel.controls.addCommand(cmd_def)
        control.isPromoted = True


def stop():
    """Tear down the button, panel (if empty), command def, and palette."""
    panel = _get_panel()
    if panel:
        control = panel.controls.itemById(CMD_ID)
        if control:
            control.deleteMe()
        if panel.controls.count == 0:
            panel.deleteMe()

    cmd_def = ui.commandDefinitions.itemById(CMD_ID)
    if cmd_def:
        cmd_def.deleteMe()

    palette = ui.palettes.itemById(PALETTE_ID)
    if palette:
        palette.deleteMe()


# --- Toolbar plumbing --------------------------------------------------------
def _get_panel():
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    if not workspace:
        return None
    tab = workspace.toolbarTabs.itemById(TAB_ID)
    if not tab:
        return None
    return tab.toolbarPanels.itemById(PANEL_ID)


def _get_or_create_panel():
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    if not workspace:
        return None
    tab = workspace.toolbarTabs.itemById(TAB_ID)
    if not tab:
        return None
    panel = tab.toolbarPanels.itemById(PANEL_ID)
    if not panel:
        panel = tab.toolbarPanels.add(PANEL_ID, PANEL_NAME, "", False)
    return panel


# --- Command lifecycle -------------------------------------------------------
def command_created(args: adsk.core.CommandCreatedEventArgs):
    futil.log(f"{CMD_NAME} command created")
    inputs = args.command.commandInputs

    material_input = inputs.addDropDownCommandInput(
        "material", "Material", adsk.core.DropDownStyles.TextListDropDownStyle
    )
    for index, (_key, label) in enumerate(MATERIAL_CHOICES):
        material_input.listItems.add(label, index == 0)

    inputs.addIntegerSpinnerCommandInput(
        "quantity", "Quantity", 1, 100000, 1, config.DEFAULT_QUANTITY
    )

    machine_input = inputs.addDropDownCommandInput(
        "machine_type", "Machine", adsk.core.DropDownStyles.TextListDropDownStyle
    )
    for index, (_key, label) in enumerate(MACHINE_CHOICES):
        machine_input.listItems.add(label, index == 0)

    futil.add_handler(args.command.execute, command_execute, local_handlers=local_handlers)
    futil.add_handler(args.command.destroy, command_destroy, local_handlers=local_handlers)


def command_execute(args: adsk.core.CommandEventArgs):
    global _last_quote
    inputs = args.command.commandInputs

    material_key = _selected_key(inputs.itemById("material"), MATERIAL_CHOICES)
    machine_key = _selected_key(inputs.itemById("machine_type"), MACHINE_CHOICES)
    quantity = inputs.itemById("quantity").value

    try:
        geometry, detected_material = extractor.get_active_part_geometry()
    except RuntimeError as err:
        ui.messageBox(str(err), CMD_NAME)
        return

    # "Auto" => use the design's assigned material name; the backend fuzzy-matches.
    if material_key == "auto":
        material = detected_material or config.DEFAULT_MATERIAL
    else:
        material = material_key

    # If the document is programmed (has CAM), auto-fill everything from the CAM
    # setup: real operations + machining times, machine type, stock material, and
    # actual stock volume. CAM values override the dialog selections.
    operations = None
    try:
        cam = cam_extractor.get_cam_inputs()
        if cam and cam.get("available"):
            operations = cam.get("operations")
            if cam.get("machine_type"):
                machine_key = cam["machine_type"]
            if cam.get("material_name"):
                material = cam["material_name"]
            if cam.get("stock_volume_cm3"):
                geometry["stock_volume_cm3"] = cam["stock_volume_cm3"]
            futil.log(
                f"CAM auto-fill: {len(operations or [])} ops, "
                f"machine={machine_key}, material={material}"
            )
    except Exception:  # noqa: BLE001 - CAM is optional; never block the quote
        operations = None

    try:
        quote = api_client.request_quote(geometry, material, quantity, machine_key, operations)
    except RuntimeError as err:
        ui.messageBox(str(err), CMD_NAME)
        return

    _last_quote = quote
    futil.log(f"Quote: {quote.get('unit_price')} / unit x {quantity}")
    _show_palette()


def command_destroy(args: adsk.core.CommandEventArgs):
    global local_handlers
    local_handlers = []
    futil.log(f"{CMD_NAME} command destroyed")


# --- Palette -----------------------------------------------------------------
def _show_palette():
    palette = ui.palettes.itemById(PALETTE_ID)
    if not palette:
        palette = ui.palettes.add(
            PALETTE_ID,
            PALETTE_NAME,
            PALETTE_URL,
            True,   # isVisible
            True,   # showCloseButton
            True,   # isResizable
            420,    # width
            520,    # height
        )
        palette.dockingState = adsk.core.PaletteDockingStates.PaletteDockStateRight
        futil.add_handler(palette.incomingFromHTML, palette_incoming, local_handlers=local_handlers)

    palette.isVisible = True
    # Try an immediate push; if the page hasn't loaded yet it will re-request
    # via the 'ready' message below.
    _send_quote(palette)


def _send_quote(palette):
    if _last_quote is not None:
        palette.sendInfoToHTML("quote", json.dumps(_last_quote))


def palette_incoming(args: adsk.core.HTMLEventArgs):
    action = args.action
    if action == "ready":
        palette = ui.palettes.itemById(PALETTE_ID)
        if palette:
            _send_quote(palette)
    elif action == "close":
        palette = ui.palettes.itemById(PALETTE_ID)
        if palette:
            palette.isVisible = False
    args.returnData = "OK"


# --- Helpers -----------------------------------------------------------------
def _selected_key(dropdown_input, choices):
    """Map a dropdown's selected row back to its underlying choice key."""
    item = dropdown_input.selectedItem if dropdown_input else None
    index = item.index if item else 0
    return choices[index][0]
