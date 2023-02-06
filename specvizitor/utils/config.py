import pathlib
import yaml


def read_yaml(filename):
    with open(pathlib.Path(__file__).parent.parent / 'data' / filename, "r") as config_file:
        return yaml.safe_load(config_file)
