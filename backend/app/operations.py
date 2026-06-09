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
    # Turning / Swiss
    turn = "turn"
    face = "face"
    drill = "drill"
    groove = "groove"
    thread = "thread"
    cutoff = "cutoff"
    # Milling (computed from path length × feed rate)
    mill_profile = "mill_profile"   # contour along a perimeter
    mill_pocket = "mill_pocket"     # area/volume clearing
    mill_face = "mill_face"         # facing a top surface
    # Generic (cycle time must come from CAM, no formula)
    mill = "mill"
    other = "other"


class Operation(BaseModel):
    """A single machining operation. Lengths/diameters in inches.

    If ``cycle_time_sec`` is set (e.g. read straight from Fusion CAM), it is used
    verbatim and the speeds/feeds math is skipped for this op. Otherwise cycle
    time is computed from the live surface speed + feed/rev for the material.
    """

    type: OperationType
    label: str | None = None
    dia_in: float | None = Field(default=None, gt=0, description="Cutting diameter")
    length_in: float | None = Field(default=None, ge=0, description="Axial length of cut")
    depth_in: float | None = Field(default=None, ge=0, description="Drill/groove depth")
    width_in: float | None = Field(default=None, ge=0, description="Groove width")
    pitch_in: float | None = Field(default=None, gt=0, description="Thread pitch (in/rev)")
    passes: int = Field(default=1, ge=1, description="Passes (turning) or hole count (drill)")
    peck: bool = False
    # Milling parameters
    area_in2: float | None = Field(default=None, ge=0, description="Pocket/face area to clear")
    stepdown_in: float | None = Field(default=None, gt=0, description="Axial depth per pass")
    stepover: float = Field(default=0.5, gt=0, le=1, description="Radial stepover (fraction of tool dia)")
    cycle_time_sec: float | None = Field(
        default=None, ge=0, description="Precomputed cycle time (e.g. from Fusion CAM)"
    )


class OperationDetail(BaseModel):
    label: str
    type: OperationType
    rpm: int
    seconds: float


def _rpm(sfm: float, dia_in: float | None, max_rpm: float) -> float:
    if not dia_in or dia_in <= 0:
        return max_rpm
    return min(sfm * 12.0 / (math.pi * dia_in), max_rpm)


def _levels(depth_in: float | None, stepdown_in: float | None) -> int:
    """Number of axial passes to reach ``depth_in`` at ``stepdown_in`` per pass."""
    if not depth_in or depth_in <= 0 or not stepdown_in or stepdown_in <= 0:
        return 1
    return max(1, math.ceil(depth_in / stepdown_in))


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
        rpm = _rpm(sfm, op.dia_in, max_rpm) if sfm > 0 else 0.0

        # Precomputed (e.g. Fusion CAM machiningTime): use it verbatim, no formula.
        if op.cycle_time_sec is not None:
            details.append(
                OperationDetail(
                    label=op.label or op.type.value,
                    type=op.type,
                    rpm=int(round(rpm)),
                    seconds=round(op.cycle_time_sec, 1),
                )
            )
            total += op.cycle_time_sec
            continue

        feed = max(feed_per_rev * rpm, 1e-9)  # in/min
        seconds = 0.0

        if op.type is OperationType.turn:
            seconds = op.passes * (op.length_in or 0.0) / feed * 60.0
        elif op.type is OperationType.face:
            seconds = ((op.dia_in or 0.0) / 2.0) / feed * 60.0
        elif op.type is OperationType.drill:
            per_hole = (op.depth_in or 0.0) / max(feed * drill_factor, 1e-9) * 60.0
            if op.peck:
                per_hole *= 1.0 + peck_penalty
            seconds = op.passes * per_hole  # passes == hole count
        elif op.type is OperationType.groove:
            seconds = (op.depth_in or 0.0) / max(feed * groove_factor, 1e-9) * 60.0
        elif op.type is OperationType.thread:
            pitch = op.pitch_in or 0.05
            seconds = op.passes * (op.length_in or 0.0) / max(pitch * rpm, 1e-9) * 60.0
            seconds += op.passes * thread_retract
        elif op.type is OperationType.cutoff:
            seconds = ((op.dia_in or 0.0) / 2.0) / max(feed * cutoff_factor, 1e-9) * 60.0
        elif op.type is OperationType.mill_profile:
            # Contour: perimeter length × (axial passes) ÷ feed rate.
            levels = _levels(op.depth_in, op.stepdown_in)
            cutting_len = (op.length_in or 0.0) * levels * op.passes
            seconds = cutting_len / feed * 60.0
        elif op.type in (OperationType.mill_pocket, OperationType.mill_face):
            # Area clearing: pass spacing = stepover × tool dia; cover the area
            # at each axial level. path_len ≈ area / spacing.
            spacing = max(op.stepover, 0.05) * (op.dia_in or 0.25)
            path_per_level = (op.area_in2 or 0.0) / max(spacing, 1e-9)
            levels = _levels(op.depth_in, op.stepdown_in)
            seconds = path_per_level * levels / feed * 60.0

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
