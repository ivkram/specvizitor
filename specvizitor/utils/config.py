import logging
import pathlib
import yaml
import platformdirs
from dictdiffer import diff, patch, swap


def read_yaml(filename, local=False) -> dict:
    if local:
        yaml_path = (pathlib.Path(__file__).parent.parent / 'data' / filename).resolve()
    else:
        yaml_path = pathlib.Path(filename).resolve()

    with open(yaml_path, "r") as yaml_file:
        return yaml.safe_load(yaml_file)


def read_config() -> dict:
    config = read_yaml('config.yml', local=True)

    user_config_filename = pathlib.Path(platformdirs.user_config_dir('specvizitor')) / 'config.yml'
    if user_config_filename.exists():
        try:
            user_config = read_yaml(user_config_filename)
        except yaml.YAMLError:
            logging.error('Error occurred when parsing `{}`. The configuration file will be overwritten.'
                          .format(user_config_filename))
            save_user_config(config)
            return config

        config_diff = diff(config, user_config)

        user_config_upd = []
        config_upd = []

        for change in config_diff:
            if change[0] == 'change':
                config_upd.append(change)
            elif change[0] == 'add' or change[0] == 'remove':
                if change[1] in ('loader.cat.colnames', 'loader.cat.translate', 'gui.object_info.items')\
                        or change[1].split('.')[:-1] in ('loader.cat.translate',):
                    config_upd.append(change)
                else:
                    user_config_upd.append(change)

        patch(swap(user_config_upd), user_config, in_place=True)
        save_user_config(user_config)

        patch(config_upd, config, in_place=True)

    return config


def save_user_config(config):
    user_config_dir = pathlib.Path(platformdirs.user_config_dir('specvizitor'))
    if not user_config_dir.exists():
        user_config_dir.mkdir()

    user_config_filename = user_config_dir / 'config.yml'
    with open(user_config_filename, 'w') as yaml_file:
        yaml.dump(config, yaml_file, sort_keys=False)
