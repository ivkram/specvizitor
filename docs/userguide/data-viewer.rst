Data Viewer
===========

.. note::

    This section assumes that the reader is already familiar with :doc:`app-settings`.

By default, the data viewer in specvizitor is configured to display the `Grizli <https://github.com/gbrammer/grizli>`_ data products. Specifically, it displays the data stored in the following files:

.. list-table::
    :header-rows: 1
    :widths: auto

    * - File
      - Description
    * - ``*1D.fits``
      - 1D spectrum
    * - ``*stack.fits``
      - 2D stacked spectrum of all exposures
    * - ``*full.fits``
      - Various extraction products including emission line maps and image cutouts

In this section, you will learn how to change the viewer configuration by modifying the ``data_widgets.yml`` file.

Configuring the defaults
++++++++++++++++++++++++

Let us start with some examples of how you can configure the default data widgets.

Changing the maximum redshift
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In the ``data_widgets.yml`` file, navigate to ``plots`` ‣ ``Spectrum 1D`` ‣ ``redshift_slider`` ‣ ``max_value``::

      ...
      plots:
        Spectrum 1D:
          ...
          redshift_slider:
            ...
            max_value: 10

Set ``max_value`` to any redshift you think would suffice to classify even the most distant objects included in your sample. Next, make the same changes to the redshift slider under ``images`` ‣ ``Spectrum 2D``::

      images:
        ...
        Spectrum 2D:
          ...
          redshift_slider:
            ...
            max_value: 10

This is required because :guilabel:`Spectrum 1D` and :guilabel:`Spectrum 2D` share the same redshift. Once you have made the changes, save ``data_widgets.yml`` and launch specvizitor. The maximum value of the redshift slider should be updated accordingly.

Changing the colorbar range
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note::

    This example demonstrates how to change the colorbar range of :guilabel:`Spectrum 2D`, however the same can be applied to any widget in the ``images`` category.

In the ``data_widgets.yml`` file, navigate to ``images`` ‣ ``Spectrum 2D`` ‣ ``color_bar`` ‣ ``limits``::

      images:
        ...
        Spectrum 2D:
          ...
          color_bar:
            ...
            limits:
              min: -0.015
              max: 0.015
              type: user

Here, you can set the ``min`` and ``max`` parameters of the colorbar. Once you have made the changes, save ``data_widgets.yml`` and launch specvizitor. The colorbar range in :guilabel:`Spectrum 2D` should be updated accordingly.

Hiding widget elements
^^^^^^^^^^^^^^^^^^^^^^

.. note::

    This example demonstrates how to change the visibility of plot axes, however the same can be applied to colorbars, sliders, spectral lines, and widgets themselves.

.. tip::

    You can hide most of the widget elements by pressing :kbd:`H` (this will not affect the visibility of redshift sliders).

In the ``data_widgets.yml`` file, navigate to ``images`` ‣ ``Spectrum 2D`` ‣ ``x_axis`` ‣ ``visible``::

      images:
        ...
        Spectrum 2D:
          ...
          x_axis:
            visible: true

Set ``visible`` to ``false``, save ``data_widgets.yml`` and launch specvizitor. The :guilabel:`Spectrum 2D`'s x-axis will disappear from the view.

Adding new widgets
++++++++++++++++++

TBU