from dataclasses import dataclass, field
from typing import ClassVar
import logging

from specvizitor.utils.params import LocalFile, Params, read_yaml, save_yaml


@dataclass
class Inner:
    x: int = 1


@dataclass
class DummyParams(Params):
    name: str = "default"
    tags: list[str] = field(default_factory=list)
    inner: Inner = field(default_factory=Inner)
    inners: dict[str, Inner] = field(default_factory=dict)


def _make_file(tmp_path, data=None, auto_backup=True):
    f = LocalFile(str(tmp_path), filename="dummy.yml", full_name="Dummy params", auto_backup=auto_backup)
    if data is not None:
        save_yaml(f.path, data)
    return f


def test_schema_version_is_1_without_migrations():
    assert DummyParams.schema_version() == 1
    assert DummyParams().to_dict()['schema_version'] == 1


def test_a_missing_file_is_created_with_the_defaults(tmp_path):
    f = _make_file(tmp_path)
    DummyParams.read_user_params(f)

    assert read_yaml(f.path) == {'schema_version': 1, 'name': 'default', 'tags': [], 'inner': {'x': 1},
                                 'inners': {}}


def test_a_valid_file_is_not_rewritten_on_read(tmp_path):
    f = _make_file(tmp_path)
    f.path.write_text("# my notes\nschema_version: 1\nname: custom  # why\n")

    params = DummyParams.read_user_params(f)

    assert params.name == "custom"
    assert f.path.read_text() == "# my notes\nschema_version: 1\nname: custom  # why\n"


def test_saving_unchanged_params_does_not_rewrite_the_file(tmp_path):
    f = _make_file(tmp_path)
    f.path.write_text("schema_version: 1\nname: custom  # why\n")

    params = DummyParams.read_user_params(f)
    params.save()
    assert f.path.read_text() == "schema_version: 1\nname: custom  # why\n"

    params.name = "changed"
    params.save()
    assert read_yaml(f.path)['name'] == "changed"


def test_additive_field_uses_default_without_a_migration(tmp_path):
    # a user file saved before `tags` was introduced: no MIGRATIONS entry needed, dacite fills it in from the
    # field's default
    params = DummyParams.read_user_params(_make_file(tmp_path, {"schema_version": 1, "name": "custom"}))
    assert params.name == "custom"
    assert params.tags == []


def test_unknown_keys_are_reported_with_their_path_and_ignored(tmp_path, caplog):
    f = _make_file(tmp_path, {"schema_version": 1, "nmae": "typo", "inner": {"y": 2},
                              "inners": {"a": {"x": 3, "z": 4}}})

    with caplog.at_level(logging.WARNING):
        params = DummyParams.read_user_params(f)

    assert params.name == "default"
    assert params.inners["a"].x == 3
    assert "nmae, inner.y, inners.a.z" in caplog.text
    # left in the file until something else changes it
    assert read_yaml(f.path)["nmae"] == "typo"


def test_an_invalid_file_is_backed_up_and_reset_with_the_reason(tmp_path, caplog):
    f = _make_file(tmp_path, {"schema_version": 1, "inner": {"x": "not-an-int"}})

    with caplog.at_level(logging.ERROR):
        params = DummyParams.read_user_params(f)

    assert params.inner.x == 1
    assert read_yaml(f.path)["inner"] == {"x": 1}
    assert read_yaml(tmp_path / "dummy.yml.bak")["inner"] == {"x": "not-an-int"}
    assert '"inner.x"' in caplog.text and "dummy.yml.bak" in caplog.text


def test_unparsable_yaml_is_backed_up_and_reset(tmp_path):
    f = _make_file(tmp_path)
    f.path.write_text("name: [unclosed\n")

    params = DummyParams.read_user_params(f)

    assert params.name == "default"
    assert (tmp_path / "dummy.yml.bak").read_text() == "name: [unclosed\n"


def test_an_invalid_cache_file_is_reset_without_a_backup(tmp_path, caplog):
    f = _make_file(tmp_path, {"schema_version": 1, "tags": "not-a-list"}, auto_backup=False)

    with caplog.at_level(logging.WARNING):
        params = DummyParams.read_user_params(f)

    assert params.tags == []
    assert read_yaml(f.path)["tags"] == []
    assert not (tmp_path / "dummy.yml.bak").exists()
    assert caplog.text == ""


def test_a_file_without_a_schema_version_is_migrated_and_backed_up(tmp_path):
    class MigratingParams(DummyParams):
        MIGRATIONS: ClassVar[dict] = {1: lambda d: {**d, "tags": d.pop("labels", [])}}

    # saved before schema versions, with the package version instead
    f = _make_file(tmp_path, {"config_version": "0.7.0", "name": "kept", "labels": ["a", "b"]})
    params = MigratingParams.read_user_params(f)

    assert params.tags == ["a", "b"]
    assert params.name == "kept"
    saved = read_yaml(f.path)
    assert saved["schema_version"] == 1 and "config_version" not in saved and "labels" not in saved
    assert read_yaml(tmp_path / "dummy.yml.bak")["labels"] == ["a", "b"]


def test_migrations_apply_in_ascending_order_from_the_stored_version(tmp_path):
    class MigratingParams(DummyParams):
        # registered out of order on purpose: they must run by version, not insertion order
        MIGRATIONS: ClassVar[dict] = {
            3: lambda d: {**d, "name": d["name"] + "-c"},
            2: lambda d: {**d, "name": d["name"] + "-b"},
            1: lambda d: {**d, "name": d["name"] + "-a"},
        }

    assert MigratingParams.schema_version() == 3

    params = MigratingParams.read_user_params(_make_file(tmp_path, {"schema_version": 1, "name": "start"}))
    assert params.name == "start-b-c"

    # already migrated: nothing runs again
    params = MigratingParams.read_user_params(_make_file(tmp_path))
    assert params.name == "start-b-c"


def test_a_file_from_a_newer_version_is_read_but_never_overwritten(tmp_path, caplog):
    f = _make_file(tmp_path, {"schema_version": 2, "name": "future", "new_section": {"a": 1}})
    before = f.path.read_text()

    with caplog.at_level(logging.WARNING):
        params = DummyParams.read_user_params(f)
    assert params.name == "future"
    assert "newer version" in caplog.text

    params.name = "changed"
    assert params.save() is False
    assert f.path.read_text() == before


def test_an_unreadable_file_from_a_newer_version_is_not_reset(tmp_path):
    f = _make_file(tmp_path, {"schema_version": 2, "tags": {"now": "a mapping"}})
    before = f.path.read_text()

    params = DummyParams.read_user_params(f)

    assert params.tags == []
    assert f.path.read_text() == before
    assert not (tmp_path / "dummy.yml.bak").exists()


def test_an_invalid_schema_version_makes_the_file_invalid(tmp_path):
    params = DummyParams.read_user_params(_make_file(tmp_path, {"schema_version": "one", "name": "x"}))

    assert params.name == "default"
    assert (tmp_path / "dummy.yml.bak").exists()


def test_replace_params_reads_an_exported_file(tmp_path):
    params = DummyParams(name="exported")
    save_yaml(tmp_path / "export.yml", params.to_dict())

    current = DummyParams.read_user_params(_make_file(tmp_path))
    replaced = current.replace_params(tmp_path / "export.yml")

    assert replaced.name == "exported"
    assert replaced.save()
    assert read_yaml(tmp_path / "dummy.yml")["name"] == "exported"
