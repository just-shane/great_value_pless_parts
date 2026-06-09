"""Logging and error-handling helpers."""

import traceback

import adsk.core

from ... import config

app = adsk.core.Application.get()
ui = app.userInterface


def log(message: str, level=adsk.core.LogLevels.InfoLogLevel, force_console: bool = False):
    """Write a message to the Fusion Text Commands console when DEBUG is on."""
    if not config.DEBUG and not force_console:
        return
    app.log(f"[{config.ADDIN_NAME}] {message}", level, adsk.core.LogTypes.ConsoleLogType)


def handle_error(name: str, show_message_box: bool = False):
    """Log an exception traceback; optionally pop a message box."""
    log("----- Error -----", force_console=True)
    log(f"{name}\n{traceback.format_exc()}", force_console=True)
    if show_message_box and ui:
        ui.messageBox(
            f"'{name}' failed:\n\n{traceback.format_exc()}",
            "Great Value Pless Parts",
        )
