"""Great Value Pless Parts — Fusion add-in entry point.

Fusion calls run() when the add-in loads and stop() when it unloads. The actual
UI and logic live in the commands package; this file just wires it up. Keep it
generic — you shouldn't need to edit it as you add commands.
"""

from . import commands
from .lib import fusionAddInUtils as futil


def run(context):
    try:
        commands.start()
    except Exception:  # noqa: BLE001 - surface any startup failure to the user
        futil.handle_error("run", show_message_box=True)


def stop(context):
    try:
        futil.clear_handlers()
        commands.stop()
    except Exception:  # noqa: BLE001
        futil.handle_error("stop", show_message_box=True)
