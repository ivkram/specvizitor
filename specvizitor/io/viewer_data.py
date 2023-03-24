from astropy.io import fits
from astropy.table import Table
import astropy.units as u
from astropy.units.core import UnitConversionError
from astropy.utils.exceptions import AstropyWarning
import numpy as np
from PIL import Image, ImageOps
from specutils import Spectrum1D

import abc
from dataclasses import dataclass
import logging
import pathlib
import re
import warnings

from ..widgets.FileBrowser import FileBrowser

logger = logging.getLogger(__name__)


@dataclass
class BaseLoader(abc.ABC):
    name: str

    @abc.abstractmethod
    def load(self, filename: pathlib.Path, **kwargs):
        pass

    def raise_error(self, e):
        logger.error(f'{type(self).__name__}: {e}')


@dataclass
class GenericFITSLoader(BaseLoader):
    name: str = 'generic_fits'

    def load(self, filename: pathlib.Path, extname: str = None, extver: str = None, **kwargs):

        try:
            hdul = fits.open(filename, **kwargs)
        except Exception as e:
            self.raise_error(e)
            return None, None

        if extname is not None and extver is None:
            index = extname
        elif extname is not None and extver is not None:
            index = (extname, extver)
        else:
            index = 1

        try:
            hdu = hdul[index]
        except KeyError:
            self.raise_error(f'Extension `{index}` not found (filename: {filename.name})')
            return None, None

        meta = hdu.header

        if meta['XTENSION'] in ('TABLE', 'BINTABLE'):
            data = Table.read(hdu)
        else:
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
class SpecutilsLoader(BaseLoader):
    name: str = 'specutils'

    def load(self, filename: pathlib.Path, **kwargs):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', AstropyWarning)
                spec: Spectrum1D = Spectrum1D.read(filename, **kwargs)
        except Exception as e:
            self.raise_error(e)
            return None, None

        try:
            # specutils treats "pix" as a valid spectral axis unit
            spec.spectral_axis.to('AA')
        except UnitConversionError:
            self.raise_error(f'Invalid spectral axis unit: {spec.spectral_axis.unit}')
            return None, None

        return spec, spec.meta


def load(loader_name: str | None, filename: pathlib.Path, widget_name: str, **kwargs):
    registered_loaders: dict[str, BaseLoader] =\
        {loader.name: loader for loader in (GenericFITSLoader(), PILLoader(), SpecutilsLoader())}

    allowed_loader_names = ('auto',) + tuple(loader.name for loader in registered_loaders.values())
    if loader_name not in allowed_loader_names:
        logger.error(f'Unknown loader type: `{loader_name}` (widget: {widget_name}).'
                     f'Available loaders: {allowed_loader_names}')
        return None, None

    if loader_name == 'auto':
        if filename.suffix == '.fits':
            loader_name = 'generic_fits'
        else:
            loader_name = 'pil'

    return registered_loaders[loader_name].load(filename, **kwargs)


def add_enabled_aliases(units: dict[str, str]):
    u.add_enabled_aliases({alias: u.Unit(unit) for alias, unit in units.items()})


def get_filename(directory, pattern: str, object_id) -> pathlib.Path | None:
    """ Find a file for a given pattern and a given object ID. If more than one file name is matched to the pattern,
    return the first item from an alphabetically ordered list of matched file names.

    @param directory: the directory where the search is performed
    @param pattern: the pattern used to match file names
    @param object_id: the object ID
    @return: the file name matched to the pattern
    """

    filenames = sorted(pathlib.Path(directory).glob('*'))

    # match to the pattern
    matched_to_pattern = [p for p in filenames if re.search(pattern, str(p))]

    # match to the ID
    if isinstance(object_id, int):
        # make sure that we don't match e.g. '1123' or '1234' to '123' (but match '0123')
        matched_ids = [re.findall(r'\d*{}\d*'.format(object_id), str(p)) for p in matched_to_pattern]
        matched = [p for i, p in enumerate(matched_to_pattern)
                   if matched_ids[i] and str(max(matched_ids[i], key=len)).lstrip('0') == str(object_id)]
    else:
        matched = [p for p in matched_to_pattern if re.search(f'{object_id}', str(p))]

    if matched:
        return matched[0]
    else:
        return


def get_id_from_filename(filename, pattern: str) -> str | None:
    """ Extract the object ID from a file name using a pattern. If more than one ID is matched to the pattern, return
    the longest match (a typical case for integer IDs).

    @param filename: the file name to parse
    @param pattern: the pattern (a regular expression) used to match the ID
    @return: the matched ID
    """

    try:
        matches: list[str] = re.findall(pattern, pathlib.Path(filename).name)
    except re.error:
        return

    if matches:
        return max(matches, key=len)
    else:
        return


def get_ids_from_dir(directory, id_pattern: str) -> np.ndarray | None:
    """ Extract IDs from a directory using a pattern.
    @param directory: the directory where the search for IDs is performed
    @param id_pattern: the pattern (a regular expression) used to match IDs
    @return: a list of matched IDs
    """

    data_files = sorted(pathlib.Path(directory).glob('*'))  # includes subdirectories, if any
    ids = [get_id_from_filename(p, id_pattern) for p in data_files]
    ids = np.array([i for i in ids if i is not None])

    try:
        # convert IDs to int
        ids = ids.astype(np.int64)
    except ValueError:
        pass

    # remove ID duplicates
    ids = np.unique(ids)

    if not ids.size:
        logger.error('No IDs retrieved from the data directory')
        return

    return ids


def data_browser(default_path, **kwargs) -> FileBrowser:
    return FileBrowser(mode=FileBrowser.OpenDirectory, default_path=default_path, **kwargs)
