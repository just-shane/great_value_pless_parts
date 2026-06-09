"""Operation graph -> cycle time (the operations-mode path).

Operation types mirror the TLK turning node set (TurnCycleNode, FaceCycleNode,
DrillCycleNode, GrooveCycleNode, ThreadCycleNode, CutoffCycleNode). Cycle time
is computed with standard machining math from the surface speed + feed/rev that
come from the live Datum speeds-&-feeds database (see speeds_feeds.py):

    rpm   = sfm × 12 / (π × cutting_diameter)
    time  = length / (feed_per_rev × rpm)        [minutes] → ×60 → seconds
"""

from __future__ import annotations

import math
from enum import Enum

from pydantic import BaseModel, Field


class OperationType(str, Enum):
    turn = "turn"
    face = "face"
    drill = "drill"
    groove = "groove"
    thread = "thread"
    cutoff = "cutoff"


class Operation(BaseModel):
    """A single turning/Swiss operation. Lengths/diameters in inches."""

    type: OperationType
    label: str | None = None
    dia_in: float | None = Field(default=None, gt=0, description="Cutting diameter")
    length_in: float | None = Field(default=None, ge=0, description="Axial length of cut")
    depth_in: float | None = Field(default=None, ge=0, description="Drill/groove depth")
    width_in: float | None = Field(default=None, ge=0, description="Groove width")
    pitch_in: float | None = Field(default=None, gt=0, description="Thread pitch (in/rev)")
    passes: int = Field(default=1, ge=1)
    peck: bool = False


class OperationDetail(BaseModel):
    label: str
    type: OperationType
    rpm: int
    seconds: float


def _rpm(sfm: float, dia_in: float | None, max_rpm: float) -> float:
    if not dia_in or dia_in <= 0:
        return max_rpm
    return min(sfm * 12.0 / (math.pi * dia_in), max_rpm)


def cycle_time_seconds(
    operations: list[Operation],
    sfm: float,
    feed_per_rev: float,
    cfg: dict,
) -> tuple[float, list[OperationDetail]]:
    """Sum the cycle time of a sequential operation list (seconds)."""
    max_rpm = cfg["max_rpm"]
    index_sec = cfg["index_seconds"]
    drill_factor = cfg["drill_feed_factor"]
    groove_factor = cfg["groove_feed_factor"]
    cutoff_factor = cfg["cutoff_feed_factor"]
    peck_penalty = cfg["peck_penalty"]
    thread_retract = cfg["thread_retract_seconds"]

    details: list[OperationDetail] = []
    total = 0.0

    for i, op in enumerate(operations):
        rpm = _rpm(sfm, op.dia_in, max_rpm)
        feed = max(feed_per_rev * rpm, 1e-9)  # in/min
        seconds = 0.0

        if op.type is OperationType.turn:
            seconds = op.passes * (op.length_in or 0.0) / feed * 60.0
        elif op.type is OperationType.face:
            seconds = ((op.dia_in or 0.0) / 2.0) / feed * 60.0
        elif op.type is OperationType.drill:
            seconds = (op.depth_in or 0.0) / max(feed * drill_factor, 1e-9) * 60.0
            if op.peck:
                seconds *= 1.0 + peck_penalty
        elif op.type is OperationType.groove:
            seconds = (op.depth_in or 0.0) / max(feed * groove_factor, 1e-9) * 60.0
        elif op.type is OperationType.thread:
            pitch = op.pitch_in or 0.05
            seconds = op.passes * (op.length_in or 0.0) / max(pitch * rpm, 1e-9) * 60.0
            seconds += op.passes * thread_retract
        elif op.type is OperationType.cutoff:
            seconds = ((op.dia_in or 0.0) / 2.0) / max(feed * cutoff_factor, 1e-9) * 60.0

        seconds += index_sec  # tool index / approach per op
        total += seconds
        details.append(
            OperationDetail(
                label=op.label or op.type.value,
                type=op.type,
                rpm=int(round(rpm)),
                seconds=round(seconds, 1),
            )
        )

    return total, details
