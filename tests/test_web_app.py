from battery_pack_designer.web.app import create_app


def test_design_api_returns_json_validation_error():
    app = create_app()
    client = app.test_client()

    response = client.post(
        "/api/design",
        json={
            "rows": 1,
            "cols": 1,
            "layers": 1,
            "series_count": 2,
            "parallel_count": 2,
        },
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "ok": False,
        "error": "Active placement capacity is smaller than S x P. Need 4 cells, but only 1 active slots are available.",
    }
