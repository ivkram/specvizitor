from dataclasses import dataclass

from ..utils.params import Params


@dataclass
class Cache(Params):
    last_inspection_file: str | None
    last_object_index: int | None
    dock_state: dict | None
