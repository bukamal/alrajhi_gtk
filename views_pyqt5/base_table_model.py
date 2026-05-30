# views_pyqt5/base_table_model.py
# -*- coding: utf-8 -*-
from PyQt5.QtCore import Qt, QAbstractTableModel, QModelIndex
from typing import List, Any, Dict, Optional

class BaseTableModel(QAbstractTableModel):
    def __init__(self, data: List[List[Any]], headers: List[str]):
        super().__init__()
        self._data = data
        self._headers = headers
        self._row_colors = {}

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._data)

    def columnCount(self, parent=QModelIndex()) -> int:
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
        if role == Qt.BackgroundRole and row in self._row_colors:
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

    def update_data(self, new_data: List[List[Any]]):
        self.beginResetModel()
        self._data = new_data if new_data is not None else []
        self._row_colors.clear()
        self.endResetModel()

    def update_row(self, row: int, new_row_data: List[Any]):
        if 0 <= row < len(self._data):
            self._data[row] = new_row_data
            self.dataChanged.emit(self.index(row, 0), self.index(row, self.columnCount() - 1))

    def insert_row(self, row: int, row_data: List[Any]):
        self.beginInsertRows(QModelIndex(), row, row)
        self._data.insert(row, row_data)
        self.endInsertRows()

    def remove_row(self, row: int):
        if 0 <= row < len(self._data):
            self.beginRemoveRows(QModelIndex(), row, row)
            self._data.pop(row)
            self.endRemoveRows()

    def set_row_background(self, row, color):
        if 0 <= row < self.rowCount():
            self._row_colors[row] = color
            self.dataChanged.emit(self.index(row, 0), self.index(row, self.columnCount() - 1))

    def clear_row_backgrounds(self):
        self._row_colors.clear()
        self.dataChanged.emit(self.index(0, 0), self.index(self.rowCount() - 1, self.columnCount() - 1))
