[![astropy](http://img.shields.io/badge/powered%20by-AstroPy-orange.svg?style=flat)](http://www.astropy.org/)

Specvizitor is a Python GUI application for a visual inspection of astronomical spectroscopic data. The main goal is to provide a flexible tool for classifying **large**, **homogeneous** samples of astrophysical objects observed with spectroscopy, which is a typical case for blind spectroscopic surveys. Originally developed for the JWST Cycle 1 program ''[FRESCO](https://jwst-fresco.astro.unige.ch)'', this software can be easily adapted for a variety of spectroscopic data sets represented in standard formats used in the astronomy community (FITS, ASCII, etc.).

![Specvizitor GUI](https://github.com/ivkram/specvizitor/blob/main/docs/screenshots/specvizitor_gui.png?raw=true "Specvizitor GUI")

## Installation

### Installing `specvizitor` using pip

Set up a local environment (Python 3.10+) and run

        $ pip install specvizitor

### Installing `specvizitor` from source

1. Clone the public repository:

        $ git clone https://github.com/ivkram/specvizitor
        $ cd specvizitor

2. Set up a local environment (Python 3.10+) and run

        $ pip install -e .

## Starting `specvizitor`
    
To start the application, activate the local environment and run this command in your terminal:

    $ specvizitor

## Troubleshooting

To reset `specvizitor` to its initial state, run the script with the `--purge` option:

    $ specvizitor --purge

## License

`specvizitor` is licensed under a 3-clause BSD style license - see the [LICENSE.txt](https://github.com/ivkram/specvizitor/blob/main/LICENSE.txt) file.
