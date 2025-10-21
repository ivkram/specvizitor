from enum import Enum, auto
from dataclasses import dataclass


__all__ = [
    "Direction",
    "NavigationAction"
]


class Direction(Enum):
    NEXT = auto()
    PREVIOUS = auto()


@dataclass
class NavigationAction:
    direction: Direction
    starred_only: bool = False
    shortcut: str | int | None = None

    @property
    def name(self) -> str:
        name = f"{self.direction.name.lower().capitalize()}"
        if self.starred_only:
            name = f"{name} Starred"
        return name
