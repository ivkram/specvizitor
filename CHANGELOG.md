# Changelog

## [0.8.0] - Unreleased

### Upgrading

- specvizitor now runs on Qt6: PyQt6 replaces PyQt5, which can be uninstalled, and pyqtgraph 0.14+
  is required.
- On Linux with X11, Qt6 needs `libxcb-cursor0` (`xcb-util-cursor` on some distributions).

### Added

- Support for PySide6 (set `QT_API=pyside6`).
- Support for Python 3.15.

### Changed

- On Wayland, specvizitor runs natively, except on GNOME, where it keeps using XWayland for a
  sharper title bar (set `QT_QPA_PLATFORM=wayland` to override).
- Switching objects during a load is more responsive.
- Star icons are magenta.

### Fixed

- A crash when restoring the viewer configuration during a load.

### Removed

- Support for Python 3.10 and Qt5.

## [0.7.1] - 2026-10-31

### Upgrading

- On the first launch, every configuration file is upgraded once to the new format (see *Changed*).
  The original files are kept next to them as `*.yml.bak`, except `layout.yml` and `state.yml`.
- The `catalogue` section of `workspace.yml` is renamed to `catalog`, and the plugins are renamed
  from `sviz-grizli` to `sviz_grizli` and from `sviz-eiger` to `sviz_allegro`. Existing workspaces
  are migrated automatically.

### Added

- Export the inspection results to CSV, in addition to FITS
  (`File → Export Inspection Results...`, previously `File → Export FITS Table...`).
- A configuration reference in the documentation, which lists every key of every configuration
  file.
- Opening a workspace whose name is already taken asks for a new name, instead of refusing.
- The inspection field editor lists every field of the inspection file with its type, not only
  the flags.

### Changed

- Configuration files are only written when something changes. Opening specvizitor no longer
  rewrites a file edited by hand, so its comments and formatting are kept.
- Unknown keys in a configuration file, such as a typo, are reported with their full path and
  ignored, instead of being dropped silently.
- An invalid configuration file is reported with the key at fault, and reset to the default values
  with a `*.yml.bak` backup. `layout.yml` and `state.yml` are reset without a backup.
- Configuration files record a `schema_version` instead of the version of specvizitor that wrote
  them. A file written by a newer version is read but never overwritten.
- The inspection file, the configuration files, the exports and the workspace archives are written
  atomically: a failed save leaves the previous file intact.
- Creating, cloning, importing, renaming and exporting a workspace report errors while the dialog
  is still open, so nothing typed is lost.

### Fixed

- Errors from loading an object no longer pop up after `File → Open...`; they are logged to the
  console, as for every other object.
- A failed save of the inspection file or of an export is reported as an error.
- Spectral lines are placed using the unit set in `spectral_lines.yml`, instead of always assuming
  Å.
- The inspection field editor could rename or delete the wrong field when the inspection file has
  fields other than flags, and two fields could not swap their names.
- Long labels in the dialogs that add or edit a table row in `Settings`, such as "Wavelength (Å)",
  were cut off.
- Comments that look like numbers are read back as text.
- A crash when switching workspaces or restarting the application.
- Images rotated by 90 or 270 degrees (`rotate` in `data_widgets.yml`) failed to load.
- Objects were looked up in the wrong column after changing the alias of the `id` column in
  `Settings`.
- A missing FITS extension (`extname`, `extver_index`) is reported as such, instead of an internal
  error.
- An unknown `loader` in `data_widgets.yml` is reported instead of crashing.

### Removed

- The unused `repr` key of `spectral_lines.yml`.

[0.7.2]: https://github.com/ivkram/specvizitor/compare/v0.7.1...HEAD
[0.7.1]: https://github.com/ivkram/specvizitor/compare/v0.7.0...v0.7.1
