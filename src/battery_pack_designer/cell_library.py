"""Built-in cylindrical cell specifications."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class CellSpec:
    model: str
    diameter_mm: float
    height_mm: float
    weight_g: float
    capacity_m_ah: int
    nominal_v: float
    full_v: float
    cutoff_v: float
    chemistry: str

    @property
    def capacity_ah(self) -> float:
        return self.capacity_m_ah / 1000

    @property
    def cell_energy_wh(self) -> float:
        return round(self.capacity_ah * self.nominal_v, 3)

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["capacity_ah"] = self.capacity_ah
        data["cell_energy_wh"] = self.cell_energy_wh
        return data


CELL_LIBRARY: dict[str, CellSpec] = {
    "14500": CellSpec("14500", 14.0, 50.0, 20, 800, 3.7, 4.2, 2.75, "Li-ion"),
    "18350": CellSpec("18350", 18.0, 35.0, 30, 900, 3.7, 4.2, 2.75, "Li-ion"),
    "18650": CellSpec("18650", 18.6, 65.2, 48, 3000, 3.7, 4.2, 2.5, "Li-ion"),
    "20700": CellSpec("20700", 20.0, 70.0, 60, 4000, 3.7, 4.2, 2.5, "Li-ion"),
    "21700": CellSpec("21700", 21.2, 70.2, 70, 5000, 3.7, 4.2, 2.5, "Li-ion"),
    "26650": CellSpec("26650", 26.0, 65.0, 90, 5000, 3.2, 3.65, 2.0, "LFP"),
    "32700": CellSpec("32700", 32.0, 70.0, 150, 6000, 3.2, 3.65, 2.0, "LFP"),
    "32140": CellSpec("32140", 32.0, 140.0, 350, 15000, 3.2, 3.65, 2.0, "LFP"),
    "46800": CellSpec("46800", 46.0, 80.0, 350, 9000, 3.7, 4.2, 2.5, "Li-ion"),
}

DEFAULT_MODEL = "18650"

