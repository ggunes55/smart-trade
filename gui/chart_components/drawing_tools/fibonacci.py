"""
Fibonacci Tool - Fibonacci Retracement & Extension
"""

import pyqtgraph as pg
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from .base import BaseTool
from ..config import (
    FIBONACCI_RETRACEMENT_LEVELS,
    FIBONACCI_RETRACEMENT_COLORS,
    FIBONACCI_RETRACEMENT_NAMES,
    FIBONACCI_EXTENSION_LEVELS,
    FIBONACCI_EXTENSION_COLORS,
    FIBONACCI_EXTENSION_NAMES,
)


class FibonacciTool(BaseTool):
    """
    Fibonacci Retracement & Extension aracı
    - Retracement: 0%, 23.6%, 38.2%, 50%, 61.8%, 78.6%, 100%
    - Extension: 0%, 61.8%, 100%, 127.2%, 161.8%, 200%, 261.8%
    """

    def __init__(self, plot_widget, parent_dialog):
        super().__init__(plot_widget, parent_dialog)
        self.lines = []
        self.labels = []
        self.mode = "retracement"  # 'retracement' veya 'extension'

    def set_mode(self, mode: str):
        """Fibonacci modunu ayarla"""
        self.mode = mode

    def activate(self, mode="retracement"):
        """Manuel Fibonacci modunu aktifleştir"""
        self.mode = mode
        self.is_active = True
        self.points = []
        self.clear()

        self._connect_mouse_click(self.on_click)

        mode_text = (
            "GERİ ÇEKİLİŞ (Retracement)"
            if mode == "retracement"
            else "UZATMA (Extension)"
        )

        if mode == "retracement":
            self._show_info(
                "📊 Fibonacci Geri Çekiliş",
                f"📊 Mod: {mode_text}\n\n"
                "Grafik üzerinde 2 nokta seçin:\n\n"
                "1️⃣ Trend BAŞLANGICI (düşük/yüksek)\n"
                "2️⃣ Trend SONU (yüksek/düşük)\n\n"
                "🔹 Yükseliş trendi: Düşük → Yüksek\n"
                "🔻 Düşüş trendi: Yüksek → Düşük\n\n"
                "Fibonacci geri çekiliş seviyeleri otomatik hesaplanacak.",
            )
        else:
            self._show_info(
                "📊 Fibonacci Uzatma",
                f"📊 Mod: {mode_text}\n\n"
                "Grafik üzerinde 3 nokta seçin:\n\n"
                "1️⃣ Trend BAŞLANGICI\n"
                "2️⃣ Trend SONU (geri çekilme öncesi)\n"
                "3️⃣ GERİ ÇEKİLME SONU (yeni pivot)\n\n"
                "Fibonacci uzatma (extension) seviyeleri hesaplanacak.",
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

                # İşaretçi ekle
                marker = pg.ScatterPlotItem(
                    x=[x],
                    y=[y],
                    size=12,
                    pen=pg.mkPen(None),
                    brush=pg.mkBrush(244, 67, 54, 220),
                    symbol="o",
                )
                self._add_item(marker)
                self.labels.append(marker)

                # Retracement: 2 nokta
                if self.mode == "retracement" and len(self.points) == 2:
                    y1 = self.points[0][1]
                    y2 = self.points[1][1]
                    start_y = min(y1, y2)
                    end_y = max(y1, y2)
                    self.draw_retracement(start_y, end_y)
                    self.deactivate()

                # Extension: 3 nokta
                elif self.mode == "extension" and len(self.points) == 3:
                    y1 = self.points[0][1]  # Trend başlangıcı
                    y2 = self.points[1][1]  # Trend sonu (pivot high/low)
                    y3 = self.points[2][1]  # Geri çekilme sonu (yeni pivot)
                    self.draw_extension(y1, y2, y3)
                    self.deactivate()

    def draw_retracement(self, start_y, end_y):
        """Fibonacci Retracement çiz"""
        self.clear()
        diff = end_y - start_y

        for level, color, name in zip(
            FIBONACCI_RETRACEMENT_LEVELS,
            FIBONACCI_RETRACEMENT_COLORS,
            FIBONACCI_RETRACEMENT_NAMES,
        ):
            price = start_y + (diff * level)

            # Çizgi
            line = pg.InfiniteLine(
                angle=0, pos=price, pen=pg.mkPen(color, width=2.5, style=Qt.DashLine)
            )
            self._add_item(line)
            self.lines.append(line)

            # Etiket
            label_text = f"  FIB {name} = {price:.2f}"
            if name == "61.8%":
                label_text += " ⭐ Golden Ratio"
            elif name == "50%":
                label_text += " 🎯 Orta Nokta"

            label = pg.TextItem(
                text=label_text,
                anchor=(0, 0.5),
                color="k",
                fill=pg.mkBrush(color + "90"),
                border=pg.mkPen(color, width=2),
            )
            font = QFont()
            font.setPointSize(11)
            font.setBold(True)
            label.setFont(font)
            label.setPos(0, price)

            self._add_item(label)
            self.labels.append(label)

    def draw_extension(self, y1, y2, y3):
        """
        Fibonacci Extension çiz (3 nokta)
        y1: Trend başlangıcı
        y2: Trend sonu (pivot)
        y3: Geri çekilme sonu (yeni pivot)
        """
        self.clear()

        # Baz hareket (trend)
        base_move = y2 - y1

        # Geri çekilme sonrası hedef seviyeleri
        # Extension, y3'ten itibaren hesaplanır
        for level, color, name in zip(
            FIBONACCI_EXTENSION_LEVELS,
            FIBONACCI_EXTENSION_COLORS,
            FIBONACCI_EXTENSION_NAMES,
        ):
            # y3'ten başlayarak trend yönünde uzat
            if base_move > 0:  # Yükseliş trendi
                price = y3 + (base_move * level)
            else:  # Düşüş trendi
                price = y3 + (base_move * level)

            # Çizgi
            line = pg.InfiniteLine(
                angle=0, pos=price, pen=pg.mkPen(color, width=2.5, style=Qt.SolidLine)
            )
            self._add_item(line)
            self.lines.append(line)

            # Etiket
            label_text = f"  EXT {name} = {price:.2f}"
            if name == "161.8%":
                label_text += " ⭐ Golden Extension"
            elif name == "100%":
                label_text += " 🎯 Tam Uzatma"

            label = pg.TextItem(
                text=label_text,
                anchor=(0, 0.5),
                color="k",
                fill=pg.mkBrush(color + "90"),
                border=pg.mkPen(color, width=2),
            )
            font = QFont()
            font.setPointSize(10)
            font.setBold(True)
            label.setFont(font)
            label.setPos(0, price)

            self._add_item(label)
            self.labels.append(label)

    def clear(self):
        """Fibonacci çizimlerini temizle"""
        for line in self.lines:
            try:
                self.plot.removeItem(line)
            except Exception:
                pass
        for label in self.labels:
            try:
                self.plot.removeItem(label)
            except Exception:
                pass
        self.lines = []
        self.labels = []

    def is_visible(self):
        """Fibonacci çizgileri görünür mü?"""
        return len(self.lines) > 0
