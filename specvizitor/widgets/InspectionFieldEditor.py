from qtpy import QtCore, QtWidgets

from itertools import repeat
import logging

from ..io.inspection_data import InspectionData
from ..utils.widgets import ParamTable

logger = logging.getLogger(__name__)


def inspection_field_table_factory(review: InspectionData, parent=None) -> ParamTable:
    header = ['Field', 'Type']
    data = list(zip(review.flag_columns, repeat('boolean')))
    item_choices = [None, ('boolean',)]

    reserved_colnames = list(review.indices) + review.default_columns
    regex_pattern = [fr"^({'|'.join(reserved_colnames)}|\s*)$", None]

    is_unique = [True, False]

    return ParamTable(header=header, data=data, name='Inspection Field', item_choices=item_choices,
                      regex_pattern=regex_pattern, is_unique=is_unique, parent=parent)


class InspectionFieldEditor(QtWidgets.QDialog):
    data_requested = QtCore.Signal()
    inspection_fields_updated = QtCore.Signal(list, list, bool)

    def __init__(self, review: InspectionData, parent=None):
        self._review = review
        self._field_table: ParamTable | None = None
        self._set_as_default_checkbox: QtWidgets.QCheckBox | None = None
        self._button_box: QtWidgets.QDialogButtonBox | None = None

        self._new_fields: list[tuple[str, str]] | None = None
        self._is_deleted: list[bool] | None = None

        super().__init__(parent=parent)
        self.setWindowTitle("Edit Inspection Fields")

        self.init_ui()
        self.set_layout()
        self.populate()

    def init_ui(self):
        self._field_table = inspection_field_table_factory(self._review, self)
        self._set_as_default_checkbox = QtWidgets.QCheckBox('Set as default for new inspection files', self)

        self._button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel, self)

        self._button_box.accepted.connect(self.accept)
        self._button_box.rejected.connect(self.reject)

        self.data_requested.connect(self._field_table.collect)
        self._field_table.data_collected.connect(self.save_inspection_fields)

    def set_layout(self):
        self.setLayout(QtWidgets.QVBoxLayout())

    def populate(self):
        self.layout().addWidget(self._field_table)
        self.layout().addWidget(self._set_as_default_checkbox)
        self.layout().addWidget(self._button_box)

    @QtCore.Slot(list, list)
    def save_inspection_fields(self, fields: list[tuple[str, str]], is_deleted: list[bool]):
        self._new_fields = fields
        self._is_deleted = is_deleted

    def accept(self):
        self._new_fields = None
        self._is_deleted = None
        self.data_requested.emit()

        warn_columns = []
        for i, old_name in enumerate(self._review.user_defined_columns):
            if self._is_deleted[i] and self._review.has_data(old_name):
                warn_columns.append(old_name)

        accept = True
        if warn_columns:
            msg_box = QtWidgets.QMessageBox(self)
            ans = msg_box.question(self, '', f"Data in the following column(s) will be deleted: {', '.join(warn_columns)}. "
                                             "Are you sure you want to proceed?", msg_box.Yes | msg_box.No)
            if ans == msg_box.No:
                accept = False

        if accept:
            self.inspection_fields_updated.emit(self._new_fields, self._is_deleted, self._set_as_default_checkbox.isChecked())
            super().accept()
