import logging
import pathlib
import yaml
from dictdiffer import diff, patch, swap
from dataclasses import dataclass, asdict
import dacite
from dacite.exceptions import WrongTypeError, MissingValueError

logger = logging.getLogger(__name__)


@dataclass
class LocalFile:
    directory: str
    filename: str = "specvizitor.yml"
    signature: str = "Local file"

    @property
    def path(self) -> pathlib.Path:
        return pathlib.Path(self.directory) / self.filename

    def save(self, data: dict):
        if not self.path.parent.exists():
            self.path.parent.mkdir()

        if self.path.exists():
            msg = "{} updated (path: {})".format(self.signature, self.path)
        else:
            msg = "{} created (path: {})".format(self.signature, self.path)

        save_yaml(self.path, data)
        logger.debug(msg)


@dataclass
class Params:
    @classmethod
    def read(cls, file: LocalFile, path_to_default: str | None = None):
        default_params = read_yaml(path_to_default, in_dist=True)
        params = dacite.from_dict(data_class=cls, data=default_params)

        if file.path.exists():
            try:
                user_params = read_yaml(file.path)
            except yaml.YAMLError:
                logger.error('Error occurred when parsing `{}`. The file will be overwritten.'.format(file.path))
                cls.save(params, file)
                return params

            # TODO: patch the user config file using dictdiffer
            try:
                user_params = dacite.from_dict(data_class=cls, data=user_params, config=dacite.Config())
            except (WrongTypeError, MissingValueError):
                logger.error('Error occurred when parsing `{}`. The file will be overwritten.'.format(file.path))
                cls.save(params, file)
                return params
            else:
                return user_params
        else:
            cls.save(params, file)

        return params

    def save(self, file: LocalFile):
        file.save(data=asdict(self))


@dataclass
class Cat:
    filename: str | None
    translate: dict[str, list[str]] | None


@dataclass
class Data:
    dir: str | None


@dataclass
class Loader:
    cat: Cat
    data: Data


@dataclass
class Geometry:
    min_width: int | None
    min_height: int | None


@dataclass
class AbstractWidget(Geometry):
    pass


@dataclass
class ControlPanel(AbstractWidget):
    button_width: int


@dataclass
class ObjectInfo(AbstractWidget):
    items: dict[str, str] | None


@dataclass
class ReviewForm(AbstractWidget):
    checkboxes: dict[str, str] | None


@dataclass
class ViewerElement(AbstractWidget):
    search_mask: str


@dataclass
class Slider:
    min_value: float | None
    max_value: float | None
    step: float | None
    default_value: float | None


@dataclass
class Spec1D(ViewerElement):
    slider: Slider


@dataclass
class Viewer(AbstractWidget):
    image_cutout: ViewerElement
    spec_2d: ViewerElement
    spec_1d: Spec1D


@dataclass
class Config(Params):
    loader: Loader
    writer: None
    control_panel: ControlPanel
    object_info: ObjectInfo
    review_form: ReviewForm
    viewer: Viewer

    @classmethod
    def read(cls, file: LocalFile, path_to_default: str | None = None):
        return super().read(file, path_to_default='default_config.yml')


@dataclass
class Cache(Params):
    last_inspection_file: str | None
    last_object_index: int | None


def read_yaml(filename=None, in_dist=False) -> dict:
    if filename is None:
        return {}

    if in_dist:
        yaml_path = (pathlib.Path(__file__).parent.parent / 'data' / filename).resolve()
    else:
        yaml_path = pathlib.Path(filename).resolve()

    with open(yaml_path, "r") as yaml_file:
        return yaml.safe_load(yaml_file)


def filter_none_values(data):
    if isinstance(data, dict):
        return {k: filter_none_values(v) for k, v in data.items() if v is not None}
    return data


def save_yaml(filename, data):
    yaml_path = pathlib.Path(filename).resolve()

    with open(yaml_path, 'w') as yaml_file:
        yaml.dump(data, yaml_file, sort_keys=False)
