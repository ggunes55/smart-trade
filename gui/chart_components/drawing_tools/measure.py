"""
Measure Tool - Ölçüm aracı
"""

import pyqtgraph as pg
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from .base import BaseTool


class MeasureTool(BaseTool):
    """
    İki nokta arası ölçüm aracı
    - Fiyat farkı
    - Yüzde değişim
    - Bar sayısı
    """

    def __init__(self, plot_widget, parent_dialog):
        super().__init__(plot_widget, parent_dialog)
        self.line = None
        self.label = None

    def activate(self):
        """Ölçüm modunu aktifleştir"""
        self.is_active = True
        self.clear()
        self.points = []

        self._connect_mouse_click(self.on_click)

        self._show_info(
            "📏 Ölçüm Modu Aktif",
            "Grafik üzerinde 2 nokta seçin:\n"
            "1. Başlangıç noktası\n"
            "2. Bitiş noktası\n\n"
            "Ölçüm otomatik hesaplanacak.",
        )

    def on_click(self, evt):
        """Mouse tıklama olayını yakala"""
        if not self.is_active:
            return

        click_event = evt[0]
        if click_event.button() == Qt.LeftButton:
            pos = click_event.scenePos()
            mouse_pos = self._get_mouse_position(pos)

            if mouse_pos:
                x, y = mouse_pos
                self.points.append((x, y))

                if len(self.points) == 2:
                    self.draw(
                        self.points[0][0],
                        self.points[0][1],
                        self.points[1][0],
                        self.points[1][1],
                    )
                    self.deactivate()

    def clear(self):
        """Ölçüm çizimlerini temizle"""
        if self.line:
            try:
                self.plot.removeItem(self.line)
            except Exception:
                pass
            self.line = None

        if self.label:
            try:
                self.plot.removeItem(self.label)
            except Exception:
                pass
            self.label = None

        self.points = []

    def draw(self, x1, y1, x2, y2):
        """İki nokta arası ölçüm çiz"""
        self.clear()

        # Çizgi
        self.line = pg.PlotDataItem(
            [x1, x2], [y1, y2], pen=pg.mkPen("#FF5722", width=3, style=Qt.SolidLine)
        )
        self._add_item(self.line)

        # Hesaplamalar
        price_diff = abs(y2 - y1)
        percent_change = (price_diff / min(y1, y2)) * 100
        bar_count = abs(int(x2 - x1))

        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2

        # Etiket
        text = "📏 ÖLÇÜM\n"
        text += f"Fiyat Farkı: {price_diff:.2f}\n"
        text += f"Değişim: {percent_change:.2f}%\n"
        text += f"Bar: {bar_count}"

        self.label = pg.TextItem(
            text=text,
            anchor=(0.5, 0.5),
            color="k",
            fill=pg.mkBrush(255, 152, 0, 220),
            border=pg.mkPen("#FF5722", width=3),
        )
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        self.label.setFont(font)
        self.label.setPos(mid_x, mid_y)
        self._add_item(self.label)
