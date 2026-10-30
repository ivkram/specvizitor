import pathlib

__all__ = [
    "available_plugins"
]

_NOT_A_PLUGIN = ('__init__', 'plugin_core')


def available_plugins() -> list[str]:
    return sorted(p.stem for p in pathlib.Path(__file__).parent.glob('*.py')
                  if p.stem not in _NOT_A_PLUGIN)
