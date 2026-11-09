import pathlib
import re
from dataclasses import fields, is_dataclass
from typing import get_args, get_type_hints

import pytest

from specvizitor.config import Config, DataWidgets, SpectralLineData
from specvizitor.config.workspace import WorkspaceConfig, WorkspaceLayout, WorkspaceRegistry, WorkspaceState

REFERENCE = pathlib.Path(__file__).parents[3] / 'docs' / 'userguide' / 'app-settings.rst'


def _field_names(tp, seen=None) -> set[str]:
    """ The names of the fields of a config dataclass and of every dataclass nested in it.
    """
    seen = set() if seen is None else seen
    if is_dataclass(tp):
        if tp in seen:
            return set()
        seen.add(tp)
        hints = get_type_hints(tp)
        names = set()
        for f in fields(tp):
            names.add(f.name)
            names |= _field_names(hints[f.name], seen)
        return names
    return set().union(*(_field_names(arg, seen) for arg in get_args(tp)))


@pytest.mark.skipif(not REFERENCE.exists(), reason="the docs are not part of an installed package")
@pytest.mark.parametrize('params', [Config, SpectralLineData, WorkspaceRegistry, WorkspaceConfig, DataWidgets,
                                    WorkspaceLayout, WorkspaceState])
def test_every_config_key_is_documented(params):
    # every part of a dotted key written as a literal, e.g. ``data.images.<label>.filename``
    documented = {part for literal in re.findall(r'``([^`]+)``', REFERENCE.read_text())
                  for part in literal.split('.')}

    assert _field_names(params) - documented == set()
