Getting started
===============

Installation
++++++++++++

.. important::

      Python **>=3.10, <3.12** is required to run specvizitor. If you have an older version of Python installed in your system, you can use `conda <https://conda.io/projects/conda/en/latest/user-guide/getting-started.html>`_ to create a virtual environment with Python version 3.10+.

Install the latest version of specvizitor using :pypi:`pip`::

      >> pip install specvizitor

If you wish to install specvizitor from source, refer to the :doc:`development/installing-from-source` section.

Basic usage
+++++++++++

.. important::

    This tutorial shows how to do inspections of `Grizli <https://github.com/gbrammer/grizli>`_ data products. Detailed instructions on how to inspect other types of spectroscopic datasets in specvizitor can be found in the :doc:`userguide/index`.

In this demo, we will be using data produced by `Grizli <https://github.com/gbrammer/grizli>`_ for the JWST Cycle 2 program "`ALT <https://www.stsci.edu/jwst/phase2-public/3516.pdf>`_".

#. Download the data as a ZIP file from `here <https://seafile.ist.ac.at/d/1409d984220043f5bcc7/>`_ (total size: 25.5 MB).

#. Unzip the archive and navigate to the directory where the files have been extracted to::

      >> unzip specvizitor_0.4.x_demo.zip
      >> cd specvizitor_0.4.x_demo

#. Start specvizitor::

      >> specvizitor

#. Navigate to :menuselection:`File --> New...` and select :guilabel:`Create a new catalog`:

   .. figure:: screenshots/demo1.png

   Click :guilabel:`OK`. You should now see the data produced by Grizli for the first out of three galaxies included in this demo:

   .. figure:: screenshots/demo2.png

   Below is the description of what is shown in the data viewer.

   - **Top row, left to right:** an image cutout in the F356W filter (the filter used in the NIRCam/grism observations), a series of emission line maps, and a redshift probability distribution function (z-PDF);
   - **Middle row:** a stacked 2D spectrum of all exposures;
   - **Bottom row:** a 1D spectrum.

#. Find the redshift that best describes the data by interacting with the slider at the bottom of the window:

   .. figure:: screenshots/demo3.gif

   This galaxy is an OIII-emitter at z ≈ 5.75!

#. Save the redshift by pressing :kbd:`Ctrl+S` or by clicking :guilabel:`Save!` next to the redshift slider. The saved value should appear in :guilabel:`Inspection Results`:

   .. figure:: screenshots/demo4.png

#. Go to the next object by pressing :kbd:`→` and repeat steps 5 & 6:

   .. figure:: screenshots/demo5.png

   This galaxy is most likely a SIII-emitter at z ≈ 2.67.

#. Go to the last object by pressing :kbd:`→` one more time:

   .. figure:: screenshots/demo6.png

   The 2D spectrum shows only a single emission line, therefore we cannot classify this galaxy. However, we can load a catalog to check the redshift suggested by Grizli (see the next step).

#. Navigate to :menuselection:`Tools --> Settings --> Catalogue` and specify the path to the catalog that was shared together with other data files (``catalog.fits``):

   .. figure:: screenshots/demo7.png

   Click :guilabel:`OK`. We can see that Grizli suggests that this galaxy is an Halpha-emitter at z ≈ 4.31, which seems very plausible:

   .. figure:: screenshots/demo8.png

#. Save the redshift of the final object and close the window.

#. Finally, check the contents of the output file (also known as the *inspection file*) created by specvizitor::

    >> cat Untitled.csv
    id,starred,z_sviz,comment
    16605,False,5.757807,
    26932,False,2.672491,
    34927,False,-1.0,

   Here, ``id`` is the ID of the object, and ``z_sviz`` is the redshift saved in :guilabel:`Inspection Results`.


Congratulations on completing the tutorial! If you want to learn more about specvizitor, navigate to the :doc:`userguide/index` section.

Updating specvizitor
++++++++++++++++++++

To update specvizitor to the latest version, run the following command::

        >> pip install specvizitor -U


.. tip::

        If you see error messages after installing the update, try to run specvizitor with the ``--purge`` option: ``specvizitor --purge``. Note, however, that this action will completely erase application settings, including custom widget configurations. If "purging" specvizitor does not help, refer to the :doc:`userguide/troubleshooting` section.
