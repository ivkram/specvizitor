Troubleshooting
===============

Specvizitor won't launch
++++++++++++++++++++++++

If you run specvizitor for the first time, you might encounter the following error::

        ...
        TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'

This means that you are using an older version of Python than the version required to run specvizitor (3.10 and higher). You can install Python 3.10+ using `conda <https://docs.conda.io/en/latest/>`_, for example.

Widget(s) disappeared from the GUI
++++++++++++++++++++++++++++++++++

If a sidebar widget (e.g., :guilabel:`Object Information`) has disappeared from the GUI and you want to bring it back, navigate to :menuselection:`View --> Docks` and click on the widget's name.

What to do if none of the above helped
++++++++++++++++++++++++++++++++++++++

1. Check the console output - error messages can help you to pinpoint the exact source of the problem.

2. `Update specvizitor <../getting-started.html#updating-specvizitor>`__ - some bugs might have been fixed in the latest version.

3. Reset specvizitor to its initial state::

        >> specvizitor --purge

.. warning::

        Running specvizitor with the ``--purge`` option will reset all application settings.

.. note::

        Running specvizitor with the ``--purge`` option will NOT affect any inspection files (``*.csv``).

4. `Open issue on GitHub <https://github.com/ivkram/specvizitor/issues/new>`_.

