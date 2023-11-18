from dataclasses import dataclass, field

from ..utils.params import Params


@dataclass
class SpectralLineData(Params):
    wave_unit: str = "angstrom"
    repr: str = "vacuum"
    wavelengths: dict[str, float] = field(default_factory=dict)
