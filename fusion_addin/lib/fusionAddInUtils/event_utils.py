"""Helpers for attaching Fusion event handlers without losing references.

Fusion will garbage-collect handler objects that aren't kept alive, which is a
classic source of "my handler never fires" bugs. ``add_handler`` builds the
right handler subclass for the given event and stashes it in a module-level
list (or a caller-supplied ``local_handlers`` list) so it survives.
"""

import sys

from . import general_utils as futil

# Module-level references so handlers aren't garbage-collected.
handlers = []


def add_handler(event, callback, *, name: str = None, local_handlers: list = None):
    """Create and register an event handler that calls ``callback(args)``."""
    module = sys.modules[event.__module__]
    handler_type_name = event.classType().split("::")[-1] + "Handler"
    handler_type = module.__dict__[handler_type_name]
    handler = _create_handler(handler_type, callback, name)
    event.add(handler)
    (handlers if local_handlers is None else local_handlers).append(handler)
    return handler


def _create_handler(handler_type, callback, name):
    label = name or getattr(callback, "__name__", "handler")

    class _Handler(handler_type):
        def __init__(self):
            super().__init__()

        def notify(self, args):
            try:
                callback(args)
            except Exception:  # noqa: BLE001
                futil.handle_error(label)

    return _Handler()


def clear_handlers():
    """Drop all globally tracked handlers (called on add-in stop)."""
    global handlers
    handlers = []
