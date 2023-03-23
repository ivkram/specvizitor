from dataclasses import dataclass, field

from ..utils.params import Params


@dataclass
class Cache(Params):
    last_inspection_file: str | None = None
    last_object_index: int | None = None
    visible_columns: list[str] | None = None
    dock_layout: dict | None = None
