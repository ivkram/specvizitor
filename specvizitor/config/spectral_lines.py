from dataclasses import dataclass

from ..utils.params import Params


@dataclass
class SpectralLines(Params):
    units: str
    list: dict[str, float]
