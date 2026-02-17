# -*- coding: utf-8 -*-
"""
Price Ticker - Canlı Fiyat Bandı
Real-time fiyat gösterileri, durumu ve alertler
"""

import logging
import time
from typing import Dict
from datetime import datetime

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QScrollArea,
    QFrame,
)
from PyQt5.QtGui import QFont, QColor

logger = logging.getLogger(__name__)


class LivePriceTicker(QWidget):
    """Canlı fiyat bandı widget'ı"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.prices = {}
        self.is_connected = False
        self._last_refresh_time = 0
        self._refresh_interval_sec = 0.4  # En fazla 400ms'de bir UI güncelle (kilitlenme önleme)
        self.init_ui()
    
    def init_ui(self):
        """UI: yukarıdan aşağı akar, mouse tekerleği ile kaydırılabilir"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Üst satır: Bağlantı durumu
        status_row = QWidget()
        status_layout = QHBoxLayout(status_row)
        status_layout.setContentsMargins(0, 0, 0, 6)
        self.status_light = QLabel("●")
        self.status_light.setStyleSheet(
            "color: red; font-size: 14pt; font-weight: bold;"
        )
        self.status_light.setToolTip("WebSocket Bağlantı: Bağlı Değil")
        status_layout.addWidget(self.status_light)
        status_layout.addWidget(QLabel("Bağlantı durumu"))
        status_layout.addStretch()
        layout.addWidget(status_row)
        
        # Dikey kaydırılabilir alan (mouse tekerleği ile)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setFocusPolicy(Qt.StrongFocus)
        self.scroll_area.setStyleSheet(
            "QScrollArea { border: none; background: #f8f9fa; border-radius: 6px; }"
            "QScrollBar:vertical { width: 12px; border-radius: 6px; background: #e0e0e0; }"
            "QScrollBar::handle:vertical { min-height: 24px; border-radius: 6px; background: #b0b0b0; }"
            "QScrollBar::handle:vertical:hover { background: #909090; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
        )
        
        self.ticker_container = QWidget()
        self.ticker_layout = QVBoxLayout(self.ticker_container)
        self.ticker_layout.setContentsMargins(4, 4, 4, 4)
        self.ticker_layout.setSpacing(6)
        self.ticker_layout.setAlignment(Qt.AlignTop)
        
        self.scroll_area.setWidget(self.ticker_container)
        layout.addWidget(self.scroll_area, 1)
        
        # Başlangıç mesajı
        self.ticker_layout.addWidget(QLabel("Fiyat akışını başlat (tarama bittikten sonra veri gelir)..."))
        
        self.setLayout(layout)
        self.setStyleSheet(
            "QWidget { background-color: #f5f5f5; border: 1px solid #ddd; border-radius: 6px; padding: 6px; }"
        )
    
    def update_price(self, symbol: str, price: float, change_pct: float):
        """Fiyat güncellemesini göster (throttle: UI en fazla 400ms'de bir yenilenir)"""
        self.prices[symbol] = {
            'price': price,
            'change_pct': change_pct,
            'timestamp': datetime.now()
        }
        now = time.time()
        if now - self._last_refresh_time >= self._refresh_interval_sec:
            self._last_refresh_time = now
            self._refresh_ticker()
    
    def _refresh_ticker(self):
        """Ticker metnini yenile"""
        try:
            # Önceki widget'ların tümünü kaldır
            while self.ticker_layout.count() > 0:
                item = self.ticker_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            
            # Fiyat öğeleri ekle (yukarıdan aşağı)
            if not self.prices:
                self.ticker_layout.addWidget(QLabel("Fiyat verisi bekleniyor..."))
            else:
                for symbol, data in sorted(self.prices.items()):
                    price = data['price']
                    change = data['change_pct']
                    widget = self._create_price_item(symbol, price, change)
                    self.ticker_layout.addWidget(widget)
        
        except Exception as e:
            logger.error(f"Ticker refresh hatası: {e}")
    
    def _create_price_item(self, symbol: str, price: float, change_pct: float) -> QWidget:
        """Tek bir fiyat satırı (sembol | fiyat | değişim %)"""
        widget = QFrame()
        row = QHBoxLayout(widget)
        row.setContentsMargins(10, 6, 10, 6)
        row.setSpacing(12)
        
        symbol_label = QLabel(symbol)
        symbol_label.setFont(QFont("Arial", 10, QFont.Bold))
        symbol_label.setMinimumWidth(52)
        row.addWidget(symbol_label)
        
        price_label = QLabel(f"₺{price:.2f}")
        price_label.setFont(QFont("Arial", 10))
        row.addWidget(price_label)
        
        change_label = QLabel(f"{change_pct:+.2f}%")
        if change_pct >= 0:
            change_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        else:
            change_label.setStyleSheet("color: #F44336; font-weight: bold;")
        row.addWidget(change_label)
        row.addStretch()
        
        widget.setStyleSheet(
            "QFrame { background-color: white; border: 1px solid #e0e0e0; border-radius: 4px; }"
        )
        return widget
    
    def set_connection_status(self, connected: bool):
        """Bağlantı durumunu güncelle"""
        self.is_connected = connected
        
        if connected:
            self.status_light.setStyleSheet(
                "color: #4CAF50; "
                "font-size: 14pt; "
                "font-weight: bold; "
                "margin-right: 10px;"
            )
            self.status_light.setToolTip("🟢 WebSocket Bağlı")
            logger.info("🟢 Price Ticker: Bağlı")
        else:
            self.status_light.setStyleSheet(
                "color: #F44336; "
                "font-size: 14pt; "
                "font-weight: bold; "
                "margin-right: 10px;"
            )
            self.status_light.setToolTip("🔴 WebSocket Bağlı Değil")
            logger.warning("🔴 Price Ticker: Bağlantı yok")
    
    def clear_prices(self):
        """Tüm fiyatları temizle"""
        self.prices.clear()
        self._refresh_ticker()
