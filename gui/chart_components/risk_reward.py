"""
Risk/Reward Tool - Pozisyon analiz aracı
"""

import pyqtgraph as pg
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtWidgets import QMessageBox


class RiskRewardTool:
    """
    Risk/Reward pozisyon analiz aracı
    - Entry, Stop-Loss, Target noktaları
    - Otomatik R/R oranı hesaplama
    - Long ve Short pozisyon desteği
    """

    def __init__(self, plot_widget, parent_dialog):
        self.plot = plot_widget
        self.parent = parent_dialog
        self.items = []
        self.is_active = False
        self.points = []
        self.proxy = None
        self.mode = "long"  # 'long' veya 'short'

    def activate(self, mode="long"):
        """R/R aracını aktifleştir"""
        self.mode = mode
        self.is_active = True
        self.points = []
        self.clear()

        self.proxy = pg.SignalProxy(
            self.plot.scene().sigMouseClicked, rateLimit=60, slot=self.on_click
        )

        position_type = "LONG (Alım)" if mode == "long" else "SHORT (Satım)"

        QMessageBox.information(
            self.parent,
            f"💰 Risk/Reward Aracı - {position_type}",
            f"📊 Pozisyon Tipi: {position_type}\n\n"
            "Grafik üzerinde 3 nokta seçin:\n\n"
            "1️⃣ GİRİŞ fiyatı (Entry)\n"
            "2️⃣ STOP-LOSS fiyatı\n"
            "3️⃣ HEDEF fiyatı (Take Profit)\n\n"
            "Risk/Reward oranı otomatik hesaplanacak.",
        )

    def on_click(self, evt):
        """Mouse tıklama olayını yakala"""
        if not self.is_active:
            return

        click_event = evt[0]
        if click_event.button() == Qt.LeftButton:
            pos = click_event.scenePos()
            if self.plot.sceneBoundingRect().contains(pos):
                mouse_point = self.plot.vb.mapSceneToView(pos)
                x, y = mouse_point.x(), mouse_point.y()

                self.points.append((x, y))

                # İşaretçi ekle
                colors = ["#2196F3", "#F44336", "#4CAF50"]
                labels = ["Entry", "Stop", "Target"]

                if len(self.points) <= 3:
                    marker = pg.ScatterPlotItem(
                        x=[x],
                        y=[y],
                        size=15,
                        pen=pg.mkPen(None),
                        brush=pg.mkBrush(QColor(colors[len(self.points) - 1])),
                        symbol="o",
                    )
                    self.plot.addItem(marker)
                    self.items.append(marker)

                    # Etiket
                    label = pg.TextItem(
                        text=labels[len(self.points) - 1],
                        anchor=(0.5, -0.5),
                        color="k",
                        fill=pg.mkBrush(colors[len(self.points) - 1]),
                    )
                    label.setPos(x, y)
                    self.plot.addItem(label)
                    self.items.append(label)

                # 3 nokta seçildi
                if len(self.points) == 3:
                    self.draw()
                    self.is_active = False
                    if self.proxy:
                        self.proxy.disconnect()

    def draw(self):
        """R/R görselleştirmesi çiz"""
        entry_x, entry_y = self.points[0]
        stop_x, stop_y = self.points[1]
        target_x, target_y = self.points[2]

        # Hesaplamalar
        risk = abs(entry_y - stop_y)
        reward = abs(target_y - entry_y)
        rr_ratio = reward / risk if risk > 0 else 0

        risk_pct = (risk / entry_y) * 100
        reward_pct = (reward / entry_y) * 100

        # Risk bölgesi (kırmızı şeffaf)
        risk_min = min(entry_y, stop_y)
        risk_max = max(entry_y, stop_y)

        risk_box = pg.QtWidgets.QGraphicsRectItem(
            0, risk_min, len(self.parent.df), risk_max - risk_min
        )
        risk_box.setPen(pg.mkPen(None))
        risk_box.setBrush(pg.mkBrush(244, 67, 54, 40))
        self.plot.addItem(risk_box)
        self.items.append(risk_box)

        # Reward bölgesi (yeşil şeffaf)
        reward_min = min(entry_y, target_y)
        reward_max = max(entry_y, target_y)

        reward_box = pg.QtWidgets.QGraphicsRectItem(
            0, reward_min, len(self.parent.df), reward_max - reward_min
        )
        reward_box.setPen(pg.mkPen(None))
        reward_box.setBrush(pg.mkBrush(76, 175, 80, 40))
        self.plot.addItem(reward_box)
        self.items.append(reward_box)

        # Yatay çizgiler
        for y, color, label in [
            (entry_y, "#2196F3", "Entry"),
            (stop_y, "#F44336", "Stop"),
            (target_y, "#4CAF50", "Target"),
        ]:
            line = pg.InfiniteLine(
                angle=0, pos=y, pen=pg.mkPen(color, width=2, style=Qt.DashLine)
            )
            self.plot.addItem(line)
            self.items.append(line)

        # R/R Bilgi Kartı
        rr_quality = (
            "🔥 Mükemmel"
            if rr_ratio >= 3
            else (
                "✅ İyi"
                if rr_ratio >= 2
                else "⚠️ Orta" if rr_ratio >= 1.5 else "❌ Zayıf"
            )
        )

        info_text = "💰 RISK/REWARD ANALİZİ\n\n"
        info_text += f"Giriş: {entry_y:.2f}\n"
        info_text += f"Stop: {stop_y:.2f}\n"
        info_text += f"Hedef: {target_y:.2f}\n\n"
        info_text += f"📊 Risk: {risk:.2f} ({risk_pct:.1f}%)\n"
        info_text += f"📈 Ödül: {reward:.2f} ({reward_pct:.1f}%)\n\n"
        info_text += f"⚖️ R/R Oranı: 1:{rr_ratio:.2f}\n"
        info_text += f"Kalite: {rr_quality}"

        info_label = pg.TextItem(
            text=info_text,
            anchor=(0, 0),
            color="k",
            fill=pg.mkBrush(255, 235, 59, 220),
            border=pg.mkPen("#FFC107", width=3),
        )
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        info_label.setFont(font)
        info_label.setPos(len(self.parent.df) * 0.6, entry_y)
        self.plot.addItem(info_label)
        self.items.append(info_label)

        # Dialog bilgilendirme
        advice = (
            "• R/R oranı 3:1 ve üzeri mükemmel!"
            if rr_ratio >= 3
            else (
                "• R/R oranı 2:1 ve üzeri kabul edilebilir."
                if 2 <= rr_ratio < 3
                else (
                    "• R/R oranı 1.5:1 altında riskli, pozisyon almayın!"
                    if rr_ratio < 1.5
                    else ""
                )
            )
        )

        QMessageBox.information(
            self.parent,
            "✅ Risk/Reward Hesaplandı",
            f"{info_text}\n\n" f"📌 Tavsiye:\n{advice}",
        )

    def clear(self):
        """Tüm R/R çizimlerini temizle"""
        for item in self.items:
            try:
                self.plot.removeItem(item)
            except Exception:
                pass
        self.items = []
        self.points = []
