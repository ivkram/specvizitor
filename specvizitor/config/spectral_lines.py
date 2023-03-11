from dataclasses import dataclass, field

from ..utils.params import Params


@dataclass
class SpectralLines(Params):
    wave_unit: str = 'angstrom'
    list: dict[str, float] = field(default_factory=dict)
