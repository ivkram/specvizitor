[![astropy](http://img.shields.io/badge/powered%20by-AstroPy-orange.svg?style=flat)](http://www.astropy.org/)

Specvizitor is a Python GUI application for a visual inspection of astronomical spectroscopic data. The main goal is to provide a flexible tool for classifying **large**, **homogeneous** samples of astrophysical objects observed with spectroscopy, which is a typical case for blind spectroscopic surveys. Originally developed for the JWST Cycle 1 program ''[FRESCO](https://jwst-fresco.astro.unige.ch)'', this software can be easily adapted for a variety of spectroscopic data sets represented in standard data formats used in the astronomy community (FITS, ASCII, etc.).

![Specvizitor GUI](https://github.com/ivkram/specvizitor/blob/main/docs/screenshots/specvizitor_gui.png?raw=true "Specvizitor GUI")

## Installation

### Installing `specvizitor` using pip

Set up a local environment (Python **3.10+**) and run

```shell
$ pip install specvizitor
```

### Installing `specvizitor` from source

1. Clone the public repository:

    ```shell
    $ git clone https://github.com/ivkram/specvizitor
    $ cd specvizitor
    ```

2. Set up a local environment (Python **3.10+**) and run

    ```shell
    $ pip install -e .
    ```

## Starting `specvizitor`
    
To start `specvizitor`, activate the local environment and run this command in your terminal:

```shell
$ specvizitor
```

## Configuring `specvizitor`

The basic settings such as the path to the catalogue/data directory are available in `Tools -> Settings`. For more advanced settings, open the directory indicated in the bottom of the `Settings` widget ("Advanced settings"). Its location is platform-specific and determined using the [platformdirs](https://pypi.org/project/platformdirs/) package. The directory should contain the following YAML files: `specvizitor.yml` (the general GUI settings), `lines.yml` (the list of spectral lines displayed along with a spectrum) and `docks.yml` (the configuration of the data viewer). Several examples of editing these files for your needs are given below, but note that in the future, `specvizitor` will be fully configurable using the GUI only.

### Extending the list of spectral lines

Open `lines.yml` and add an entry with the name of the spectral line and its rest wavelength to `list`, e.g.:

```yaml
list:
  # ...
  PaG: 10938.086
```

By default, all wavelengths are represented in angstroms. The wavelength unit is controlled by the `wave_unit` parameter in `lines.yml`.

### Configuring the data viewer

The content of the data viewer is described in `docks.yml`. There are three types of data that can be displayed in the data viewer: `images`, `plots` and `spectra`. 

## Troubleshooting

To reset `specvizitor` to its initial state, run the script with the `--purge` option:

```shell
$ specvizitor --purge
```

## License

`specvizitor` is licensed under a 3-clause BSD style license - see the [LICENSE.txt](https://github.com/ivkram/specvizitor/blob/main/LICENSE.txt) file.
