Application Settings
====================

Basic settings
++++++++++++++

Some basic settings such as the data path are available in :menuselection:`Tools --> Settings`. You can also access :guilabel:`Settings` by clicking on the cogwheel in :guilabel:`Toolbar`:

.. figure:: ../screenshots/cogwheel.png



:guilabel:`Settings` include the following sections:

.. list-table::
    :header-rows: 1
    :widths: auto

    * - Section
      - Purpose(s)
    * - :guilabel:`Appearance`
      - Change the application theme, configure antialiasing [#f1]_
    * - :guilabel:`Catalog`
      - Load a new catalog, configure aliases for column names
    * - :guilabel:`Data Source`
      - Change the data path, enable recursive search [#f2]_, add new images
    * - :guilabel:`Data Viewer`
      - Add spectral lines to the data viewer

Any changes will take effect immediately once you click :guilabel:`OK` (except for the application theme, which requires a restart).

Adding spectral lines
^^^^^^^^^^^^^^^^^^^^^

Open :guilabel:`Settings` ‣ :guilabel:`Data Viewer`. Click :guilabel:`Add...` and enter the line's name and wavelength:

.. figure:: ../screenshots/add_spectral_line.png

Click :guilabel:`OK`. The new line should appear in the data viewer.

Advanced settings
+++++++++++++++++

Some applications settings, for example widget configurations, cannot be modified from the GUI (yet). To view and modify these settings, open the directory indicated at the bottom of :guilabel:`Settings` (under the "Advanced settings"):

.. figure:: ../screenshots/advanced_settings.png



For example, in Linux this directory will be ``$HOME/.config/specvizitor``. There you will find the following `YAML <https://yaml.org>`_ files:

.. list-table::
    :header-rows: 1
    :widths: auto

    * - File
      - Description
      - Integrated in the GUI
    * - ``config.yml``
      - General application settings
      - Yes (for the most part)
    * - ``data_widgets.yml``
      - Widget configurations
      - No
    * - ``spectral_lines.yml``
      - List of spectral lines
      - Yes

Open one of these files in the text editor, and make the desired changes. Restart specvizitor for the changes to take effect.

.. note::

        If the ``*.yml`` file contains errors, it will be overwritten by specvizitor at startup. However, the original file will still be accessible from the same directory under the name ``*.yml.bkp`` (e.g., ``config.yml.bkp``).

Most of the parameters stored in these ``*.yml`` files can be modified directly from the GUI, with the important exception of widget configurations (``data_widgets.yml``). A comprehensive guide on how to modify of the ``data_widgets.yml`` file (add new widgets, configure existing ones) can be found in the :doc:`data-viewer` section.

.. rubric:: Footnotes

.. [#f1] Enabling antialiasing might decrease the GUI responsiveness.
.. [#f2] Enabling recursive search might severely slow down the transition between objects.
