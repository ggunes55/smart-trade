"""
Trend Line Tool - Trend çizgisi aracı
"""

import pyqtgraph as pg
from PyQt5.QtCore import Qt
from .base import BaseTool


class TrendLineTool(BaseTool):
    """
    Trend çizgisi aracı
    - 2 nokta ile trend çiz
    - Yeşil = Yükseliş, Kırmızı = Düşüş
    - Hareket ettirilebilir noktalar
    """

    def __init__(self, plot_widget, parent_dialog):
        super().__init__(plot_widget, parent_dialog)
        self.lines = []

    def activate(self):
        """Trend çizgisi modunu aktifleştir"""
        self.is_active = True
        self.points = []

        self._connect_mouse_click(self.on_click)

        self._show_info(
            "📈 Trend Çizgisi Modu",
            "Grafik üzerinde 2 nokta seçin:\n"
            "1. Başlangıç noktası\n"
            "2. Bitiş noktası\n\n"
            "Trend çizgisi oluşturulacak.\n"
            "Yeşil = Yükseliş, Kırmızı = Düşüş\n\n"
            "✨ Oluştuktan sonra noktaları sürükleyebilirsiniz.",
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

                if len(self.points) == 1:
                    # Hareket ettirilebilir marker
                    marker = pg.ScatterPlotItem(
                        x=[x],
                        y=[y],
                        size=10,
                        pen=pg.mkPen(None),
                        brush=pg.mkBrush(33, 150, 243, 200),
                        symbol="o",
                    )
                    self._add_item(marker)

                elif len(self.points) == 2:
                    x1, y1 = self.points[0]
                    x2, y2 = self.points[1]

                    # Renk belirleme
                    color = "#4CAF50" if y2 > y1 else "#F44336"

                    self.add_line(x1, y1, x2, y2, color)
                    self.deactivate()

    def add_line(self, x1, y1, x2, y2, color="#2196F3"):
        """Trend çizgisi ekle"""
        line = pg.PlotDataItem([x1, x2], [y1, y2], pen=pg.mkPen(color, width=3))
        self._add_item(line)
        self.lines.append(line)
        return line

    def clear_all(self):
        """Tüm trend çizgilerini sil"""
        self.clear()
        self.lines = []

    def remove_last(self):
        """Son trend çizgisini sil"""
        if self.lines:
            line = self.lines.pop()
            try:
                self.plot.removeItem(line)
                if line in self.items:
                    self.items.remove(line)
            except Exception:
                pass
