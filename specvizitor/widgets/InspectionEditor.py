from qtpy import QtCore, QtWidgets

from itertools import repeat
import logging

from ..io.inspection_data import InspectionData
from ..utils.widgets.ParamTable import ParamTable

logger = logging.getLogger(__name__)


def inspection_field_table_factory(review: InspectionData, parent=None) -> ParamTable:
    header = ['Field', 'Type']
    data = list(zip(review.flag_columns, repeat('boolean')))

    return ParamTable(header=header, data=data, name='Inspection Field', item_choices=[None, ('boolean',)],
                      parent=parent)


class InspectionEditor(QtWidgets.QDialog):
    changes_accepted = QtCore.Signal()
    inspection_fields_updated = QtCore.Signal(list, list)

    def __init__(self, review: InspectionData, parent=None):
        self._review = review
        self._field_table: ParamTable | None = None
        self._button_box: QtWidgets.QDialogButtonBox | None = None

        super().__init__(parent=parent)
        self.setWindowTitle("Edit Inspection File")

        self.init_ui()
        self.set_layout()
        self.populate()

    def init_ui(self):
        self._field_table = inspection_field_table_factory(self._review, self)

        self._button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel, self)

        self._button_box.accepted.connect(self.accept)
        self._button_box.rejected.connect(self.reject)

        self.changes_accepted.connect(self._field_table.collect)
        self._field_table.table_changed.connect(self.inspection_fields_updated.emit)

    def set_layout(self):
        self.setLayout(QtWidgets.QVBoxLayout())

    def populate(self):
        self.layout().addWidget(self._field_table)
        self.layout().addWidget(self._button_box)

    def accept(self):
        self.changes_accepted.emit()
        super().accept()
