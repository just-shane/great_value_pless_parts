"""Command registry. Each command module exposes start()/stop()."""

from .quote import entry as quote

# Add new command modules here; start()/stop() will fan out to all of them.
commands = [quote]


def start():
    for command in commands:
        command.start()


def stop():
    for command in commands:
        command.stop()
