import pathlib
import yaml


def read_default_params():
    with open(pathlib.Path(__file__).parent / 'data' / 'config.yml', "r") as config_file:
        return yaml.safe_load(config_file)
