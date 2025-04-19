from astropy.io import fits
from astropy.table import Table
import astropy.units as u
from astropy.utils.exceptions import AstropyWarning
from astropy.wcs import WCS
import numpy as np
from PIL import Image, ImageOps
import rasterio

import abc
import logging
import pathlib
from string import Formatter
from typing import Any
import warnings

from .catalog import Catalog
from ..utils.qt_tools import QSingleton
from ..utils.widgets import FileBrowser


__all__ = [
    "add_image",
    "get_cutout_params",
    "load_widget_data",
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
        self._meta = None

    @abc.abstractmethod
    def open(self, filename: str, **kwargs):
        pass

    def load(self, **kwargs):
        return self._dataset, self._meta

    def close(self):
        self._dataset.close()

    @classmethod
    def validate_extension(cls, filename: str | pathlib.Path):
        return any(str(filename).endswith(s) for s in cls.extensions)

    @staticmethod
    def get_cutout_params(arr_shape, x0=None, y0=None, cutout_size=100, **kwargs):
        if x0 is None:
            x0 = arr_shape[1] // 2
        if y0 is None:
            y0 = arr_shape[0] // 2

        x1, x2 = x0 - cutout_size, x0 + cutout_size
        y1, y2 = y0 - cutout_size, y0 + cutout_size

        return (x1, x2, y1, y2), cutout_size


class GenericFITSLoader(BaseLoader):
    name = 'generic_fits'
    extensions = ('.fits', '.fits.gz')

    def open(self, filename: str, **kwargs):
        self._dataset = fits.open(filename, **kwargs)

    def load(self, extname: str = None, extver: str = None, extver_index: int = None, create_cutout=False, **kwargs):
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
            (x1, x2, y1, y2), _ = self.get_cutout_params(data.shape, **kwargs)
            data = data[y1:y2, x1:x2]

        return data, meta


class PILLoader(BaseLoader):
    name = 'pil'

    def open(self, filename: pathlib.Path, **kwargs):
        image = Image.open(filename, **kwargs)
        image = ImageOps.flip(image)
        self._dataset, self._meta = np.array(image), image.info


class RasterIOLoader(BaseLoader):
    name = 'rasterio'
    extensions = ('.tif', '.tiff')

    def open(self, filename: pathlib.Path, **kwargs):
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=rasterio.errors.NotGeoreferencedWarning)
            self._dataset = rasterio.open(filename, **kwargs)

    def load(self, create_cutout=False, **kwargs):
        if create_cutout:
            (x1, x2, y1, y2), cutout_size = self.get_cutout_params(self._dataset.shape, **kwargs)

            # wow, this actually works!
            data = self._dataset.read(window=rasterio.windows.Window(x1, self._dataset.height - y2,
                                                                     2 * cutout_size, 2 * cutout_size))
            data = np.moveaxis(data, 0, -1)
            data = np.flip(data, 0)
        else:
            data = self._dataset.read()

        return data, self._meta


class ViewerData(metaclass=QSingleton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._data: dict[str, tuple[BaseLoader, dict[str, Any]]] = {}
        self._loaders: dict[str, type(BaseLoader)] = {
            loader.name: loader for loader in (GenericFITSLoader, RasterIOLoader, PILLoader)
        }

    @property
    def loader_names(self):
        return ('auto',) + tuple(loader.name for loader in self._loaders.values())

    def _get_loader(self, filename: str) -> str:
        for ln, loader in self._loaders.items():
            if loader.validate_extension(filename):
                return ln
        return GenericFITSLoader.name

    def add(self, filename: str, loader: str | None = None, **loader_params):
        loader: str
        if loader is None:
            loader = 'auto'
        if loader not in self.loader_names:
            logger.error(f"Unknown loader type: `{loader}`. Available loaders: {', '.join(self.loader_names)}")
        if loader == 'auto':
            loader = self._get_loader(filename)

        loader: BaseLoader = self._loaders[loader]()
        try:
            loader.open(filename, **loader_params)
        except Exception as e:
            logger.error(f"{loader.name}: {e} (filename: {filename})")
            return None

        self._data[filename] = (loader, loader_params)
        logger.info(f"Database connection open (filename: {filename})")
        return self._data[filename]

    def load(self, filename: str, allowed_dtypes=None, **kwargs):
        if not self._data.get(filename):
            if not self.add(filename, **kwargs):
                return None, None

        loader = self._data[filename][0]
        try:
            data, meta = loader.load(**kwargs)
        except Exception as e:
            logger.error(f"{loader.name}: {e} (filename: {filename})")
            return None, None

        if allowed_dtypes and not _validate_dtype(data, allowed_dtypes):
            logger.error(f"Invalid input data type: {type(data)} (filename: {filename})")
            return None, None

        logger.info(f"Data loaded (filename: {filename})")
        return data, meta

    def close(self, filename: str):
        if not self._data.get(filename):
            return
        self._data.get(filename)[0].close()
        logger.info(f"Database connection closed (filename: {filename})")


def add_image(filename: str, loader: str, wcs_source: str | None = None, **kwargs):
    ViewerData().add(filename, loader=loader, **kwargs)
    if wcs_source:
        ViewerData().add(wcs_source)


def get_cutout_params(cat_entry: Catalog, wcs_source: str) -> dict:
    params = dict(create_cutout=True)

    ra, dec = None, None
    try:
        ra = cat_entry.get_col('ra')
    except KeyError as e:
        logger.warning(e)
    try:
        dec = cat_entry.get_col('dec')
    except KeyError as e:
        logger.warning(e)
    if ra is None or dec is None:
        return params

    _, meta = ViewerData().load(wcs_source)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', AstropyWarning)
        try:
            wcs = WCS(meta)
        except Exception as e:
            logger.warning(f"Failed to create a WCS object from image: {e} (image: {wcs_source})")
            return params

    x0, y0 = wcs.all_world2pix(ra, dec, 0)
    if not np.isfinite(x0) or not np.isfinite(y0):
        logger.debug(f"Calculation of pixel coordinates failed (image: {wcs_source})")
        return params
    x0, y0 = int(x0), int(y0)
    params.update(x0=x0, y0=y0)

    return params


def load_widget_data(obj_id: str | int, filename: str, loader: str, widget_title: str,
                     cat_entry: Catalog | None, allowed_dtypes: tuple[type] | None = None, silent: bool = False,
                     **kwargs):
    logger.disabled = True if silent else False

    field_values = dict(id=obj_id)

    try:
        field_names = [fn for _, fn, _, _ in Formatter().parse(filename) if fn is not None]
    except Exception as e:
        logger.error(e)
        return None, None, None

    if "id" in field_names:
        field_names.remove("id")

    if field_names:
        if not cat_entry:
            logger.error(f"Failed to resolve the filename: Catalog entry not loaded (widget: {widget_title})")
            return None, None, None

        for fn in field_names:
            try:
                fv = cat_entry.get_col(fn)
            except KeyError as e:
                logger.error(f"Failed to resolve the filename: {e} (widget: {widget_title})")
                return None, None, None
            else:
                field_values[fn] = fv

    filename = _resolve_filename(filename, **field_values)

    if not pathlib.Path(filename).exists():
        logger.error(f"{widget_title} not found (filename: {filename})")
        return None, None, None

    data, meta = ViewerData().load(filename, loader=loader, allowed_dtypes=allowed_dtypes, **kwargs)
    return filename, data, meta


def _resolve_filename(filename: str, **field_values) -> str:
    filename = filename.format(**field_values)
    filename = pathlib.Path(filename).resolve()
    return str(filename)


def _validate_dtype(data, allowed_dtypes: tuple[type, ...]) -> bool:
    if not any(isinstance(data, t) for t in allowed_dtypes):
        return False
    return True


def add_unit_aliases(unit_aliases: dict[str, list[str]]):
    for unit, aliases in unit_aliases.items():
        u.add_enabled_aliases({alias: u.Unit(unit) for alias in aliases})


def data_browser(default_path, **kwargs) -> FileBrowser:
    return FileBrowser(mode=FileBrowser.OpenDirectory, default_path=default_path, **kwargs)
