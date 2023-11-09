[![astropy](http://img.shields.io/badge/powered%20by-AstroPy-orange.svg?style=flat)](http://www.astropy.org/)

Specvizitor is a Python GUI application for a visual inspection of astronomical spectroscopic data. The main goal is to provide a flexible tool for classifying **large** and **homogeneous** spectroscopic samples of galaxies, which is a typical case for blind spectroscopic surveys. Originally developed for the JWST Cycle 1 program [FRESCO](https://jwst-fresco.astro.unige.ch), this software can be easily adapted for a variety of spectroscopic data sets represented in standard data formats used in the astronomy community (FITS, ASCII, etc.).

![Specvizitor GUI](https://github.com/ivkram/specvizitor/blob/main/docs/screenshots/specvizitor_gui.png?raw=true "Specvizitor GUI")

## Installation

### Installing `specvizitor` using pip

Set up a local Python environment and run

```shell
$ pip install specvizitor
```

**NOTE:** Python >=3.10 is required to run specvizitor.

### Installing `specvizitor` from source

1. Clone the public repository:

    ```shell
    $ git clone https://github.com/ivkram/specvizitor
    $ cd specvizitor
    ```

2. Set up a local Python environment and run

    ```shell
    $ pip install -e .
    ```

## Starting `specvizitor`
    
Activate the local environment and run this command in your terminal:

```shell
$ specvizitor
```

## Configuring `specvizitor`

The basic settings such as the path to the catalogue or the data directory are available in `Tools > Settings`. For advanced settings, open the directory indicated in the bottom of the `Settings` widget ("Advanced settings"). This directory should contain the following YAML files: `config.yml` (the general GUI settings), `spectral_lines.yml` (the list of spectral lines displayed along with a 1D spectrum) and `data_widgets.yml` (the data viewer configuration). A few examples of how to tweak these settings for your needs are given below.

### Adding spectral lines

Open `spectral_lines.yml` and add an entry with a name of a spectral line and its rest wavelength to `wavelengths`, e.g.:

```yaml
wavelengths:
  # ...
  PaG: 10938.086
```

Save the file and restart specvizitor. The new line should appear in the spectrum widget.

### Hide a widget

Open `data_widgets.yml` and navigate to the configuration of the widget that you want to hide. Set the `visible` parameter to `false`, save the file and restart specvizitor. The widget should be removed from the view.

## Troubleshooting

To reset `specvizitor` to its initial state, run the script with the `--purge` option:

```shell
$ specvizitor --purge
```

## License

`specvizitor` is licensed under a 3-clause BSD style license - see the [LICENSE.txt](https://github.com/ivkram/specvizitor/blob/main/LICENSE.txt) file.
