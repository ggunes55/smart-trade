"""
Candlestick Item - Mum çubukları çizimi
"""

import pyqtgraph as pg
from PyQt5.QtGui import QColor, QBrush
from PyQt5.QtCore import QPointF, QRectF
from .config import THEMES, CURRENT_THEME


class CandlestickItem(pg.GraphicsObject):
    """
    Optimize edilmiş mum çubukları
    - Bollinger Squeeze desteği (sarı mum)
    - Numpy vektörleme
    """

    def __init__(self, data, df=None):
        super().__init__()
        self.data = data
        self.df = df  # DataFrame (squeeze detection için)
        self.picture = None
        self._generate_picture()

    def _generate_picture(self):
        """Mum çubuklarını çiz"""
        self.picture = pg.QtGui.QPicture()
        painter = pg.QtGui.QPainter(self.picture)

        theme = THEMES[CURRENT_THEME]

        # Squeeze detection
        has_squeeze = self.df is not None and "BB_Squeeze" in self.df.columns

        for i in range(len(self.data)):
            o, h, low, c = map(float, self.data[i])
            up = c >= o

            # Bollinger Squeeze kontrolü
            is_squeeze = (
                has_squeeze and i < len(self.df) and self.df["BB_Squeeze"].iloc[i]
            )

            if is_squeeze:
                # Squeeze durumunda sarı renk
                color = QColor("#FFC107")  # Amber/Sarı
            else:
                # Normal renk
                color = QColor(theme["candle_up"] if up else theme["candle_down"])

            # Fitil çiz (high-low)
            painter.setPen(pg.mkPen(color, width=1))
            painter.drawLine(QPointF(i, low), QPointF(i, h))

            # Gövde çiz (open-close)
            painter.setBrush(QBrush(color))
            painter.drawRect(QRectF(i - 0.35, min(o, c), 0.7, abs(c - o) or 0.1))

        painter.end()

    def paint(self, painter, *args):
        """PyQtGraph render"""
        painter.drawPicture(0, 0, self.picture)

    def boundingRect(self):
        """Bounding box"""
        return QRectF(self.picture.boundingRect())

    def setData(self, data, df=None):
        """Veriyi güncelle ve yeniden çiz"""
        self.data = data
        self.df = df
        self._generate_picture()
        self.update()
