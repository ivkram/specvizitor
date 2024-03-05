Widget configurations
=====================

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

