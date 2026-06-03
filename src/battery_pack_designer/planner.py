"""Core planning engine shared by web and desktop experiences."""

from __future__ import annotations

import math
from dataclasses import replace
from typing import Any, Iterable

from .cell_library import CELL_LIBRARY, DEFAULT_MODEL
from .models import (
    BalanceLead,
    CellPlacement,
    DesignMetrics,
    DesignRequest,
    DesignResult,
    JumpWire,
    RouteOption,
    TabStrip,
    WeldStep,
    serialize,
)


ROUTE_SCHEME_LABELS: dict[str, tuple[str, str]] = {
    "snake_horizontal": ("Snake Horizontal", "Alternate row direction to reduce jump distance."),
    "snake_vertical": ("Snake Vertical", "Alternate column direction for taller packs."),
    "linear_horizontal": ("Linear Horizontal", "Left-to-right, top-to-bottom series assignment."),
    "linear_vertical": ("Linear Vertical", "Top-to-bottom, left-to-right series assignment."),
    "layer_zigzag": ("Layer Zigzag", "Favor stacked designs by flipping direction between layers."),
}


def parse_request(payload: dict[str, Any] | None = None) -> DesignRequest:
    payload = payload or {}
    hole_mask_text = str(payload.get("hole_mask_text", "")).strip()
    hole_mask = _parse_hole_mask(hole_mask_text)
    return DesignRequest(
        cell_model=str(payload.get("cell_model", DEFAULT_MODEL)),
        placement_mode=str(payload.get("placement_mode", "honeycomb")).lower(),
        stack_base_mode=str(payload.get("stack_base_mode", "honeycomb")).lower(),
        rows=_coerce_int(payload.get("rows", 4), minimum=1, maximum=99),
        cols=_coerce_int(payload.get("cols", 3), minimum=1, maximum=99),
        layers=_coerce_int(payload.get("layers", 1), minimum=1, maximum=99),
        series_count=_coerce_int(payload.get("series_count", 4), minimum=1, maximum=99),
        parallel_count=_coerce_int(payload.get("parallel_count", 3), minimum=1, maximum=99),
        gap_mm=_coerce_float(payload.get("gap_mm", 2.0), minimum=0.0, maximum=30.0),
        layer_gap_mm=_coerce_float(payload.get("layer_gap_mm", 3.0), minimum=0.0, maximum=30.0),
        route_scheme=str(payload.get("route_scheme", "auto")).lower(),
        orientation_mode=str(payload.get("orientation_mode", "alternating")).lower(),
        hole_mask=hole_mask,
    )


def build_design(request: DesignRequest | dict[str, Any] | None = None) -> dict[str, Any]:
    if not isinstance(request, DesignRequest):
        request = parse_request(request if isinstance(request, dict) else None)

    if request.cell_model not in CELL_LIBRARY:
        raise ValueError(f"Unknown cell model: {request.cell_model}")

    spec = CELL_LIBRARY[request.cell_model]
    placements = _generate_placements(request, spec.diameter_mm)
    active_cells = [cell for cell in placements if cell.active]
    required_cells = request.series_count * request.parallel_count

    warnings: list[str] = []
    if len(active_cells) < required_cells:
        raise ValueError(
            "Active placement capacity is smaller than S x P. "
            f"Need {required_cells} cells, but only {len(active_cells)} active slots are available."
        )
    if len(active_cells) > required_cells:
        warnings.append(
            f"{len(active_cells) - required_cells} active slots are unused because S x P = {required_cells}."
        )

    used_cells = active_cells[:required_cells]
    route_options = _build_route_options(used_cells, request, spec.diameter_mm)
    selected_route = _select_route(route_options, request.route_scheme)
    ordered_ids = _route_order(used_cells, selected_route.key)
    ordered_cells = [next(cell for cell in used_cells if cell.id == cell_id) for cell_id in ordered_ids]

    grouped: list[list[CellPlacement]] = []
    for series_index in range(request.series_count):
        start = series_index * request.parallel_count
        stop = start + request.parallel_count
        group = ordered_cells[start:stop]
        grouped.append(group)
        polarity_up = True
        if request.orientation_mode == "alternating":
            polarity_up = series_index % 2 == 0
        elif request.orientation_mode == "inverted":
            polarity_up = False
        for parallel_index, cell in enumerate(group, start=1):
            cell.used = True
            cell.series_group = series_index + 1
            cell.parallel_index = parallel_index
            cell.polarity_up = polarity_up
            cell.voltage_node_negative = f"B{series_index}"
            cell.voltage_node_positive = f"B{series_index + 1}"

    tab_strips, jump_wires = _build_tabs_and_jump_wires(grouped, request, spec.nominal_v)
    balance_leads = _build_balance_leads(tab_strips, request.series_count)
    weld_steps = _build_weld_steps(grouped, tab_strips, jump_wires, balance_leads)
    metrics = _build_metrics(request, spec, used_cells)

    result = DesignResult(
        request=serialize(request),
        cell_spec=spec.to_dict(),
        metrics=metrics,
        selected_route=selected_route,
        route_options=route_options,
        cells=placements,
        tab_strips=tab_strips,
        jump_wires=jump_wires,
        balance_leads=balance_leads,
        weld_steps=weld_steps,
        warnings=warnings,
    )
    return serialize(result)


def _generate_placements(request: DesignRequest, diameter_mm: float) -> list[CellPlacement]:
    placements: list[CellPlacement] = []
    pitch_x = diameter_mm + request.gap_mm
    pitch_y_rect = diameter_mm + request.gap_mm
    pitch_y_honeycomb = pitch_x * math.sin(math.radians(60))
    triangle_dx = pitch_x / 2
    triangle_dy = pitch_y_honeycomb
    mask = set(request.hole_mask)
    base_mode = request.stack_base_mode if request.placement_mode == "stack" else request.placement_mode

    cell_index = 1
    for layer in range(request.layers):
        z_mm = layer * (diameter_mm + request.layer_gap_mm)
        for row in range(request.rows):
            for col in range(request.cols):
                if base_mode == "triangle" and col > row:
                    continue

                x_mm = col * pitch_x
                y_mm = row * pitch_y_rect
                if base_mode == "honeycomb":
                    x_mm = (col * pitch_x) + ((row % 2) * (pitch_x / 2))
                    y_mm = row * pitch_y_honeycomb
                elif base_mode == "triangle":
                    width = (row + 1) * triangle_dx
                    x_mm = col * pitch_x + ((request.cols * pitch_x - width) / 2)
                    y_mm = row * triangle_dy

                active = (layer, row, col) not in mask
                placements.append(
                    CellPlacement(
                        id=f"C{cell_index:03d}",
                        index=cell_index,
                        layer=layer + 1,
                        row=row + 1,
                        col=col + 1,
                        x_mm=round(x_mm, 3),
                        y_mm=round(y_mm, 3),
                        z_mm=round(z_mm, 3),
                        active=active,
                        used=False,
                    )
                )
                cell_index += 1
    return placements


def _build_route_options(
    used_cells: list[CellPlacement], request: DesignRequest, diameter_mm: float
) -> list[RouteOption]:
    options: list[RouteOption] = []
    for key, (name, description) in ROUTE_SCHEME_LABELS.items():
        order = _route_order(used_cells, key)
        ordered_cells = [next(cell for cell in used_cells if cell.id == cell_id) for cell_id in order]
        group_count = request.series_count
        parallel_count = request.parallel_count
        centroids: list[tuple[float, float, float]] = []
        fold_count = 0
        total_bus = 0.0
        max_span = 0.0
        preview = order[: min(8, len(order))]

        for group_index in range(group_count):
            group = ordered_cells[group_index * parallel_count : (group_index + 1) * parallel_count]
            centroid = _centroid(group)
            centroids.append(centroid)
            span = _group_span(group)
            max_span = max(max_span, span)
            total_bus += span
            if group_index > 0:
                prev = centroids[group_index - 1]
                delta = _distance(prev, centroid)
                total_bus += delta
                if group[0].layer != ordered_cells[(group_index - 1) * parallel_count].layer:
                    fold_count += 1
                if delta > diameter_mm * 2.2:
                    fold_count += 1

        jump_wire_count = 0
        for previous, current in zip(centroids, centroids[1:]):
            if _distance(previous, current) > diameter_mm * 2.8 or previous[2] != current[2]:
                jump_wire_count += 1

        difficulty = min(5, max(1, 1 + jump_wire_count + (1 if fold_count >= 2 else 0) + (1 if max_span > diameter_mm * 2.4 else 0)))
        options.append(
            RouteOption(
                key=key,
                name=name,
                description=description,
                difficulty=difficulty,
                jump_wire_count=jump_wire_count,
                fold_count=fold_count,
                max_span_mm=round(max_span, 2),
                total_bus_length_mm=round(total_bus, 2),
                order_preview=preview,
            )
        )

    return sorted(options, key=lambda option: (option.difficulty, option.jump_wire_count, option.total_bus_length_mm))


def _select_route(route_options: list[RouteOption], requested_key: str) -> RouteOption:
    if requested_key and requested_key != "auto":
        for option in route_options:
            if option.key == requested_key:
                return option
    return route_options[0]


def _route_order(cells: list[CellPlacement], scheme: str) -> list[str]:
    layers = sorted({cell.layer for cell in cells})
    rows = sorted({cell.row for cell in cells})
    cols = sorted({cell.col for cell in cells})
    indexed = {(cell.layer, cell.row, cell.col): cell for cell in cells}
    order: list[str] = []

    if scheme == "snake_vertical":
        for layer in layers:
            for col in cols:
                row_iter = rows if col % 2 == 1 else list(reversed(rows))
                for row in row_iter:
                    cell = indexed.get((layer, row, col))
                    if cell:
                        order.append(cell.id)
    elif scheme == "linear_horizontal":
        for layer in layers:
            for row in rows:
                for col in cols:
                    cell = indexed.get((layer, row, col))
                    if cell:
                        order.append(cell.id)
    elif scheme == "linear_vertical":
        for layer in layers:
            for col in cols:
                for row in rows:
                    cell = indexed.get((layer, row, col))
                    if cell:
                        order.append(cell.id)
    elif scheme == "layer_zigzag":
        for layer in layers:
            row_iter = rows if layer % 2 == 1 else list(reversed(rows))
            for row in row_iter:
                col_iter = cols if row % 2 == 1 else list(reversed(cols))
                for col in col_iter:
                    cell = indexed.get((layer, row, col))
                    if cell:
                        order.append(cell.id)
    else:
        for layer in layers:
            for row in rows:
                col_iter = cols if row % 2 == 1 else list(reversed(cols))
                for col in col_iter:
                    cell = indexed.get((layer, row, col))
                    if cell:
                        order.append(cell.id)
    return order


def _build_tabs_and_jump_wires(
    grouped: list[list[CellPlacement]], request: DesignRequest, nominal_v: float
) -> tuple[list[TabStrip], list[JumpWire]]:
    tab_strips: list[TabStrip] = []
    jump_wires: list[JumpWire] = []

    def build_strip(node_label: str, side: str, voltage_v: float, cells: list[CellPlacement], suffix: str) -> TabStrip:
        points = [(cell.x_mm, cell.y_mm, cell.z_mm) for cell in cells]
        return TabStrip(
            id=f"T-{node_label}-{suffix}",
            node_label=node_label,
            side=side,
            voltage_v=round(voltage_v, 3),
            cell_ids=[cell.id for cell in cells],
            points=points,
            span_mm=round(_group_span(cells), 2),
            folded=len({cell.layer for cell in cells}) > 1,
        )

    for group_index, group in enumerate(grouped):
        node_neg = f"B{group_index}"
        node_pos = f"B{group_index + 1}"
        voltage_neg = group_index * nominal_v
        voltage_pos = (group_index + 1) * nominal_v
        polarity_up = bool(group[0].polarity_up)
        negative_side = "bottom" if polarity_up else "top"
        positive_side = "top" if polarity_up else "bottom"

        neg_strip = build_strip(node_neg, negative_side, voltage_neg, group, f"{group_index + 1}N")
        pos_strip = build_strip(node_pos, positive_side, voltage_pos, group, f"{group_index + 1}P")
        tab_strips.append(neg_strip)
        tab_strips.append(pos_strip)

        if group_index < len(grouped) - 1:
            next_group = grouped[group_index + 1]
            next_negative_side = "bottom" if bool(next_group[0].polarity_up) else "top"
            if positive_side != next_negative_side or _distance(_centroid(group), _centroid(next_group)) > (group[0].x_mm * 0 + 40):
                source = _centroid(group)
                target = _centroid(next_group)
                jump_wires.append(
                    JumpWire(
                        id=f"JW-{group_index + 1}-{group_index + 2}",
                        from_node=node_pos,
                        to_node=f"B{group_index + 1}",
                        from_x_mm=round(source[0], 3),
                        from_y_mm=round(source[1], 3),
                        from_z_mm=round(source[2], 3),
                        to_x_mm=round(target[0], 3),
                        to_y_mm=round(target[1], 3),
                        to_z_mm=round(target[2], 3),
                        length_mm=round(_distance(source, target), 2),
                    )
                )

    merged: dict[tuple[str, str], list[TabStrip]] = {}
    for strip in tab_strips:
        merged.setdefault((strip.node_label, strip.side), []).append(strip)

    merged_strips: list[TabStrip] = []
    for (node_label, side), strips in merged.items():
        all_cells: list[str] = []
        all_points: list[tuple[float, float, float]] = []
        voltage = strips[0].voltage_v
        folded = any(strip.folded for strip in strips) or len(strips) > 1
        for strip in strips:
            all_cells.extend(strip.cell_ids)
            all_points.extend(strip.points)
        span = round(max((_point_distance(point, center) for point in all_points for center in all_points), default=0.0), 2)
        merged_strips.append(
            TabStrip(
                id=f"T-{node_label}-{side}",
                node_label=node_label,
                side=side,
                voltage_v=voltage,
                cell_ids=all_cells,
                points=all_points,
                span_mm=span,
                folded=folded,
            )
        )
    merged_strips.sort(key=lambda strip: (int(strip.node_label[1:]), strip.side))
    return merged_strips, jump_wires


def _build_balance_leads(tab_strips: list[TabStrip], series_count: int) -> list[BalanceLead]:
    leads: list[BalanceLead] = []
    for node_index in range(series_count + 1):
        node = f"B{node_index}"
        strip = next((item for item in tab_strips if item.node_label == node), None)
        if not strip:
            continue
        x_mm, y_mm, z_mm = _centroid_points(strip.points)
        leads.append(
            BalanceLead(
                label=node,
                node_label=node,
                x_mm=round(x_mm, 3),
                y_mm=round(y_mm, 3),
                z_mm=round(z_mm, 3),
            )
        )
    return leads


def _build_weld_steps(
    grouped: list[list[CellPlacement]],
    tab_strips: list[TabStrip],
    jump_wires: list[JumpWire],
    balance_leads: list[BalanceLead],
) -> list[WeldStep]:
    steps = [
        WeldStep(
            index=1,
            title="Place cells",
            description="Place all assigned cylindrical cells and confirm polarity orientation before welding.",
            highlight_cell_ids=[cell.id for group in grouped for cell in group],
        )
    ]
    step_index = 2
    for strip in tab_strips:
        steps.append(
            WeldStep(
                index=step_index,
                title=f"Weld {strip.node_label} tab strip",
                description=f"Weld the {strip.side} tab strip for {strip.node_label} ({strip.voltage_v} V node).",
                highlight_tab_ids=[strip.id],
                highlight_cell_ids=strip.cell_ids,
            )
        )
        step_index += 1
    for wire in jump_wires:
        steps.append(
            WeldStep(
                index=step_index,
                title=f"Weld jump wire {wire.id}",
                description=f"Add jump wire from {wire.from_node} to {wire.to_node}, estimated length {wire.length_mm} mm.",
                highlight_wire_ids=[wire.id],
            )
        )
        step_index += 1
    for lead in balance_leads:
        steps.append(
            WeldStep(
                index=step_index,
                title=f"Attach balance lead {lead.label}",
                description=f"Attach and insulate balance lead {lead.label}.",
                highlight_balance_labels=[lead.label],
            )
        )
        step_index += 1
    return steps


def _build_metrics(request: DesignRequest, spec: Any, used_cells: list[CellPlacement]) -> DesignMetrics:
    total_capacity_ah = round(spec.capacity_ah * request.parallel_count, 3)
    total_voltage_v = round(spec.nominal_v * request.series_count, 3)
    total_energy_wh = round(total_capacity_ah * total_voltage_v, 3)
    total_weight_kg = round((spec.weight_g * len(used_cells)) / 1000, 3)

    min_x = min(cell.x_mm for cell in used_cells)
    max_x = max(cell.x_mm for cell in used_cells)
    min_y = min(cell.y_mm for cell in used_cells)
    max_y = max(cell.y_mm for cell in used_cells)
    min_z = min(cell.z_mm for cell in used_cells)
    max_z = max(cell.z_mm for cell in used_cells)
    pack_width_mm = round((max_x - min_x) + spec.diameter_mm, 2)
    pack_depth_mm = round((max_y - min_y) + spec.diameter_mm, 2)
    pack_height_mm = round((max_z - min_z) + spec.height_mm, 2)

    return DesignMetrics(
        total_cells=len(used_cells),
        used_cells=len(used_cells),
        total_capacity_ah=total_capacity_ah,
        total_voltage_v=total_voltage_v,
        total_energy_wh=total_energy_wh,
        total_weight_kg=total_weight_kg,
        pack_width_mm=pack_width_mm,
        pack_depth_mm=pack_depth_mm,
        pack_height_mm=pack_height_mm,
    )


def _parse_hole_mask(text: str) -> list[tuple[int, int, int]]:
    if not text:
        return []
    result: list[tuple[int, int, int]] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [part.strip() for part in line.replace(";", ",").replace(":", ",").split(",")]
        if len(parts) != 3:
            continue
        try:
            layer, row, col = [int(part) for part in parts]
        except ValueError:
            continue
        result.append((layer - 1, row - 1, col - 1))
    return result


def _coerce_int(value: Any, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid integer value: {value}") from exc
    return max(minimum, min(maximum, number))


def _coerce_float(value: Any, minimum: float, maximum: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid numeric value: {value}") from exc
    return max(minimum, min(maximum, number))


def _centroid(cells: Iterable[CellPlacement]) -> tuple[float, float, float]:
    points = [(cell.x_mm, cell.y_mm, cell.z_mm) for cell in cells]
    return _centroid_points(points)


def _centroid_points(points: Iterable[tuple[float, float, float]]) -> tuple[float, float, float]:
    points = list(points)
    if not points:
        return (0.0, 0.0, 0.0)
    count = len(points)
    x_mm = sum(point[0] for point in points) / count
    y_mm = sum(point[1] for point in points) / count
    z_mm = sum(point[2] for point in points) / count
    return (x_mm, y_mm, z_mm)


def _group_span(cells: Iterable[CellPlacement]) -> float:
    points = [(cell.x_mm, cell.y_mm, cell.z_mm) for cell in cells]
    return max((_point_distance(first, second) for first in points for second in points), default=0.0)


def _point_distance(first: tuple[float, float, float], second: tuple[float, float, float]) -> float:
    return math.sqrt(
        ((first[0] - second[0]) ** 2) + ((first[1] - second[1]) ** 2) + ((first[2] - second[2]) ** 2)
    )


def _distance(first: tuple[float, float, float], second: tuple[float, float, float]) -> float:
    return _point_distance(first, second)

