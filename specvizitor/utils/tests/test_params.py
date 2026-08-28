from dataclasses import dataclass, field
from typing import ClassVar

import specvizitor.utils.params as params_mod
from specvizitor.utils.params import LocalFile, Params, save_yaml


@dataclass
class DummyParams(Params):
    name: str = "default"
    tags: list[str] = field(default_factory=list)


def _make_file(tmp_path, data=None):
    f = LocalFile(str(tmp_path), filename="dummy.yml", full_name="Dummy params")
    if data is not None:
        save_yaml(f.path, data)
    return f


def test_config_version_defaults_to_package_version():
    assert DummyParams().config_version == params_mod.CURRENT_VERSION


def test_read_user_params_stamps_current_version_when_file_missing(tmp_path):
    params = DummyParams.read_user_params(_make_file(tmp_path))
    assert params.config_version == params_mod.CURRENT_VERSION


def test_additive_field_uses_default_without_a_migration(tmp_path):
    # a user file saved before `tags` was introduced -- no MIGRATIONS entry needed,
    # dacite fills it in from the field's default
    f = _make_file(tmp_path, {"name": "custom"})
    params = DummyParams.read_user_params(f)
    assert params.name == "custom"
    assert params.tags == []


def test_missing_config_version_is_treated_as_oldest(tmp_path):
    class MigratingParams(DummyParams):
        MIGRATIONS: ClassVar[dict] = {
            "0.1.0": lambda d: {**d, "name": d.get("name", "default") + "-migrated"},
        }

    f = _make_file(tmp_path, {"name": "legacy"})  # no config_version key at all
    params = MigratingParams.read_user_params(f)
    assert params.name == "legacy-migrated"


def test_migration_renames_a_field_and_preserves_the_rest(monkeypatch, tmp_path):
    monkeypatch.setattr(params_mod, "CURRENT_VERSION", "0.2.0")

    class MigratingParams(DummyParams):
        MIGRATIONS: ClassVar[dict] = {
            "0.1.0": lambda d: {**d, "tags": d.pop("labels", [])},
        }

    f = _make_file(tmp_path, {"config_version": "0.1.0", "name": "kept", "labels": ["a", "b"]})
    params = MigratingParams.read_user_params(f)

    assert params.tags == ["a", "b"]
    assert params.name == "kept"
    assert params.config_version == "0.2.0"


def test_chained_migrations_apply_in_ascending_order(monkeypatch, tmp_path):
    monkeypatch.setattr(params_mod, "CURRENT_VERSION", "0.3.0")

    class MigratingParams(DummyParams):
        # registered out of order on purpose -- _migrate() must sort by version, not insertion order
        MIGRATIONS: ClassVar[dict] = {
            "0.2.0": lambda d: {**d, "name": d["name"] + "-b"},
            "0.1.0": lambda d: {**d, "name": d["name"] + "-a"},
        }

    f = _make_file(tmp_path, {"name": "start"})  # no config_version -> oldest, both migrations apply
    params = MigratingParams.read_user_params(f)

    assert params.name == "start-a-b"
    assert params.config_version == "0.3.0"


def test_migration_does_not_rerun_on_a_file_it_already_migrated(monkeypatch, tmp_path):
    monkeypatch.setattr(params_mod, "CURRENT_VERSION", "0.2.0")

    class MigratingParams(DummyParams):
        MIGRATIONS: ClassVar[dict] = {
            "0.1.0": lambda d: {**d, "tags": d.pop("labels", []) + ["extra"]},
        }

    f = _make_file(tmp_path, {"config_version": "0.1.0", "labels": ["a"]})
    MigratingParams.read_user_params(f)  # first read: migrates and re-saves as 0.2.0
    params = MigratingParams.read_user_params(f)  # second read: already at 0.2.0

    assert params.tags == ["a", "extra"]
    assert params.config_version == "0.2.0"


def test_dacite_failure_after_migration_falls_back_to_defaults(tmp_path):
    f = _make_file(tmp_path, {"tags": "not-a-list"})  # wrong type, no migration registered for it
    params = DummyParams.read_user_params(f)

    assert params.tags == []
    assert params.config_version == params_mod.CURRENT_VERSION
    assert (tmp_path / "dummy.yml.bak").exists()  # the broken file was backed up, not silently dropped
