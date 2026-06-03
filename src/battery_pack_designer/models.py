"""Shared data models for planning and serialization."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any


@dataclass(slots=True)
class DesignRequest:
    cell_model: str = "18650"
    placement_mode: str = "honeycomb"
    stack_base_mode: str = "honeycomb"
    rows: int = 4
    cols: int = 3
    layers: int = 1
    series_count: int = 4
    parallel_count: int = 3
    gap_mm: float = 2.0
    layer_gap_mm: float = 3.0
    route_scheme: str = "auto"
    orientation_mode: str = "alternating"
    hole_mask: list[tuple[int, int, int]] = field(default_factory=list)


@dataclass(slots=True)
class CellPlacement:
    id: str
    index: int
    layer: int
    row: int
    col: int
    x_mm: float
    y_mm: float
    z_mm: float
    active: bool
    used: bool
    series_group: int | None = None
    parallel_index: int | None = None
    polarity_up: bool | None = None
    voltage_node_negative: str | None = None
    voltage_node_positive: str | None = None


@dataclass(slots=True)
class JumpWire:
    id: str
    from_node: str
    to_node: str
    from_x_mm: float
    from_y_mm: float
    from_z_mm: float
    to_x_mm: float
    to_y_mm: float
    to_z_mm: float
    length_mm: float


@dataclass(slots=True)
class TabStrip:
    id: str
    node_label: str
    side: str
    voltage_v: float
    cell_ids: list[str]
    points: list[tuple[float, float, float]]
    span_mm: float
    folded: bool


@dataclass(slots=True)
class BalanceLead:
    label: str
    node_label: str
    x_mm: float
    y_mm: float
    z_mm: float


@dataclass(slots=True)
class RouteOption:
    key: str
    name: str
    description: str
    difficulty: int
    jump_wire_count: int
    fold_count: int
    max_span_mm: float
    total_bus_length_mm: float
    order_preview: list[str]


@dataclass(slots=True)
class WeldStep:
    index: int
    title: str
    description: str
    highlight_tab_ids: list[str] = field(default_factory=list)
    highlight_cell_ids: list[str] = field(default_factory=list)
    highlight_wire_ids: list[str] = field(default_factory=list)
    highlight_balance_labels: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DesignMetrics:
    total_cells: int
    used_cells: int
    total_capacity_ah: float
    total_voltage_v: float
    total_energy_wh: float
    total_weight_kg: float
    pack_width_mm: float
    pack_depth_mm: float
    pack_height_mm: float


@dataclass(slots=True)
class DesignResult:
    request: dict[str, Any]
    cell_spec: dict[str, Any]
    metrics: DesignMetrics
    selected_route: RouteOption
    route_options: list[RouteOption]
    cells: list[CellPlacement]
    tab_strips: list[TabStrip]
    jump_wires: list[JumpWire]
    balance_leads: list[BalanceLead]
    weld_steps: list[WeldStep]
    warnings: list[str]


def serialize(value: Any) -> Any:
    if is_dataclass(value):
        return {key: serialize(val) for key, val in asdict(value).items()}
    if isinstance(value, dict):
        return {key: serialize(val) for key, val in value.items()}
    if isinstance(value, list):
        return [serialize(item) for item in value]
    if isinstance(value, tuple):
        return [serialize(item) for item in value]
    return value

