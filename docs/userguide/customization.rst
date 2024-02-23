Customization
=============

The basic settings such as the path to the catalogue or the data directory are available in :menuselection:`Tools --> Settings`. For advanced settings, open the directory indicated in the bottom of the :menuselection:`Settings` widget ("Advanced settings"). This directory should contain the following YAML files: ``config.yml`` (the general GUI settings), ``spectral_lines.yml`` (the list of spectral lines displayed along with a 1D spectrum) and ``data_widgets.yml`` (the data viewer configuration). A few examples of how to tweak these settings for your needs are given below.

Adding spectral lines
+++++++++++++++++++++

Open ``spectral_lines.yml`` and add an entry with a name of a spectral line and its rest wavelength to ``wavelengths``, e.g.:

.. code-block:: yaml

        wavelengths:
          ...
          PaG: 10938.086


Save the file and restart specvizitor. The new line should appear in the spectrum widget.

Hiding a widget
+++++++++++++++

Open ``data_widgets.yml`` and navigate to the configuration of the widget that you want to hide. Set the ``visible`` parameter to ``false``, save the file and restart specvizitor. The widget should be removed from the view.
