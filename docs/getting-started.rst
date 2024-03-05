Getting started
===============

Installation
++++++++++++

.. important::

      Python >=\ **3.10** is required to run specvizitor. If you have an older version of Python installed in your system, consider using `conda <https://conda.io/projects/conda/en/latest/user-guide/getting-started.html>`_.

Install the latest version of specvizitor using :pypi:`pip`::

      pip install specvizitor

If you wish to install specvizitor from source, refer to the :doc:`development/installing-from-source` section.

Basic usage
+++++++++++

Start the application::

      specvizitor

Updating specvizitor
++++++++++++++++++++

To update specvizitor to the latest version, run the following command::

        pip install specvizitor -U


.. tip::

        If you see error messages after installing the update, try to run specvizitor with the ``--purge`` option: ``specvizitor --purge``. Note, however, that this action will completely erase application settings, including custom widget configurations. If "purging" specvizitor does not help, refer to the :doc:`userguide/troubleshooting` section.
