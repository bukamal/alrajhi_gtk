# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt
try:
    import pyqtgraph as pg
    PG_AVAILABLE = True
except ImportError:
    PG_AVAILABLE = False

class ModernChart(QWidget):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-weight: bold; margin-bottom: 8px;")
        layout.addWidget(self.title_label)
        if PG_AVAILABLE:
            self.plot_widget = pg.PlotWidget()
            self.plot_widget.setBackground('w')
            self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
            layout.addWidget(self.plot_widget)
        else:
            self.plot_widget = QLabel("⚠️ pyqtgraph غير مثبت. قم بتثبيته لعرض الرسوم البيانية.")
            layout.addWidget(self.plot_widget)

    def plot_line(self, x, y, label, color='#3b82f6'):
        if not PG_AVAILABLE:
            self.plot_widget.setText("⚠️ pyqtgraph غير مثبت")
            return
        try:
            if not x or len(x) == 0:
                return
            if isinstance(x[0], str):
                x_numeric = list(range(len(x)))
                self.plot_widget.getAxis('bottom').setTicks([[(i, str(x[i])) for i in range(len(x))]])
            else:
                x_numeric = x
            y_numeric = [float(val) if isinstance(val, (int, float)) else 0 for val in y]
            pen = pg.mkPen(color=color, width=2)
            self.plot_widget.plot(x_numeric, y_numeric, pen=pen, name=label)
        except Exception as e:
            self.plot_widget.clear()
            self.plot_widget.setLabel('bottom', f'خطأ: {str(e)[:50]}')

    def plot_bar(self, x, y, color='#3b82f6'):
        if not PG_AVAILABLE:
            self.plot_widget.setText("⚠️ pyqtgraph غير مثبت")
            return
        try:
            if not x or len(x) == 0:
                return
            if isinstance(x[0], str):
                x_numeric = list(range(len(x)))
                self.plot_widget.getAxis('bottom').setTicks([[(i, str(x[i])) for i in range(len(x))]])
            else:
                x_numeric = x
            y_numeric = [float(val) if isinstance(val, (int, float)) else 0 for val in y]
            bargraph = pg.BarGraphItem(x=x_numeric, height=y_numeric, width=0.8, brush=color)
            self.plot_widget.clear()
            self.plot_widget.addItem(bargraph)
        except Exception as e:
            self.plot_widget.clear()
            self.plot_widget.setLabel('bottom', f'خطأ: {str(e)[:50]}')

    def clear(self):
        if PG_AVAILABLE:
            self.plot_widget.clear()
