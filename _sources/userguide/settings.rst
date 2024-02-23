Application settings
====================

Basic settings
++++++++++++++

Some basic settings such as the data path are available in :menuselection:`Tools --> Settings`. You can also access :guilabel:`Settings` by clicking on the cogwheel in :guilabel:`Toolbar`.

:guilabel:`Settings` comprises the following sections:

.. list-table::
    :header-rows: 1
    :widths: auto

    * - Section
      - Purpose
    * - :guilabel:`Appearance`
      - Change the application theme, enable/disable antialiasing [#f1]_
    * - :guilabel:`Catalog`
      - Change the catalog
    * - :guilabel:`Data Source`
      - Change the path to the data folder

Advanced settings
+++++++++++++++++

To access advanced settings, open the directory indicated in the bottom of :guilabel:`Settings` (under the "Advanced settings"). This directory should comprise the following `YAML <https://yaml.org>`_ files:

.. list-table::
    :header-rows: 1
    :widths: auto

    * - File
      - Purpose
    * - ``config.yml``
      - General GUI settings
    * - ``data_widgets.yml``
      - Configurations of data widgets
    * - ``spectral_lines.yml``
      - The list of spectral lines displayed in the GUI

.. rubric:: Footnotes

.. [#f1] Enabling antialiasing might decrease the GUI responsiveness.

