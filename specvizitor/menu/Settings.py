from platformdirs import user_config_dir, user_cache_dir
from qtpy import QtWidgets

import logging

from ..appdata import AppData
from ..io.catalogue import load_cat, create_cat, cat_browser
from ..io.viewer_data import data_browser
from ..utils.logs import qlog

logger = logging.getLogger(__name__)


class Settings(QtWidgets.QDialog):
    def __init__(self, rd: AppData, parent=None):
        self.rd = rd

        super().__init__(parent)
        self.setWindowTitle("Settings [Beta]")

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(20)

        self._browsers = {
            'data': data_browser(self.rd.config.data.dir, self),
            'cat': cat_browser(self.rd.config.catalogue.filename, self)
        }

        for b in self._browsers.values():
            layout.addWidget(b)

        # add a horizontal separator
        self.separator = QtWidgets.QFrame(self)
        self.separator.setFrameShape(QtWidgets.QFrame.HLine)
        layout.addWidget(self.separator)

        self._info_label = QtWidgets.QLabel(f"GUI Configuration: {user_config_dir('specvizitor')}\n\n"
                                            f"Cache: {user_cache_dir('specvizitor')}", parent=self)
        layout.addWidget(self._info_label)

        # add OK/Cancel buttons
        self._button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel, parent=self)
        layout.addWidget(self._button_box)
        self._button_box.accepted.connect(self.accept)
        self._button_box.rejected.connect(self.reject)

        self.setLayout(layout)

    @qlog
    def validate(self) -> bool:
        for name, b in self._browsers.items():
            if (name == 'data' and not b.is_filled(verbose=True)) or not b.exists(verbose=True):
                return False
        return True

    def accept(self):
        if not self.validate():
            return

        if self._browsers['cat'].is_filled():
            cat = load_cat(self._browsers['cat'].path, translate=self.rd.config.catalogue.translate)
            if not cat:
                return

            self.rd.cat = cat
            self.rd.config.catalogue.filename = self._browsers['cat'].path

        else:
            self.rd.config.catalogue.filename = None
            if self.rd.df is not None:
                self.rd.cat = create_cat(self.rd.df.index.values)

        self.rd.config.data.dir = self._browsers['data'].path
        self.rd.config.save()

        super().accept()
