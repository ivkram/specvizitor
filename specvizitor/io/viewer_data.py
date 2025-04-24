from astropy.io import fits
from astropy.table import Table
import astropy.units as u
from astropy.utils.exceptions import AstropyWarning
from astropy.wcs import WCS
import numpy as np
from PIL import Image, ImageOps
import rasterio

import abc
from collections import OrderedDict
import logging
import pathlib
from string import Formatter
from typing import Any
import warnings

from .catalog import Catalog
from ..utils.widgets import FileBrowser


__all__ = [
    "ViewerData",
    "DataPath",
    "LocalPath",
    "URLPath",
    "add_unit_aliases",
    "data_browser"
]

Image.MAX_IMAGE_PIXELS = None  # ignore warnings when loading large images
logger = logging.getLogger(__name__)


class BaseLoader(abc.ABC):
    name: str
    extensions: tuple[str, ...] = ()

    def __init__(self):
        self._dataset = None
        self._meta: dict | None = None

        self._last_kwargs: dict | None = None
        self.last_data: tuple[Any, Any] | None = None

    def open(self, filename: str, **kwargs):
        self._open(filename, **kwargs)
        self._last_kwargs = kwargs

    @abc.abstractmethod
    def _open(self, filename: str, **kwargs):
        pass

    def reopen(self, filename: str):
        if self._last_kwargs is None:
            raise RuntimeError("Failed to re-open the file: file was never opened")
        self.open(filename, **self._last_kwargs)

    def load(self, **kwargs) -> tuple[Any, Any]:
        self.last_data = self._load(**kwargs)
        return self.last_data

    def _load(self, **kwargs):
        return self._dataset, self._meta

    def close(self):
        self._dataset.close()

    @classmethod
    def validate_extension(cls, filename: str | pathlib.Path) -> bool:
        return any(str(filename).endswith(s) for s in cls.extensions)

    @staticmethod
    def get_cutout_params(arr_shape, x0=None, y0=None, cutout_size=100, **kwargs) -> tuple[tuple[float, float, float, float], float]:
        if x0 is None:
            x0 = arr_shape[1] // 2
        if y0 is None:
            y0 = arr_shape[0] // 2

        x0, y0 = int(x0), int(y0)

        x1, x2 = x0 - cutout_size, x0 + cutout_size
        y1, y2 = y0 - cutout_size, y0 + cutout_size

        return (x1, x2, y1, y2), cutout_size


class GenericFITSLoader(BaseLoader):
    name = 'generic_fits'
    extensions = ('.fits', '.fits.gz')

    def _open(self, filename: str, **kwargs):
        self._dataset = fits.open(filename, **kwargs)

    def _load(self, extname: str = None, extver: str = None, extver_index: int = None, create_cutout=False,
              create_wcs=False, **kwargs):
        hdul = self._dataset

        if extname is not None and extver is not None:
            index = (extname, extver)
        elif extname is not None and extver_index is not None:
            extname_match_indices = [i for i, hdu in enumerate(hdul) if hdu.header.get('EXTNAME') == extname]
            try:
                index = extname_match_indices[extver_index]
            except IndexError:
                IndexError(f"EXTVER `{extver_index}` out of range")
        elif extname is not None:
            index = extname
        elif len(hdul) > 1:
            index = 1
        else:
            index = 0

        try:
            hdu = hdul[index]
        except KeyError:
            KeyError(f"Extension `{index}` not found")

        meta = hdu.header
        if meta.get('XTENSION') and meta['XTENSION'] in ('TABLE', 'BINTABLE'):
            data = Table.read(hdu)
        else:
            data = hdu.data

        if create_cutout:
            coords, _ = self.get_cutout_params(data.shape, **kwargs)
            data = self._create_cutout(data, *coords)

        if create_wcs:
            meta.wcs = self._create_wcs(meta)

        return data, meta

    @staticmethod
    def _create_cutout(data, x1, x2, y1, y2):
        return data[y1:y2, x1:x2]

    @staticmethod
    def _create_wcs(meta):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', AstropyWarning)
            wcs = WCS(meta)
        return wcs


class PILLoader(BaseLoader):
    name = 'pil'

    def _open(self, filename: pathlib.Path, **kwargs):
        image = Image.open(filename, **kwargs)
        image = ImageOps.flip(image)
        self._dataset, self._meta = np.array(image), image.info


class RasterIOLoader(BaseLoader):
    name = 'rasterio'
    extensions = ('.tif', '.tiff')

    def _open(self, filename: pathlib.Path, **kwargs):
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=rasterio.errors.NotGeoreferencedWarning)
            self._dataset = rasterio.open(filename, **kwargs)

    def _load(self, create_cutout=False, **kwargs):
        if create_cutout:
            (x1, x2, y1, y2), cutout_size = self.get_cutout_params(self._dataset.shape, **kwargs)
            data = self._create_cutout(x1, y2, cutout_size)
        else:
            data = self._dataset.read()

        return data, self._meta

    def _create_cutout(self, x1, y2, cutout_size):
        # wow, this actually works!
        data = self._dataset.read(window=rasterio.windows.Window(x1, self._dataset.height - y2,
                                                                 2 * cutout_size, 2 * cutout_size))
        data = np.moveaxis(data, 0, -1)
        data = np.flip(data, 0)
        return data


class ViewerData:
    def __init__(self):
        self._loaders: dict[str, BaseLoader] = {}
        self._loader_constructors: OrderedDict[str, type(BaseLoader)] = OrderedDict(
            [(loader.name, loader) for loader in (GenericFITSLoader, RasterIOLoader, PILLoader)]
        )

    @property
    def loader_names(self):
        return ('auto',) + tuple(loader.name for loader in self._loader_constructors.values())

    def _get_loader(self, filename: str) -> str:
        for ln, loader in self._loader_constructors.items():
            if loader.validate_extension(filename):
                return ln
        return GenericFITSLoader.name

    def open(self, filename: str, loader: str | None = None, **loader_params):
        loader: str
        if loader is None:
            loader = 'auto'
        if loader not in self.loader_names:
            logger.error(f"Unknown loader type: `{loader}`. Available loaders: {', '.join(self.loader_names)}")
        if loader == 'auto':
            loader = self._get_loader(filename)

        loader: BaseLoader = self._loader_constructors[loader]()
        try:
            loader.open(filename, **loader_params)
        except Exception as e:
            logger.error(f"{type(loader).__name__}: {e} (filename: {filename})")
            return None

        self._loaders[filename] = loader
        logger.debug(f"Database connection opened (filename: {filename})")

        return loader

    def reopen(self, filename: str):
        loader = self._loaders.get(filename)
        if not loader:
            logger.error(f"Failed to re-open connection: connection not open (filename: {filename})")
            return

        loader.reopen(filename)

    def open_image(self, filename: str, loader: str, wcs_source: str | None = None, **kwargs):
        self.open(filename, loader=loader, **kwargs)
        if wcs_source:
            self.open(wcs_source)

    def load(self, filename: str, allowed_dtypes=None, silent: bool = False, lazy: bool = False, **kwargs):
        if not self._loaders.get(filename):
            if not self.open(filename, **kwargs):
                return None, None

        loader = self._loaders.get(filename)
        if lazy and loader.last_data is not None:
            return loader.last_data

        try:
            data, meta = loader.load(**kwargs)
        except Exception as e:
            if not silent:
                logger.error(f"{type(loader).__name__}: {e} (filename: {filename})")
            return None, None

        if allowed_dtypes and not self._validate_dtype(data, allowed_dtypes):
            logger.error(f"Invalid input data type: {type(data)} (filename: {filename})")
            return None, None

        logger.debug(f"Data loaded (filename: {filename})")
        return data, meta

    def close(self, filename: str):
        if not self._loaders.get(filename):
            return
        self._loaders.pop(filename).close()
        logger.debug(f"Database connection closed (filename: {filename})")

    def close_all(self):
        for filename in list(self._loaders):
            self.close(filename)

    @staticmethod
    def _validate_dtype(data, allowed_dtypes: tuple[type, ...]) -> bool:
        if not any(isinstance(data, t) for t in allowed_dtypes):
            return False
        return True


class DataPath(abc.ABC):
    def __init__(self, path: str):
        self._path: str = path

    def __str__(self):
        return self._path

    @property
    def name(self) -> str:
        return self._path

    def resolve(self, obj_id: str | int, cat_entry: Catalog | None):
        field_values = dict(id=obj_id)
        field_names = [fn for _, fn, _, _ in Formatter().parse(self._path) if fn is not None]

        if "id" in field_names:
            field_names.remove("id")

        if field_names:
            if not cat_entry:
                raise ValueError("Catalog entry not loaded")

            for fn in field_names:
                fv = cat_entry.get_col(fn)
                field_values[fn] = fv

        self._path = self._path.format(**field_values)

    def validate(self):
        pass


class LocalPath(DataPath):
    @property
    def name(self) -> str:
        return self._path_obj.name

    @property
    def _path_obj(self) -> pathlib.Path:
        return pathlib.Path(self._path)

    def resolve(self, obj_id: str | int, cat_entry: Catalog | None):
        super().resolve(obj_id, cat_entry)
        self._path = str(self._path_obj.resolve())

    def validate(self):
        if not self._path_obj.exists():
            raise FileNotFoundError


class URLPath(DataPath):
    pass


def add_unit_aliases(unit_aliases: dict[str, list[str]]):
    for unit, aliases in unit_aliases.items():
        u.add_enabled_aliases({alias: u.Unit(unit) for alias in aliases})


def data_browser(default_path, **kwargs) -> FileBrowser:
    return FileBrowser(mode=FileBrowser.OpenDirectory, default_path=default_path, **kwargs)
