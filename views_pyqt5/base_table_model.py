# -*- coding: utf-8 -*-
from PyQt5.QtCore import Qt, QAbstractTableModel, QModelIndex

class BaseTableModel(QAbstractTableModel):
    def __init__(self, data, headers):
        super().__init__()
        self._data = data
        self._headers = headers
        self._row_colors = {}  # تخزين ألوان الخلفية لكل صف

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return len(self._headers)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = index.row()
        col = index.column()
        if role == Qt.DisplayRole:
            try:
                value = self._data[row][col]
                return str(value) if value is not None else ""
            except Exception:
                return ""
        if role == Qt.TextAlignmentRole:
            return Qt.AlignCenter
        if role == Qt.BackgroundRole:
            if row in self._row_colors:
                return self._row_colors[row]
        if hasattr(self, 'custom_data'):
            custom = self.custom_data(index, role)
            if custom is not None:
                return custom
        return None

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if 0 <= section < len(self._headers):
                return self._headers[section]
        return None

    def update_data(self, new_data):
        self.beginResetModel()
        self._data = new_data if new_data is not None else []
        self._row_colors.clear()
        self.endResetModel()

    def set_row_background(self, row, color):
        """تحديد لون خلفية لصف معين"""
        if 0 <= row < self.rowCount():
            self._row_colors[row] = color
            # إعادة رسم الصف
            self.dataChanged.emit(self.index(row, 0), self.index(row, self.columnCount() - 1))

    def clear_row_backgrounds(self):
        """مسح جميع ألوان الخلفية"""
        self._row_colors.clear()
        self.dataChanged.emit(self.index(0, 0), self.index(self.rowCount() - 1, self.columnCount() - 1))
