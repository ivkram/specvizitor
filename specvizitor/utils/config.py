import logging
import pathlib
import yaml
import platformdirs
from dictdiffer import diff, patch, swap


logger = logging.getLogger('specvizitor')


def read_yaml(filename, in_dist=False) -> dict:
    if in_dist:
        yaml_path = (pathlib.Path(__file__).parent.parent / 'data' / filename).resolve()
    else:
        yaml_path = pathlib.Path(filename).resolve()

    with open(yaml_path, "r") as yaml_file:
        return yaml.safe_load(yaml_file)


def save_yaml(filename, data):
    yaml_path = pathlib.Path(filename).resolve()

    with open(yaml_path, 'w') as yaml_file:
        yaml.dump(data, yaml_file, sort_keys=False)


# TODO: create Cache and Config classes
def get_user_config_filename():
    return pathlib.Path(platformdirs.user_config_dir('specvizitor')) / 'specvizitor.yml'


def get_cache_filename():
    return pathlib.Path(platformdirs.user_cache_dir('specvizitor')) / 'specvizitor.yml'


def read_config() -> dict:
    config = read_yaml('default_config.yml', in_dist=True)
    config_meta = read_yaml('config_meta.yml', in_dist=True)

    user_config_filename = get_user_config_filename()
    if user_config_filename.exists():
        try:
            user_config = read_yaml(user_config_filename)
        except yaml.YAMLError:
            logger.error('Error occurred when parsing `{}`. The configuration file will be overwritten.'.
                         format(user_config_filename))
            save_config(config)
            return config

        config_diff = diff(config, user_config, expand=True)

        user_config_revert = []
        config_upd = []

        for change in config_diff:
            print(change)
            if change[0] == 'change':
                config_upd.append(change)
            elif change[0] == 'add' or change[0] == 'remove':
                if any(change[1].startswith(key) for key in config_meta['dynamic']):
                    config_upd.append(change)
                else:
                    user_config_revert.append(change)

        if user_config_revert:
            patch(swap(user_config_revert), user_config, in_place=True)
            save_config(user_config)

        patch(config_upd, config, in_place=True)

    return config


def read_cache() -> dict:
    cache = {}

    cache_filename = get_cache_filename()
    if cache_filename.exists():
        try:
            cache = read_yaml(cache_filename)
        except yaml.YAMLError:
            logger.error('Error occurred when parsing `{}`. The cache file will be erased.'.
                         format(cache_filename))
            cache_filename.unlink()
            return {}

    return cache


def save_config(config):
    user_config_filename = get_user_config_filename()
    if not user_config_filename.parent.exists():
        user_config_filename.parent.mkdir()

    save_yaml(user_config_filename, config)
    logger.info('Configuration file updated')


def save_cache(cache):
    cache_filename = get_cache_filename()
    if not cache_filename.parent.exists():
        cache_filename.parent.mkdir()

    save_yaml(cache_filename, cache)
    logger.info('Cache updated')
