Data Viewer
=====================

Adding spectral lines
+++++++++++++++++++++

Open :guilabel:`Settings` ‣ :guilabel:`Data Viewer`. Click :guilabel:`Add...` and enter the line's name and wavelength:


.. figure:: ../screenshots/add_spectral_line.png



Click :guilabel:`OK`. The new line should appear in the data viewer.

Hiding a widget
+++++++++++++++

Open ``data_widgets.yml`` and navigate to the configuration of the widget that you want to hide. Set the ``visible`` parameter to ``false``, save the file and restart specvizitor. The widget should be removed from the view.

