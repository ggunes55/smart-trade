"""
Shapes Tool - Yatay çizgi, Kanal, Dikdörtgen
"""

import pyqtgraph as pg
from PyQt5.QtCore import Qt
from .base import BaseTool


class HorizontalLineTool(BaseTool):
    """
    Yatay çizgi aracı
    - Hareket ettirilebilir
    - Destek/Direnç seviyeleri için ideal
    """

    def __init__(self, plot_widget, parent_dialog):
        super().__init__(plot_widget, parent_dialog)
        self.lines = []

    def activate(self):
        """Yatay çizgi modunu aktifleştir"""
        self.is_active = True
        self._connect_mouse_click(self.on_click)

        self._show_info(
            "📊 Yatay Çizgi",
            "Grafik üzerinde bir fiyat seviyesi seçin.\n\n"
            "✨ Çizgi oluştuktan sonra sürükleyip hareket ettirebilirsiniz.",
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

                # Hareket ettirilebilir çizgi
                line = pg.InfiniteLine(
                    angle=0,
                    pos=y,
                    movable=True,  # ✨ Hareket ettirilebilir
                    pen=pg.mkPen("#2196F3", width=2, style=Qt.DashLine),
                )
                self._add_item(line)
                self.lines.append(line)

                self.deactivate()

    def clear_all(self):
        """Tüm yatay çizgileri sil"""
        for line in self.lines:
            try:
                self.plot.removeItem(line)
            except Exception:
                pass
        self.lines = []
        self.items = []


class ChannelTool(BaseTool):
    """
    Paralel kanal çizgi aracı
    - 3 nokta ile kanal oluştur
    - Trend kanalları için
    """

    def __init__(self, plot_widget, parent_dialog):
        super().__init__(plot_widget, parent_dialog)
        self.channels = []

    def activate(self):
        """Kanal çizgi modunu aktifleştir"""
        self.is_active = True
        self.points = []
        self._connect_mouse_click(self.on_click)

        self._show_info(
            "📉 Kanal Çizgisi",
            "3 nokta seçin:\n"
            "1. Trend başlangıcı\n"
            "2. Trend sonu\n"
            "3. Kanal genişliği",
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

                if len(self.points) == 3:
                    self.draw_channel()
                    self.deactivate()

    def draw_channel(self):
        """Paralel kanal çiz"""
        x1, y1 = self.points[0]
        x2, y2 = self.points[1]
        x3, y3 = self.points[2]

        # Ana trend çizgisi
        line1 = pg.PlotDataItem([x1, x2], [y1, y2], pen=pg.mkPen("#2196F3", width=2))
        self._add_item(line1)

        # Paralel çizgi hesapla
        offset = y3 - ((y2 - y1) / (x2 - x1) * (x3 - x1) + y1)
        y1_parallel = y1 + offset
        y2_parallel = y2 + offset

        line2 = pg.PlotDataItem(
            [x1, x2], [y1_parallel, y2_parallel], pen=pg.mkPen("#2196F3", width=2)
        )
        self._add_item(line2)

        self.channels.append((line1, line2))

    def clear_all(self):
        """Tüm kanalları sil"""
        for line1, line2 in self.channels:
            try:
                self.plot.removeItem(line1)
                self.plot.removeItem(line2)
            except Exception:
                pass
        self.channels = []
        self.items = []


class RectangleTool(BaseTool):
    """
    Dikdörtgen çizim aracı
    - 2 nokta ile kutu oluştur
    - Destek/Direnç bölgeleri için
    """

    def __init__(self, plot_widget, parent_dialog):
        super().__init__(plot_widget, parent_dialog)
        self.rectangles = []

    def activate(self):
        """Dikdörtgen modunu aktifleştir"""
        self.is_active = True
        self.points = []
        self._connect_mouse_click(self.on_click)

        self._show_info("▭ Dikdörtgen", "2 nokta seçin (köşegen köşeler)")

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
                    self.draw_rectangle()
                    self.deactivate()

    def draw_rectangle(self):
        """Dikdörtgen çiz"""
        x1, y1 = self.points[0]
        x2, y2 = self.points[1]

        rect = pg.QtWidgets.QGraphicsRectItem(
            min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1)
        )
        rect.setPen(pg.mkPen("#FF9800", width=2))
        rect.setBrush(pg.mkBrush(255, 152, 0, 30))

        self._add_item(rect)
        self.rectangles.append(rect)

    def clear_all(self):
        """Tüm dikdörtgenleri sil"""
        for rect in self.rectangles:
            try:
                self.plot.removeItem(rect)
            except Exception:
                pass
        self.rectangles = []
        self.items = []
