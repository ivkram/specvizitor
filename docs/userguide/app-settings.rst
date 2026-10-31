Settings
========

Settings come in two scopes:

* **Your preferences** (e.g., the theme or the list of spectral lines) apply to every workspace.
* **Workspace settings** (e.g., the data and catalog paths, or the data viewer configuration)
  belong to the current workspace (see :doc:`workspaces`).

Most of them can be changed in :guilabel:`Settings`. The others are changed by editing the
configuration files, which are listed in full in `Configuration reference`_.

The Settings dialog
+++++++++++++++++++

Open :menuselection:`Tools --> Settings`, or click on the cogwheel in :guilabel:`Toolbar`:

.. figure:: ../screenshots/cogwheel.png



:guilabel:`Settings` include the following sections:

.. list-table::
    :header-rows: 1
    :widths: auto

    * - Section
      - Purpose(s)
      - Scope
    * - :guilabel:`Appearance`
      - Change the application theme, configure antialiasing [#f1]_, etc.
      - You
    * - :guilabel:`Catalog`
      - Load a new catalog, configure aliases for column names
      - Workspace
    * - :guilabel:`Data Source`
      - Change the data path, add new images, configure unit aliases
      - Workspace
    * - :guilabel:`Data Viewer`
      - Set the redshift steps and the default screenshot location, add spectral lines
      - You
    * - :guilabel:`Plugins`
      - Enable the plugins that adapt the data viewer to a dataset
      - Workspace

Most changes take effect immediately once you click :guilabel:`OK`. A few cannot, because they
are applied once while the application starts, and specvizitor will offer to restart:

.. list-table::
    :header-rows: 1
    :widths: auto

    * - Setting
      - Why a restart is needed
    * - Application theme
      - Applied as a stylesheet at startup
    * - Plugins
      - Imported at startup

Adding spectral lines
^^^^^^^^^^^^^^^^^^^^^

Open :guilabel:`Settings` ‣ :guilabel:`Data Viewer`. Click :guilabel:`Add...` and enter the line's name and its vacuum wavelength (in Å by default):

.. figure:: ../screenshots/add_spectral_line.png

Click :guilabel:`OK`. The new line should appear in the data viewer.

.. _config-files:

Configuration files
+++++++++++++++++++

The settings are stored as `YAML <https://yaml.org>`_ files. Your preferences are in the
application configuration directory [#f2]_, and the workspace settings are in the workspace
directory. Click the directory indicated at the bottom of :guilabel:`Settings` (under "Advanced
settings") to open it in your file manager:

.. figure:: ../screenshots/advanced_settings.png



.. list-table::
    :header-rows: 1
    :widths: auto

    * - File
      - Directory
      - Contents
      - In :guilabel:`Settings`
    * - ``config.yml``
      - Application
      - Your preferences
      - Yes
    * - ``spectral_lines.yml``
      - Application
      - The spectral lines shown in the data viewer
      - Yes
    * - ``workspaces.yml``
      - Application
      - The list of known workspaces
      - Managed by specvizitor
    * - ``workspace.yml``
      - Workspace
      - Data and catalog paths, catalog settings, plugins
      - Yes
    * - ``data_widgets.yml``
      - Workspace
      - The widgets of the data viewer (see :doc:`data-viewer`)
      - No
    * - ``layout.yml``
      - Workspace
      - The window layout
      - Managed by specvizitor
    * - ``state.yml``
      - Workspace
      - The inspection file you had open, and your position in it
      - Managed by specvizitor

Open one of these files in a text editor and make the desired changes.

.. tip::

    You do not have to restart specvizitor after editing ``data_widgets.yml``. Use
    :menuselection:`Widgets --> Restore...` and select the file you just edited: the new
    configuration is applied immediately.

How the files are read and written
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* **Missing files** are created with the default values the first time specvizitor needs them.
* **Files are only written when something changes.** Opening specvizitor does not rewrite a file
  you edited by hand, so your comments and formatting stay until the application itself saves a
  change to that file.
* **Missing keys** take their default value.
* **Unknown keys**, such as a misspelled one, are ignored. Specvizitor logs a warning that names
  each of them with its full path (e.g., ``catalog.filname``). They are dropped the next time the
  application saves the file.
* **Invalid files** (a YAML syntax error, or a value of the wrong type) are reset to their default
  values, and the error is logged with the key it concerns. For every file except
  ``layout.yml`` and ``state.yml``, the original is kept next to it as ``*.yml.bak``
  (e.g., ``workspace.yml.bak``).
* **Schema versions.** Every file starts with ``schema_version``, the version of the layout it was
  written in. Do not edit it. A file written by an older version of specvizitor is upgraded once,
  and the original is kept as ``*.yml.bak``. A file written by a newer version is read as well as
  possible but never overwritten.

Configuration reference
+++++++++++++++++++++++

In the tables below, a dotted key such as ``appearance.theme`` is written in YAML as a nested
mapping::

    appearance:
      theme: dark

``config.yml``
^^^^^^^^^^^^^^

.. list-table::
    :header-rows: 1
    :widths: auto

    * - Key
      - Default
      - Description
    * - ``appearance.theme``
      - ``dark``
      - ``dark`` or ``light``. Applied at startup.
    * - ``appearance.antialiasing``
      - ``false``
      - Smooth lines and edges in the data viewer (might decrease the GUI responsiveness)
    * - ``appearance.viewer_spacing``
      - ``3``
      - Space between the widgets of the data viewer, in pixels
    * - ``appearance.viewer_margins``
      - ``3``
      - Margins around each widget of the data viewer, in pixels
    * - ``data_viewer.default_screenshot_location``
      - ``null``
      - The directory proposed when saving a screenshot
    * - ``data_viewer.redshift_step``
      - ``0.01``
      - How much :kbd:`Q` and :kbd:`W` change the redshift
    * - ``data_viewer.redshift_small_step``
      - ``0.0005``
      - How much :kbd:`Shift+Q` and :kbd:`Shift+W` change the redshift

``spectral_lines.yml``
^^^^^^^^^^^^^^^^^^^^^^

.. list-table::
    :header-rows: 1
    :widths: auto

    * - Key
      - Default
      - Description
    * - ``wave_unit``
      - ``angstrom``
      - The unit of the wavelengths below, in any form astropy understands (e.g., ``micron``)
    * - ``wavelengths``
      - (see the file)
      - The rest-frame vacuum wavelength of each line, by name (e.g., ``Ha: 6564.633``)

``workspaces.yml``
^^^^^^^^^^^^^^^^^^

.. list-table::
    :header-rows: 1
    :widths: auto

    * - Key
      - Default
      - Description
    * - ``active``
      - ``null``
      - The path of the workspace opened at startup
    * - ``known``
      - ``[]``
      - The paths of the known workspaces, most recently used first

``workspace.yml``
^^^^^^^^^^^^^^^^^

.. list-table::
    :header-rows: 1
    :widths: auto

    * - Key
      - Default
      - Description
    * - ``name``
      - ``null``
      - The name of the workspace. Without a name, the directory name is shown.
    * - ``catalog.filename``
      - ``null``
      - The path to the catalog
    * - ``catalog.translate``
      - (see the file)
      - Aliases for catalog column names, as ``name: [alias, ...]``. For example,
        ``id: [ID, NUMBER]`` uses the first of ``ID`` or ``NUMBER`` found in the catalog as the
        ``id`` column. The ``id`` column is required; ``id2``, ``id3``, ... add further ID levels.
    * - ``data.dir``
      - ``null``
      - The directory with the data files
    * - ``data.id_pattern``
      - (see the file)
      - A regular expression that matches the object ID in data file names. If several matches are
        found in a file name, the longest one is used.
    * - ``data.images``
      - ``{}``
      - Images shared by all objects, e.g., large mosaics that widgets cut out from. Each image has
        a label and the keys below.
    * - ``data.images.<label>.filename``
      - ``null``
      - The path to the image
    * - ``data.images.<label>.wcs_source``
      - ``null``
      - The file to read the WCS from, if not the image itself
    * - ``data.images.<label>.loader``
      - ``auto``
      - How to read the image (see ``data.loader`` under ``data_widgets.yml``)
    * - ``data.images.<label>.loader_params``
      - ``{}``
      - Parameters passed to the loader (see ``data.loader_params`` under ``data_widgets.yml``)
    * - ``data.enabled_unit_aliases``
      - (see the file)
      - Non-standard unit names found in data files, as ``unit: [alias, ...]``
        (e.g., ``AA: [ANGSTROMS]``)
    * - ``inspection_results.default_flags``
      - ``[]``
      - The flags added to every new inspection file
    * - ``plugins``
      - (see the file)
      - The enabled plugins. Applied at startup.

.. _data-widgets-reference:

``data_widgets.yml``
^^^^^^^^^^^^^^^^^^^^

The widgets are listed by title under ``images`` and ``plots`` (see :doc:`data-viewer` for
examples).

Keys shared by all widgets
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
    :header-rows: 1
    :widths: auto

    * - Key
      - Default
      - Description
    * - ``visible``
      - ``true``
      - Show the widget
    * - ``position``
      - ``bottom``
      - Where the widget's dock is placed: ``top``, ``bottom``, ``left``, ``right``, ``above``
        or ``below``
    * - ``relative_to``
      - ``null``
      - The title of the widget that ``position`` refers to. Without it, the dock is placed
        relative to the whole data viewer.
    * - ``dock_title_fmt``
      - ``short``
      - The dock title: ``fixed`` (the widget title), ``short`` (the FITS extension name and
        version, if any) or ``long`` (the file name followed by the extension)
    * - ``data``
      -
      - Where the data comes from (see `Data`_)
    * - ``x_axis``, ``y_axis``
      -
      - The axes (see `Axes`_)
    * - ``spectral_lines``
      -
      - The spectral lines (see `Spectral lines`_)
    * - ``smoothing_slider``
      - visible, up to ``3`` in steps of ``0.05``
      - Smooths the data with a Gaussian of the chosen width (see `Sliders`_)
    * - ``redshift_slider``
      - hidden, up to ``10`` in steps of ``1e-6``
      - Moves the spectral lines (see `Sliders`_)

Keys of images
~~~~~~~~~~~~~~

.. list-table::
    :header-rows: 1
    :widths: auto

    * - Key
      - Default
      - Description
    * - ``wcs_transform``
      - ``false``
      - Show the image in sky coordinates, using its WCS
    * - ``rotate``
      - ``null``
      - Rotate the image by this angle in degrees, or by the catalog's ``PA`` column with ``auto``
    * - ``color_bar``
      -
      - The color bar (see `Color bars`_)
    * - ``central_axes.x``, ``central_axes.y``
      - ``false``
      - Draw a horizontal (``x``) or vertical (``y``) line through the center of the image
    * - ``central_crosshair``
      - ``false``
      - Draw a crosshair at the center of the image
    * - ``show_sources``
      - ``false``
      - Mark the catalog sources that fall within the image (needs ``ra`` and ``dec`` columns and a
        WCS). Clicking a source label opens that object.

Keys of plots
~~~~~~~~~~~~~

.. list-table::
    :header-rows: 1
    :widths: auto

    * - Key
      - Default
      - Description
    * - ``plots``
      - ``{}``
      - The lines drawn in the widget, by label
    * - ``plots.<label>.x``, ``plots.<label>.y``
      - (required)
      - The table columns plotted against each other
    * - ``plots.<label>.color``
      - ``null``
      - The line color, as a name (e.g., ``red``) or a hex code (e.g., ``'#ff0000'``)
    * - ``plots.<label>.hide_label``
      - ``false``
      - Leave the line out of the legend

Data
~~~~

.. list-table::
    :header-rows: 1
    :widths: auto

    * - Key
      - Default
      - Description
    * - ``data.filename``
      - ``null``
      - The data file, relative to ``data.dir`` in ``workspace.yml``. Fields in braces are filled
        in for each object: ``{id}`` and any catalog column, with Python format specs
        (e.g., ``'{root}_{id:05d}.1D.fits'``).
    * - ``data.source``
      - ``null``
      - The label of a shared image in ``workspace.yml`` (``data.images``) to cut out from,
        instead of ``data.filename``. The cutout is centered on the object's ``ra`` and ``dec``.
    * - ``data.loader``
      - ``auto``
      - How to read the file: ``generic_fits``, ``rasterio`` or ``pil``. ``auto`` picks one by the
        file extension, and falls back to ``generic_fits``.
    * - ``data.loader_params``
      - ``{}``
      - Parameters passed to the loader. For FITS files: ``extname`` and ``extver``, or ``extname``
        and ``extver_index`` (the n-th extension of that name, starting from 0). For a cutout
        (``data.source``): ``cutout_size``, half the width of the cutout in pixels (``100`` by
        default).

Axes
~~~~

.. list-table::
    :header-rows: 1
    :widths: auto

    * - Key
      - Default
      - Description
    * - ``visible``
      - ``true``
      - Show the axis
    * - ``link_to``
      - ``null``
      - The title of another widget whose axis this one follows when panning and zooming
    * - ``unit``
      - ``null``
      - The unit the data is shown in (e.g., ``micron``). Without it, the data's own unit is used.
    * - ``scale``
      - ``linear``
      - ``linear`` or ``log``
    * - ``label``
      - ``null``
      - The axis label. Without it, plots are labelled with the name of the plotted column.
    * - ``limits.min``, ``limits.max``
      - ``null``
      - The default axis range. Without them, the range of the data is used.

Sliders
~~~~~~~

.. list-table::
    :header-rows: 1
    :widths: auto

    * - Key
      - Default
      - Description
    * - ``visible``
      - (see above)
      - Show the slider
    * - ``link_to``
      - ``null``
      - The title of another widget whose slider of the same kind this one follows
    * - ``min_value``, ``max_value``, ``step``
      - (see above)
      - The slider range and step
    * - ``default_value``
      - ``0``
      - The value the slider starts at
    * - ``catalog_name``
      - ``null``
      - A catalog column to start at instead, e.g., ``redshift``
    * - ``show_text_editor``
      - ``false`` (``true`` for the redshift)
      - Show a field for typing the value
    * - ``n_decimal_places``
      - ``6``
      - The number of decimal places shown in that field
    * - ``show_save_button``
      - ``false`` (``true`` for the redshift)
      - Show a button that saves the value to :guilabel:`Inspection Results` (redshift slider only)

Color bars
~~~~~~~~~~

.. list-table::
    :header-rows: 1
    :widths: auto

    * - Key
      - Default
      - Description
    * - ``visible``
      - ``true``
      - Show the color bar
    * - ``link_to``
      - ``null``
      - The title of another widget whose color bar levels this one follows
    * - ``limits.type``
      - ``minmax``
      - How the levels are set, as in `SAOImage DS9 <https://github.com/SAOImageDS9/SAOImageDS9/>`_:
        ``minmax``, ``zscale`` or ``user``
    * - ``limits.min``, ``limits.max``
      - ``null``
      - The levels for ``user``. A level left out is taken from the data.

Spectral lines
~~~~~~~~~~~~~~

.. list-table::
    :header-rows: 1
    :widths: auto

    * - Key
      - Default
      - Description
    * - ``visible``
      - ``false``
      - Show the lines listed in ``spectral_lines.yml``
    * - ``color``
      - ``null``
      - The line color. Without it, the color depends on the theme.

``layout.yml`` and ``state.yml``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. list-table::
    :header-rows: 1
    :widths: auto

    * - Key
      - File
      - Description
    * - ``dock_layout``
      - ``layout.yml``
      - The arrangement of the data viewer's docks
    * - ``last_inspection_file``
      - ``state.yml``
      - The inspection file opened at startup
    * - ``last_object_index``
      - ``state.yml``
      - The object shown at startup
    * - ``last_subset_file``
      - ``state.yml``
      - The subset being inspected, if any

.. rubric:: Footnotes

.. [#f1] Enabling antialiasing might decrease the GUI responsiveness.
.. [#f2] On Linux, ``$HOME/.config/specvizitor``.
