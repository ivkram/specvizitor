Getting started
===============

Installation
++++++++++++

.. important::

      Python **>=3.10** is required to run specvizitor. If you have an older version of Python installed in your system, you can use `conda <https://docs.conda.io/en/latest/>`_ to create a virtual environment with Python version 3.10+ (if you are looking for a minimal conda installer, check out `miniforge <https://github.com/conda-forge/miniforge>`_).

Install the latest version of specvizitor using :pypi:`pip`:

.. code-block:: sh

      pip install specvizitor

If you wish to install specvizitor from source, refer to the :doc:`development/installing-from-source` section.

Basic usage
+++++++++++

.. important::

    This tutorial shows how to inspect `Grizli <https://github.com/gbrammer/grizli>`_ data products. Instructions on how to inspect other kinds of spectroscopic datasets in specvizitor can be found in the :doc:`userguide/index`.

In this demo, we will be using data from the JWST Cycle 2 program "`ALT <https://ui.adsabs.harvard.edu/abs/2024arXiv241001874N/abstract>`_", reduced using the `Grizli <https://github.com/gbrammer/grizli>`_ tool.

#. Download the data as a ZIP file from `here <https://seafile.ist.ac.at/d/1409d984220043f5bcc7/>`_ (total size: 25.5 MB).

#. Unzip the archive and navigate to the directory to which the files have been extracted:

   .. code-block:: sh

      unzip specvizitor_demo.zip
      cd specvizitor_demo

#. Start specvizitor:

   .. code-block:: sh

      specvizitor

#. Navigate to :menuselection:`File --> New...`. Optionally give a name to the project (``demo.csv`` in this tutorial) and specify the path to the catalog - the ``catalog.fits`` file in the ``specvizitor_demo`` directory:

   .. figure:: screenshots/demo1.png

   Click :guilabel:`OK`. You should now see the Grizli data products created for the first of the three galaxies included in this demo:

   .. figure:: screenshots/demo2.png

   Here is the description of what is shown in the data viewer:

   - **Top row, left to right:** an image cutout in the F356W filter (i.e., the filter used in the NIRCam/grism observations), a series of emission line maps, and a redshift probability distribution function (z-PDF);
   - **Middle row:** a 2D grism spectrum;
   - **Bottom row:** a 1D grism spectrum.

#. This galaxy was correctly identified by Grizli as an OIII-emitter at z ≈ 5.76 (you can see this on the right under :guilabel:`Object Information`). Save the redshift by pressing :kbd:`Ctrl+S` or by clicking :guilabel:`Save!` next to the redshift slider. The saved value will appear in :guilabel:`Inspection Results`:

   .. figure:: screenshots/demo3.png

#. Go to the next object by pressing :kbd:`→`:

   .. figure:: screenshots/demo4.png

#. This object has an unphysical redshift value of ``-1.0`` stored in the catalog, which means that spectrum fitting failed. Find the redshift that best describes the data by interacting with the slider at the bottom of the window:

   .. figure:: screenshots/demo5.gif

   This galaxy is likely to be an SIII-emitter at z ≈ 2.68!

#. Save the redshift of the second object (see step 5).

#. Go to the last object by pressing :kbd:`→` one more time:

   .. figure:: screenshots/demo6.png

   The 2D spectrum shows just one emission line which prevents us from unambiguously identifying the redshift of this object. However, we can see that Grizli suggests that this is an Halpha-emitter at z ≈ 4.31, which seems plausible considering the compactness of the source.

#. Save the redshift of the last object and close the window.

#. Finally, check the contents of the output file (also known as the *inspection file*):

   .. csv-table:: demo.csv

      id,starred,z_sviz,comment
      16605,False,5.760862,
      26932,False,2.677225,
      34927,False,4.307806,

   As you can see, the redshifts were saved to the ``z_sviz`` column.


Congratulations on completing this tutorial! If you want to learn more about specvizitor, navigate to the :doc:`userguide/index` section.

Updating specvizitor
++++++++++++++++++++

To update specvizitor to the latest version, run the following command:

.. code-block:: sh

   pip install specvizitor -U


.. tip::

        If you see error messages after installing the update, try to run specvizitor with the ``--purge`` option: ``specvizitor --purge``. Note that this action will erase application settings, including any custom widget configurations. If the issue still persists, refer to the :doc:`userguide/troubleshooting` section.
