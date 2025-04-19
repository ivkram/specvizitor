from astropy.io import fits
from astropy.io.fits.header import Header
from astropy.table import Table
import astropy.units as u
from astropy.utils.exceptions import AstropyWarning
from astropy.wcs import WCS
import numpy as np
from PIL import Image, ImageOps
import rasterio

import abc
from dataclasses import dataclass
from enum import Enum
import logging
import pathlib
from string import Formatter
import warnings

from .catalog import Catalog
from ..utils.widgets import FileBrowser

Image.MAX_IMAGE_PIXELS = None  # ignore warnings when loading large images
logger = logging.getLogger(__name__)


class REQUESTS(Enum):
    CUTOUT = 0


@dataclass
class FieldImage:
    filename: pathlib.Path
    data: np.ndarray | rasterio.DatasetReader
    meta: dict | Header | None = None

    def create_cutout(self, cutout_size: float, ra=None, dec=None):
        x, y = self.data.shape[0] // 2, self.data.shape[1] // 2

        if ra and dec:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', AstropyWarning)
                try:
                    wcs = WCS(self.meta)
                except Exception as e:
                    logger.error(f'Failed to create a WCS object from image: {e} (image: {self.filename.name})')
                    return None
            x, y = wcs.all_world2pix(ra, dec, 0)
            if not np.isfinite(x) or not np.isfinite(y):
                #logger.error(f'Cutout error: Failed to convert pixel coordinates to world coordinates '
                #             f'(image: {self.filename.name}, RA: {ra}, Dec: {dec})')
                return None
            x, y = int(x), int(y)

        x1, x2 = x - cutout_size, x + cutout_size
        y1, y2 = y - cutout_size, y + cutout_size

        if isinstance(self.data, rasterio.DatasetReader):
            # wow, this actually worked
            data = self.data.read(window=rasterio.windows.Window(x1, self.data.height - y2,
                                                                 2 * cutout_size, 2 * cutout_size))
            data = np.moveaxis(data, 0, -1)
            data = np.flip(data, 0)

            # reopen the dataset to free resources
            self.data.close()
            self.data, _ = RasterIOLoader().load(self.filename)
        else:
            data = self.data[y1:y2, x1:x2]
        return data


@dataclass
class BaseLoader(abc.ABC):
    name: str
    supports_memmap: bool = False
    extensions: tuple[str, ...] = ()

    @abc.abstractmethod
    def load(self, filename: pathlib.Path, **kwargs):
        pass

    @classmethod
    def validate_extension(cls, filename: str | pathlib.Path):
        return any(str(filename).endswith(s) for s in cls.extensions)

    def raise_error(self, e):
        logger.error(f'{type(self).__name__}: {e}')


@dataclass
class GenericFITSLoader(BaseLoader):
    name: str = 'generic_fits'
    supports_memmap: bool = True
    extensions: tuple[str, ...] = ('.fits', '.fits.gz')

    def load(self, filename: pathlib.Path, extname: str = None, extver: str = None, extver_index: int = None,
             reverse_search=False, memmap=True, **kwargs):

        try:
            hdul = fits.open(filename, memmap=memmap, **kwargs)
        except Exception as e:
            self.raise_error(e)
            return None, None

        if extname is not None and extver is not None:
            index = (extname, extver)
        elif extname is not None and extver_index is not None:
            extname_match_indices = [i for i, hdu in enumerate(hdul) if hdu.header.get('EXTNAME') == extname]
            try:
                index = extname_match_indices[extver_index]
            except IndexError:
                self.raise_error(f'EXTVER `{extver_index}` out of range (filename: {filename.name})')
                hdul.close()
                return None, None
        elif extname is not None:
            index = extname
        elif len(hdul) > 1:
            index = 1
        else:
            index = 0

        try:
            hdu = hdul[index]
        except KeyError:
            self.raise_error(f'Extension `{index}` not found (filename: {filename.name})')
            hdul.close()
            return None, None

        # read the header
        meta = hdu.header

        if meta.get('XTENSION') and meta['XTENSION'] in ('TABLE', 'BINTABLE'):
            # read table data
            data = Table.read(hdu)
        else:
            # read image data
            data = hdu.data

        hdul.close()
        return data, meta


@dataclass
class PILLoader(BaseLoader):
    name: str = 'pil'

    def load(self, filename: pathlib.Path, **kwargs):
        try:
            image = Image.open(filename, **kwargs)
        except Exception as e:
            self.raise_error(e)
            return None, None

        image = ImageOps.flip(image)

        data, meta = np.array(image), image.info
        image.close()

        return data, meta


@dataclass
class RasterIOLoader(BaseLoader):
    name: str = 'rasterio'
    supports_memmap: bool = True

    def load(self, filename: pathlib.Path, memmap=True, **kwargs):
        try:
            warnings.filterwarnings("ignore", category=rasterio.errors.NotGeoreferencedWarning)
            dataset = rasterio.open(filename, **kwargs)
        except Exception as e:
            self.raise_error(e)
            return None, None

        meta = dataset.meta

        return dataset, meta


def load(loader_name: str | None, filename: pathlib.Path, memmap: bool = False, **kwargs):
    registered_loaders: dict[str, type(BaseLoader)] = {loader.name: loader for loader in (GenericFITSLoader,
                                                                                          PILLoader,
                                                                                          RasterIOLoader)}

    allowed_loader_names = ('auto',) + tuple(loader.name for loader in registered_loaders.values())
    if loader_name not in allowed_loader_names:
        logger.error(f'Unknown loader type: `{loader_name}`. Available loaders: {allowed_loader_names}')
        return None, None

    if loader_name == 'auto':
        if GenericFITSLoader.validate_extension(filename):
            loader_name = 'generic_fits'
        else:
            if memmap:
                loader_name = 'rasterio'
            else:
                loader_name = 'pil'

    loader: BaseLoader = registered_loaders[loader_name]()
    if loader.supports_memmap:
        return loader.load(filename, memmap=memmap, **kwargs)
    else:
        return loader.load(filename, **kwargs)


def load_image(filename: str, loader: str, widget_title: str, wcs_source: str | None = None,
               memmap=True, **kwargs):
    filename = pathlib.Path(filename)
    if not filename.exists():
        logger.error(f'Image not found: {filename} (widget: {widget_title})')
        return None, None

    data, meta = load(loader, filename, memmap=memmap, **kwargs)
    if data is None or not _validate_dtype(data, (np.ndarray, rasterio.DatasetReader), widget_title):
        return None, None

    if wcs_source:
        wcs_source = pathlib.Path(wcs_source)
        if not wcs_source.exists():
            logger.error(f'Image not found: {wcs_source} (widget: {widget_title})')
        _, meta = load('auto', wcs_source)

    return data, meta


def load_widget_data(obj_id: str | int, data_source: str, filename: str, loader: str, widget_title: str,
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

    data_path = str(pathlib.Path(data_source) / filename)
    filename = _resolve_data_path(data_path, **field_values)

    if not filename.exists():
        logger.error(f"{widget_title} not found (object ID: {obj_id})")
        return None, None, None

    data, meta = load(loader, filename, **kwargs)
    if data is None or (allowed_dtypes and not _validate_dtype(data, allowed_dtypes, widget_title)):
        return None, None, None

    return filename, data, meta


def _resolve_data_path(data_path: str, **field_values) -> pathlib.Path:
    data_path = data_path.format(**field_values)
    data_path = pathlib.Path(data_path).resolve()
    return data_path


def _validate_dtype(data, allowed_dtypes: tuple[type, ...], widget_title: str) -> bool:
    if not any(isinstance(data, t) for t in allowed_dtypes):
        logger.error(f"Invalid input data type: {type(data)} (widget: {widget_title})")
        return False
    return True


def add_unit_aliases(unit_aliases: dict[str, list[str]]):
    for unit, aliases in unit_aliases.items():
        u.add_enabled_aliases({alias: u.Unit(unit) for alias in aliases})


def data_browser(default_path, **kwargs) -> FileBrowser:
    return FileBrowser(mode=FileBrowser.OpenDirectory, default_path=default_path, **kwargs)
