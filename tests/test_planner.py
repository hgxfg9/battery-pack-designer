from battery_pack_designer.planner import build_design, parse_request


def test_default_design_metrics():
    design = build_design(
        {
            "cell_model": "18650",
            "placement_mode": "honeycomb",
            "rows": 4,
            "cols": 3,
            "layers": 1,
            "series_count": 4,
            "parallel_count": 3,
        }
    )
    assert design["metrics"]["total_cells"] == 12
    assert design["metrics"]["total_capacity_ah"] == 9.0
    assert design["metrics"]["total_voltage_v"] == 14.8
    assert len(design["route_options"]) == 5
    assert len(design["balance_leads"]) == 5


def test_triangle_layout_is_supported():
    design = build_design(
        {
            "cell_model": "21700",
            "placement_mode": "triangle",
            "rows": 4,
            "cols": 4,
            "layers": 1,
            "series_count": 2,
            "parallel_count": 5,
        }
    )
    assert design["metrics"]["total_cells"] == 10
    assert any(cell["used"] for cell in design["cells"])


def test_hole_mask_reduces_capacity():
    request = parse_request(
        {
            "rows": 2,
            "cols": 3,
            "layers": 1,
            "series_count": 2,
            "parallel_count": 2,
            "hole_mask_text": "1,1,1\n1,2,3",
        }
    )
    design = build_design(request)
    inactive = [cell for cell in design["cells"] if not cell["active"]]
    assert len(inactive) == 2

