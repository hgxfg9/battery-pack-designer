"""Flask web entrypoint."""

from __future__ import annotations

import argparse
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from ..cell_library import CELL_LIBRARY, DEFAULT_MODEL
from ..planner import build_design, parse_request


def create_app() -> Flask:
    package_root = Path(__file__).resolve().parents[1]
    app = Flask(
        __name__,
        template_folder=str(package_root / "templates"),
        static_folder=str(package_root / "static"),
        static_url_path="/static",
    )

    @app.get("/")
    def index() -> str:
        defaults = {
            "cell_model": DEFAULT_MODEL,
            "placement_mode": "honeycomb",
            "stack_base_mode": "honeycomb",
            "rows": 4,
            "cols": 3,
            "layers": 1,
            "series_count": 4,
            "parallel_count": 3,
            "gap_mm": 2.0,
            "layer_gap_mm": 3.0,
            "route_scheme": "auto",
            "orientation_mode": "alternating",
            "hole_mask_text": "",
        }
        initial_result = build_design(defaults)
        return render_template(
            "index.html",
            cell_library={key: spec.to_dict() for key, spec in CELL_LIBRARY.items()},
            defaults=defaults,
            initial_result=initial_result,
        )

    @app.post("/api/design")
    def api_design():
        payload = request.get_json(silent=True) or request.form.to_dict()
        design = build_design(parse_request(payload))
        return jsonify(design)

    @app.get("/api/health")
    def health():
        return jsonify({"ok": True})

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="Battery Pack Designer web server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=5000, type=int)
    args = parser.parse_args()
    app = create_app()
    app.run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()

