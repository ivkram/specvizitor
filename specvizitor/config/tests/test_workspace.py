
import pytest

from specvizitor.config.migration import migrate_legacy_config, needs_migration
from specvizitor.config.config import Image
from specvizitor.config.workspace import WORKSPACE_CONFIG_FILENAME, Workspace, WorkspaceRegistry
from specvizitor.utils.params import read_yaml, save_yaml


@pytest.fixture
def workspace(tmp_path):
    return Workspace.create(tmp_path / 'fresco', name='FRESCO')


# ---------------------------------------------------------------- creating and identifying

def test_create_seeds_the_workspace_from_the_bundled_defaults(workspace):
    assert workspace.name == 'FRESCO'
    assert workspace.config.plugins  # the bundled default declares the Grizli plugins
    assert workspace.widgets.images  # and a default set of viewer widgets


def test_a_directory_without_the_marker_file_is_not_a_workspace(tmp_path):
    (tmp_path / 'empty').mkdir()
    assert not Workspace.is_workspace(tmp_path / 'empty')
    assert Workspace.open(tmp_path / 'empty') is None


def test_create_refuses_to_overwrite_an_existing_workspace(workspace):
    assert Workspace.create(workspace.path, name='Other') is None


# ---------------------------------------------------------------- paths

def test_paths_are_restored_when_the_workspace_is_reopened(workspace):
    workspace.config.data.dir = '/home/alice/fresco/data'
    workspace.config.catalogue.filename = '/home/alice/fresco/cat.fits'
    workspace.config.data.images = {'Cluster': Image(filename='/net/cluster.fits', wcs_source='/net/wcs.fits')}
    workspace.config.save()

    reopened = Workspace.open(workspace.path)

    assert reopened.config.data.dir == '/home/alice/fresco/data'
    assert reopened.config.catalogue.filename == '/home/alice/fresco/cat.fits'
    assert reopened.config.data.images['Cluster'].filename == '/net/cluster.fits'
    assert reopened.config.data.images['Cluster'].wcs_source == '/net/wcs.fits'


# ---------------------------------------------------------------- naming

def test_the_name_is_stored_in_the_shared_configuration(workspace):
    # so that it travels with the workspace when it is shared
    assert 'FRESCO' in (workspace.path / WORKSPACE_CONFIG_FILENAME).read_text()


def test_an_unnamed_workspace_falls_back_to_its_directory_name(tmp_path):
    assert Workspace.create(tmp_path / 'unnamed').name == 'unnamed'


def test_the_name_is_independent_of_the_directory_name(tmp_path):
    workspace = Workspace.create(tmp_path / 'dr2_products', name='FRESCO DR2')

    assert workspace.name == 'FRESCO DR2'
    assert workspace.path.name == 'dr2_products'


def test_name_at_reads_the_name_without_opening_the_workspace(workspace):
    assert Workspace.name_at(workspace.path) == 'FRESCO'


def test_name_at_falls_back_to_the_directory_name(tmp_path):
    assert Workspace.name_at(tmp_path / 'nonexistent') == 'nonexistent'


def test_renaming_keeps_the_directory_in_place(workspace):
    path = workspace.path

    workspace.rename('FRESCO DR2')

    assert workspace.path == path
    assert Workspace.open(path).name == 'FRESCO DR2'


def test_renaming_preserves_the_rest_of_the_configuration(workspace):
    workspace.config.data.dir = '/srv/data'
    workspace.config.save()

    workspace.rename('Renamed')
    reopened = Workspace.open(workspace.path)

    assert reopened.config.data.dir == '/srv/data'
    assert reopened.config.plugins == workspace.config.plugins


# ---------------------------------------------------------------- copying

def test_copy_creates_an_independent_workspace(workspace, tmp_path):
    workspace.config.data.dir = '/srv/data'
    workspace.config.inspection_results.default_flags = ['broad_line']
    workspace.config.save()

    copied = workspace.copy(tmp_path / 'fresco-variant', name='FRESCO variant')

    assert copied is not None
    assert copied.name == 'FRESCO variant'
    assert copied.config.inspection_results.default_flags == ['broad_line']
    assert copied.config.plugins == workspace.config.plugins
    # the original keeps its own name
    assert Workspace.open(workspace.path).name == 'FRESCO'


def test_a_copy_inherits_this_machines_paths(workspace, tmp_path):
    workspace.config.data.dir = '/srv/data'
    workspace.config.data.images = {'Cluster': Image(filename='/net/cluster.fits')}
    workspace.config.save()

    copied = workspace.copy(tmp_path / 'variant')

    # a copy stays on the machine that made it, so re-entering the paths would be pointless
    assert copied.config.data.dir == '/srv/data'
    assert copied.config.data.images['Cluster'].filename == '/net/cluster.fits'


def test_a_copy_inherits_the_widgets_and_the_spectral_lines(workspace, tmp_path):
    copied = workspace.copy(tmp_path / 'variant')

    assert copied.widgets.images.keys() == workspace.widgets.images.keys()
    assert copied.spectral_lines.wavelengths == workspace.spectral_lines.wavelengths


def test_a_copy_inherits_the_layout(workspace, tmp_path):
    workspace.layout.visible_columns = ['id', 'ra', 'dec']
    workspace.layout.save()

    copied = workspace.copy(tmp_path / 'variant')

    assert copied.layout.visible_columns == ['id', 'ra', 'dec']


def test_a_copy_inherits_the_open_inspection_file_and_position(workspace, tmp_path):
    workspace.state.last_inspection_file = '/srv/inspection.csv'
    workspace.state.last_object_index = 42
    workspace.state.save()

    copied = workspace.copy(tmp_path / 'variant')

    # a clone is for trying a different setup on the same data, so it resumes where you were --
    # both workspaces then save to that same inspection file
    assert copied.state.last_inspection_file == '/srv/inspection.csv'
    assert copied.state.last_object_index == 42


def test_editing_a_copy_leaves_the_original_alone(workspace, tmp_path):
    copied = workspace.copy(tmp_path / 'variant', name='Variant')
    copied.config.inspection_results.default_flags = ['only_here']
    copied.config.save()

    assert Workspace.open(workspace.path).config.inspection_results.default_flags == []


def test_copy_refuses_an_existing_directory(workspace, tmp_path):
    (tmp_path / 'taken').mkdir()

    assert workspace.copy(tmp_path / 'taken') is None


def test_copy_refuses_to_copy_onto_itself(workspace):
    assert workspace.copy(workspace.path) is None
    assert Workspace.open(workspace.path) is not None


def test_a_copy_without_an_explicit_name_inherits_the_original_one(workspace, tmp_path):
    # which would duplicate it, so callers are expected to supply a unique name -- the GUI
    # pre-fills one from WorkspaceRegistry.unique_name()
    copied = workspace.copy(tmp_path / 'variant')
    assert copied.name == 'FRESCO'



# ---------------------------------------------------------------- deleting

def test_delete_removes_the_directory(workspace):
    path = workspace.path

    assert workspace.delete()
    assert not path.exists()


def test_delete_refuses_a_directory_that_is_not_a_workspace(tmp_path):
    plain = tmp_path / 'not-a-workspace'
    plain.mkdir()
    (plain / 'precious.txt').write_text('keep me')

    workspace = Workspace.create(tmp_path / 'real')
    workspace.path = plain  # pretend the workspace moved somewhere unrelated

    assert workspace.delete() is False
    assert (plain / 'precious.txt').exists()


# ---------------------------------------------------------------- the registry

def test_register_moves_a_workspace_to_the_front(tmp_path):
    registry = WorkspaceRegistry()
    registry.register(tmp_path / 'a')
    registry.register(tmp_path / 'b')
    registry.register(tmp_path / 'a')

    assert [p.rsplit('/', 1)[-1] for p in registry.known] == ['a', 'b']


def test_set_active_also_registers(tmp_path):
    registry = WorkspaceRegistry()
    registry.set_active(tmp_path / 'a')

    assert registry.active in registry.known


def test_forget_falls_back_to_the_next_workspace(tmp_path):
    registry = WorkspaceRegistry()
    registry.register(tmp_path / 'b')
    registry.set_active(tmp_path / 'a')
    registry.forget(tmp_path / 'a')

    assert registry.active.endswith('b')


def test_resolve_active_skips_workspaces_that_are_gone(workspace, tmp_path):
    registry = WorkspaceRegistry()
    registry.set_active(tmp_path / 'never-existed')
    registry.register(workspace.path)

    assert registry.resolve_active() == str(workspace.path)
    # an unreachable workspace stays listed: a network share is routinely offline
    assert len(registry.known) == 2


@pytest.fixture
def two_workspaces(tmp_path):
    first = Workspace.create(tmp_path / 'one', name='FRESCO')
    second = Workspace.create(tmp_path / 'two', name='EIGER')
    registry = WorkspaceRegistry()
    registry.register(first.path)
    registry.register(second.path)
    return registry, first, second


def test_find_by_name_uses_the_stored_name_not_the_directory(two_workspaces):
    registry, first, _ = two_workspaces

    assert registry.find_by_name('FRESCO') == str(first.path)
    assert registry.find_by_name('one') is None  # the directory name is not the workspace name


def test_validate_name_refuses_a_name_taken_by_another_workspace(two_workspaces):
    registry, first, second = two_workspaces

    assert not registry.validate_name('FRESCO')
    assert registry.validate_name('FRESCO', path=first.path)
    assert not registry.validate_name('FRESCO', path=second.path)


def test_unique_name_suffixes_a_taken_name(two_workspaces):
    registry, _, _ = two_workspaces

    assert registry.unique_name('EIGER') == 'EIGER (2)'
    assert registry.unique_name('Unclaimed') == 'Unclaimed'


def test_unique_name_keeps_counting_until_it_finds_a_gap(tmp_path):
    registry = WorkspaceRegistry()
    for i, dirname in enumerate(('a', 'b', 'c')):
        name = 'FRESCO' if i == 0 else f'FRESCO ({i + 1})'
        registry.register(Workspace.create(tmp_path / dirname, name=name).path)

    assert registry.unique_name('FRESCO') == 'FRESCO (4)'


def test_resolve_active_returns_none_when_nothing_is_usable(tmp_path):
    registry = WorkspaceRegistry()
    registry.set_active(tmp_path / 'never-existed')

    assert registry.resolve_active() is None


# ---------------------------------------------------------------- migration

LEGACY_CONFIG = {
    'config_version': '0.6.0',
    'appearance': {'theme': 'light', 'antialiasing': True},
    'data_viewer': {'redshift_step': 0.02},
    'catalogue': {'filename': '/srv/fresco/cat.fits', 'translate': {'id': ['ID']}},
    'data': {'dir': '/srv/fresco/data', 'id_pattern': r'\d+'},
    'inspection_results': {'default_flags': ['broad_line']},
    'plugins': ['sviz-grizli'],
}

LEGACY_CACHE = {
    'last_inspection_file': '/srv/fresco/inspection.csv',
    'last_object_index': 42,
    'visible_columns': ['id', 'ra', 'dec'],
}


@pytest.fixture
def legacy(tmp_path):
    config_dir = tmp_path / 'config'
    cache_dir = tmp_path / 'cache'
    config_dir.mkdir()
    cache_dir.mkdir()
    save_yaml(config_dir / 'config.yml', LEGACY_CONFIG)
    save_yaml(config_dir / 'data_widgets.yml', {'images': {}, 'plots': {}})
    save_yaml(cache_dir / 'specvizitor.yml', LEGACY_CACHE)
    return config_dir, cache_dir


def _migrate(legacy):
    config_dir, cache_dir = legacy
    return migrate_legacy_config(config_dir, cache_dir, config_dir / 'workspaces', 'specvizitor.yml')


def test_migration_is_detected_only_for_a_pre_workspace_installation(legacy, tmp_path):
    config_dir, _ = legacy
    assert needs_migration(config_dir, 'workspaces.yml')

    # once the registry exists, the installation is already on workspaces
    save_yaml(config_dir / 'workspaces.yml', {'active': None, 'known': []})
    assert not needs_migration(config_dir, 'workspaces.yml')


def test_migration_is_not_detected_for_a_fresh_installation(tmp_path):
    assert not needs_migration(tmp_path, 'workspaces.yml')


def test_migration_splits_the_legacy_configuration(legacy):
    config_dir, _ = legacy
    workspace = Workspace.open(_migrate(legacy))

    # project-scoped settings moved into the workspace
    assert workspace.name == 'Default'
    assert workspace.config.inspection_results.default_flags == ['broad_line']
    assert workspace.config.plugins == ['sviz-grizli']
    assert workspace.config.catalogue.translate == {'id': ['ID']}

    assert workspace.config.data.dir == '/srv/fresco/data'
    assert workspace.config.catalogue.filename == '/srv/fresco/cat.fits'

    # user-scoped preferences stayed behind
    user_config = read_yaml(config_dir / 'config.yml')
    assert user_config['appearance']['theme'] == 'light'
    assert 'plugins' not in user_config


def test_migration_carries_the_session_state_over(legacy):
    workspace = Workspace.open(_migrate(legacy))

    assert workspace.state.last_inspection_file == '/srv/fresco/inspection.csv'
    assert workspace.state.last_object_index == 42
    assert workspace.layout.visible_columns == ['id', 'ra', 'dec']


def test_migration_keeps_the_legacy_files_recoverable(legacy):
    config_dir, _ = legacy
    _migrate(legacy)

    assert (config_dir / 'config.pre-workspace.yml').exists()
    assert (config_dir / 'data_widgets.pre-workspace.yml').exists()
    # ...and does not leave the originals where they would silently stop taking effect
    assert not (config_dir / 'data_widgets.yml').exists()


def test_migration_does_not_run_twice(legacy):
    config_dir, _ = legacy
    _migrate(legacy)
    assert not needs_migration(config_dir, 'workspaces.yml') or 'plugins' not in read_yaml(config_dir / 'config.yml')


def test_a_default_data_dir_is_not_carried_over(tmp_path):
    config_dir = tmp_path / 'config'
    cache_dir = tmp_path / 'cache'
    config_dir.mkdir()
    cache_dir.mkdir()
    save_yaml(config_dir / 'config.yml', {**LEGACY_CONFIG, 'data': {'dir': '.', 'id_pattern': r'\d+'}})

    workspace = Workspace.open(migrate_legacy_config(config_dir, cache_dir, config_dir / 'workspaces',
                                                      'specvizitor.yml'))

    # '.' was the old default and means nothing on a new machine
    assert workspace.config.data.dir is None
