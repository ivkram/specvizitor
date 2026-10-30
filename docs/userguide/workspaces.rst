Workspaces
==========

A **workspace** is a directory that holds the settings of one project: the data and catalog
paths, the data viewer configuration, the active plugins, and more. Your own preferences (e.g.,
the list of spectral lines) are not part of a workspace and apply to all of them.

All workspace commands are in the :guilabel:`File` menu.

Switching workspaces
++++++++++++++++++++

:menuselection:`File --> Recent Workspaces` lists the known workspaces, most recently used first.
Select one to switch to it. The active workspace is checked in the list and shown in the window
title. Switching restarts the application.

A workspace that cannot be found is marked ``(unavailable)``. Click it to remove it from the list
or to keep it, for example while a network share is offline.

Creating a workspace
++++++++++++++++++++

Navigate to :menuselection:`File --> New Workspace...`, then enter a name and a location. The new
workspace starts from the default configuration.

To open a workspace that is not in the list, use :menuselection:`File --> Open...` and select the
``workspace.yml`` file in its directory, or launch specvizitor with::

    specvizitor --workspace /path/to/workspace

Renaming a workspace
^^^^^^^^^^^^^^^^^^^^

Navigate to :menuselection:`File --> Rename Workspace...`. Only the name changes, not the
directory. Workspace names must be unique.

Cloning a workspace
^^^^^^^^^^^^^^^^^^^

Navigate to :menuselection:`File --> Clone Workspace...` to copy the current workspace under a
new name, then switch to the copy. The clone keeps everything, including the data paths and the
open inspection file.

.. important::

    The clone and the original save to the *same* inspection file. To keep separate results,
    create a new inspection file in the clone (:menuselection:`File --> New...`).

Removing a workspace
^^^^^^^^^^^^^^^^^^^^

Delete the workspace directory with your file manager, then click its ``(unavailable)`` entry in
:menuselection:`File --> Recent Workspaces` and choose :guilabel:`Forget Workspace`. Inspection
files **that are stored outside the workspace directory** are not affected.

What is in a workspace
++++++++++++++++++++++

.. list-table::
    :header-rows: 1
    :widths: auto

    * - File
      - Contents
    * - ``workspace.yml``
      - Data and catalog paths, active plugins, etc.
    * - ``data_widgets.yml``
      - Data viewer configuration (see :doc:`data-viewer`)
    * - ``layout.yml``
      - Window layout
    * - ``state.yml``
      - The inspection file you had open, and your position in it

The path to the workspace directory is shown at the bottom of :guilabel:`Settings`; click it to
open the directory in your file manager.

Sharing a workspace
+++++++++++++++++++

Exporting
^^^^^^^^^

Navigate to :menuselection:`File --> Export Workspace...`, choose what to include and where to
save the ``.sviz`` archive:

.. list-table::
    :header-rows: 1
    :widths: auto

    * - Option
      - Default
    * - Data viewer configuration
      - On
    * - Window layout
      - On
    * - Inspection results
      - Off
    * - This machine's data paths
      - Off

The data, catalog and image paths are left out of the archive unless you include this machine's
data paths, which is only useful when the recipient has the data at the same location. The
image labels are kept, so the data viewer configuration still applies.

Importing
^^^^^^^^^

Navigate to :menuselection:`File --> Open...`, select the ``.sviz`` file, then enter a name and a
location for the new workspace. If the archive contains inspection results, they are opened in the
new workspace.

After the import, specvizitor asks for any data, catalog and image paths that are not set. Leave a
field blank to set it later in :menuselection:`Tools --> Settings`.

Upgrading from an earlier version
+++++++++++++++++++++++++++++++++

On the first launch of this version, the project settings are moved into a workspace named
"Default", along with the widget configuration, the layout and the last open object. The original
files are kept with a ``.pre-workspace`` suffix (for example ``config.pre-workspace.yml``).
